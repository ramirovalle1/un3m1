# coding=utf-8
import os
import random
import calendar
import zipfile
from _decimal import Decimal
from datetime import datetime, timedelta
from pathlib import Path
from django.core.files import File
from django.core.files.base import ContentFile
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, ExpressionWrapper, F, DateField
from django.db.models.functions import TruncDate
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from mobile.views import make_thumb_picture, make_thumb_fotopersona
from inno.models import MateriaAsignadaPlanificacionSedeVirtualExamen, MatriculaSedeExamen
from matricula.models import PeriodoMatricula
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavesilabo, conviert_html_to_pdfsavepracticas, \
    conviert_html_to_pdf_parametros_save, conviert_html_to_pdf
from django.db import connection, transaction, connections
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_planificacion
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.aulavirtual import MatriculaMateriaAsignadaSerializer, MatriculaSerializer, \
    MatriculaMateriaSerializer, MallaSerializer, PeriodoSerializer, \
    CompaMateriaAsignadaSerializer, LibroKohaProgramaAnaliticoAsignaturaSerializer, Silabo_2_Serializar, \
    GPGuiaPracticaSemanal_Serializar, AvComunicacionSerializer, AvPreguntaDocenteSerializer, \
    TestSilaboSemanalSerializer, TareaSilaboSemanalSerializer, ForoSilaboSemanalSerializer, \
    TareaPracticaSilaboSemanalSerializer, HorarioExamenDetalleAlumnoSerializer, PlanificacionSedeSerializer, \
    MatriculaSedeExamenSerializer, InscripcionSerializer
from certi.models import CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora, Certificado
from sga.funciones import null_to_decimal, variable_valor, log, remover_caracteres_tildes_unicode, \
    remover_caracteres_especiales_unicode, generar_nombre
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, MateriaAsignada, InscripcionMalla, \
    AsignaturaMalla, Materia, PeriodoGrupoSocioEconomico, Inscripcion, PerdidaGratuidad, AuditoriaNotas, \
    AgregacionEliminacionMaterias, Silabo, Periodo, DetalleSilaboSemanalBibliografiaDocente, \
    LibroKohaProgramaAnaliticoAsignatura, GPGuiaPracticaSemanal, Persona, AvComunicacion, AvPreguntaDocente, \
    TestSilaboSemanal, TareaSilaboSemanal, ForoSilaboSemanal, TareaPracticaSilaboSemanal, HorarioExamen, SesionZoom, \
    DetalleSesionZoom, HorarioExamenDetalleAlumno, DiapositivaSilaboSemanal, CompendioSilaboSemanal, \
    GuiaEstudianteSilaboSemanal, SedeVirtual, PersonaDocumentoPersonal, FirmaCertificadoSecretaria
from sga.templatetags.sga_extras import encrypt
from django.template import Context
from django.template.loader import get_template
from settings import DEBUG, NOTA_ESTADO_EN_CURSO, USA_PLANIFICACION, SITE_STORAGE, GENERAR_TUMBAIL
from moodle import moodle
from django.shortcuts import render, redirect
from api.helpers.functions_helper import get_variable, conviert_html_to_pdf_save_path
from sga.commonviews import get_client_ip
from django.core.cache import cache


class AulaVirtualAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_AULA_VIRTUAL'

    @api_security
    def post(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        tiempo_cache = int(tiempo_cache.total_seconds())
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        try:
            payload = request.auth.payload
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'listarBibliografia':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    if not 'idp' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    aLibros = []
                    id = encrypt(eRequest.get('id', encrypt('0')))
                    idp = encrypt(eRequest.get('idp', encrypt('0')))
                    persona = Persona.objects.get(pk=int(idp))
                    materia = Materia.objects.get(pk=int(id))
                    bibliografiabasicas = []
                    complementarias = []
                    if materia.silabo_actual():
                        bibliografiabasicas = materia.silabo_actual().programaanaliticoasignatura.bibliografiaprogramaanaliticoasignatura_set.values_list('librokohaprogramaanaliticoasignatura_id', flat=False).filter(status=True).distinct()
                        complementarias = DetalleSilaboSemanalBibliografiaDocente.objects.values_list('librokohaprogramaanaliticoasignatura_id', flat=False).filter(status=True, silabosemanal__silabo=materia.silabo_actual()).distinct()
                    librosinvestigacion = LibroKohaProgramaAnaliticoAsignatura.objects.filter(Q(status=True), (Q(pk__in=complementarias) | Q(pk__in=bibliografiabasicas))).distinct().order_by('nombre')
                    # libroserializer = LibroKohaProgramaAnaliticoAsignaturaSerializer(librosinvestigacion, many= True)

                    for libro in librosinvestigacion:
                        libro_data = LibroKohaProgramaAnaliticoAsignaturaSerializer(libro).data
                        libro_data.__setitem__('visitas', libro.cantidad_visitas_libro(materia, persona, 1 ))
                        aLibros.append(libro_data)

                    #
                    # materiaasignada = MateriaAsignada.objects.get(pk=int(id))
                    # materiasasignadas = MateriaAsignada.objects.filter(materia__id=materiaasignada.materia.id).order_by(
                    #     "matricula__inscripcion__persona")
                    #
                    # matriasig_serializer = CompaMateriaAsignadaSerializer(materiasasignadas, many=True)

                    aData = {
                        'libros': aLibros

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'mostrarsilabodigital':
                try:
                    if not 'idm' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    idm = encrypt(eRequest.get('idm', encrypt('0')))
                    idp = encrypt(eRequest.get('idp', encrypt('0')))

                    silabo = Silabo.objects.get(materia_id=int(idm), status=True,
                                                profesor=int(idp))
                    directory = os.path.join(SITE_STORAGE, 'media', 'documentos', 'silabos')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    qrname='Silabo{}'.format(random.randint(1, 100000).__str__())
                    valida = conviert_html_to_pdfsavesilabo(
                        'pro_planificacion/silabo_pdf.html',
                        # 'alu_documentos/silabodigital_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': silabo.silabo_pdf(),
                        }, qrname + '.pdf'

                    )
                    archivodescargar = 'documentos/silabos/' + qrname + '.pdf'
                    value = get_variable('SITE_URL_SGA')

                    # return redirect('/media/{}'.format(archivodescargar))
                    return Helper_Response(isSuccess=True, data={'file': f"{value}/media/{archivodescargar}"}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'practica_indpdf':
                try:
                    data = {}
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de guía práctica.')
                    id = encrypt(eRequest.get('id', encrypt('0')))
                    practica = GPGuiaPracticaSemanal.objects.get(status=True, pk=int(id))
                    data['practicas'] = GPGuiaPracticaSemanal.objects.filter(status=True, id=practica.id)
                    data['decano'] = practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(
                        practica.silabosemanal.silabo.materia.nivel.periodo,
                        1) if practica.silabosemanal.silabo.materia.coordinacion_materia().responsable_periododos(
                        practica.silabosemanal.silabo.materia.nivel.periodo, 1) else None
                    data['director'] = practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(
                        practica.silabosemanal.silabo.materia.nivel.periodo,
                        practica.silabosemanal.silabo.profesor.coordinacion.sede).persona.nombre_completo_inverso() if practica.silabosemanal.silabo.materia.asignaturamalla.malla.carrera.coordinador(
                        practica.silabosemanal.silabo.materia.nivel.periodo,
                        practica.silabosemanal.silabo.profesor.coordinacion.sede) else None

                    directory = os.path.join(SITE_STORAGE, 'media', 'documentos', 'guia_practicas')
                    try:
                        os.stat(directory)
                    except:
                        os.mkdir(directory)
                    qrname='guia_practica_{}'.format(random.randint(1, 100000).__str__())
                    valida = conviert_html_to_pdfsavepracticas(
                        'pro_planificacion/practica_pdf.html',
                        # 'alu_documentos/silabodigital_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }, qrname + '.pdf'

                    )
                    archivodescargar = 'documentos/guia_practicas/' + qrname + '.pdf'
                    value = get_variable('SITE_URL_SGA')

                    # return redirect('/media/{}'.format(archivodescargar))
                    return Helper_Response(isSuccess=True, data={'file': f"{value}/media/{archivodescargar}"}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'guiapracticas':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(eRequest.get('id', encrypt('0')))
                    hoy = datetime.now()
                    mate = ""
                    practicas = None
                    materia = Materia.objects.get(pk=int(id))
                    if materia.silabo_actual():
                        practicas = GPGuiaPracticaSemanal.objects.filter(Q(status=True),
                                                                        Q(silabosemanal__silabo=materia.silabo_actual()),
                                                                        (Q(estadoguiapractica__estado=2) | Q(
                                                                            estadoguiapractica__estado=3)))
                        # practicas = GPGuiaPracticaSemanal.objects.filter(pk=3103)
                    mate = '%s - %s - %s %s' %(materia.asignaturamalla.asignatura, materia.asignaturamalla.nivelmalla, materia.paralelo, materia.nivel.paralelo)
                    if practicas:
                        guia_serializer = GPGuiaPracticaSemanal_Serializar(practicas, many = True)

                    aData = {
                        'guia_practica': guia_serializer.data if practicas.exists() else [],
                        'materia': mate

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'comunicaciones':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(eRequest.get('id', encrypt('0')))
                    materiaasignada = MateriaAsignada.objects.get(pk=int(id))
                    materia = materiaasignada.materia
                    # comunicaciones = materiaasignada.materia.avcomunicacion_set.filter(pk = 5718, visible=True).order_by(
                    #     "-fecha_creacion")
                    comunicaciones = materiaasignada.materia.avcomunicacion_set.filter(visible=True).order_by("-fecha_creacion")
                    # comunicaciones = AvComunicacion.objects.filter(pk=5718).order_by(
                    #     "-fecha_creacion")

                    nombre = materia.nombre_mostrar()
                    ePeriodoMatriculas = materia.nivel.periodo.periodomatricula_set.filter(status=True)
                    if ePeriodoMatriculas.values("id").exists():
                        ePeriodoMatricula = ePeriodoMatriculas[0]
                        if not ePeriodoMatricula.ver_profesor_materia:
                            nombre = materia.nombre_mostrar_sin_profesor()

                    if comunicaciones:
                        comunicaciones_serializer = AvComunicacionSerializer(comunicaciones, many = True)

                    aData = {
                        'comunicaciones': comunicaciones_serializer.data if comunicaciones.exists() else [],
                        'materia_nombre': nombre
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'controlacademico':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    if not 'idins' in eRequest:
                        raise NameError(u'No se encontro parametro de inscripcion.')
                    if not 'idp' in eRequest:
                        raise NameError(u'No se encontro parametro de periodo.')
                    periodo = encrypt(eRequest.get('idp', encrypt('0')))
                    id = encrypt(eRequest.get('id', encrypt('0')))
                    idins = encrypt(eRequest.get('idins', encrypt('0')))
                    materiaasignada = MateriaAsignada.objects.get(pk=int(id))
                    periodo = materiaasignada.materia.nivel.periodo.id
                    inscripcion = Inscripcion.objects.get(pk=int(idins))
                    pregunta = AvPreguntaDocente.objects.filter(materiaasignada = materiaasignada , status=True)
                    modalidadcarrera = inscripcion.modalidad_id
                    pregunta_serializer = AvPreguntaDocenteSerializer(pregunta, many=True)

                    aData = {
                        'preguntas': pregunta_serializer.data if pregunta.exists() else [],
                        'modalidadcarrera': modalidadcarrera,
                        'periodo': int(periodo)
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'listarSilabo':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    id = encrypt(eRequest.get('id', encrypt('0')))
                    hoy = datetime.now()

                    materia = Materia.objects.get(pk=int(id))
                    profesor = profesor = materia.profesor_principal()
                    silabos = materia.silabo_set.filter(profesor=profesor, status=True)
                    silabo_serializer = Silabo_2_Serializar(silabos, many=True)
                    aprobar = variable_valor('APROBAR_SILABO')
                    rechazar = variable_valor('RECHAZAR_SILABO')
                    pendiente = variable_valor('PENDIENTE_SILABO')
                    horassegundos = hoy.strftime('%Y%m%d_%H%M%S')

                    aData = {
                        'silabos': silabo_serializer.data if silabos.exists() else [],
                        'aprobar': aprobar,
                        'rechazar': rechazar,
                        'pendiente': pendiente,
                        'horassegundos': horassegundos

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'addcliczoom':
                try:
                    aData = {}
                    if not variable_valor('GUARDAR_ASISTENCIA_EXAMENES'):
                        return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                    if not 'id' in eRequest:
                        raise NameError(u'No se encontro parametro de materia asignada.')
                    if not 'idExamen' in eRequest:
                        raise NameError(u'No se encontro parametro de examen.')
                    if not 'navegador' in eRequest:
                        raise NameError(u'No se encontro parametro de Navegador.')
                    if not 'os' in eRequest:
                        raise NameError(u'No se encontro parametro de os.')
                    if not 'screensize' in eRequest:
                        raise NameError(u'No se encontro parametro de screensize.')

                    horarioexamen_id = encrypt(eRequest['idExamen'])
                    materiaasignada_id = encrypt(eRequest['id'])
                    detallealumno = HorarioExamenDetalleAlumno.objects.filter(status=True, materiaasignada_id=materiaasignada_id, horarioexamendetalle__horarioexamen_id=horarioexamen_id).first()
                    if not detallealumno.disponibleexamen():
                        raise NameError(u'Este exámen aún no esta disponible')
                    if not detallealumno:
                        raise NameError(u'Usted no se encuentra planificado en este exámen')
                    if detallealumno.asistioexamen:
                        raise NameError(u'Su asistencia ya fue registrada el {}'.format(detallealumno.fechaasistenciaexamen))
                    detallealumno.asistioexamen = True
                    detallealumno.fechaasistenciaexamen = datetime.now()

                    detallealumno.save(request, update_fields=['asistioexamen', 'fechaasistenciaexamen'])


                    log(u'Alumno registra asistencia de acceso a examen:%s ' % (detallealumno), request, "add")
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'viewCalendario':
                try:
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')
                    if payload['matricula']['id'] is None:
                        raise NameError(u'No se encuentra matriculado.')
                    eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                    eInscripcion = eMatricula.inscripcion
                    ePersona = eInscripcion.persona
                    ePeriodo = eMatricula.nivel.periodo
                    eMateriasAsignadas = eMatricula.materiaasignada_set.filter(status=True, retiramateria=False)
                    calendario = calendar.Calendar()
                    fecha = datetime.now().date()
                    # numerosemana = fecha.isocalendar()[1]
                    aCalendario = []
                    for semanas in calendario.monthdatescalendar(fecha.year, fecha.month):
                        dia = 0
                        numerosemana = semanas[0].isocalendar()[1]
                        aActividades = None
                        eTestSilaboSemanales = None
                        eExposicionSilaboSemanales = None
                        eTallerSilaboSemanales = None
                        eTareaSilaboSemanales = None
                        eTrabajoInvestigacionSilaboSemanales = None
                        eAnalisisCasosSilaboSemanales = None
                        eForoSilaboSemanales = None
                        eTareaPracticaSilaboSemanales = None
                        for eMateriaAsignada in eMateriasAsignadas:
                            eMateria = eMateriaAsignada.materia
                            eProfesor = eMateria.profesor_principal()
                            for eSilabo in eMateria.silabo_set.filter(profesor=eProfesor, status=True):
                                eAprobarSilabo = eMateria.tiene_silabo_aprobado(eProfesor.id)
                                tieneAprobadoSilabo = True if eSilabo.codigoqr else True if eAprobarSilabo else False
                                if tieneAprobadoSilabo:
                                    eSilaboSemanales = eSilabo.silabosemanal_set.filter(status=True)
                                    numerosemanaactual = numerosemana
                                    eSilaboSemanales = eSilaboSemanales.filter(semana__in=[numerosemanaactual])
                                    for eSilaboSemanal in eSilaboSemanales.order_by('semana'):
                                        eTestSilaboSemanales = TestSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal)
                                        eExposicionSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal, actividad_id=2)
                                        eTallerSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal, actividad_id=3)
                                        eTareaSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal, actividad_id=5)
                                        eTrabajoInvestigacionSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal, actividad_id=7)
                                        eAnalisisCasosSilaboSemanales = TareaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal, actividad_id=8)
                                        eForoSilaboSemanales = ForoSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal)
                                        eTareaPracticaSilaboSemanales = TareaPracticaSilaboSemanal.objects.filter(Q(estado_id=4) | Q(estado__migramoodle=True), silabosemanal=eSilaboSemanal)

                        aSemana = []
                        for f in semanas:
                            dia += 1
                            ############################################################################################
                            # TEST
                            aTests = []
                            if not eTestSilaboSemanales is None:
                                for eTestSilaboSemanal in eTestSilaboSemanales:
                                    if eTestSilaboSemanal.fechadesde >= f and eTestSilaboSemanal.fechahasta <= f:
                                        aTests.append(TestSilaboSemanalSerializer(eTestSilaboSemanal).data)
                            ############################################################################################
                            # EXPOSICIONES
                            aExposiciones = []
                            if not eExposicionSilaboSemanales is None:
                                for eExposicionSilaboSemanal in eExposicionSilaboSemanales:
                                    if eExposicionSilaboSemanal.fechadesde >= f and eExposicionSilaboSemanal.fechahasta <= f:
                                        aExposiciones.append(TareaSilaboSemanalSerializer(eExposicionSilaboSemanal).data)
                            ############################################################################################
                            # TALLERES
                            aTalleres = []
                            if not eTallerSilaboSemanales is None:
                                for eTallerSilaboSemanal in eTallerSilaboSemanales:
                                    if eTallerSilaboSemanal.fechadesde >= f and eTallerSilaboSemanal.fechahasta <= f:
                                        aTalleres.append(TareaSilaboSemanalSerializer(eTallerSilaboSemanal).data)
                            ############################################################################################
                            # TAREAS
                            aTareas = []
                            if not eTareaSilaboSemanales is None:
                                for eTareaSilaboSemanal in eTareaSilaboSemanales:
                                    if eTareaSilaboSemanal.fechadesde >= f and eTareaSilaboSemanal.fechahasta <= f:
                                        aTareas.append(TareaSilaboSemanalSerializer(eTareaSilaboSemanal).data)
                            ############################################################################################
                            # TRABAJOS DE INVESTIGACION
                            aTrabajosInvesigacion = []
                            if not eTrabajoInvestigacionSilaboSemanales is None:
                                for eTrabajoInvestigacionSilaboSemanal in eTrabajoInvestigacionSilaboSemanales:
                                    if eTrabajoInvestigacionSilaboSemanal.fechadesde >= f and eTrabajoInvestigacionSilaboSemanal.fechahasta <= f:
                                        aTrabajosInvesigacion.append(TareaSilaboSemanalSerializer(eTallerSilaboSemanal).data)
                            ############################################################################################
                            # ANALISIS DE CASOS
                            aAnalisisCasos = []
                            if not eAnalisisCasosSilaboSemanales is None:
                                for eAnalisisCasosSilaboSemanal in eAnalisisCasosSilaboSemanales:
                                    if eAnalisisCasosSilaboSemanal.fechadesde >= f and eAnalisisCasosSilaboSemanal.fechahasta <= f:
                                        aAnalisisCasos.append(TareaSilaboSemanalSerializer(eAnalisisCasosSilaboSemanal).data)
                            ############################################################################################
                            # FOROS
                            aForos = []
                            if not eForoSilaboSemanales is None:
                                for eForoSilaboSemanal in eForoSilaboSemanales:
                                    if eForoSilaboSemanal.fechadesde >= f and eForoSilaboSemanal.fechahasta <= f:
                                        aForos.append(ForoSilaboSemanalSerializer(eForoSilaboSemanal).data)
                            ############################################################################################
                            # TRABAJOS PRACTICOS
                            aTareasPracticas = []
                            if not eTareaPracticaSilaboSemanales is None:
                                for eTareaPracticaSilaboSemanal in eTareaPracticaSilaboSemanales:
                                    if eTareaPracticaSilaboSemanal.fechadesde >= f and eTareaPracticaSilaboSemanal.fechahasta <= f:
                                        aTareasPracticas.append(TareaPracticaSilaboSemanalSerializer(eTareaPracticaSilaboSemanal).data)
                            aActividades.append({"aTests": aTests,
                                                 "aExposiciones": aExposiciones,
                                                 "aTalleres": aTalleres,
                                                 "aTareas": aTareas,
                                                 "aTrabajosInvesigacion": aTrabajosInvesigacion,
                                                 "aAnalisisCasos": aAnalisisCasos,
                                                 "aForos": aForos,
                                                 "aTareasPracticas": aTareasPracticas,
                                                 })
                            aSemana.append([{"dia": dia, "fecha": f, "actividades": aActividades}])
                        aCalendario.append(aSemana)
                    print(aCalendario)

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'descargaractividades':
                with transaction.atomic():
                    try:
                        materia = MateriaAsignada.objects.get(id=encrypt(eRequest.get('idmateriaasignada', encrypt('0'))), status=True).materia
                        silabo = materia.silabo_set.filter(status=True).order_by('-id').first()
                        url = '/media/recursos_zip/silabo_%s.zip' % (encrypt(silabo.id))
                        data = {}
                        data['horasegundo'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                        data['persona'] = materia.profesor_principal()
                        data['profesor'] = profesor = materia.profesor_principal()
                        # directory_principal = os.path.join(SITE_STORAGE, 'media', 'recursos_zip')
                        # try:
                        #     os.stat(directory_principal)
                        # except:
                        #     os.mkdir(directory_principal)

                        fantasy_zip = zipfile.ZipFile(SITE_STORAGE + url, 'w')
                        for tarea in TareaSilaboSemanal.objects.filter(status=True, silabosemanal__silabo=silabo):
                            nombredocumento_tarea = u"%s_%s" % (remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((tarea.nombre.__str__()).replace(' ', '_'))), random.randint(1, 100000).__str__())
                            ruta2_tarea = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((tarea.silabosemanal.silabo.materia.asignatura.__str__()).replace(' ', '_')))

                            directory = os.path.join(SITE_STORAGE, 'media', 'reportetareasilabo', ruta2_tarea)
                            try:
                                os.stat(directory)
                            except:
                                os.mkdir(directory)

                            valida_tarea = conviert_html_to_pdf_parametros_save('pro_planificacion/reporte_tarea_pdf.html', {'pagesize': 'A4', 'data': data, },
                                                                                nombredocumento_tarea, 'reportetareasilabo', ruta2_tarea)
                            if valida_tarea:
                                tarea.reportetareasilabo = u"reportetareasilabo/%s/%s.pdf" % (ruta2_tarea, nombredocumento_tarea)
                                tarea.save(request)

                            if tarea.reportetareasilabo:
                                ext = tarea.reportetareasilabo.__str__()[tarea.reportetareasilabo.__str__().rfind("."):]
                                fantasy_zip.write(SITE_STORAGE + "/media/"+str(tarea.reportetareasilabo), '%s%s' % (tarea.nombre.replace(' ', '_'), ext.lower()))

                        for practica in TareaPracticaSilaboSemanal.objects.filter(status=True, silabosemanal__silabo=silabo):
                            nombredocumento_pract = u"%s_%s" % (remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((practica.nombre.__str__()).replace(' ', '_'))), random.randint(1, 100000).__str__())
                            ruta2_pract = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((practica.silabosemanal.silabo.materia.asignatura.__str__()).replace(' ', '_')))
                            directory = os.path.join(SITE_STORAGE, 'media', 'reportetareapractica', ruta2_pract)
                            try:
                                os.stat(directory)
                            except:
                                os.mkdir(directory)
                            valida_pract = conviert_html_to_pdf_parametros_save('pro_planificacion/reporte_trabajopractico_pdf.html',
                                                                                {'pagesize': 'A4', 'data': data, },
                                                                                nombredocumento_pract, 'reportetareapractica', ruta2_pract)
                            if valida_pract:
                                practica.reportetareapracticasilabo = u"reportetareapractica/%s/%s.pdf" % (ruta2_pract, nombredocumento_pract)
                                practica.save(request)

                            if practica.reportetareapracticasilabo:
                                ext = practica.reportetareapracticasilabo.__str__()[practica.reportetareapracticasilabo.__str__().rfind("."):]
                                fantasy_zip.write(SITE_STORAGE + "/media/"+str(practica.reportetareapracticasilabo), '%s%s' % (practica.nombre.replace(' ', '_'), ext.lower()))

                        for foro in ForoSilaboSemanal.objects.filter(status=True, silabosemanal__silabo=silabo):
                            nombredocumento_foro = u"%s_%s" % (remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((foro.nombre.__str__()).replace(' ', '_'))), random.randint(1, 100000).__str__())
                            ruta2_foro = remover_caracteres_tildes_unicode(remover_caracteres_especiales_unicode((foro.silabosemanal.silabo.materia.asignatura.__str__()).replace(' ', '_')))
                            directory = os.path.join(SITE_STORAGE, 'media', 'reporteforosilabo', ruta2_foro)
                            try:
                                os.stat(directory)
                            except:
                                os.mkdir(directory)
                            valida_foro = conviert_html_to_pdf_parametros_save('pro_planificacion/reporte_foro_pdf.html',
                                                                               {'pagesize': 'A4', 'data': data, },
                                                                               nombredocumento_foro, 'reporteforosilabo', ruta2_foro)
                            if valida_foro:
                                foro.reporteforosilabo = u"reporteforosilabo/%s/%s.pdf" % (ruta2_foro, nombredocumento_foro)
                                foro.save(request)

                            if foro.reporteforosilabo:
                                ext = foro.reporteforosilabo.__str__()[foro.reporteforosilabo.__str__().rfind("."):]
                                fantasy_zip.write(SITE_STORAGE + "/media/"+str(foro.reporteforosilabo), '%s%s' % (foro.nombre.replace(' ', '_'), ext.lower()))
                        return Helper_Response(isSuccess=True, data={'url':url}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'descargarrecursos':
                try:
                    materia = MateriaAsignada.objects.get(id=encrypt(eRequest.get('idmateriaasignada', encrypt('0'))), status=True).materia
                    silabo = materia.silabo_set.filter(status=True).order_by('-id').first()
                    url = '/media/recursos_zip/silabo_%s.zip' % (encrypt(silabo.id))
                    data = {}
                    data['horasegundo'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                    data['persona'] = materia.profesor_principal()
                    data['profesor'] = profesor = materia.profesor_principal()
                    # directory_principal = os.path.join(SITE_STORAGE, 'media', 'recursos_zip')
                    # try:
                    #     os.stat(directory_principal)
                    # except:
                    #     os.mkdir(directory_principal)

                    fantasy_zip = zipfile.ZipFile(SITE_STORAGE + url, 'w')
                    for diapositiva in DiapositivaSilaboSemanal.objects.filter(status=True, silabosemanal__silabo=silabo):
                        if diapositiva.archivodiapositiva:
                            ext = diapositiva.archivodiapositiva.__str__()[diapositiva.archivodiapositiva.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + diapositiva.archivodiapositiva.url, '%s%s' % (diapositiva.nombre.replace(' ', '_'), ext.lower()))
                    for compendio in CompendioSilaboSemanal.objects.filter(status=True, silabosemanal__silabo=silabo):
                        if compendio.archivocompendio:
                            ext = compendio.archivocompendio.__str__()[compendio.archivocompendio.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + compendio.archivocompendio.url, '%s%s' % (compendio.descripcion.replace(' ', '_'), ext.lower()))
                        if compendio.archivoplagio:
                            ext = compendio.archivoplagio.__str__()[compendio.archivoplagio.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + compendio.archivoplagio.url, 'archivoplagio%s%s' % (compendio.id, ext.lower()))
                        if compendio.archivo_logo:
                            ext = compendio.archivo_logo.__str__()[compendio.archivo_logo.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + compendio.archivo_logo.url, 'compendio_archivologo%s%s' % (compendio.id, ext.lower()))
                        if compendio.archivo_sin_logo:
                            ext = compendio.archivo_sin_logo.__str__()[compendio.archivo_sin_logo.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + compendio.archivo_sin_logo.url, 'compendio_archivosinlogo%s%s' % (compendio.id, ext.lower()))
                    for guia in GuiaEstudianteSilaboSemanal.objects.filter(status=True, silabosemanal__silabo=silabo):
                        if guia.archivoguiaestudiante:
                            ext = guia.archivoguiaestudiante.__str__()[guia.archivoguiaestudiante.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + guia.archivoguiaestudiante.url, '%s%s' % (guia.observacion.replace(' ', '_'), ext.lower()))
                        if guia.archivo_logo:
                            ext = guia.archivo_logo.__str__()[guia.archivo_logo.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + guia.archivo_logo.url, 'guiaestudiante_archivologo%s%s' % (guia.id, ext.lower()))
                        if guia.archivo_sin_logo:
                            ext = guia.archivo_sin_logo.__str__()[guia.archivo_sin_logo.__str__().rfind("."):]
                            fantasy_zip.write(SITE_STORAGE + guia.archivo_sin_logo.url, 'guiaestudiante_archivosinlogo%s%s' % (guia.id, ext.lower()))
                    return Helper_Response(isSuccess=True, data={'url':url}, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'certiderechoregresado':
                try:
                    inscripcion = Inscripcion.objects.get(id=int(encrypt(eRequest['idinscripcion'])))
                    if inscripcion.egresadocderecho:
                        ePersona = inscripcion.persona
                        data = {}
                        data['nombres'] = ePersona.nombre_completo()
                        data['fechaemision'] = datetime.now().strftime('%d/%m/%Y %I.%M %p')
                        data['user'] = inscripcion.persona.usuario
                        data['firmasecretaria'] = str(FirmaCertificadoSecretaria.objects.filter(areafirma=1, activo=True, status=True).first().persona.firmapersona_set.first().firma.url)

                        url_path = 'http://127.0.0.1:8000'
                        if not DEBUG:
                            url_path = 'https://sga.unemi.edu.ec'
                        fileName = f'{ahora.strftime("%Y_%m_%d__%H_%M_%S")}'
                        folder_comprobante = os.path.join(
                            os.path.join(SITE_STORAGE, 'media', 'certificado', 'egresadoderecho', ePersona.documento(),
                                         str(ahora.year), f'{ahora.month:02d}', f'{ahora.day:02d}', 'pdf', ''))
                        ruta_pdf = folder_comprobante + fileName + '.pdf'
                        url_pdf = f'{url_path}/media/certificado/egresadoderecho/{ePersona.documento()}/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileName}.pdf'
                        url_pdf_final = f'/media/certificado/egresadoderecho/{ePersona.documento()}/{str(ahora.year)}/{ahora.month:02d}/{ahora.day:02d}/pdf/{fileName}.pdf'
                        if os.path.isfile(ruta_pdf):
                            os.remove(ruta_pdf)
                        os.makedirs(folder_comprobante, exist_ok=True)


                        result = conviert_html_to_pdf_save_path(request=None,
                                                                template_path='pregrado/aulavirtual/egresado_derecho/egresado_derecho.html',
                                                                context_dict={
                                                                    'pagesize': 'A4',
                                                                    'data': data,
                                                                }, output_folder=folder_comprobante,
                                                                fileName=f"{fileName}.pdf", css=None)
                        isSuccess = result.get('isSuccess', False)
                        filepdf = result.get('data',{}).get('filepdf',{}).name

                        return Helper_Response(isSuccess=True, data={'url': url_pdf_final, }, )
                    else:
                        raise NameError(f'No está egresado de la carrera de derecho')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveSedeExamen':
                with transaction.atomic():
                    try:
                        payload = request.auth.payload
                        if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                            eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
                        eInscripcion = eMatricula.inscripcion
                        sedevirtual_id = eRequest.get('sedevirtual_id', 0)
                        try:
                            eSedeVirtual = SedeVirtual.objects.get(pk=sedevirtual_id)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la sede")
                        try:
                            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=eMatricula.id)
                        except ObjectDoesNotExist:
                            eMatriculaSedeExamen = MatriculaSedeExamen(matricula_id=eMatricula.id)
                        eMatriculaSedeExamen.sede = eSedeVirtual
                        if eInscripcion.es_admision():
                            eMatriculaSedeExamen.detallemodeloevaluativo_id = 114
                        else:
                            eMatriculaSedeExamen.detallemodeloevaluativo_id = 37
                        eMatriculaSedeExamen.save(request)
                        log(u'Selecciona sede de examen final: %s ' % eMatriculaSedeExamen, request, "add")
                        return Helper_Response(isSuccess=True, data={'msg': 'Exito en tu semana exámenes'}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDataArchivoIdentidad':
                with transaction.atomic():
                    try:
                        payload = request.auth.payload
                        if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                            eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
                        eInscripcion = eMatricula.inscripcion
                        try:
                            eSedeVirtual = SedeVirtual.objects.get(pk=1)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la sede")
                        try:
                            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=eMatricula.id)
                        except ObjectDoesNotExist:
                            eMatriculaSedeExamen = MatriculaSedeExamen(matricula_id=eMatricula.id,
                                                                       sede=eSedeVirtual)
                            if eInscripcion.es_admision():
                                eMatriculaSedeExamen.detallemodeloevaluativo_id = 114
                            else:
                                eMatriculaSedeExamen.detallemodeloevaluativo_id = 37
                            eMatriculaSedeExamen.save(request)
                            log(u'Sede de examen final: %s se asigno automaticamente' % eMatriculaSedeExamen, request, "add")
                        eMatriculaSedeExamen = MatriculaSedeExamenSerializer(eMatriculaSedeExamen).data
                        return Helper_Response(isSuccess=True, data={'eMatriculaSedeExamen': eMatriculaSedeExamen}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveMatriculaSedeExamenDocumentoIdentidad':
                with transaction.atomic():
                    try:

                        if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                            eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
                        eInscripcion = eMatricula.inscripcion
                        try:
                            eSedeVirtual = SedeVirtual.objects.get(pk=1)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la sede")
                        try:
                            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=eMatricula.id)
                        except ObjectDoesNotExist:
                            eMatriculaSedeExamen = MatriculaSedeExamen(matricula_id=eMatricula.id,
                                                                       sede=eSedeVirtual)
                            if eInscripcion.es_admision():
                                eMatriculaSedeExamen.detallemodeloevaluativo_id = 114
                            else:
                                eMatriculaSedeExamen.detallemodeloevaluativo_id = 37
                            eMatriculaSedeExamen.save(request)
                            log(u'Sede de examen final: %s se asigno automaticamente' % eMatriculaSedeExamen, request, "add")
                        archivoidentidad = eFiles.get('archivoidentidad', None)
                        if archivoidentidad is None:
                            if not eMatriculaSedeExamen.archivoidentidad:
                                ePersonaDocumentoPersonal = eMatriculaSedeExamen.matricula.inscripcion.persona.documentos_personales()
                                if ePersonaDocumentoPersonal is None:
                                    raise NameError(u"Archivo de documento de identidad es requerido")
                                if not ePersonaDocumentoPersonal.cedula:
                                    raise NameError(u"Archivo de documento de identidad es requerido")
                                new_archivoidentidad = ContentFile(ePersonaDocumentoPersonal.cedula.file.read())
                                new_archivoidentidad.name = generar_nombre("documento_", os.path.basename(ePersonaDocumentoPersonal.cedula.name))
                                eMatriculaSedeExamen.archivoidentidad = new_archivoidentidad
                                eMatriculaSedeExamen.save(request)
                                log(u'Adiciono documento de identidad al proceso de matrícula sede examen: %s' % eMatriculaSedeExamen, request, "add")
                                utilizararchivo = eRequest.get('utilizararchivo', 'false') == 'true'
                        else:
                            extensionDocumento = archivoidentidad._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if archivoidentidad.size > 15000000:
                                raise NameError(u"Archivo de documento, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() == 'pdf':
                                raise NameError(u"Archivo de documento, solo se permiten archivos formato pdf")
                            archivoidentidad._name = generar_nombre("documento_", archivoidentidad._name)
                            eMatriculaSedeExamen.archivoidentidad = archivoidentidad
                            eMatriculaSedeExamen.save(request)
                            log(u'Adiciono documento de identidad al proceso de matrícula sede examen: %s' % eMatriculaSedeExamen, request, "add")
                            ePersonaDocumentoPersonal = eMatriculaSedeExamen.matricula.inscripcion.persona.documentos_personales()
                            archivoidentidad._name = generar_nombre("dp_documento_", archivoidentidad._name)
                            if ePersonaDocumentoPersonal is None:
                                ePersonaDocumentoPersonal = PersonaDocumentoPersonal(persona=eMatriculaSedeExamen.matricula.inscripcion.persona,
                                                                                     cedula=archivoidentidad,
                                                                                     estadocedula=1)
                                ePersonaDocumentoPersonal.save(request)
                            else:
                                utilizararchivo = eRequest.get('utilizararchivo', 'false') == 'true'
                                if not ePersonaDocumentoPersonal.cedula or utilizararchivo:
                                    ePersonaDocumentoPersonal.cedula = archivoidentidad
                                    ePersonaDocumentoPersonal.estadocedula = 1
                                    ePersonaDocumentoPersonal.save(request)

                        eMatriculaSedeExamen = MatriculaSedeExamenSerializer(eMatriculaSedeExamen).data
                        return Helper_Response(isSuccess=True, data={'eMatriculaSedeExamen': eMatriculaSedeExamen}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveMatriculaSedeExamenFotoPerfil':
                with transaction.atomic():
                    try:
                        if cache.has_key(f"matricula_id_{payload['matricula']['id']}"):
                            eMatricula = cache.get(f"matricula_id_{payload['matricula']['id']}")
                        else:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, tiempo_cache)
                        eInscripcion = eMatricula.inscripcion
                        try:
                            eSedeVirtual = SedeVirtual.objects.get(pk=1)
                        except ObjectDoesNotExist:
                            raise NameError(u"No se encontro la sede")
                        try:
                            eMatriculaSedeExamen = MatriculaSedeExamen.objects.get(matricula_id=eMatricula.id)
                        except ObjectDoesNotExist:
                            eMatriculaSedeExamen = MatriculaSedeExamen(matricula_id=eMatricula.id,
                                                                       sede=eSedeVirtual)
                            if eInscripcion.es_admision():
                                eMatriculaSedeExamen.detallemodeloevaluativo_id = 114
                            else:
                                eMatriculaSedeExamen.detallemodeloevaluativo_id = 37
                            eMatriculaSedeExamen.save(request)
                            log(u'Sede de examen final: %s se asigno automaticamente' % eMatriculaSedeExamen, request, "add")
                        ePersona = eMatriculaSedeExamen.matricula.inscripcion.persona
                        archivofoto = eFiles.get('archivofoto', None)
                        if archivofoto is None:
                            if not eMatriculaSedeExamen.archivofoto:
                                if not ePersona.tiene_foto():
                                    raise NameError(u"Imagen de perfil es requerido")
                                eFotoPersona = ePersona.foto()
                                new_foto = ContentFile(eFotoPersona.foto.file.read())
                                new_foto.name = generar_nombre("foto_", os.path.basename(eFotoPersona.foto.name))
                                eMatriculaSedeExamen.archivofoto = new_foto
                                eMatriculaSedeExamen.save(request)
                                log(u'Adiciono foto de perfil al proceso de matrícula sede examen: %s' % eMatriculaSedeExamen, request, "add")
                        else:
                            extensionFoto = archivofoto._name.split('.')
                            tamFoto = len(extensionFoto)
                            exteFoto = extensionFoto[tamFoto - 1]
                            if archivofoto.size > 1500000:
                                raise NameError(u"Foto de perfil, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteFoto.lower() in ['jpg']:
                                raise NameError(u"Foto de perfil, solo se permiten archivos .jpg")
                            archivofoto._name = generar_nombre("foto_", archivofoto._name)
                            eMatriculaSedeExamen.archivofoto = archivofoto
                            eMatriculaSedeExamen.save(request)
                            log(u'Adiciono foto de perfil al proceso de matrícula sede examen: %s' % eMatriculaSedeExamen, request, "add")
                            if not ePersona.tiene_foto():
                                eFotoPersona = ePersona.foto(nFile=archivofoto, request=request)
                                make_thumb_picture(ePersona)
                                if GENERAR_TUMBAIL:
                                    make_thumb_fotopersona(ePersona)
                                log(u'Adicionó foto de persona: %s' % eFotoPersona, request, "add")
                            else:
                                utilizarfoto = eRequest.get('utilizarfoto', 'false') == 'true'
                                if utilizarfoto:
                                    eFotoPersona = ePersona.foto(nFile=archivofoto, request=request)
                                    make_thumb_picture(ePersona)
                                    if GENERAR_TUMBAIL:
                                        make_thumb_fotopersona(ePersona)
                                    log(u'Edito foto de perfil al proceso de matrícula sede examen: %s' % eMatriculaSedeExamen, request, "edit")

                        eMatriculaSedeExamen = MatriculaSedeExamenSerializer(eMatriculaSedeExamen).data
                        return Helper_Response(isSuccess=True, data={'eMatriculaSedeExamen': eMatriculaSedeExamen}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            ahora = datetime.now()
            fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
            tiempo_cache = fecha_fin - ahora
            tiempo_cache = int(tiempo_cache.total_seconds())
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, tiempo_cache)
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            id_matricula = payload['matricula'].get('id', encrypt(0))
            if id_matricula == 0:
                raise NameError(u'No se encuentra matriculado.')
            if cache.has_key(f"matricula_id_{id_matricula}"):
                eMatricula = cache.get(f"matricula_id_{id_matricula}")
            else:
                try:
                    eMatricula = Matricula.objects.db_manager("sga_select").get(pk=int(encrypt(id_matricula)))
                    cache.set(f"matricula_id_{id_matricula}", eMatricula, tiempo_cache)
                except ObjectDoesNotExist:
                    eMatricula = None
            eInscripcion = eMatricula.inscripcion
            ePersona = eInscripcion.persona
            ePeriodo = eMatricula.nivel.periodo
            confirmar_automatricula_pregrado = eInscripcion.tiene_automatriculapregrado_por_confirmar(ePeriodo)
            if confirmar_automatricula_pregrado:
                mat = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                if mat.nivel.fechainicioagregacion > datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de aceptación de matrícula empieza {mat.nivel.fechainicioagregacion.__str__()}",
                                           status=status.HTTP_200_OK)
                if mat.nivel.fechafinagregacion < datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",
                                           status=status.HTTP_200_OK)
                if PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo, status=True).exists():
                    ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=ePeriodo, status=True)[0]
                    if not ePeriodoMatricula.activo:
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de matrícula se encuentra inactivo",
                                               status=status.HTTP_200_OK)
                return Helper_Response(isSuccess=False, redirect="alu_matricula", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de matrícula se encuentra activo debe aceptar la automatricula",
                                       status=status.HTTP_200_OK)

            # automatricula de admisión
            confirmar_automatricula_admision = eInscripcion.tiene_automatriculaadmision_por_confirmar(ePeriodo)
            if confirmar_automatricula_admision:
                mat = eInscripcion.mi_matricula_periodo(ePeriodo.id)
                if mat.nivel.fechainicioagregacion > datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de aceptación de matrícula empieza {mat.nivel.fechainicioagregacion.__str__()}",
                                           status=status.HTTP_200_OK)
                if mat.nivel.fechafinagregacion < datetime.now().date():
                    return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                           message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",
                                           status=status.HTTP_200_OK)
                if PeriodoMatricula.objects.values("id").filter(periodo=ePeriodo, status=True).exists():
                    ePeriodoMatricula = PeriodoMatricula.objects.filter(periodo=ePeriodo, status=True)[0]
                    if not ePeriodoMatricula.activo:
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                               message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de matrícula se encuentra inactivo",
                                               status=status.HTTP_200_OK)
                return Helper_Response(isSuccess=False, redirect="alu_matricula", module_access=False,
                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de matrícula se encuentra activo debe aceptar la automatricula",
                                       status=status.HTTP_200_OK)
            if cache.has_key(f"periodo_id_{encrypt(ePeriodo.id)}_serealizer"):
                ePeriodo_serealizer = cache.get(f"periodo_id_{encrypt(ePeriodo.id)}_serealizer")
            else:
                ePeriodo_serealizer = PeriodoSerializer(ePeriodo).data
                cache.set(f"periodo_id_{encrypt(ePeriodo.id)}_serealizer", ePeriodo_serealizer, tiempo_cache)

            if cache.has_key(f"matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual"):
                eMatricula_serializer = cache.get(f"matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual")
            else:
                eMatricula_serializer = MatriculaSerializer(eMatricula).data
                cache.set(f"matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual", eMatricula_serializer, tiempo_cache)

            if cache.has_key(f"materiaasignada__matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual"):
                eMateriasAsignadas_serializer = cache.get(f"materiaasignada__matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual")
            else:
                eMateriasAsignadas = eMatricula.materias().filter(retiramateria=False).order_by('materia__inicio')
                eMateriasAsignadas_serializer = MatriculaMateriaAsignadaSerializer(eMateriasAsignadas, many=True).data if eMateriasAsignadas.values("id").exists() else []
                cache.set(f"materiaasignada__matricula_id_{encrypt(eMatricula.id)}_serealizer_aulavirtual", eMateriasAsignadas_serializer, tiempo_cache)

            eMalla = eInscripcion.mi_malla()
            if cache.has_key(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_aulavirtual"):
                eMalla_serializar = cache.get(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_aulavirtual")
            else:
                eMalla_serializar = MallaSerializer(eMalla).data
                cache.set(f"malla__inscripcion_id_{encrypt(eInscripcion.id)}_serealizer_aulavirtual", eMalla_serializar, tiempo_cache)

            es_admision = eInscripcion.es_admision()
            es_pregrado = eInscripcion.es_pregrado()
            data = {
                'eMateriasAsignadas': eMateriasAsignadas_serializer,
                # 'usa_planificacion': usa_planificacion,
                'eMatricula': eMatricula_serializer,
                'ePeriodo': ePeriodo_serealizer,
                'es_admision': es_admision,
                'es_pregrado': es_pregrado,
                'eMalla': eMalla_serializar,
                'eInscripcion': InscripcionSerializer(eInscripcion).data,
                'coordinacion_detalles':eInscripcion.mi_coordinacion().id,
                'puede_elegir_sede_examen': variable_valor('PUEDE_ELEGIR_SEDE_EXAMEN_FINAL'),
                'admision_visualiza_materias': variable_valor('ADMISION_VISUALIZA_MATERIAS')

            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
