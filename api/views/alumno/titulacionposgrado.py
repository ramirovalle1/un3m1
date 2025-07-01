# coding=utf-8
import io
import tempfile

from _decimal import Decimal
from datetime import datetime

from django.core.files import File
from django.core.files.base import ContentFile
from django.db.models import Q
from django.http import JsonResponse
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from django.db.models.functions import Concat
from django.db.models import Sum, Q, F,Avg,Value
from api.serializers.alumno.titulacionposgrado import TemaTitulacionPosgradoMatriculaSerializar, \
    TemaTitulacionPosgradoMatriculaHistorialSerializar, TemaTitulacionPosgradoMatriculaCabeceraSerializar, \
    ConfiguracionTitulacionPosgradoSerializer, ProfesorSerializer, EtapaTemaTitulacionPosgradoSerializer, \
    TutoriasTemaTitulacionPosgradoProfesorSerializer, HistorialFirmaActaAprobacionComplexivoSerializer, \
    CalificacionTitulacionPosgradoSerializer, TemaTitulacionPosgradoProfesorSerializer, \
    SolicitudTutorTemaHistorialSerializer, PersonaSerializer, CarreraSerializer, \
    InscripcionMallaSerializer, MecanismoTitulacionPosgradoSerializer, PropuestaSubLineaInvestigacionSerializer, \
    RevisionPropuestaComplexivoPosgradoSerializer, ArchivoRevisionPropuestaComplexivoPosgradoSerializer, \
    DetalleGrupoTitulacionPostgradoSerializer, GrupoTitulacionPostgradoSerializer, \
    ProgramaEtapaTutoriaPosgradoSerializer, ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer, \
    SolicitudProrrogaIngresoTemaMatriculaSerializer, HistorialSolicitudProrrogaIngresoTemaMatriculaSerializer, \
    RevisionSerializer, MecanismoTitulacionPosgradoMallaSerializer, SolicitudIngresoTitulacionPosgradoSerializer, \
    EncuestaTitulacionPosgradoSerializer, InscripcionEncuestaTitulacionPosgradoSerializer
from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from posgrado.models import SolicitudProrrogaIngresoTemaMatricula, HistorialSolicitudProrrogaIngresoTemaMatricula, \
    Revision, Informe, HistorialDocRevisionTribunal, SolicitudIngresoTitulacionPosgrado, ConfiguraInformePrograma, \
    InscripcionEncuestaTitulacionPosgrado, EncuestaTitulacionPosgrado, JornadaSedeEncuestaTitulacionPosgrado, \
    RespuestaSedeInscripcionEncuesta
from sagest.models import PersonaDepartamentoFirmas
from sga.funciones_templatepdf import actaaprobacionexamencomplexivoposgrado, \
    actaaprobacionexamencomplexivoposgrado_svelte
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavesilabo, conviert_html_to_pdfsavepracticas, \
    conviert_html_to_pdf_save_file_model
import os
import random
from django.db import connection, transaction, connections
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.aulavirtual import MatriculaMateriaAsignadaSerializer, MatriculaSerializer, \
    MatriculaMateriaSerializer, MallaSerializer, PeriodoSerializer, \
    CompaMateriaAsignadaSerializer, LibroKohaProgramaAnaliticoAsignaturaSerializer, Silabo_2_Serializar, \
    GPGuiaPracticaSemanal_Serializar, AvComunicacionSerializer, AvPreguntaDocenteSerializer
from certi.models import CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora, Certificado
from sga.funciones import null_to_decimal, variable_valor, log, generar_nombre, remover_caracteres_tildes_unicode, \
    remover_caracteres_especiales_unicode
from sga.models import Noticia, Inscripcion, PerfilUsuario, MateriaAsignada, InscripcionMalla, \
    AsignaturaMalla, Materia, \
    PeriodoGrupoSocioEconomico, Inscripcion, PerdidaGratuidad, AuditoriaNotas, AgregacionEliminacionMaterias, Silabo, \
    Periodo, DetalleSilaboSemanalBibliografiaDocente, TemaTitulacionPosgradoMatricula, \
    LibroKohaProgramaAnaliticoAsignatura, GPGuiaPracticaSemanal, Persona, AvComunicacion, AvPreguntaDocente, \
    TemaTitulacionPosgradoMatriculaHistorial, ConfiguracionTitulacionPosgrado, Periodo, \
    TemaTitulacionPosgradoMatriculaCabecera, RevisionTutoriasTemaTitulacionPosgradoProfesor, \
    RevisionPropuestaComplexivoPosgrado, TIPO_ARCHIVO_COMPLEXIVO_PROPUESTA, EtapaTemaTitulacionPosgrado, \
    TemaTitulacionPosgradoProfesor, SolicitudTutorTemaHistorial, Profesor, MecanismoTitulacionPosgrado, \
    PropuestaSubLineaInvestigacion, Matricula, ArchivoRevisionPropuestaComplexivoPosgrado, TIPO_ARCHIVO_PORSGRADO, \
    DetalleGrupoTitulacionPostgrado, GrupoTitulacionPostgrado, HistorialFirmaActaAprobacionComplexivo, \
    TemaTitulacionPosArchivoFinal, TutoriasTemaTitulacionPosgradoProfesor, \
    ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor, MecanismoTitulacionPosgradoMalla
from sga.templatetags.sga_extras import encrypt
from django.template import Context
from django.template.loader import get_template
from settings import DEBUG, NOTA_ESTADO_EN_CURSO, USA_PLANIFICACION, SITE_STORAGE
from moodle import moodle
from django.shortcuts import render, redirect
from api.helpers.functions_helper import get_variable
import json

import os

from tempfile import NamedTemporaryFile


def add_propuesta_individual(eRequest,request,eFiles,matricula,eInscripcion):
    if not TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=matricula).exists():
        if int(eRequest['mecanismotitulacionposgrado']) in [15,21]:
            tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula(matricula=matricula,
                                                                              sublinea=None,
                                                                              mecanismotitulacionposgrado_id=int(
                                                                                  eRequest['mecanismotitulacionposgrado']),
                                                                              propuestatema=eRequest['propuestatema'],
                                                                              convocatoria_id=int(eRequest['convocatoria']),
                                                                              variabledependiente=" ",
                                                                              tutor=None,
                                                                              moduloreferencia=eRequest['moduloreferencia']
                                                                              )
        else:
            tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula(matricula=matricula,
                                                                              sublinea_id=int(eRequest['sublinea']),
                                                                              mecanismotitulacionposgrado_id=int(
                                                                                  eRequest['mecanismotitulacionposgrado']),
                                                                              propuestatema=eRequest['propuestatema'],
                                                                              convocatoria_id=int(eRequest['convocatoria']),
                                                                              variabledependiente=eRequest['variabledependiente'],
                                                                              variableindependiente=eRequest['variableindependiente'],
                                                                              tutor=None)
        tematitulacionposgradomatricula.save(request)
        if 'archivo' in eFiles:
            newfile = eFiles['archivo']
            newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
            tematitulacionposgradomatricula.archivo = newfile
        tematitulacionposgradomatricula.save(request)
        # Guardar Historial
        tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoMatriculaHistorial(
            tematitulacionposgradomatricula=tematitulacionposgradomatricula,
            observacion='NINGUNA',
            estado=1)
        tematitulacionposgradomatriculahistorial.save(request)
        log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatricula, request, "add")
    else:
        raise NameError("Ya se encuentra registrada su solicitud.")

def add_propuesta_pareja(eRequest,request,eFiles,matricula,eInscripcion):
    if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=int(eRequest['companero'])).exists():
        teamanteriorcompaniero = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=int(eRequest['companero']))[0]
        raise NameError(u"El compañero que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (
            teamanteriorcompaniero.propuestatema, teamanteriorcompaniero.mecanismotitulacionposgrado))
    if int(eRequest['companero']) == matricula.pk:
        raise NameError(u"No puede seleccionarse usted mismo")

    cabecera = TemaTitulacionPosgradoMatriculaCabecera(
        mecanismotitulacionposgrado_id=int(eRequest['mecanismotitulacionposgrado']),
        convocatoria_id=int(eRequest['convocatoria']),
        propuestatema=eRequest['propuestatema'],
        tutor=None,
        variabledependiente=eRequest['variabledependiente'],
        variableindependiente=eRequest['variableindependiente'])

    cabecera.save(request)
    if eRequest['sublinea'] == 'undefined':
        cabecera.sublinea = None
    else:
        cabecera.sublinea_id = int(eRequest['sublinea'])
    cabecera.save(request)

    # guardar las dos parejas

    if int(eRequest['mecanismotitulacionposgrado']) in [15,21]:  # por examen complexivo
        tematitulacionposgradomatriculaestudiante1 = TemaTitulacionPosgradoMatricula(matricula=matricula,
                                                                                     sublinea=None,
                                                                                     mecanismotitulacionposgrado_id=int(
                                                                                         eRequest['mecanismotitulacionposgrado']),
                                                                                     propuestatema=eRequest['propuestatema'],
                                                                                     convocatoria_id=int(eRequest['convocatoria']),
                                                                                     variabledependiente=" ",
                                                                                     variableindependiente=" ",
                                                                                     tutor=None,
                                                                                     moduloreferencia=eRequest['moduloreferencia'],
                                                                                     cabeceratitulacionposgrado=cabecera
                                                                                     )
        tematitulacionposgradomatriculaestudiante2 = TemaTitulacionPosgradoMatricula(
            matricula_id=int(eRequest['companero']),
            sublinea=None,
            mecanismotitulacionposgrado_id=int(eRequest['mecanismotitulacionposgrado']),
            propuestatema=eRequest['propuestatema'],
            convocatoria_id=int(eRequest['convocatoria']),
            variabledependiente=" ",
            variableindependiente=" ",
            tutor=None,
            moduloreferencia=eRequest['moduloreferencia'],
            cabeceratitulacionposgrado=cabecera
        )
    else:  # por proyecto de investigacion y desarrollo u otros
        tematitulacionposgradomatriculaestudiante1 = TemaTitulacionPosgradoMatricula(
            matricula=matricula,
            sublinea_id=int(eRequest['sublinea']),
            mecanismotitulacionposgrado_id=int(eRequest['mecanismotitulacionposgrado']),
            propuestatema=eRequest['propuestatema'],
            convocatoria_id=int(eRequest['convocatoria']),
            variabledependiente=eRequest['variabledependiente'],
            variableindependiente=eRequest['variableindependiente'],
            tutor=None,
            cabeceratitulacionposgrado=cabecera
        )
        tematitulacionposgradomatriculaestudiante2 = TemaTitulacionPosgradoMatricula(
            matricula_id=int(eRequest['companero']),
            sublinea_id=int(eRequest['sublinea']),
            mecanismotitulacionposgrado_id=int(eRequest['mecanismotitulacionposgrado']),
            propuestatema=eRequest['propuestatema'],
            convocatoria_id=int(eRequest['convocatoria']),
            variabledependiente=eRequest['variabledependiente'],
            variableindependiente=eRequest['variableindependiente'],
            tutor=None,
            cabeceratitulacionposgrado=cabecera
        )
    tematitulacionposgradomatriculaestudiante1.save(request)
    tematitulacionposgradomatriculaestudiante2.save(request)

    if 'archivo' in request.FILES:
        newfile = request.FILES['archivo']
        newfile2 = request.FILES['archivo']
        newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
        tematitulacionposgradomatriculaestudiante1.archivo = newfile

        newfile2._name = generar_nombre(str(tematitulacionposgradomatriculaestudiante2.matricula.inscripcion.persona.id), newfile2._name)
        tematitulacionposgradomatriculaestudiante2.archivo = newfile2

    tematitulacionposgradomatriculaestudiante1.save(request)
    tematitulacionposgradomatriculaestudiante2.save(request)
    # Guaddar Historial estudiante 1
    tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(
        tematitulacionposgradomatricula=tematitulacionposgradomatriculaestudiante1,
        observacion='NINGUNA',
        estado=1)
    # Guardar Historial estudiante 2
    tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
        tematitulacionposgradomatricula=tematitulacionposgradomatriculaestudiante2,
        observacion='NINGUNA',
        estado=1)

    tematitulacionposgradomatriculahistorialestudiante1.save(request)

    log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatriculahistorialestudiante1, request, "add")
    tematitulacionposgradomatriculahistorialestudiante2.save(request)

    log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatriculahistorialestudiante2, request, "add")

def add_propuesta_grupal(eRequest,request,eFiles,matricula,eInscripcion):
    integrantes_matricula_id = tuple(json.loads(eRequest['selectCompaneroMultiples']))
    if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id__in=integrantes_matricula_id).exists():
        companiero = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id__in=integrantes_matricula_id)[0]
        raise NameError(u"El integrante del grupo que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (companiero.propuestatema, companiero.mecanismotitulacionposgrado))
    if matricula.pk in tuple(json.loads(eRequest['selectCompaneroMultiples']))  :
        raise NameError(u"No puede seleccionarse usted mismo")

    integrantes_matricula_id = integrantes_matricula_id + (matricula.pk,)

    cabecera = TemaTitulacionPosgradoMatriculaCabecera(
        mecanismotitulacionposgrado_id=int(eRequest['mecanismotitulacionposgrado']),
        convocatoria_id=int(eRequest['convocatoria']),
        propuestatema=eRequest['propuestatema'],
        tutor=None,
        variabledependiente=eRequest['variabledependiente'],
        variableindependiente=eRequest['variableindependiente'])

    cabecera.save(request)
    if eRequest['sublinea'] == 'undefined':
        cabecera.sublinea = None
    else:
        cabecera.sublinea_id = int(eRequest['sublinea'])
    cabecera.save(request)

    for matricula_id in integrantes_matricula_id:
        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula(
            matricula_id=matricula_id,
            sublinea_id=int(eRequest['sublinea']),
            mecanismotitulacionposgrado_id=int(eRequest['mecanismotitulacionposgrado']),
            propuestatema=eRequest['propuestatema'],
            convocatoria_id=int(eRequest['convocatoria']),
            variabledependiente=eRequest['variabledependiente'],
            variableindependiente=eRequest['variableindependiente'],
            tutor=None,
            cabeceratitulacionposgrado=cabecera
        )
        eTemaTitulacionPosgradoMatricula.save(request)

        if 'archivo' in eFiles:
            newfile = eFiles['archivo']
            newfile._name = generar_nombre(str(cabecera.pk), newfile._name)
            eTemaTitulacionPosgradoMatricula.archivo = newfile
            eTemaTitulacionPosgradoMatricula.save(request)
            # Guardar Historial estudiante
        eTemaTitulacionPosgradoMatriculaHistorial = TemaTitulacionPosgradoMatriculaHistorial(
            tematitulacionposgradomatricula=eTemaTitulacionPosgradoMatricula,
            observacion='NINGUNA',
            estado=1)
        eTemaTitulacionPosgradoMatriculaHistorial.save(request)
        log(u'Adiciono Tema Titulación PosGrado grupal: %s' % eTemaTitulacionPosgradoMatriculaHistorial, request, "add")


def add_propuesta(eRequest, request, eFiles, matricula, eInscripcion):
    hoy = datetime.now()
    if 'archivo' in eFiles:
        arch = eFiles['archivo']
        extension = arch._name.split('.')
        tam = len(extension)
        exte = extension[tam - 1]
        if arch.size > 10485760:
            raise NameError(u"Error, el tamaño del archivo es mayor a 10 Mb.")
        if not exte.lower() == 'pdf':
            raise NameError(u"Solo se permiten archivos .pdf")

    if 'pareja' in eRequest and eRequest['pareja'] == 'on':  # si hace en pareja
        add_propuesta_pareja(eRequest, request, eFiles, matricula, eInscripcion)

    elif 'grupal' in eRequest and eRequest['grupal'] == 'on':
        add_propuesta_grupal(eRequest, request, eFiles, matricula, eInscripcion)
    else:  # individual
        add_propuesta_individual(eRequest, request, eFiles, matricula, eInscripcion)


class TemaTitulacionPosgradoAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_TEMA_TITULACION_POSGRADO'

    def post(self, request):
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar a la información.')
        eInscripcion = ePerfilUsuario.inscripcion
        ePersona = eInscripcion.persona
        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
        matricula = eInscripcion.matricula_periodo(periodo)

        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        action = eRequest['action']

        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            if action == 'addPropuestaTitulacion':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        add_propuesta(eRequest, request, eFiles, matricula, eInscripcion)
                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'editPropuestaTitulacion':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        if 'archivo' in eFiles:
                            arch = eFiles['archivo']
                            extension = arch._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if arch.size > 10485760:
                                raise NameError("Error, el tamaño del archivo es mayor a 10 Mb.")
                            if not exte.lower() == 'pdf':
                               raise NameError( u"Solo se permiten archivos .pdf")


                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id, status =True)
                        if 'pareja' in eRequest and eRequest['pareja'] == 'on': #es en pareja
                            maestrante_actual = tema
                            companiero = None
                            nuevo_companiero = None

                            if maestrante_actual.cabeceratitulacionposgrado:#si tiene companiero
                                companiero = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=maestrante_actual.cabeceratitulacionposgrado, status=True).exclude(id=maestrante_actual.pk)

                            if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=int(eRequest['companero'])).exists():
                                nuevo_companiero = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=int(eRequest['companero']))[0]


                            if companiero:
                                if nuevo_companiero:
                                    if not nuevo_companiero.pk == companiero[0].pk:
                                        if nuevo_companiero:
                                           raise NameError(u"El compañero que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                 nuevo_companiero.propuestatema,
                                                                 nuevo_companiero.mecanismotitulacionposgrado))


                                        if nuevo_companiero:
                                            if maestrante_actual.pk == nuevo_companiero.pk:
                                                raise NameError( u"usted ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                             maestrante_actual.propuestatema,
                                                                             maestrante_actual.mecanismotitulacionposgrado))

                            else:
                                if nuevo_companiero:
                                    if maestrante_actual.pk == nuevo_companiero.pk:
                                       raise NameError( u"usted ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                 maestrante_actual.propuestatema,
                                                                 maestrante_actual.mecanismotitulacionposgrado))
                                    else:
                                        if nuevo_companiero:
                                           raise NameError( u"El compañero que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                     nuevo_companiero.propuestatema,
                                                                     nuevo_companiero.mecanismotitulacionposgrado))

                            if tema.cabeceratitulacionposgrado:#si tiene pareja


                                tema.sublinea_id = int(eRequest['sublinea'])
                                tema.mecanismotitulacionposgrado_id = int(eRequest['mecanismotitulacionposgrado'])
                                tema.propuestatema = eRequest['propuestatema']
                                tema.variabledependiente = eRequest['variabledependiente']
                                tema.variableindependiente = eRequest['variableindependiente']
                                tema.convocatoria_id = int(eRequest['convocatoria'])

                                if int(eRequest['mecanismotitulacionposgrado']) in  [15,21]:  # examen omplexivo
                                    tema.moduloreferencia = eRequest['moduloreferencia']
                                    tema.variabledependiente = ""
                                    tema.variableindependiente = ""

                                else:  # proyecto desarrollo e investigacion
                                    tema.moduloreferencia = ""
                                tema.save(request)
                                if 'archivo' in eFiles:
                                    newfile = eFiles['archivo']
                                    newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
                                    # newfile._name = generar_nombre(inscripcion.persona.nombre_completo_inverso(), newfile._name)
                                    tema.archivo = newfile
                                tema.save(request)

                                #edito la cabecera
                                cabecera  = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk = tema.cabeceratitulacionposgrado.pk, status = True)
                                cabecera.sublinea = tema.sublinea
                                cabecera.mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado
                                cabecera.convocatoria = tema.convocatoria
                                cabecera.propuestatema = tema.propuestatema
                                cabecera.tutor = None
                                cabecera.variabledependiente = tema.variabledependiente
                                cabecera.variableindependiente = tema.variableindependiente
                                cabecera.save(request)



                                #asigno nuevo companero
                                # copio lo mismo para el integrante 2

                                # si cambia de pareja
                                maestrante_actual = tema
                                companiero = None
                                nuevo_companiero = None

                                if maestrante_actual.cabeceratitulacionposgrado:  # si tiene companiero
                                    companiero = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=maestrante_actual.cabeceratitulacionposgrado,status=True).exclude(id=maestrante_actual.pk)

                                if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=int(eRequest['companero'])).exists():
                                    nuevo_companiero = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id= int(eRequest['companero']))[0]

                                if companiero:
                                    if nuevo_companiero:
                                        if not nuevo_companiero.pk == companiero[0].pk:
                                            for com in companiero:
                                                com.status = False
                                                com.save(request)

                                            matriculaestudiante2 = TemaTitulacionPosgradoMatricula(
                                                matricula_id=int(eRequest['companero']),
                                                sublinea=tema.sublinea,
                                                mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                                propuestatema=tema.propuestatema,
                                                convocatoria=tema.convocatoria,
                                                variabledependiente=tema.variabledependiente,
                                                variableindependiente=tema.variableindependiente,
                                                tutor=None,
                                                moduloreferencia=tema.moduloreferencia,
                                                cabeceratitulacionposgrado=cabecera,
                                                archivo=tema.archivo,

                                            )
                                            matriculaestudiante2.save(request)
                                            # guardo el historial 1
                                            if not tema.get_ultimo_estado() == 1:
                                                tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(
                                                tematitulacionposgradomatricula=tema,
                                                observacion='NINGUNA',
                                                estado=1)
                                                tematitulacionposgradomatriculahistorialestudiante1.save(request)
                                                log(u'Edito Tema Titulación PosGrado Pareja: %s' % tematitulacionposgradomatriculahistorialestudiante1, request,"add")
                                                # guardo el historial del estudiante 2
                                            if not matriculaestudiante2.get_ultimo_estado() == 1:
                                                tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                                    tematitulacionposgradomatricula=matriculaestudiante2,
                                                    observacion='NINGUNA',
                                                    estado=1)
                                                tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                                log(u'Modifico compañero de titulación: compañero actual: %s' % matriculaestudiante2, request,
                                                    "add")
                                        else:
                                                companiero[0].sublinea = tema.sublinea
                                                companiero[0].mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado
                                                companiero[0].propuestatema = tema.propuestatema
                                                companiero[0].convocatoria = tema.convocatoria
                                                companiero[0].variabledependiente = tema.variabledependiente
                                                companiero[0].variableindependiente = tema.variableindependiente
                                                companiero[0].tutor = None
                                                companiero[0].moduloreferencia = tema.moduloreferencia
                                                companiero[0].cabeceratitulacionposgrado = cabecera
                                                companiero[0].archivo = tema.archivo
                                                companiero[0].save(request)
                                                # guardo el historial 1
                                                if not maestrante_actual.get_ultimo_estado() == 1:
                                                    tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=maestrante_actual,observacion='NINGUNA',estado=1)
                                                    tematitulacionposgradomatriculahistorialestudiante1.save(request)
                                                    log(u'Edito Tema Titulación PosGrado pareja: %s' % tematitulacionposgradomatriculahistorialestudiante1,request, "add")

                                                # guardo el historial del estudiante 2
                                                if not companiero[0].get_ultimo_estado() == 1:
                                                    tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=companiero[0], observacion='NINGUNA',estado=1)
                                                    tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                                    log(u'Edito compañero de titulación posgrado pareja: compañero actual: %s' % tematitulacionposgradomatriculahistorialestudiante2, request,"add")


                            else: #si no tiene es indivudual y quiere en pareja
                                tema.sublinea_id = int(eRequest['sublinea'])#edito la info
                                tema.mecanismotitulacionposgrado_id = int(eRequest['mecanismotitulacionposgrado'])
                                tema.propuestatema = eRequest['propuestatema']
                                tema.variabledependiente = eRequest['variabledependiente']
                                tema.variableindependiente = eRequest['variableindependiente']
                                tema.convocatoria_id = int(eRequest['convocatoria'])
                                if int(eRequest['mecanismotitulacionposgrado']) in [15,21]:  # examen omplexivo
                                    tema.moduloreferencia = eRequest['moduloreferencia']
                                    tema.variabledependiente = " "
                                    tema.variableindependiente = " "

                                else:  # proyecto desarrollo e investigacion
                                    tema.moduloreferencia = ""
                                tema.save(request)
                                if 'archivo' in eFiles:
                                    newfile = eFiles['archivo']
                                    newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
                                    # newfile._name = generar_nombre(inscripcion.persona.nombre_completo_inverso(), newfile._name)
                                    tema.archivo = newfile
                                tema.save(request)

                                #creoo la cabecera

                                if not TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True,
                                    sublinea=tema.sublinea,
                                    mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                    convocatoria=tema.convocatoria,
                                    propuestatema=tema.propuestatema).exists():


                                    cabecera = TemaTitulacionPosgradoMatriculaCabecera(
                                        sublinea=tema.sublinea,
                                        mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                        convocatoria=tema.convocatoria,
                                        propuestatema=tema.propuestatema,
                                        tutor=None,
                                        variabledependiente=tema.variabledependiente,
                                        variableindependiente=tema.variableindependiente)

                                    cabecera.save(request)
                                else:
                                    cabecera=TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True,
                                                                                           sublinea=tema.sublinea,
                                                                                           mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                                                                           convocatoria=tema.convocatoria,
                                                                                           propuestatema=tema.propuestatema)[0]
                                # asigno las parejas las dos parejas
                                tema.cabeceratitulacionposgrado = cabecera#integrante 1
                                tema.save(request)
                                #copio lo mismo para el integrante 2
                                matriculaestudiante2 = TemaTitulacionPosgradoMatricula(
                                    matricula_id=int(eRequest['companero']),
                                    sublinea=tema.sublinea,
                                    mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                    propuestatema=tema.propuestatema,
                                    convocatoria=tema.convocatoria,
                                    variabledependiente=tema.variabledependiente,
                                    variableindependiente=tema.variableindependiente,
                                    tutor=None,
                                    moduloreferencia=tema.moduloreferencia,
                                    cabeceratitulacionposgrado=cabecera,
                                    archivo=tema.archivo,

                                )
                                matriculaestudiante2.save(request)
                                # guardo el historial 1
                                if TemaTitulacionPosgradoMatriculaHistorial.objects.filter(tematitulacionposgradomatricula=tema, status=True,).exists():
                                    if not tema.get_ultimo_estado() == 1:
                                        tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(
                                            tematitulacionposgradomatricula=tema,
                                            observacion='NINGUNA',
                                            estado=1)
                                        tematitulacionposgradomatriculahistorialestudiante1.save(request)
                                        log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatriculahistorialestudiante1,
                                            request,
                                            "add")

                                # guardo el historial 2
                                if TemaTitulacionPosgradoMatriculaHistorial.objects.filter(tematitulacionposgradomatricula=matriculaestudiante2,status=True).exists():
                                    if not matriculaestudiante2.get_ultimo_estado() == 1:
                                        tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                            tematitulacionposgradomatricula=matriculaestudiante2,
                                            observacion='NINGUNA',
                                            estado=1)
                                        tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                        log(u'Adiciono Tema Titulación PosGrado: %s' % matriculaestudiante2,
                                            request,
                                            "add")
                                else:
                                    tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                        tematitulacionposgradomatricula=matriculaestudiante2,
                                        observacion='NINGUNA',
                                        estado=1)
                                    tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                    log(u'Adiciono Tema Titulación PosGrado: %s' % matriculaestudiante2,
                                        request,
                                        "add")

                        else:#individual check
                            tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id, status=True)
                            if tema.cabeceratitulacionposgrado:#si hizo en pareja pero ahora quiere individual
                                #eliminar companero y quitar
                                companero_anterior = TemaTitulacionPosgradoMatricula.objects.filter(
                                    cabeceratitulacionposgrado=tema.cabeceratitulacionposgrado, status=True).exclude(id=tema.pk)
                                for com in companero_anterior:
                                    com.status = False
                                    com.save(request)

                                id_cabecera = tema.cabeceratitulacionposgrado.pk
                                tema.cabeceratitulacionposgrado = None
                                tema.save(request)
                                # eliminar cabecera
                                cab = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(pk=id_cabecera, status = True)[0]
                                cab.status=False
                                cab.save(request)

                                log(u'Quito a su compañero de titulación, ahora va hacer individual: %s' % tema, request, "edit")
                            else:
                                # si se registra individual
                                if eRequest['sublinea'] == '0':
                                    tema.sublinea_id = None
                                else:
                                    tema.sublinea_id = int(eRequest['sublinea'])

                                tema.mecanismotitulacionposgrado_id = int(eRequest['mecanismotitulacionposgrado'])
                                tema.propuestatema = eRequest['propuestatema']
                                tema.variabledependiente = eRequest['variabledependiente']
                                tema.variableindependiente = eRequest['variableindependiente']
                                tema.convocatoria_id = int(eRequest['convocatoria'])
                                if int(eRequest['mecanismotitulacionposgrado']) in [15,21]: #examen omplexivo
                                   tema.moduloreferencia= eRequest['moduloreferencia']
                                   tema.variabledependiente = " "
                                   tema.variableindependiente = " "

                                else:#proyecto desarrollo e investigacion
                                    tema.moduloreferencia = ""
                                tema.save(request)
                                if 'archivo' in eFiles:
                                    newfile = eFiles['archivo']
                                    newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
                                    # newfile._name = generar_nombre(inscripcion.persona.nombre_completo_inverso(), newfile._name)
                                    tema.archivo = newfile
                                tema.save(request)
                                #Guaddar Historial
                                if TemaTitulacionPosgradoMatriculaHistorial.objects.filter(tematitulacionposgradomatricula=tema, status = True).exists():
                                    if not tema.get_ultimo_estado() == 1:
                                        tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=tema,
                                                                                                                            observacion = 'NINGUNA',
                                                                                                                            estado = 1)
                                        tematitulacionposgradomatriculahistorial.save(request)
                                        log(u'Modifico Tema Titulación PosGrado: %s' % tema, request, "edit")
                                else:
                                    tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoMatriculaHistorial(
                                        tematitulacionposgradomatricula=tema,
                                        observacion='NINGUNA',
                                        estado=1)
                                    tematitulacionposgradomatriculahistorial.save(request)
                                    log(u'Modifico Tema Titulación PosGrado: %s' % tema, request, "edit")




                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'addavancetutoriaposgrado':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        newfilep = None

                        id = int(eRequest['id_tutoria'])
                        if 'archivo' in eFiles:
                            newfilep = eFiles['archivo']
                            if newfilep:
                                if newfilep.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilep.size <= 0:
                                    raise NameError( u"Error, el archivo Propuesta Práctica esta vacío.")
                                else:
                                    newfilesd = newfilep._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilep._name = generar_nombre("avance_tutoria_", newfilep._name)
                                    elif ext == '.docx':
                                        newfilep._name = generar_nombre("avance_tutoria_", newfilep._name)

                                    elif ext == '.pdf':
                                        newfilep._name = generar_nombre("avance_tutoria_", newfilep._name)
                                    else:
                                        raise NameError(u"Error, archivo de Propuesta Práctica solo en .doc, docx. y .pdf")


                        if newfilep:
                            tutoria = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk = id)


                            revision_tutoria = RevisionTutoriasTemaTitulacionPosgradoProfesor()
                            revision_tutoria.tematitulacionposgradomatricula = tutoria.tematitulacionposgradomatricula
                            revision_tutoria.tematitulacionposgradomatriculacabecera = tutoria.tematitulacionposgradomatriculacabecera
                            revision_tutoria.tutoriatematitulacionposgradoprofesor = tutoria
                            revision_tutoria.save(request)

                            archivo_tutoria = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor()
                            archivo_tutoria.archivo = newfilep
                            archivo_tutoria.revisiontutoriastematitulacionposgradoprofesor = revision_tutoria
                            archivo_tutoria.fecha=datetime.now()
                            archivo_tutoria.tipo=6
                            archivo_tutoria.save(request)


                            log(u"Añade avance de  tutoria  %s de posgrado" % (archivo_tutoria), request, "add")

                        else:
                            raise NameError( u'Ingrese almenos un archivo')

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'addcorreccionrevisiontribunal':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        newfilep = None

                        id =  int(encrypt(eRequest['id_tema']))
                        es_pareja = json.loads(eRequest['es_pareja'])
                        if 'archivo' in eFiles:
                            newfilep = eFiles['archivo']
                            if newfilep:
                                if newfilep.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilep.size <= 0:
                                    raise NameError( u"Error, el archivo de corrección está vacío.")
                                else:
                                    newfilesd = newfilep._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilep._name = generar_nombre("correccion_documento_", newfilep._name)
                                    elif ext == '.docx':
                                        newfilep._name = generar_nombre("correccion_documento_", newfilep._name)

                                    elif ext == '.pdf':
                                        newfilep._name = generar_nombre("correccion_documento_", newfilep._name)
                                    else:
                                        raise NameError(u"Error, archivo de Propuesta Práctica solo en .doc, docx. y .pdf")


                        if newfilep:
                            if es_pareja:
                                subirarchivo = TemaTitulacionPosArchivoFinal(tematitulacionposgradomatriculacabecera_id=id)
                            else:
                                subirarchivo = TemaTitulacionPosArchivoFinal(tematitulacionposgradomatricula_id=id)

                            subirarchivo.save(request)

                            subirarchivo.archivo = newfilep
                            subirarchivo.estado = 1
                            subirarchivo.save(request)

                            log(u"Añade corrección revisión por tribunal  %s de posgrado" % (subirarchivo), request, "add")

                        else:
                            raise NameError( u'Ingrese almenos un archivo')

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'editdoccorreccionrevisiontribunal':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        newfilep = None
                        id =  int(eRequest['id'])
                        if 'archivo' in eFiles:
                            newfilep = eFiles['archivo']
                            if newfilep:
                                if newfilep.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilep.size <= 0:
                                    raise NameError( u"Error, el archivo de corrección está vacío.")
                                else:
                                    newfilesd = newfilep._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilep._name = generar_nombre("correccion_documento_", newfilep._name)
                                    elif ext == '.docx':
                                        newfilep._name = generar_nombre("correccion_documento_", newfilep._name)

                                    elif ext == '.pdf':
                                        newfilep._name = generar_nombre("correccion_documento_", newfilep._name)
                                    else:
                                        raise NameError(u"Error, archivo de Propuesta Práctica solo en .doc, docx. y .pdf")


                        if newfilep:
                            subirarchivo= TemaTitulacionPosArchivoFinal.objects.get(pk=id)
                            subirarchivo.archivo = newfilep
                            subirarchivo.save(request)

                            log(u"Edito doc correccion revisión por tribunal  %s de posgrado" % (subirarchivo), request, "add")

                        else:
                            raise NameError( u'Ingrese almenos un archivo')

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'adddocensayo':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        newfilep = None
                        newfilex = None
                        id = int(encrypt(eRequest['id']))
                        propuestatema = eRequest['tema']
                        moduloreferencia = eRequest['moduloreferencia']
                        if 'propuesta' in eFiles:
                            newfilep = eFiles['propuesta']
                            if newfilep:
                                if newfilep.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilep.size <= 0:
                                    raise NameError( u"Error, el archivo Propuesta Práctica esta vacío.")
                                else:
                                    newfilesd = newfilep._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                    elif ext == '.docx':
                                        newfilep._name = generar_nombre("propuesta_", newfilep._name)

                                    elif ext == '.pdf':
                                        newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                    else:
                                        raise NameError(u"Error, archivo de Propuesta Práctica solo en .doc, docx. y .pdf")

                        if 'extracto' in eFiles:
                            newfilex = eFiles['extracto']
                            if newfilex:
                                if newfilex.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilex.size <= 0:
                                    raise NameError(u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío.")
                                else:
                                    newfilesd = newfilex._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilex._name = generar_nombre("extracto_", newfilex._name)
                                    elif ext == '.docx':
                                        newfilex._name = generar_nombre("extracto_", newfilex._name)
                                    elif ext == '.pdf':
                                        newfilep._name = generar_nombre("extracto_", newfilep._name)
                                    else:
                                        raise NameError( u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx. y .pdf")

                        if newfilep:
                            es_pareja = json.loads(eRequest['es_pareja'])
                            if es_pareja == True:
                                grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                                cabecera = RevisionPropuestaComplexivoPosgrado(tematitulacionposgradomatriculacabecera=grupo, fecharevision=datetime.now())
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(revisionpropuestacomplexivoposgrado=cabecera, tipo=5,archivo=newfilep, fecha=datetime.now())
                                    propuesta.save(request)
                                    if newfilex:
                                        propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(revisionpropuestacomplexivoposgrado=cabecera, tipo=2,archivo=newfilex, fecha=datetime.now())
                                        propuesta.save(request)
                                        log(u"Añade archivo propuesta en pareja version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (grupo.id, grupo.propuestatema), request, "add")
                                    grupo.propuestatema = propuestatema
                                    grupo.save(request)
                                    for tema in grupo.obtener_parejas():
                                        tema.propuestatema = propuestatema
                                        tema.moduloreferencia = moduloreferencia
                                        tema.save(request)


                            else:
                                grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                                cabecera = RevisionPropuestaComplexivoPosgrado(tematitulacionposgradomatricula=grupo, fecharevision=datetime.now())
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(revisionpropuestacomplexivoposgrado=cabecera, tipo=5, archivo=newfilep,fecha=datetime.now())
                                    propuesta.save(request)
                                    if newfilex:
                                        propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(revisionpropuestacomplexivoposgrado=cabecera, tipo=2, archivo=newfilex,fecha=datetime.now())
                                        propuesta.save(request)
                                        log(u"Añade archivo propuesta version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (grupo.id, grupo.propuestatema), request, "add")
                                    grupo.moduloreferencia = moduloreferencia
                                    grupo.propuestatema = propuestatema
                                    grupo.save(request)
                        else:
                            raise NameError( u'Ingrese almenos un archivo')

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'firmar_solicitud_ingreso_titulacion':
                with transaction.atomic():
                    try:
                        firmadirector = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)
                        data = {}
                        hoy = datetime.now()
                        nombre_mes = lambda x:  ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
                        month, day = "%02d" % hoy.month, "%02d" % hoy.day
                        mes = "%s" % nombre_mes(int(hoy.strftime("%m")))
                        fecha_cabecera = f"{day} de {mes.lower()} del {hoy.year}"
                        eMecanismo = MecanismoTitulacionPosgrado.objects.get(pk=int(eRequest['mecanismo_id']))

                        firma = None
                        data['fecha_cabecera'] = fecha_cabecera
                        data['matricula'] = matricula
                        data['eMecanismo'] = eMecanismo
                        data['firmadirector'] = firmadirector

                        eSolicitudIngresoTitulacionPosgrado= SolicitudIngresoTitulacionPosgrado.objects.filter(status=True,matricula = matricula,firmado =True)
                        if not eSolicitudIngresoTitulacionPosgrado.exists():
                            if 'firma' in eFiles:
                                firma = eFiles['firma']

                                pdf_file, response = conviert_html_to_pdf_save_file_model( 'alu_tematitulacionposgrado/solicitudingreso.html',  {'pagesize': 'A4', 'data': data})
                                filename = generar_nombre(f'solicitud_ingreso_{matricula.inscripcion.persona.cedula}', 'titulacion') + ".pdf"
                                eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado(
                                    matricula=matricula,
                                    mecanismotitulacionposgrado_id=int(eRequest['mecanismo_id']),
                                    archivo=filename,
                                    firmado =True
                                )
                                eSolicitudIngresoTitulacionPosgrado.archivo.save(filename, pdf_file)
                                eSolicitudIngresoTitulacionPosgrado.save(request)
                            else:
                                raise NameError(u'Ingrese su firma')
                        else:
                            solicitud = eSolicitudIngresoTitulacionPosgrado.first()
                            if 'firma' in eFiles:
                                firma = eFiles['firma']

                                pdf_file, response = conviert_html_to_pdf_save_file_model( 'alu_tematitulacionposgrado/solicitudingreso.html',  {'pagesize': 'A4', 'data': data})
                                filename = generar_nombre(f'solicitud_ingreso_{matricula.inscripcion.persona.cedula}', 'titulacion') + ".pdf"
                                solicitud.mecanismotitulacionposgrado_id=int(eRequest['mecanismo_id'])
                                solicitud.archivo=filename
                                solicitud.firmado=True
                                solicitud.archivo.save(filename, pdf_file)
                                solicitud.save(request)
                            else:
                                raise NameError(u'Ingrese su firma')

                        try:
                            eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=matricula,firmado=True).first()
                            pdf = SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=matricula , firmado =True).first().archivo
                            palabras = u"%s" % eSolicitudIngresoTitulacionPosgrado.matricula.inscripcion.persona
                            firma = eFiles["firma"]
                            passfirma = eRequest['palabraclave']
                            bytes_certificado = firma.read()
                            extension_certificado = os.path.splitext(firma.name)[1][1:]
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                            datau = JavaFirmaEc(
                                archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                extension_certificado=extension_certificado,
                                password_certificado=passfirma,
                                page=int(numpaginafirma), reason='', lx=x + 190, ly=y - 300
                            ).sign_and_get_content_bytes()

                            documento_a_firmar = io.BytesIO()
                            documento_a_firmar.write(datau)
                            documento_a_firmar.seek(0)
                            eSolicitudIngresoTitulacionPosgrado.archivo.save(f'{eSolicitudIngresoTitulacionPosgrado.archivo.name.split("/")[-1].replace(".pdf", "")}_firmado.pdf',ContentFile(documento_a_firmar.read()))
                            nombrefile_ = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode(pdf.name)).replace('-', '_').replace('.pdf', '')

                        except Exception as ex:
                            raise NameError("Documento con inconsistencia en la firma,intenteo otra vez, revisé que sus credenciales sean las correctas.")



                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'subir_solicitud_ingreso_firmada':
                with transaction.atomic():
                    try:
                        if 'archivo' in eFiles:
                            newfile = eFiles['archivo']
                            newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
                            if newfile:
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    raise NameError(u"Error, el tamaño del archivo es mayor a 4 Mb.")
                                if exte in ['pdf', 'PDF']:
                                    newfile._name = generar_nombre("acta_firmada", newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    raise NameError(u"Error, solo archivos .pdf")

                                eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=matricula)
                                if  eSolicitudIngresoTitulacionPosgrado.exists():
                                    solicitud = eSolicitudIngresoTitulacionPosgrado.first()
                                    solicitud.archivo = newfile
                                    solicitud.firmado = True
                                    solicitud.save(request)
                                else:
                                    raise NameError(u"Error, solicitud no generada, genere la solicitud desde el sistema para  firmar por token")
                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'descargar_pdf_solicitud_ingreso_titulacion':
                with transaction.atomic():
                    try:
                        firmadirector = PersonaDepartamentoFirmas.objects.get(tipopersonadepartamento_id=1, departamentofirma_id=1, status=True, actualidad=True)
                        data = {}
                        hoy = datetime.now()
                        nombre_mes = lambda x:  ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"][int(x) - 1]
                        month, day = "%02d" % hoy.month, "%02d" % hoy.day
                        mes = "%s" % nombre_mes(int(hoy.strftime("%m")))
                        fecha_cabecera = f"{day} de {mes.lower()} del {hoy.year}"
                        eMecanismo = MecanismoTitulacionPosgrado.objects.get(pk=int(eRequest['mecanismo_id']))

                        firma = None
                        data['fecha_cabecera'] = fecha_cabecera
                        data['matricula'] = matricula
                        data['eMecanismo'] = eMecanismo
                        data['firmadirector'] = firmadirector

                        eSolicitudIngresoTitulacionPosgrado= SolicitudIngresoTitulacionPosgrado.objects.filter(status=True,matricula = matricula)
                        if not eSolicitudIngresoTitulacionPosgrado.exists():
                            pdf_file, response = conviert_html_to_pdf_save_file_model( 'alu_tematitulacionposgrado/solicitudingreso.html',  {'pagesize': 'A4', 'data': data})
                            filename = generar_nombre(f'solicitud_ingreso_{matricula.inscripcion.persona.cedula}', 'titulacion') + ".pdf"
                            eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado(
                                matricula=matricula,
                                mecanismotitulacionposgrado_id=int(eRequest['mecanismo_id']),
                                archivo=filename,
                                firmado =False
                            )
                            eSolicitudIngresoTitulacionPosgrado.archivo.save(filename, pdf_file)
                            eSolicitudIngresoTitulacionPosgrado.save(request)

                        else:
                            eSolicitudIngresoTitulacionPosgrado = eSolicitudIngresoTitulacionPosgrado.first()
                            pdf_file, response = conviert_html_to_pdf_save_file_model( 'alu_tematitulacionposgrado/solicitudingreso.html',  {'pagesize': 'A4', 'data': data})
                            filename = generar_nombre(f'solicitud_ingreso_{matricula.inscripcion.persona.cedula}', 'titulacion') + ".pdf"
                            eSolicitudIngresoTitulacionPosgrado.mecanismotitulacionposgrado_id=int(eRequest['mecanismo_id'])
                            eSolicitudIngresoTitulacionPosgrado.archivo=filename
                            eSolicitudIngresoTitulacionPosgrado.firmado=False
                            eSolicitudIngresoTitulacionPosgrado.archivo.save(filename, pdf_file)
                            eSolicitudIngresoTitulacionPosgrado.save(request)

                        aData = {
                            'file_url': eSolicitudIngresoTitulacionPosgrado.archivo.url,
                        }

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'adddocfinaltitulacionposgrado':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        newfilep = None
                        newfilex = None
                        id = int(encrypt(eRequest['id']))
                        id_tutoria = int(eRequest['id_tutoria'])

                        tutoria = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk = id_tutoria)

                        if 'propuesta' in eFiles:
                            newfilep = eFiles['propuesta']
                            if newfilep:
                                if newfilep.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilep.size <= 0:
                                    raise NameError(u"Error, el archivo Propuesta Práctica esta vacío.")
                                else:
                                    newfilesd = newfilep._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                    elif ext == '.docx':
                                        newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                    elif ext == '.pdf':
                                        newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                    else:
                                        raise NameError(
                                            u"Error, archivo de Propuesta Práctica solo en .doc, docx.")

                        if 'extracto' in eFiles:
                            newfilex = eFiles['extracto']
                            if newfilex:
                                if newfilex.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfilex.size <= 0:
                                    raise NameError(
                                        u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío.")
                                else:
                                    newfilesd = newfilex._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfilex._name = generar_nombre("extracto_", newfilex._name)
                                    elif ext == '.docx':
                                        newfilex._name = generar_nombre("extracto_", newfilex._name)

                                    elif ext == '.pdf':
                                        newfilex._name = generar_nombre("extracto_", newfilex._name)

                                    else:
                                        raise NameError(
                                            u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx.")

                        if newfilep and newfilex:
                            es_pareja = json.loads(eRequest['es_pareja'])
                            if es_pareja == True:
                                grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                                cabecera = RevisionTutoriasTemaTitulacionPosgradoProfesor( tematitulacionposgradomatriculacabecera=grupo, fecharevision=datetime.now(),tutoriatematitulacionposgradoprofesor =tutoria )
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor( revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=1, archivo=newfilep, fecha=datetime.now())
                                    propuesta.save(request)
                                if newfilex:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=2,  archivo=newfilex, fecha=datetime.now())
                                    propuesta.save(request)
                                log(u"Añade archivo propuesta en pareja version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (
                                    grupo.id, grupo.propuestatema), request, "add")
                            else:
                                grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                                cabecera = RevisionTutoriasTemaTitulacionPosgradoProfesor(tematitulacionposgradomatricula = grupo, fecharevision = datetime.now(),tutoriatematitulacionposgradoprofesor =tutoria)
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=1, archivo=newfilep, fecha=datetime.now())
                                propuesta.save(request)
                                if newfilex:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=2, archivo=newfilex, fecha=datetime.now())
                                propuesta.save(request)
                                log(u"Añade archivo propuesta version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (
                                grupo.id, grupo.propuestatema), request, "add")

                            aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'adddocumentofinaltitulacionpormecanismo':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()

                        newfileborrador = None
                        newfileaceptacion = None
                        newfileacompanamiento = None
                        id = int(encrypt(eRequest['id']))
                        id_tutoria = int(eRequest['id_tutoria'])
                        link_Revista = eRequest['linkrevista']
                        tutoria = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=id_tutoria)

                        if 'borrador_articulo' in eFiles:
                            newfileborrador = eFiles['borrador_articulo']
                            if newfileborrador:
                                if newfileborrador.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfileborrador.size <= 0:
                                    raise NameError(u"Error, el archivo Propuesta Práctica esta vacío.")
                                else:
                                    newfilesd = newfileborrador._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfileborrador._name = generar_nombre("borrador_articulo_", newfileborrador._name)
                                    elif ext == '.docx':
                                        newfileborrador._name = generar_nombre("borrador_articulo_", newfileborrador._name)
                                    elif ext == '.pdf':
                                        newfileborrador._name = generar_nombre("borrador_articulo_", newfileborrador._name)
                                    else:
                                        raise NameError(
                                            u"Error, archivo de borrador articulo solo en .doc, .docx, .pdf")

                        if 'carta_de_aceptacion' in eFiles:
                            newfileaceptacion = eFiles['carta_de_aceptacion']
                            if newfileaceptacion:
                                if newfileaceptacion.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfileaceptacion.size <= 0:
                                    raise NameError(
                                        u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío.")
                                else:
                                    newfilesd = newfileaceptacion._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfileaceptacion._name = generar_nombre("carta_de_aceptacion_", newfileaceptacion._name)
                                    elif ext == '.docx':
                                        newfileaceptacion._name = generar_nombre("carta_de_aceptacion_", newfileaceptacion._name)

                                    elif ext == '.pdf':
                                        newfileaceptacion._name = generar_nombre("carta_de_aceptacion_", newfileaceptacion._name)

                                    else:
                                        raise NameError(
                                            u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, .docx, .pdf")

                        if 'acta_de_acompanamieno' in eFiles:
                            newfileacompanamiento = eFiles['acta_de_acompanamieno']
                            if newfileacompanamiento:
                                if newfileacompanamiento.size > 203246208:
                                    raise NameError(u"Error, archivo mayor a 108 Mb.")
                                elif newfileacompanamiento.size <= 0:
                                    raise NameError(u"Error, el archivo Propuesta Práctica esta vacío.")
                                else:
                                    newfilesd = newfileacompanamiento._name
                                    ext = newfilesd[newfilesd.rfind("."):]
                                    if ext == '.doc':
                                        newfileacompanamiento._name = generar_nombre("acta_de_acompanamieno_",
                                                                               newfileacompanamiento._name)
                                    elif ext == '.docx':
                                        newfileacompanamiento._name = generar_nombre("acta_de_acompanamieno_",
                                                                               newfileacompanamiento._name)
                                    elif ext == '.pdf':
                                        newfileacompanamiento._name = generar_nombre("acta_de_acompanamieno_",
                                                                               newfileacompanamiento._name)
                                    else:
                                        raise NameError(  u"Error, archivo de borrador articulo solo en .doc, .docx, .pdf")

                        if newfileborrador and newfileaceptacion and newfileacompanamiento:
                            es_pareja = json.loads(eRequest['es_pareja'])
                            if es_pareja == True:
                                grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                                cabecera = RevisionTutoriasTemaTitulacionPosgradoProfesor( tematitulacionposgradomatriculacabecera=grupo, fecharevision=datetime.now(),tutoriatematitulacionposgradoprofesor =tutoria , linkrevista = link_Revista)
                                cabecera.save(request)
                                if newfileborrador:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor( revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=7, archivo=newfileborrador, fecha=datetime.now())
                                    propuesta.save(request)
                                if newfileaceptacion:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=8,  archivo=newfileaceptacion, fecha=datetime.now())
                                    propuesta.save(request)
                                if newfileacompanamiento:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor( revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=9,  archivo=newfileacompanamiento, fecha=datetime.now())
                                    propuesta.save(request)

                                log(u"Añade archivos propuesta en pareja version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % ( grupo.id, grupo.propuestatema), request, "add")
                            else:
                                grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                                cabecera = RevisionTutoriasTemaTitulacionPosgradoProfesor(tematitulacionposgradomatricula = grupo, fecharevision = datetime.now(),tutoriatematitulacionposgradoprofesor =tutoria, linkrevista = link_Revista)
                                cabecera.save(request)
                                if newfileborrador:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=7, archivo=newfileborrador, fecha=datetime.now())
                                propuesta.save(request)

                                if newfileaceptacion:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=8, archivo=newfileaceptacion, fecha=datetime.now())
                                propuesta.save(request)

                                if newfileacompanamiento:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=9, archivo=newfileacompanamiento, fecha=datetime.now())
                                propuesta.save(request)

                                log(u"Añade archivos propuesta version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (
                                grupo.id, grupo.propuestatema), request, "add")

                            aData = {}


                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'editdocensayo':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        archivo = ArchivoRevisionPropuestaComplexivoPosgrado.objects.get(pk=id)
                        if 'archivo' in eFiles:
                            newfile = eFiles['archivo']
                            if archivo.tipo == 5:
                                nombre = "propuesta_ensayo"
                            else:
                                nombre = "propuesta_ensayo"
                            newfile._name = generar_nombre(nombre, newfile._name)
                            archivo.archivo = newfile
                            archivo.fecha = datetime.now()
                            archivo.save(request)
                            if archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatricula:
                                vista_grupo = archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatricula.id
                                vista_revision_grupo = archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatricula.propuestatema
                            else:
                                vista_grupo = archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatriculacabecera.id
                                vista_revision_grupo = archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatriculacabecera.propuestatema
                            log(u"Edita archivo propuesta ensayo %s del grupo [%s] con línea de investigación: %s, de posgrado" % (
                            nombre, vista_grupo, vista_revision_grupo), request, "edit")

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'editdocfinaltitulacionposgrado':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=id)
                        if 'archivo' in eFiles:
                            newfile = eFiles['archivo']
                            if archivo.tipo == 1:
                                nombre = "propuesta"
                            else:
                                nombre = "propuesta version urkund"
                            newfile._name = generar_nombre(nombre, newfile._name)
                            archivo.archivo = newfile
                            archivo.fecha = datetime.now()
                            archivo.save(request)


                            if archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatricula:
                                vista_grupo =archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatricula.id
                                vista_revision_grupo=archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatricula.propuestatema
                            else:
                                vista_grupo = archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatriculacabecera.id
                                vista_revision_grupo = archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatriculacabecera.propuestatema
                            log(u"Edita archivo %s del grupo [%s] con línea de investigación: %s, de posgrado" % (nombre, vista_grupo ,vista_revision_grupo),request, "edit")

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'addarchivofinaltitulacion':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        en_pareja = json.loads(eRequest['en_pareja'])

                        if 'archivo' in eFiles:
                            newfile = eFiles['archivo']
                            nombre = "documentotitulacionfinal"
                            newfile._name = generar_nombre(nombre, newfile._name)
                            ext = newfile._name.split('.')
                            if not (ext[1] == 'pdf' or ext[1] == 'PDF' or ext[1] == '.pdf' or ext[1] == '.PDF'or ext[1] == '.docx'):
                                raise NameError(u"Error, solo archivos pdf")

                            if newfile.size > 203246208:
                                raise NameError(u"Error, archivo mayor a 108 Mb.")

                            if en_pareja:
                                grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                            else:
                                grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)

                            tribunal = grupo.detalletribunal()[0]
                            #creo revision
                            #informe_activo = Informe.objects.filter(status=True,tipo = 1,mecanismotitulacionposgrado = grupo.mecanismotitulacionposgrado, estado =True)
                            eConfiguraInformePrograma = ConfiguraInformePrograma.objects.filter(
                                status=True, mecanismotitulacionposgrado=grupo.mecanismotitulacionposgrado,
                                programa=grupo.convocatoria.carrera, estado=True)
                            if eConfiguraInformePrograma.exists():
                                informe = eConfiguraInformePrograma[0].informe
                                revision = Revision(
                                        tribunal = tribunal,
                                        archivo=newfile
                                )
                                revision.save(request)
                                revision.crear_estructura_informe(informe,request)

                                historial = HistorialDocRevisionTribunal(
                                    revision=revision,
                                    persona=ePersona,
                                    estado=revision.estado,
                                    observacion=revision.observacion
                                )
                                historial.save(request)
                            else:
                                raise NameError(u"Error, no existe informe activo.")
                        else:
                            raise NameError(u"Error, no ha enviado su archivo.")

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'editar_cupo_grupo_complexivo':
                with transaction.atomic():
                    try:
                        id_grupo_anterior = int(encrypt(eRequest['id_grupo_anterior']))
                        id_tema = int(eRequest['id_tema'])
                        id_grupo = int(encrypt(eRequest['id_grupo']))

                        inscrito = DetalleGrupoTitulacionPostgrado.objects.get(
                            grupoTitulacionPostgrado__id=id_grupo_anterior, inscrito__id=id_tema, status=True)
                        inscrito.grupoTitulacionPostgrado_id = id_grupo
                        inscrito.save(request)
                        log(u"Cambio de grupo inscripcion titulacion posgrado %s" % (inscrito), request, "edit")

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'asignar_cupo_grupo_complexivo':
                with transaction.atomic():
                    try:
                        id_tema = int(eRequest['id_tema'])
                        id_grupo = int(encrypt(eRequest['id_grupo']))

                        if(DetalleGrupoTitulacionPostgrado.objects.filter(grupoTitulacionPostgrado__id =id_grupo,inscrito__id= id_tema,status=True).exists()):
                            raise NameError("Usted ya se encuentra inscrito en este grupo.")


                        inscripcion = DetalleGrupoTitulacionPostgrado(
                            grupoTitulacionPostgrado_id=id_grupo,
                            inscrito_id=id_tema
                        )
                        inscripcion.save(request)
                        log(u"Inscripcion a grupo titulacion posgrador %s" % (inscripcion), request, "add")

                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'subir_acta_firmada':
                with transaction.atomic():
                    try:
                        id = int(eRequest['id'])
                        if 'archivo' in eFiles:
                            newfile = eFiles['archivo']
                            newfile._name = generar_nombre(str(eInscripcion.persona_id), newfile._name)
                            if newfile:
                                extension = newfile._name.split('.')
                                tam = len(extension)
                                exte = extension[tam - 1]
                                if newfile.size > 4194304:
                                    raise NameError(  u"Error, el tamaño del archivo es mayor a 4 Mb.")
                                if exte in ['pdf', 'PDF']:
                                    newfile._name = generar_nombre("acta_firmada", newfile._name)
                                else:
                                    transaction.set_rollback(True)
                                    raise NameError( u"Error, solo archivos .pdf")

                                tema_titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=id)

                                tema_titulacion.actaaprobacionexamen = newfile
                                tema_titulacion.estado_acta_firma = 2
                                tema_titulacion.save(request)
                                log(u"El maestrante subió acta de aprobación firmada %s" % (tema_titulacion), request, "change")
                                historial = HistorialFirmaActaAprobacionComplexivo(
                                    tema = tema_titulacion,
                                    persona = ePersona,
                                    actaaprobacionfirmada = newfile,
                                    estado_acta_firma = 2
                                )
                                historial.save(request)


                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'seleccionar_docente_tutor':
                with transaction.atomic():
                    try:
                        hoy = datetime.now()
                        if 'id' in eRequest and 'st' in eRequest and 'obs' in eRequest:
                            id = int(encrypt(eRequest['id']))
                            profesor = TemaTitulacionPosgradoProfesor.objects.get(pk=id)
                            if 1 == int(eRequest['st']):
                                profesor.estado_estudiante = 2  # aprobado
                                profesor.save(request)
                                log(u'Aprobó la solicitud del docente para ser su tutor en su proceso de titulación %s' % (
                                    profesor), request, "add")
                                if profesor.tematitulacionposgradomatricula:
                                    temamatricula = profesor.tematitulacionposgradomatricula
                                    temamatricula.tutor = profesor.profesor
                                    temamatricula.save(request)
                                    # rechazo el resto
                                    otras_solicitudes = TemaTitulacionPosgradoProfesor.objects.filter(
                                        tematitulacionposgradomatricula=profesor.tematitulacionposgradomatricula,
                                        status=True).exclude(pk=profesor.pk)
                                    for solicitud in otras_solicitudes:
                                        solicitud.estado_estudiante = 3  # rechazo
                                        solicitud.save(request)
                                        log(u'Rechazó la solicitud del docente para ser su tutor en su proceso de titulación %s' % (
                                            solicitud), request, "update")
                                        historial = SolicitudTutorTemaHistorial(
                                            tematitulacionposgradoprofesor=solicitud,
                                            persona=ePersona,
                                            estado=3,  # rechazado
                                            observacion="Rechazó la solicitud del docente para ser su tutor en su proceso de titulación."

                                        )
                                        historial.save(request)


                                else:
                                    temamatricula = profesor.tematitulacionposgradomatriculacabecera
                                    temamatricula.tutor = profesor.profesor
                                    temamatricula.save(request)
                                    # rechazo el resto
                                    otras_solicitudes = TemaTitulacionPosgradoProfesor.objects.filter(
                                        tematitulacionposgradomatriculacabecera=temamatricula, status=True).exclude(
                                        pk=profesor.pk)
                                    for solicitud in otras_solicitudes:
                                        solicitud.estado_estudiante = 3  # rechazo
                                        solicitud.save(request)
                                        log(u'Rechazó la solicitud del docente para ser tutor en su proceso de titulación %s' % (
                                            solicitud), request, "update")
                                        historial = SolicitudTutorTemaHistorial(
                                            tematitulacionposgradoprofesor=solicitud,
                                            persona=ePersona,
                                            estado=3,  # rechazado
                                            observacion="Rechazó la solicitud del docente porque ya seleccionó otro tutor en su proceso de titulación."

                                        )
                                        historial.save(request)

                                historial = SolicitudTutorTemaHistorial(
                                    tematitulacionposgradoprofesor=profesor,
                                    persona=ePersona,
                                    estado=2,  # aprobado
                                    observacion=eRequest['obs']

                                )
                                historial.save(request)
                                aprobo = True
                            else:
                                profesor.estado_estudiante = 3  # rechazado
                                profesor.save(request)

                                if profesor.tematitulacionposgradomatricula: #individual
                                    temamatricula = profesor.tematitulacionposgradomatricula
                                    temamatricula.tutor = None
                                    temamatricula.save(request)
                                else:
                                    temamatricula = profesor.tematitulacionposgradomatriculacabecera
                                    temamatricula.tutor = None#quito en cabecera
                                    temamatricula.save(request)
                                    for tema in temamatricula.obtener_parejas():
                                        tema.tutor = None#quito en individual
                                        tema.save(request)

                                log(u'Rechazó la solicitud del docente para ser su tutor en su proceso de titulación %s' % (
                                    profesor), request, "add")
                                historial = SolicitudTutorTemaHistorial(
                                    tematitulacionposgradoprofesor=profesor,
                                    persona=ePersona,
                                    estado=3,  # rechazado
                                    observacion=eRequest['obs']

                                )
                                historial.save(request)
                                aprobo = False
                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'deletepropuestatematitulacion':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        solicitud = TemaTitulacionPosgradoMatricula.objects.get(pk=id, status=True)
                        if solicitud.cabeceratitulacionposgrado:#si es en pareja boora la solicitud del companero y la cabecera
                            pareja = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=solicitud.cabeceratitulacionposgrado)
                            for tema in pareja:
                                log(u'Eliminó la solicitud del estudiante de posgrado: %s' % tema, request, "del")
                                tema.status = False
                                tema.save(request)
                            cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=solicitud.cabeceratitulacionposgrado.pk)
                            cabecera.status = False
                            cabecera.save(request)
                            log(u'Eliminó la cabecera de los estudiantes de posgrado: %s' % cabecera, request, "del")

                        else:
                            log(u'Eliminó la solicitud estudiante posgrado: %s' % solicitud, request, "del")
                            solicitud.status=False
                            solicitud.save(request)
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'addsolicitudprorrogaregistropropuestatitulacion':
                with transaction.atomic():
                    try:
                        solicitud = SolicitudProrrogaIngresoTemaMatricula(
                            matricula = matricula,
                            observacion = eRequest['observacion']
                        )
                        solicitud.save(request)
                        log(u'solicito prorroga registro propuesta titulacion: %s' % solicitud,request, "add")

                        historial = HistorialSolicitudProrrogaIngresoTemaMatricula(
                            solicitud=solicitud,
                            persona=ePersona,
                            estado=1,  # pendiente
                        )
                        historial.save(request)



                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'deletesolicitudprorrogapropuestatitulacion':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk=id)
                        solicitud.status = False
                        solicitud.save(request)
                        log(u'Eliminó la solicitud estudiante posgrado: %s' % solicitud, request, "del")

                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'editsolicitudprorrogaregistropropuestatitulacion':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id']))
                        solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk=id)
                        solicitud.observacion = eRequest['observacion']
                        solicitud.save(request)
                        log(u'Editó la solicitud de prorroga de registro de propuesta de titulacion: %s' % solicitud, request, "edit")
                        aData = {}

                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'firmarelectronica':
                with transaction.atomic():
                    try:
                        ACTA_SUSTENTACION_NOTA = 10
                        tipo = ACTA_SUSTENTACION_NOTA
                        pk = int(encrypt(eRequest['id']))
                        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                        if tipo == ACTA_SUSTENTACION_NOTA:
                            CARGO_PRESIDENTE = "PRESIDENTE/A DEL TRIBUNAL"
                            CARGO_VOCAL = "VOCAL"
                            CARGO_SECRETARIO = "SECRETARIO/A DEL TRIBUNAL"
                            CARGO_MAGISTER = "MAGÍSTER"
                            observacion = f'Acta sustentación con notas firmado por {ePersona}'
                            if variable_valor("PUEDE_FIRMAR_ACTA_SUSTENTACION_POR_ORDEN"):
                                puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo(ePersona, ACTA_SUSTENTACION_NOTA)
                            else:
                                puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo_por_tipo(ePersona,ACTA_SUSTENTACION_NOTA)

                            if puede:
                                integrante = eTemaTitulacionPosgradoMatricula.get_integrante_por_tipo(ePersona, ACTA_SUSTENTACION_NOTA)
                                pdf = eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota()
                                if integrante.ordenfirma_id == 7:  # presidente
                                    palabras = CARGO_PRESIDENTE
                                if integrante.ordenfirma_id == 8:  # vocal
                                    palabras = CARGO_VOCAL
                                if integrante.ordenfirma_id == 9:  # secretario
                                    palabras = CARGO_SECRETARIO
                                if integrante.ordenfirma_id == 10:  # maestrante
                                    palabras = CARGO_MAGISTER
                                # palabras = u"%s" % integrante.persona.nombres
                                firma = eFiles['eFileSolicitudForm']
                                passfirma = eRequest.get('ePassword', None)
                                bytes_certificado = firma.read()
                                extension_certificado = os.path.splitext(firma.name)[1][1:]
                                x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                                datau = JavaFirmaEc(
                                    archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                    extension_certificado=extension_certificado,
                                    password_certificado=passfirma,
                                    page=int(numpaginafirma), reason='', lx=x + 50, ly=y + 30
                                ).sign_and_get_content_bytes()

                                documento_a_firmar = io.BytesIO()
                                documento_a_firmar.write(datau)
                                documento_a_firmar.seek(0)
                                orden_firma = f'_firm_orden_{str(integrante.ordenfirma.orden)}'
                                eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota().save(f'{eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota().name.split("/")[-1].replace(".pdf", "")}{orden_firma}.pdf',ContentFile(documento_a_firmar.read()))
                                integrante.firmo = True
                                integrante.save(request)
                                eTemaTitulacionPosgradoMatricula.save(request)

                                eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat_acta_sustentacion_nota(request, observacion, eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota())
                                eTemaTitulacionPosgradoMatricula.notificar_integrantes_a_firmar_acta_sustentacion(request)
                                log(u"Firmo ACTA_SUSTENTACION_NOTA", request, 'edit')
                            else:
                                raise NameError(f"{mensaje}")
                        aData = {}

                        return Helper_Response(isSuccess=True,message=f'Firmado correctamente!', data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'subirarchivotoken':
                with transaction.atomic():
                    try:
                        ACTA_SUSTENTACION_NOTA = 10
                        tipo = ACTA_SUSTENTACION_NOTA
                        pk = int(encrypt(eRequest['id']))
                        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                        if tipo == ACTA_SUSTENTACION_NOTA:
                            CARGO_PRESIDENTE = "PRESIDENTE/A DEL TRIBUNAL"
                            CARGO_VOCAL = "VOCAL"
                            CARGO_SECRETARIO = "SECRETARIO/A DEL TRIBUNAL"
                            CARGO_MAGISTER = "MAGÍSTER"
                            observacion = f'Acta sustentación con notas firmado por {ePersona}'
                            if variable_valor("PUEDE_FIRMAR_ACTA_SUSTENTACION_POR_ORDEN"):
                                puede, mensaje = eTemaTitulacionPosgradoMatricula.puede_firmar_integrante_segun_orden_por_tipo(ePersona, ACTA_SUSTENTACION_NOTA)
                            else:
                                puede, mensaje = eTemaTitulacionPosgradoMatricula.integrante_ya_firmo_por_tipo(ePersona,ACTA_SUSTENTACION_NOTA)
                            if puede:
                                integrante = eTemaTitulacionPosgradoMatricula.get_integrante_por_tipo(ePersona, ACTA_SUSTENTACION_NOTA)
                                hoy = datetime.now()
                                nfileDocumento = eFiles['eFileSolicitudSignForm']
                                extensionDocumento = nfileDocumento._name.split('.')
                                tamDocumento = len(extensionDocumento)
                                exteDocumento = extensionDocumento[tamDocumento - 1]
                                if nfileDocumento.size > 1500000:
                                    mensaje = 'Error al cargar, el archivo es mayor a 15 Mb.'
                                    aData = {}
                                    return Helper_Response(isSuccess=False, data=aData, message=mensaje, status=status.HTTP_200_OK)
                                if not exteDocumento.lower() == 'pdf':
                                    mensaje = 'Error al cargar, solo se permiten archivos .pdf'
                                    aData = {}
                                    return Helper_Response(isSuccess=False, data=aData, message=mensaje, status=status.HTTP_200_OK)

                                nfileDocumento._name = generar_nombre("acta_sustentacion_nota", nfileDocumento._name)

                                eTemaTitulacionPosgradoMatricula.archivo_acta_sustentacion = nfileDocumento
                                integrante.firmo = True
                                integrante.save(request)
                                eTemaTitulacionPosgradoMatricula.save(request)

                                eTemaTitulacionPosgradoMatricula.guardar_historial_firma_titulacion_pos_mat_acta_sustentacion_nota( request, observacion,eTemaTitulacionPosgradoMatricula.get_documento_acta_sustentacion_nota())
                                eTemaTitulacionPosgradoMatricula.notificar_integrantes_a_firmar_acta_sustentacion(request)
                                log(u"Firmo ACTA SUSTENTACION NOTA POR TOKEN", request, 'edit')

                            else:
                                raise NameError(f"{mensaje}")

                        aData = {}
                        return Helper_Response(isSuccess=True,message=f'Firmado correctamente!', data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'savejornadasedegraduacion':
                with transaction.atomic():
                    try:

                        pk = int(eRequest['pkjornada'])
                        eJornadaSedeEncuestaTitulacionPosgrado = JornadaSedeEncuestaTitulacionPosgrado.objects.get(pk=pk)
                        if not eJornadaSedeEncuestaTitulacionPosgrado.get_cupo_disponible() > 0:
                            raise NameError(f'No hay cupos disponibles')

                        eInscripcionEncuestaTitulacionPosgrados = InscripcionEncuestaTitulacionPosgrado.objects.filter(status=True,encuestatitulacionposgrado =eJornadaSedeEncuestaTitulacionPosgrado.sedeencuestatitulacionposgrado.encuestatitulacionposgrado,inscripcion = eInscripcion)
                        if eInscripcionEncuestaTitulacionPosgrados.exists():
                            eInscripcionEncuestaTitulacionPosgrados.update(respondio=True)
                            eInscripcionEncuestaTitulacionPosgrados.update(participa=True)
                            eInscripcionEncuestaTitulacionPosgrados.update(observacion=eRequest['observacion'])

                            if not eInscripcionEncuestaTitulacionPosgrados.filter(respondio=False).exists():
                                for eInscripcionEncuestaTitulacionPosgrado in eInscripcionEncuestaTitulacionPosgrados:
                                    eRespuestaSedeInscripcionEncuesta = RespuestaSedeInscripcionEncuesta(
                                        inscripcionencuestatitulacionposgrado = eInscripcionEncuestaTitulacionPosgrado,
                                        jornadasedeencuestatitulacionposgrado = eJornadaSedeEncuestaTitulacionPosgrado
                                    )
                                    eRespuestaSedeInscripcionEncuesta.save(request)


                        aData = {}
                        return Helper_Response(isSuccess=True,message=f'Sede de graduación guardada correctamente!', data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            if action == 'confirmarnoparticipargraduacion':
                with transaction.atomic():
                    try:
                        pk = int(eRequest['pkencuesta'])
                        eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.get(pk=pk)
                        eInscripcionEncuestaTitulacionPosgrados = InscripcionEncuestaTitulacionPosgrado.objects.filter(status=True,encuestatitulacionposgrado =eEncuestaTitulacionPosgrado,inscripcion = eInscripcion)
                        if eInscripcionEncuestaTitulacionPosgrados.exists():
                            for eInscripcionEncuestaTitulacionPosgrado in eInscripcionEncuestaTitulacionPosgrados:
                                eInscripcionEncuestaTitulacionPosgrado.participa = False
                                eInscripcionEncuestaTitulacionPosgrado.respondio = True
                                eInscripcionEncuestaTitulacionPosgrado.save(request)

                        aData = {}
                        return Helper_Response(isSuccess=True,message=f'Sede de graduación guardada correctamente!', data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrio un error al guardar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)


        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar a la información.')
        eInscripcion = ePerfilUsuario.inscripcion
        ePersona = eInscripcion.persona
        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
        matricula = eInscripcion.matricula_periodo(periodo)
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']

                if action == 'addPropuestaTitulacion':
                    try:
                        hoy = datetime.now()
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id']))).id
                        inscripcion = ePerfilUsuario.inscripcion
                        malla = inscripcion.malla_inscripcion().malla
                        carrera = inscripcion.carrera.id
                       #PRORROGA PROPUESTA TEMA
                        prorroga_propuesta_titulacion = SolicitudProrrogaIngresoTemaMatricula.objects.filter(status=True,estado=2, matricula = matricula).order_by('-id')
                        formImputConvocatoria = ConfiguracionTitulacionPosgrado.objects.filter(status=True, periodo=periodo, carrera=carrera, fechainimaestrante__lte=hoy, fechafinmaestrante__gte=hoy,publicado=True)
                        if prorroga_propuesta_titulacion.exists():
                            if hoy.date()  >= prorroga_propuesta_titulacion[0].fechainicioprorroga  and   hoy.date() <= prorroga_propuesta_titulacion[0].fechafinprorroga :
                                formImputConvocatoria = ConfiguracionTitulacionPosgrado.objects.filter(status=True, periodo=periodo, carrera=carrera,publicado=True)


                        formImputSublinea = PropuestaSubLineaInvestigacion.objects.filter(status=True, configuraciontitulacionposgradosublinea__configuraciontitulacionposgrado__periodo=periodo, configuraciontitulacionposgradosublinea__configuraciontitulacionposgrado__carrera=carrera, configuraciontitulacionposgradosublinea__status=True)
                        # formImputMecanismoTitulacion = MecanismoTitulacionPosgrado.objects.filter(status=True, mecanismotitulacionposgradomalla__malla=malla, mecanismotitulacionposgradomalla__status=True)
                        formImputMecanismoTitulacionMalla = MecanismoTitulacionPosgradoMalla.objects.filter(status=True, malla=malla)
                        eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado.objects.filter(status=True,matricula = matricula)
                        if eSolicitudIngresoTitulacionPosgrado.exists():
                            formImputMecanismoTitulacionMalla= formImputMecanismoTitulacionMalla.filter(mecanismotitulacionposgrado__pk=eSolicitudIngresoTitulacionPosgrado.first().mecanismotitulacionposgrado_id)

                        formImputConvocatoria_serializer = ConfiguracionTitulacionPosgradoSerializer(formImputConvocatoria, many = True)
                        formImputSublinea_serializer = PropuestaSubLineaInvestigacionSerializer(formImputSublinea, many = True)
                        # formImputMecanismoTitulacion_serializer = MecanismoTitulacionPosgradoSerializer(formImputMecanismoTitulacion, many = True)
                        formImputMecanismoTitulacionMalla_serializer = MecanismoTitulacionPosgradoMallaSerializer(formImputMecanismoTitulacionMalla, many = True)
                        aData = {
                            'formImputConvocatoria': formImputConvocatoria_serializer.data if formImputConvocatoria else [],
                            'formImputMecanismoTitulacion': formImputMecanismoTitulacionMalla_serializer.data if formImputMecanismoTitulacionMalla else [],
                            'formImputSublinea': formImputSublinea_serializer.data if formImputSublinea else [],
                            'periodo_id': periodo,
                            'carrera_id': carrera,
                            'editar':False,

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'respuestaseedegraduacionposgrado':
                    try:
                        hoy = datetime.now()
                        encuesta= None
                        eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.filter(status=True, inscripcion=eInscripcion, respondio=False)
                        if eInscripcionEncuestaTitulacionPosgrado.exists():
                            existen_encuestas = True
                            eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.filter(status=True, pk__in=eInscripcionEncuestaTitulacionPosgrado.values_list('encuestatitulacionposgrado',flat=True))
                            if eEncuestaTitulacionPosgrado.exists():
                                encuesta = eEncuestaTitulacionPosgrado.first()

                        eEncuestaTitulacionPosgradoSerializer = EncuestaTitulacionPosgradoSerializer(encuesta)

                        aData = {
                            'eEncuestaTitulacionPosgradoSerializer': eEncuestaTitulacionPosgradoSerializer.data if eEncuestaTitulacionPosgrado else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'editPropuestaTitulacion':
                    try:
                        hoy = datetime.now()
                        id = int(encrypt(request.query_params['id']))
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id']))).id
                        inscripcion = ePerfilUsuario.inscripcion
                        malla = inscripcion.malla_inscripcion().malla
                        carrera = inscripcion.carrera.id
                        formImputConvocatoria = ConfiguracionTitulacionPosgrado.objects.filter(status=True, periodo=periodo, carrera=carrera, fechainimaestrante__lte=hoy, fechafinmaestrante__gte=hoy,publicado=True)
                        formImputSublinea = PropuestaSubLineaInvestigacion.objects.filter(status=True, configuraciontitulacionposgradosublinea__configuraciontitulacionposgrado__periodo=periodo, configuraciontitulacionposgradosublinea__configuraciontitulacionposgrado__carrera=carrera, configuraciontitulacionposgradosublinea__status=True)
                        formImputMecanismoTitulacion = MecanismoTitulacionPosgrado.objects.filter(status=True, mecanismotitulacionposgradomalla__malla=malla, mecanismotitulacionposgradomalla__status=True)

                        formImputConvocatoria_serializer = ConfiguracionTitulacionPosgradoSerializer(formImputConvocatoria, many = True)
                        formImputSublinea_serializer = PropuestaSubLineaInvestigacionSerializer(formImputSublinea, many = True)
                        formImputMecanismoTitulacion_serializer = MecanismoTitulacionPosgradoSerializer(formImputMecanismoTitulacion, many = True)


                        #
                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                        if tema.cabeceratitulacionposgrado:
                            pareja = True
                            companerotema = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=tema.cabeceratitulacionposgrado,status=True).exclude(pk=tema.pk)
                            companero = companerotema[0]
                        else:
                            pareja = False
                            companero = None

                        companero_serializer = TemaTitulacionPosgradoMatriculaSerializar(companero)
                        tema_serializer = TemaTitulacionPosgradoMatriculaSerializar(tema)

                        aData = {
                            'formImputConvocatoria': formImputConvocatoria_serializer.data if formImputConvocatoria else [],
                            'formImputMecanismoTitulacion': formImputMecanismoTitulacion_serializer.data if formImputMecanismoTitulacion else [],
                            'formImputSublinea': formImputSublinea_serializer.data if formImputSublinea else [],
                            'periodo_id': periodo,
                            'carrera_id': carrera,
                            'companero':companero_serializer.data if companero else [],
                            'tema':tema_serializer.data if tema else [],
                            'pareja':pareja,
                            'editar':True,


                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'adddocensayo':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        tema = ''
                        grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                        if grupo.cabeceratitulacionposgrado:
                            cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=grupo.cabeceratitulacionposgrado_id)
                            grupo = cabecera
                            grupo_serializers = TemaTitulacionPosgradoMatriculaCabeceraSerializar(grupo)
                            es_pareja = True
                        else:
                            grupo = grupo
                            grupo_serializers = TemaTitulacionPosgradoMatriculaSerializar(grupo)
                            es_pareja = False
                        aData = {
                            'grupo': grupo_serializers.data if grupo else [],
                            'es_pareja': es_pareja,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)
                if action == 'solicitudIngresoTitulacion':
                    try:
                        hoy = datetime.now()
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id']))).id
                        inscripcion = ePerfilUsuario.inscripcion
                        malla = inscripcion.malla_inscripcion().malla
                        carrera = inscripcion.carrera.id
                        formImputMecanismoTitulacionMalla = MecanismoTitulacionPosgradoMalla.objects.filter(status=True, malla=malla)
                        formImputMecanismoTitulacionMalla_serializer = MecanismoTitulacionPosgradoMallaSerializer(formImputMecanismoTitulacionMalla, many = True)

                        aData = {
                            'formImputMecanismoTitulacion': formImputMecanismoTitulacionMalla_serializer.data if formImputMecanismoTitulacionMalla else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'solicitudIngresoTitulacionToken':
                    try:
                        hoy = datetime.now()
                        payload = request.auth.payload
                        ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                        periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id']))).id
                        inscripcion = ePerfilUsuario.inscripcion
                        malla = inscripcion.malla_inscripcion().malla
                        carrera = inscripcion.carrera.id
                        formImputMecanismoTitulacionMalla = MecanismoTitulacionPosgradoMalla.objects.filter(status=True, malla=malla)
                        formImputMecanismoTitulacionMalla_serializer = MecanismoTitulacionPosgradoMallaSerializer(formImputMecanismoTitulacionMalla, many = True)

                        aData = {
                            'formImputMecanismoTitulacion': formImputMecanismoTitulacionMalla_serializer.data if formImputMecanismoTitulacionMalla else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)


                if action == 'adddocfinaltitulacionposgrado':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        id_tutoria = int(encrypt(request.query_params['id_tutoria']))
                        grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                        if grupo.cabeceratitulacionposgrado:
                            cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=grupo.cabeceratitulacionposgrado_id)
                            grupo = cabecera
                            grupo_serializers = TemaTitulacionPosgradoMatriculaCabeceraSerializar(grupo)
                            es_pareja = True
                        else:
                            grupo = grupo
                            grupo_serializers = TemaTitulacionPosgradoMatriculaSerializar(grupo)
                            es_pareja = False
                        aData = {
                            'grupo': grupo_serializers.data if grupo else [],
                            'es_pareja': es_pareja,
                            'id_tutoria':id_tutoria,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'adddocumentofinaltitulacionpormecanismo':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        id_tutoria = int(encrypt(request.query_params['id_tutoria']))
                        grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                        if grupo.cabeceratitulacionposgrado:
                            cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=grupo.cabeceratitulacionposgrado_id)
                            grupo = cabecera
                            grupo_serializers = TemaTitulacionPosgradoMatriculaCabeceraSerializar(grupo)
                            es_pareja = True
                        else:
                            grupo = grupo
                            grupo_serializers = TemaTitulacionPosgradoMatriculaSerializar(grupo)
                            es_pareja = False

                        aData = {
                            'grupo': grupo_serializers.data if grupo else [],
                            'es_pareja': es_pareja,
                            'id_tutoria':id_tutoria,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'editdocfinaltitulacionposgrado':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=id)
                        archivo_serializer = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesorSerializer(archivo)
                        tipo = archivo.tipo
                        tiparchivo = TIPO_ARCHIVO_PORSGRADO.__getitem__(tipo - 1)[1]

                        aData = {
                        'archivo':archivo_serializer.data if archivo else [],
                        'action':'editdocfinaltitulacionposgrado'
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'asignar_grupo_complexivo':
                    try:
                        id_tema = int(encrypt(request.query_params['id_tema']))
                        eTemaTitulacionPosgradoMatricula = TemaTitulacionPosgradoMatricula.objects.get(pk = id_tema)
                        id_configuracion = int(encrypt(request.query_params['id_configuracion']))
                        se_encuentra_inscrito = False
                        grupo_seleccionado = None
                        eGrupoTitulacionPostgrado = GrupoTitulacionPostgrado.objects.filter(status=True, configuracion=id_configuracion,itinerariomallaespecilidad__itinerario=eTemaTitulacionPosgradoMatricula.matricula.inscripcion.itinerario)
                        if eGrupoTitulacionPostgrado.exists():
                            grupos = GrupoTitulacionPostgrado.objects.filter(status=True,configuracion=id_configuracion, itinerariomallaespecilidad__itinerario =eTemaTitulacionPosgradoMatricula.matricula.inscripcion.itinerario)
                        else:
                            grupos = GrupoTitulacionPostgrado.objects.filter(status=True,configuracion=id_configuracion)

                        grupos_serializer = GrupoTitulacionPostgradoSerializer(grupos, many = True)

                        if DetalleGrupoTitulacionPostgrado.objects.filter(inscrito=id_tema,status=True).exists():
                            grupo_seleccionado = DetalleGrupoTitulacionPostgrado.objects.get(inscrito=id_tema,status=True)
                            se_encuentra_inscrito = True


                        grupo_seleccionado_serializer = DetalleGrupoTitulacionPostgradoSerializer(grupo_seleccionado)
                        aData = {
                            'se_encuentra_inscrito':se_encuentra_inscrito,
                            'id_tema':id_tema,
                            'grupos':grupos_serializer.data if grupos else [],
                            'grupo_seleccionado':grupo_seleccionado_serializer.data if grupo_seleccionado else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'editdocensayo':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        archivo = ArchivoRevisionPropuestaComplexivoPosgrado.objects.get(pk=id)
                        archivo_serializer = ArchivoRevisionPropuestaComplexivoPosgradoSerializer(archivo)
                        tipo = archivo.tipo
                        tiparchivo = TIPO_ARCHIVO_PORSGRADO.__getitem__(tipo - 1)[1]
                        aData = {
                        'archivo':archivo_serializer.data if archivo else [],
                        'action':'editdocensayo'
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'subir_acta_firmada':
                    try:
                        id = int(encrypt(request.query_params['id']))

                        aData = {
                        'id':id,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'subir_solicitud_ingreso_firmada':
                    try:
                        aData = {}
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'aprobar_rechazar_tutor_titulacion':
                    try:
                        id = encrypt(request.query_params['id'])
                        tema = TemaTitulacionPosgradoProfesor.objects.get(pk=id)
                        Tema_titulacion_posgrado_profesor_serializer = TemaTitulacionPosgradoProfesorSerializer(tema)

                        aData = {
                            'tema': Tema_titulacion_posgrado_profesor_serializer.data if tema else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'buscar':
                    try:
                        filterText = request.query_params['filterText']
                        periodo_id = int(request.query_params['periodo_id'])
                        carrera_id = int(request.query_params['carrera_id'])
                        if ' ' in filterText:
                            s = filterText.split(" ")
                            if len(s) == 2:
                                matriculados_companeros = Matricula.objects.annotate(
                                    display=Concat(F("inscripcion__persona__apellido1"), Value(" "),
                                                   F("inscripcion__persona__apellido2"), Value(" "),
                                                   F("inscripcion__persona__nombres"), Value(" - "),
                                                   F("inscripcion__persona__cedula"))
                                ).values('id', 'display').filter(
                                    (Q(inscripcion__persona__apellido1__icontains=s[0]) |
                                     Q(inscripcion__persona__apellido2__icontains=s[1]) |
                                     Q(inscripcion__persona__nombres__icontains=s[0]) |
                                     Q(inscripcion__persona__nombres__icontains=s[1])
                                     )
                                ).filter(status=True, inscripcion__carrera_id=carrera_id,
                                         nivel__periodo_id=periodo_id).distinct()[:20]
                            if len(s) == 3:
                                matriculados_companeros = Matricula.objects.annotate(
                                    display=Concat(F("inscripcion__persona__apellido1"), Value(" "),
                                                   F("inscripcion__persona__apellido2"), Value(" "),
                                                   F("inscripcion__persona__nombres"), Value(" - "),
                                                   F("inscripcion__persona__cedula"))
                                ).values('id', 'display').filter(
                                    (Q(inscripcion__persona__apellido1__icontains=s[0]) |
                                     Q(inscripcion__persona__apellido2__icontains=s[1]) |
                                     Q(inscripcion__persona__nombres__contains=s[2])

                                     )
                                ).filter(status=True, inscripcion__carrera_id=carrera_id,
                                         nivel__periodo_id=periodo_id).distinct()[:20]

                            if len(s) == 4:
                                matriculados_companeros = Matricula.objects.annotate(
                                    display=Concat(F("inscripcion__persona__apellido1"), Value(" "),
                                                   F("inscripcion__persona__apellido2"), Value(" "),
                                                   F("inscripcion__persona__nombres"), Value(" - "),
                                                   F("inscripcion__persona__cedula"))
                                ).values('id', 'display').filter(
                                    (Q(inscripcion__persona__apellido1__icontains=s[0]) |
                                     Q(inscripcion__persona__apellido2__icontains=s[1]) |
                                     Q(inscripcion__persona__nombres__icontains=s[2]) |
                                     Q(inscripcion__persona__nombres__icontains=s[3])
                                     )
                                ).filter(status=True, inscripcion__carrera_id=carrera_id,
                                         nivel__periodo_id=periodo_id).distinct()[:20]
                        else:
                            matriculados_companeros = Matricula.objects.annotate(
                                display=Concat(F("inscripcion__persona__apellido1"), Value(" "),
                                               F("inscripcion__persona__apellido2"), Value(" "),
                                               F("inscripcion__persona__nombres"), Value(" - "),
                                               F("inscripcion__persona__cedula"))
                            ).values('id', 'display').filter(
                                Q(inscripcion__persona__apellido1__icontains=filterText) |
                                Q(inscripcion__persona__apellido2__icontains=filterText) |
                                Q(inscripcion__persona__nombres__icontains=filterText) |
                                Q(inscripcion__persona__cedula__icontains=filterText)
                            ).filter(status=True, inscripcion__carrera_id=carrera_id,
                                     nivel__periodo_id=periodo_id).distinct()[:20]


                        aData = {
                            'items': matriculados_companeros,

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'addarchivofinaltitulacion':
                    try:
                        id = int(encrypt(request.query_params['id']))

                        en_pareja = json.loads(request.query_params['en_pareja'])
                        if en_pareja:
                            tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                            tema_participante = TemaTitulacionPosgradoMatriculaCabeceraSerializar(tema)
                        else:
                            tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                            tema_participante = TemaTitulacionPosgradoMatriculaSerializar(tema)

                        aData = {
                             'tema_participante': tema_participante.data if tema else [],
                             'en_pareja':en_pareja,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'addavancetutoriaposgrado':
                    try:
                        id = int(encrypt(request.query_params['id']))

                        aData = {
                            'id_tutoria':id,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'addcorreccionrevisiontribunal':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        es_pareja = json.loads(request.query_params['es_pareja'])
                        if es_pareja:
                            tema = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=id)
                            tema_serializer = TemaTitulacionPosgradoMatriculaCabeceraSerializar(tema)
                        else:
                            tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                            tema_serializer = TemaTitulacionPosgradoMatriculaSerializar(tema)



                        aData = {
                            'tema_serializer': tema_serializer.data if tema else [],
                            'es_pareja': es_pareja,
                            'action': 'addcorreccionrevisiontribunal',
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'editdoccorreccionrevisiontribunal':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        es_pareja = json.loads(request.query_params['es_pareja'])
                        aData = {
                            'id': id,
                            'es_pareja': es_pareja,
                            'action': 'editdoccorreccionrevisiontribunal',
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'listarhistorial':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=id)
                        historial = TemaTitulacionPosgradoMatriculaHistorial.objects.filter(status=True,
                                                                                            tematitulacionposgradomatricula=tema).order_by(
                            '-id')
                        histo = TemaTitulacionPosgradoMatriculaHistorialSerializar(historial, many=True)
                        aData = {
                            'historial': histo.data if historial.exists() else [],
                            'tema': tema.propuestatema,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'listarhistorialsolicitudprorrogapropuestatitulacion':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk= id)
                        historiales = solicitud.historial_solicitud()
                        historiales_serializer = HistorialSolicitudProrrogaIngresoTemaMatriculaSerializer(historiales, many = True)
                        aData = {
                            'historial_prorroga_propuesta': historiales_serializer.data if historiales else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'pdfactaaprobacionexamencomplexivo':
                    try:
                        file_url = None
                        id = int(encrypt(request.query_params['id']))
                        file_pdf_actaaprobacionexamencomplexivo = actaaprobacionexamencomplexivoposgrado_svelte(id, request)
                        aData = {
                            'file_url':file_pdf_actaaprobacionexamencomplexivo,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return JsonResponse({"result": "bad", "mensaje": u"Problemas al ejecutar el reporte"})

                if action == 'historialAprobacionTutor':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        temaProfesor = TemaTitulacionPosgradoProfesor.objects.get(pk=id)
                        historial = temaProfesor.solicitudtutortemahistorial_set.filter(status=True).order_by("-id")
                        historialAprobacionTutor_serializer = SolicitudTutorTemaHistorialSerializer(historial,
                                                                                                    many=True)
                        aData = {
                            'historialAprobacionTutor': historialAprobacionTutor_serializer.data if historial.exists() else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'detalletutoriaposgrado':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        tutoria= TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=id)
                        tutoria_serializer = TutoriasTemaTitulacionPosgradoProfesorSerializer(tutoria)
                        aData = {
                            'tutoria': tutoria_serializer.data if tutoria else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'detalle_revision_tribunal':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        revision = Revision.objects.get(pk=id)
                        revision_serializer = RevisionSerializer(revision)
                        aData = {
                            'revision': revision_serializer.data if revision else [],
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'instruccionformaldocente':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        profesor = Profesor.objects.get(pk=id)
                        profesor_serializer = ProfesorSerializer(profesor)

                        aData = {
                            'profesor': profesor_serializer.data if profesor else [],

                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'addsolicitudprorrogaregistropropuestatitulacion':
                    try:
                        id = matricula
                        aData = {
                            'editar':False,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'editsolicitudprorrogaregistropropuestatitulacion':
                    try:
                        id = int(encrypt(request.query_params['id']))
                        solicitud = SolicitudProrrogaIngresoTemaMatricula.objects.get(pk=id)
                        solicitud_serializer = SolicitudProrrogaIngresoTemaMatriculaSerializer(solicitud)

                        aData = {
                        'solicitud':solicitud_serializer.data if solicitud else [],
                        'editar':True,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

                if action == 'verificar_turno_firmar':
                    try:
                        ACTA_SUSTENTACION_CON_NOTA = 10
                        pk =  int(encrypt(request.query_params['id']))
                        tipo_documento =ACTA_SUSTENTACION_CON_NOTA
                        if pk == 0:
                            raise NameError("Parametro no encontrado")
                        if tipo_documento == 0:
                            raise NameError("Parametro no encontrado")

                        if tipo_documento == ACTA_SUSTENTACION_CON_NOTA:
                            tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.get(pk=pk)
                            if variable_valor("PUEDE_FIRMAR_ACTA_SUSTENTACION_POR_ORDEN"):
                                puede, mensaje = tematitulacionposgradomatricula.puede_firmar_integrante_segun_orden_por_tipo(ePersona, ACTA_SUSTENTACION_CON_NOTA)
                            else:
                                puede, mensaje = tematitulacionposgradomatricula.integrante_ya_firmo_por_tipo(ePersona,ACTA_SUSTENTACION_CON_NOTA)

                        aData = {
                        'puede':puede,
                        'mensaje':mensaje,
                        }
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                               status=status.HTTP_200_OK)



                return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada',
                                       status=status.HTTP_200_OK)
            else:
                try:
                    hoy = datetime.now()
                    revisiones=None
                    existen_encuestas=False
                    eEncuestaTitulacionPosgrado = None
                    eInscripcionEncuestaTitulacionPosgrado = None
                    cronograma = None
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    persona = ePerfilUsuario.persona
                    persona_serializer = PersonaSerializer(persona)
                    periodo = Periodo.objects.get(pk=int(encrypt(payload['periodo']['id'])))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    inscripcion = ePerfilUsuario.inscripcion
                    if inscripcion.mi_coordinacion().id != 7:
                        raise NameError(u'Módulo solo para estudiantes de posgrado.')

                    malla = inscripcion.malla_inscripcion().malla
                    matricula = inscripcion.matricula_periodo(periodo)
                    carrera = inscripcion.carrera
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')

                    if periodo.tipo.id == 3 or periodo.tipo.id == 4:
                        a = 1
                    else:
                        raise NameError(u'Solo los perfiles de estudiantes de Maestrías pueden ingresar al modulo.')


                    #actualizacion de datos
                    datospersonales, datosdomicilio, datosetnia, datostitulo, campos, datosactualizados = inscripcion.tiene_informacion_matriz_completa()
                    if datospersonales or datosdomicilio or datosetnia or datostitulo or datosactualizados:
                        return Helper_Response(isSuccess=False, data={'url_matricula':True}, redirect="alu_actualizadatos", module_access=False, token=True, status=status.HTTP_200_OK)

                    tema = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=encrypt(payload['matricula']['id'])).order_by('-id')
                    # attr
                    es_en_pareja = False
                    tiene_nota_complexivo = False
                    lista_tutorias_individuales = None
                    lista_tutorias_pareja = None
                    historial_firma = None
                    puede = False
                    puede2 = True
                    mensaje1 = ''
                    mensaje2 = ''
                    mensaje3 = ''
                    mensajesmaterias = ''
                    habilitar_adicionar_propuesta = False
                    if not ConfiguracionTitulacionPosgrado.objects.filter(periodo=periodo, carrera=inscripcion.carrera,status=True, publicado=True).exists() and not tema.exists():
                        raise NameError("No existe una convocatoria configurada que se encuentre públicada para realizar el proceso de postulación.")

                    if ConfiguracionTitulacionPosgrado.objects.filter(periodo=periodo, carrera=inscripcion.carrera,status=True,publicado=True).exists() and not tema.exists():
                        cronograma = ConfiguracionTitulacionPosgrado.objects.filter(periodo=periodo,carrera=inscripcion.carrera,status=True,publicado=True)[0]
                        if cronograma.fechafinmaestrante and cronograma.fechainimaestrante:
                            if datetime.now().date() <= cronograma.fechafinmaestrante and datetime.now().date() >= cronograma.fechainimaestrante:
                                habilitar_adicionar_propuesta = True
                    else:
                        if tema.exists():
                            cronograma = tema[0].convocatoria
                            if cronograma.fechafinmaestrante and cronograma.fechainimaestrante:
                                if datetime.now().date() <= cronograma.fechafinmaestrante and datetime.now().date() >= cronograma.fechainimaestrante:
                                    habilitar_adicionar_propuesta = True



                    tematitulacionposgradomatriculacabecera = None
                    if tema.exists():
                        eInscripcionEncuestaTitulacionPosgrado = InscripcionEncuestaTitulacionPosgrado.objects.filter(encuestatitulacionposgrado__status=True,status=True,inscripcion =tema[0].matricula.inscripcion)
                        if eInscripcionEncuestaTitulacionPosgrado.filter(respondio =False).exists():
                            existen_encuestas=True
                            eEncuestaTitulacionPosgrado = EncuestaTitulacionPosgrado.objects.filter(status=True,activo =True,inicio__lte=hoy, fin__gte=hoy, pk__in= eInscripcionEncuestaTitulacionPosgrado.values_list('encuestatitulacionposgrado',flat =True) )
                            eEncuestaTitulacionPosgradoSerializer = EncuestaTitulacionPosgradoSerializer(eEncuestaTitulacionPosgrado, many=True)
                            eInscripcionEncuestaTitulacionPosgradoSerializer = InscripcionEncuestaTitulacionPosgradoSerializer(eInscripcionEncuestaTitulacionPosgrado, many=True)

                        if eInscripcionEncuestaTitulacionPosgrado.exists():
                            eInscripcionEncuestaTitulacionPosgradoSerializer = InscripcionEncuestaTitulacionPosgradoSerializer(eInscripcionEncuestaTitulacionPosgrado, many=True)

                        # envio el tema
                        tematitulacionposgradomatricula_serializers = TemaTitulacionPosgradoMatriculaSerializar(tema[0])
                        historial_firma = tema[0].obtener_historial_firma_acta_aprobacion_complexivo()
                        historialfirmaactaaprobacioncomplexivo_serializer = HistorialFirmaActaAprobacionComplexivoSerializer( historial_firma, many=True)
                        if tema[0].tiene_calificacion_ensayo_complexivoposgrado() or tema[0].tiene_calificacion_examen_complexivoposgrado():
                            tiene_nota_complexivo = True
                        else:
                            tiene_nota_complexivo = False
                        #
                        if tema[0].cabeceratitulacionposgrado:
                            es_en_pareja = True
                            tematitulacionposgradomatriculacabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(status=True, pk=tema[0].cabeceratitulacionposgrado.pk)
                            tematitulacionposgradomatriculacabecera_serializers = TemaTitulacionPosgradoMatriculaCabeceraSerializar(tematitulacionposgradomatriculacabecera)

                        else:
                            es_en_pareja = False
                            tematitulacionposgradomatriculacabecera = None

                    if not inscripcion.inscripcionmalla_set.filter(status=True):
                        raise NameError(u'Debe tener malla asociada para poder inscribirse.')

                    mensaje1 = 'No existe configuración de su periodo para ingreso de Tema de Titulación'
                    if ConfiguracionTitulacionPosgrado.objects.filter(status=True, periodo=periodo, carrera=carrera,publicado=True).exists():
                        puede = True
                        mensaje1 = ''
                    if malla.tiene_itinerario_malla_especialidad():
                        idasignaturasmalla = malla.asignaturamalla_set.values_list('id', flat=True).filter(status=True,itinerario__in = [0,inscripcion.itinerario,None])
                    else:
                        idasignaturasmalla = malla.asignaturamalla_set.values_list('id', flat=True).filter(status=True)

                    cantidadmalla = idasignaturasmalla.count()
                    cantidadaprobadas = inscripcion.recordacademico_set.filter(status=True,asignaturamalla_id__in=idasignaturasmalla,aprobada=True).count()
                    totalmateriasparatesis = cantidadmalla - 3
                    mostrar_aviso = False
                    # porcentaje_aprobado= 0
                    # porcentaje_aprobado = (cantidadaprobadas / cantidadmalla) * 100
                    # if not porcentaje_aprobado >= 50:
                    #     puede = False

                    if cantidadaprobadas < totalmateriasparatesis:
                        # puede = False
                        mensaje2 = 'Aun no tiene aprobado curso como requisito de titulación'
                        asignaturasmallas = AsignaturaMalla.objects.filter(status=True, pk__in=idasignaturasmalla)
                        for a in asignaturasmallas:
                            if inscripcion.recordacademico_set.filter(status=True, asignaturamalla=a,aprobada=True).exists():
                                mensajesmaterias = mensajesmaterias + a.asignatura.nombre + ' - APROBADA <br>'
                            else:
                                mensajesmaterias = mensajesmaterias + a.asignatura.nombre + ' - PENDIENTE <br>'
                                mostrar_aviso = True

                    if puede:
                        historial = TemaTitulacionPosgradoMatriculaHistorial.objects.filter(status=True,tematitulacionposgradomatricula__matricula=matricula,tematitulacionposgradomatricula__status=True)
                        if historial:
                            puede2 = False
                            estado = historial.order_by('-id')[0].estado
                            if estado == 1:
                                puede = False
                                mensaje1 = 'Su propuesta está en revisión, por favor espere.'
                            if estado == 2:
                                puede = False
                                mensaje1 = 'Su propuesta está aprobada, puede continuar a la siguiente etapa.'
                            if estado == 3:
                                puede = True
                                mensaje1 = 'Su propuesta esta rechazada, para continuar con la siguiente etapa su propuesta debe estar aprobada.'
                        else:
                            cabecera = TemaTitulacionPosgradoMatricula.objects.filter(matricula=matricula, status=True)
                            if cabecera:
                                puede2 = False
                                estado = cabecera.order_by('-id')[0].estado
                                if estado == 1:
                                    puede = False
                                    mensaje1 = 'Su propuesta está en revisión, por favor espere.'
                                if estado == 2:
                                    puede = False
                                    mensaje1 = 'Su propuesta está aprobada, puede continuar a la siguiente etapa.'
                                if estado == 3:
                                    puede = True
                                    mensaje1 = 'Su propuesta esta rechazada, para continuar con la siguiente etapa su propuesta debe estar aprobada.'
                            else:
                                puede = True
                                puede2 = True

                    listarubros = persona.rubro_set.filter(status=True)
                    contadorrubrosdebe = 0
                    for lrubro in listarubros:
                        if not lrubro.pagos():
                            if not lrubro.fechavence >= datetime.now().date():
                                if not lrubro.cancelado:
                                    contadorrubrosdebe = contadorrubrosdebe + 1
                        else:
                            if not lrubro.fechavence >= datetime.now().date():
                                if not lrubro.cancelado:
                                    contadorrubrosdebe = contadorrubrosdebe + 1

                    if contadorrubrosdebe > 0:
                        # puede = False
                        mensaje3 = 'Tiene deudas pendientes, reviselo en el módulo MIS FINANZAS'

                    # tutorias
                    matricula = inscripcion.matricula_periodo(periodo)
                    estudiante = inscripcion.persona
                    disponible = True
                    disponible_elejirTutor = False
                    detallecalificacion = None

                    #solicita prorroga
                    solicitudes_prorroga = SolicitudProrrogaIngresoTemaMatricula.objects.filter(status=True,matricula = matricula)
                    if solicitudes_prorroga.exists():
                        solicitudes_prorroga_serializer = SolicitudProrrogaIngresoTemaMatriculaSerializer(solicitudes_prorroga, many =True)
                     #
                    puede_solicitar_prorroga = False
                    if cronograma.fechafintutoria and cronograma.fechainiciotutoria:
                        if not datetime.now().date() >= cronograma.fechainiciotutoria :
                            if not solicitudes_prorroga.filter(estado__in=[1,2,3]).order_by("-id").exists():
                                if not tema.exists():
                                    puede_solicitar_prorroga = True
                            else:
                                if solicitudes_prorroga.filter(estado__in=[2]).order_by("-id").count() < 2 and solicitudes_prorroga.filter(estado__in=[1]).order_by("-id").count() <= 1 :
                                    if not tema.exists():
                                        puede_solicitar_prorroga = True


                    #habilitar boton adicionar propuesta  - para prorroga
                    prorroga_activa = False
                    if solicitudes_prorroga.filter(estado = 2).exists():
                        if datetime.now().date() <= solicitudes_prorroga.filter(estado = 2).order_by('-id')[0].fechafinprorroga and datetime.now().date() >= solicitudes_prorroga.filter(estado = 2).order_by('-id')[0].fechainicioprorroga:
                            prorroga_activa = True


                    grupo = None
                    tutor = None
                    tipoarchivo = None
                    numerointegrantes = None
                    propuestas = None
                    propuestas_ensayo = None
                    grupo_seleccionado_complexivo = None
                    grupo_seleccionado_complexivo_serializer = None
                    if TemaTitulacionPosgradoMatricula.objects.values('id').filter(status=True,matricula=matricula).exists():

                        grupo = TemaTitulacionPosgradoMatricula.objects.get(status=True, matricula=matricula)
                        if grupo.convocatoria.fechafintutoria and grupo.convocatoria.fechainiciotutoria:
                            if datetime.now().date() < grupo.convocatoria.fechainiciotutoria:
                                disponible_elejirTutor = True
                        grupo_serializers = TemaTitulacionPosgradoMatriculaSerializar(grupo)
                        detallecalificacion = grupo.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                        detallecalificacion_serializer = CalificacionTitulacionPosgradoSerializer(detallecalificacion,many=True)
                        tipoarchivo = TIPO_ARCHIVO_COMPLEXIVO_PROPUESTA

                        tutor = grupo.tutor if not grupo.tutor else None
                        profesor_serializer = ProfesorSerializer(tutor)
                        numerointegrantes = 1
                        if not TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=matricula)[0].mecanismotitulacionposgrado.id in [15,21]:
                            if not TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=matricula)[0].tutor:
                                disponible = False
                        estado = 0
                        # ---PAREJA PROPUESTA
                        if tema:
                            if tema[0].cabeceratitulacionposgrado:
                                cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(status=True, pk=tema[0].cabeceratitulacionposgrado.pk)
                                if not cabecera.tutor:
                                    if not cabecera.mecanismotitulacionposgrado.id in [15,21]:
                                        disponible = False
                                else:
                                    disponible = True

                                if cabecera.mecanismotitulacionposgrado.id in [15,21]:
                                    if RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatriculacabecera=cabecera, status=True).order_by('-id'):
                                        estado = RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatriculacabecera=cabecera, status=True).order_by( '-id')[ 0].estado
                                    if estado == 1:
                                        disponible = False

                                    if estado == 2:
                                        disponible = False

                                else:
                                    if RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatriculacabecera=cabecera, status=True,tutoriatematitulacionposgradoprofesor__programaetapatutoria__etapatutoria__id = 8).order_by('-id'):
                                        estado = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatriculacabecera=cabecera, status=True,tutoriatematitulacionposgradoprofesor__programaetapatutoria__etapatutoria__id = 8).order_by('-id')[0].estado

                                    if estado == 1:
                                        disponible = False

                                    if estado == 2:
                                        disponible = False

                                propuestas = cabecera.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('id')

                                propuestas_ensayo = cabecera.revisionpropuestacomplexivoposgrado_set.filter(status=True).order_by('id')

                                lista_tutorias_pareja = cabecera.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('id')

                                lista_tutorias_pareja_serializer = TutoriasTemaTitulacionPosgradoProfesorSerializer(lista_tutorias_pareja, many=True)
                            else:
                                if tema[0].mecanismotitulacionposgrado.id in [15,21]:
                                    if RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatricula=grupo, status=True).order_by('-id'):
                                        estado = RevisionPropuestaComplexivoPosgrado.objects.filter(tematitulacionposgradomatricula=grupo, status=True).order_by('-id')[0].estado
                                    if estado == 1:
                                        disponible = False

                                    if estado == 2:
                                        disponible = False
                                else:
                                    if RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatricula=grupo, status=True,tutoriatematitulacionposgradoprofesor__programaetapatutoria__etapatutoria__id = 8).order_by('-id'):
                                        estado = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatricula=grupo, status=True,tutoriatematitulacionposgradoprofesor__programaetapatutoria__etapatutoria__id = 8).order_by('-id')[0].estado

                                    if estado == 1:
                                        disponible = False

                                    if estado == 2:
                                        disponible = False

                                propuestas = grupo.revisiontutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('id')

                                propuestas_ensayo = grupo.revisionpropuestacomplexivoposgrado_set.filter( status=True).order_by('id')

                                lista_tutorias_individuales = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('id')
                                lista_tutorias_individuales_serializer = TutoriasTemaTitulacionPosgradoProfesorSerializer(lista_tutorias_individuales, many=True)

                        # seleccion de tutores por parte del estudiante - lista disponible
                        if grupo.cabeceratitulacionposgrado:
                            tema_grupo = grupo.cabeceratitulacionposgrado
                            profesores_disponibles = tema_grupo.tematitulacionposgradoprofesor_set.filter(status=True, aprobado=True).order_by( '-id')
                        else:
                            tema_grupo = grupo
                            profesores_disponibles = tema_grupo.tematitulacionposgradoprofesor_set.filter(status=True, aprobado=True).order_by( '-id')

                        profesores_disponibles_serializer = TemaTitulacionPosgradoProfesorSerializer( profesores_disponibles, many=True)

                    else:
                        profesores_disponibles = None
                        disponible = False

                    # serializers
                    puede_subir_correccion_revision_tribunal = True
                    if tema:
                        if tema[0]:
                            if DetalleGrupoTitulacionPostgrado.objects.filter(inscrito=tema[0], status = True).exists() :
                                grupo_seleccionado_complexivo = DetalleGrupoTitulacionPostgrado.objects.get(inscrito=tema[0],status = True)
                                grupo_seleccionado_complexivo_serializer = DetalleGrupoTitulacionPostgradoSerializer(grupo_seleccionado_complexivo)

                            revisiones = tema[0].obtener_revisiones()
                            if revisiones:
                                if revisiones.count() <= 2:
                                    if revisiones.filter(estado=1,status=True).exists():
                                        puede_subir_correccion_revision_tribunal = False
                                    if revisiones.filter(estado__in = [2,3]).exists():
                                        puede_subir_correccion_revision_tribunal = False
                                else:
                                    puede_subir_correccion_revision_tribunal = False

                                revisiones_serializer = RevisionSerializer(revisiones, many=True)



                    propuestas_ensayo_serializer = RevisionPropuestaComplexivoPosgradoSerializer(propuestas_ensayo, many=True)
                    cronograma_serializers = ConfiguracionTitulacionPosgradoSerializer(cronograma)
                    configuracion_programa_etapa = None
                    if tema:
                        miconvocatoria  = tema[0].cabeceratitulacionposgrado.convocatoria  if tema[0].cabeceratitulacionposgrado else  tema[0].convocatoria
                        if variable_valor('HABILITAR_TUTORIA_POR_MECANISMO'):
                            mecanismo_id = tema[0].cabeceratitulacionposgrado.mecanismotitulacionposgrado_id  if tema[0].cabeceratitulacionposgrado else  tema[0].mecanismotitulacionposgrado_id
                            configuracion_programa_etapa = miconvocatoria.obtener_etapas_de_tutorias(mecanismo_id)
                        else:
                            configuracion_programa_etapa = miconvocatoria.obtener_etapas_de_tutorias_antiguo()

                    configuracion_programa_etapa_serializer = ProgramaEtapaTutoriaPosgradoSerializer(configuracion_programa_etapa, many=True)
                    matricula_serializer = MatriculaSerializer(matricula)

                    nombre_mes = lambda x: ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre","Noviembre", "Diciembre"][int(x) - 1]
                    month, day = "%02d" % hoy.month, "%02d" % hoy.day
                    mes = "%s" % nombre_mes(int(hoy.strftime("%m")))

                    eSolicitudIngresoTitulacionPosgrado = SolicitudIngresoTitulacionPosgrado.objects.filter(status=True, matricula=matricula, firmado =True)
                    eSolicitudIngresoTitulacionPosgradoSerializer = SolicitudIngresoTitulacionPosgradoSerializer(eSolicitudIngresoTitulacionPosgrado.first())

                    data = {
                        'tematitulacionposgradomatricula_serializers': tematitulacionposgradomatricula_serializers.data if tema else [],
                        'historial_firma': historialfirmaactaaprobacioncomplexivo_serializer.data if historial_firma else [],
                        'tematitulacionposgradomatriculacabecera_serializers': tematitulacionposgradomatriculacabecera_serializers.data if tematitulacionposgradomatriculacabecera else [],
                        'cronograma': cronograma_serializers.data if cronograma else [],
                        'tutor': profesor_serializer.data if tutor else [],
                        'grupo': grupo_serializers.data if grupo else [],
                        'configuracion_programa_etapa': configuracion_programa_etapa_serializer.data if configuracion_programa_etapa else [],
                        'detallecalificacion': detallecalificacion_serializer.data if detallecalificacion else [],
                        'lista_tutorias_individuales': lista_tutorias_individuales_serializer.data if lista_tutorias_individuales else [],
                        'lista_tutorias_pareja': lista_tutorias_pareja_serializer.data if lista_tutorias_pareja else [],
                        'matricula': matricula_serializer.data if matricula else [],
                        'ePersona': persona_serializer.data if persona else [],
                        'es_en_pareja': es_en_pareja,
                        'tiene_notas_complexivo': tiene_nota_complexivo,
                        'puede': puede,
                        'puede2': puede2,
                        'mensaje1': mensaje1,
                        'mensaje2': mensaje2,
                        'mensaje3': mensaje3,
                        'tipoarchivo': tipoarchivo,
                        'mensajesmaterias': mensajesmaterias,
                        'mostrar_aviso': mostrar_aviso,
                        'disponible_elejirTutor': disponible_elejirTutor,
                        'disponible': disponible,
                        'puede_solicitar_prorroga': puede_solicitar_prorroga,
                        'prorroga_activa': prorroga_activa,
                        'habilitar_adicionar_propuesta': habilitar_adicionar_propuesta,
                        'numerointegrantes': numerointegrantes,
                        'puede_subir_correccion_revision_tribunal': puede_subir_correccion_revision_tribunal,
                        'profesores_disponibles': profesores_disponibles_serializer.data if profesores_disponibles else [],
                        'propuestas_ensayo': propuestas_ensayo_serializer.data if propuestas_ensayo else [],
                        'grupo_seleccionado': grupo_seleccionado_complexivo_serializer.data if grupo_seleccionado_complexivo else [],
                        'solicitudes_prorroga': solicitudes_prorroga_serializer.data if solicitudes_prorroga else [],
                        'revisiones_serializer': revisiones_serializer.data if revisiones else [],
                        'eEncuestaTitulacionPosgradoSerializer': eEncuestaTitulacionPosgradoSerializer.data if eEncuestaTitulacionPosgrado else [],
                        'eInscripcionEncuestaTitulacionPosgradoSerializer': eInscripcionEncuestaTitulacionPosgradoSerializer.data if eInscripcionEncuestaTitulacionPosgrado else [],
                        'hoy': f"Milagro, {day} de {mes.lower()} del {hoy.year}",
                        'solicitudingreso': eSolicitudIngresoTitulacionPosgradoSerializer.data

                        }
                    return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)
