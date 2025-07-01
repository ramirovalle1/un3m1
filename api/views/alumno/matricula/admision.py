# coding=utf-8
from datetime import datetime
from django.db import transaction
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.views.alumno.matricula.functions import validate_entry_to_student_api
from api.serializers.alumno.matriculacion import MatriInscripcionSerializer, MatriPeriodoMatriculaSerializer, \
    MatriInscripcionMallaSerializer, MatriNivelMallaSerializer, MatriMateriaAsignadaSerializer, \
    MatriMallaSerializer, MatriCarreraSerializer, MatriPersonaSerializer, MatriculaSerializer, \
    MatriRazaSerializer, MatriPerfilInscripcionSerializer, MatriDiscapacidadSerializer, \
    MatriInstitucionBecaSerializer, MatriNacionalidadIndigenaSerializer, MatriCredoSerializer, \
    MatriPersonaReligionSerializer, PaisSerializer, MigrantePersonaSerializer
from matricula.models import PeriodoMatricula
from sagest.models import Rubro
from sga.funciones import log, generar_nombre, convertir_fecha_invertida
from sga.models import Inscripcion, PerfilUsuario, Periodo, ConfirmarMatricula, Matricula, \
    AuditoriaMatricula, Raza, PerfilInscripcion, Discapacidad, InstitucionBeca, NacionalidadIndigena, \
    TipoArchivo, Archivo, HistorialPersonaPPL, Credo, ESTADOS_PERMANENCIA, Pais
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache


CASO_ULTIMA_MATRICULA_ID = 1
EJE_FORMATIVO_PRACTICAS = 9
EJE_FORMATIVO_VINCULACION = 11
EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]


class MatriculaAdmisionAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    parser_class = (MultiPartParser, FormParser,)
    api_key_module = 'ALUMNO_MATRICULA'

    @api_security
    def post(self, request, format=None, *args, **kwargs):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            hoy = datetime.now()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'admision')
            if not valid:
                raise NameError(msg_error)
            ePeriodo = None
            if 'id' in payload['periodo']:
                if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                    ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                else:
                    ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodoMatricula = None
            eMatricula = None
            if not 'action' in eRequest:
                raise NameError(u'Acción no permitida')
            action = eRequest.get('action')
            if not action:
                raise NameError(u'Acción no permitida')

            elif action == 'saveInformacionPersonal':
                with transaction.atomic():
                    try:
                        if not ePeriodo:
                            raise NameError(u"Periodo no encontrado")
                        if not eInscripcion:
                            raise NameError(u"Inscripción no encontrada")
                        eMatricula = Matricula.objects.filter(nivel__periodo=ePeriodo, inscripcion=eInscripcion, status=True)
                        if not Matricula.objects.values("id").filter(nivel__periodo=ePeriodo, inscripcion=eInscripcion, status=True):
                            raise NameError(u"Matrícula no valida")
                        eMatricula = eMatricula[0]
                        eInscripcion = eMatricula.inscripcion
                        ePersona = eInscripcion.persona
                        if not 'fileDocumento' in eFiles:
                            raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte")

                        nfileDocumento = None
                        if 'fileDocumento' in eFiles:
                            nfileDocumento = eFiles['fileDocumento']
                            extensionDocumento = nfileDocumento._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if nfileDocumento.size > 15000000:
                                raise NameError(u"Error al cargar la cédula/pasaporte, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() == 'pdf':
                                raise NameError(u"Error al cargar la cédula/pasaporte, solo se permiten archivos .pdf")
                        nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)
                        tdocum = TipoArchivo.objects.get(pk=6)
                        if ePersona.tipo_documento() == 'PASAPORTE':
                            tdocum = TipoArchivo.objects.get(pk=3)
                        nombreDocumento = u"Admisión tipo de documento %s de la persona: %s " % (tdocum.nombre, ePersona.__str__())
                        archivoDocumento = Archivo(nombre=nombreDocumento,
                                                   fecha=datetime.now().date(),
                                                   archivo=nfileDocumento,
                                                   tipo=tdocum,  # ARCHIVO_TIPO_GENERAL,
                                                   inscripcion=eInscripcion)
                        archivoDocumento.save(request)
                        if not 'sexo_id' in eRequest:
                            raise NameError(u"Favor complete el campo de sexo")
                        if not 'nacimiento' in eRequest:
                            raise NameError(u"Favor complete el campo de fecha de nacimiento")
                        if not 'correo' in eRequest:
                            raise NameError(u"Favor complete el campo de correo personal")
                        if not 'lgtbi' in eRequest:
                            raise NameError(u"Favor complete el campo de LGTBI")
                        if not 'es_zurda' in eRequest:
                            raise NameError(u"Favor complete el campo de es zurda")
                        ePersona.sexo_id = int(eRequest.get("sexo_id"))
                        ePersona.nacimiento = convertir_fecha_invertida(eRequest.get("nacimiento"))
                        ePersona.email = eRequest.get("correo")
                        ePersona.lgtbi = eRequest.get("lgtbi") == 'true'
                        ePersona.eszurdo = eRequest.get("es_zurda") == 'true'

                        nfileBachiller = None
                        if not 'fileBachiller' in eFiles:
                            raise NameError(u"Favor complete el campo de archivo de bachiller")
                        nfileBachiller = eFiles['fileBachiller']
                        extensionBachiller = nfileBachiller._name.split('.')
                        tamBachiller = len(extensionBachiller)
                        exteBachiller = extensionBachiller[tamBachiller - 1]
                        if nfileBachiller.size > 15000000:
                            raise NameError(u"Error al cargar el documento de bachiller, el tamaño del archivo es mayor a 15 Mb.")
                        if not exteBachiller.lower() == 'pdf':
                            raise NameError(u"Error al cargar el el documento de bachiller, solo se permiten archivos .pdf")

                        nfileBachiller._name = generar_nombre("dp_actagradobachiller", nfileBachiller._name)
                        if not 'tipoDocumentoGradoBachiller' in eRequest:
                            raise NameError(u"Favor complete campo de tipo de documento de bachiller")
                        tacta = TipoArchivo.objects.get(pk=int(eRequest.get('tipoDocumentoGradoBachiller')))
                        nombreBachiller = "Admisión tipo documento %s de la persona: %s " % (tacta.nombre, ePersona.__str__())
                        archivoBachiller = Archivo(nombre=nombreBachiller,
                                                   fecha=datetime.now().date(),
                                                   archivo=nfileBachiller,
                                                   tipo=tacta,  # ARCHIVO_TIPO_GENERAL,
                                                   inscripcion=eInscripcion)
                        archivoBachiller.save(request)

                        if not 'es_migrante' in eRequest:
                            raise NameError(u"Favor complete el campo de Residente en otro pais")

                        es_migrante = eRequest['es_migrante'] == 'true'
                        if es_migrante:
                            if not 'fileMigrante' in eFiles:
                                raise NameError(u"Por favor suba documento de persona en el exterior")
                            nfileMigrante = None
                            nfileMigrante = eFiles['fileMigrante']
                            extensionMigrante = nfileMigrante._name.split('.')
                            tamMigrante = len(extensionMigrante)
                            exteMigrante = extensionMigrante[tamMigrante - 1]
                            if nfileMigrante.size > 15000000:
                                raise NameError(u"Error al cargar el documento de persona en el exterior, el tamaño del archivo es mayor a 4 Mb.")
                            if not exteMigrante.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de persona en el exterior, solo se permiten archivos .pdf")
                            nfileMigrante = eFiles['fileMigrante']
                            nfileMigrante._name = generar_nombre("archivomigrante_", nfileMigrante._name)
                            if not 'pais_residencia' in eRequest:
                                raise NameError(u"Favor complete el campo de pais residencia en el exterior")
                            if not 'estado_permanencia' in eRequest:
                                raise NameError(u"Favor complete el campo de estado de permanencia en el exterior")
                            anios_residencia = 0
                            meses_residencia = 0
                            if int(eRequest['estado_permanencia']) == 1:
                                if not 'anios_residencia' in eRequest:
                                    raise NameError(u"Favor complete el campo de años de residencia en el exterior")
                                if not eRequest['anios_residencia'].isdigit():
                                    raise NameError(u"El campo de años de residencia en el exterior debe ser numérico")
                                if not 'meses_residencia' in eRequest:
                                    raise NameError(u"Favor complete el campo de meses de residencia en el exterior")
                                if not eRequest['meses_residencia'].isdigit():
                                    raise NameError(u"El campo de meses de residencia en el exterior debe ser numérico")
                                anios_residencia = int(eRequest['anios_residencia'])
                                meses_residencia = int(eRequest['meses_residencia'])

                            es_nuevo = False
                            eMigrantePersona = ePersona.migrantepersona_set.filter(status=True).first()
                            if eMigrantePersona is None:
                                es_nuevo = True
                                eMigrantePersona = ePersona.migrantepersona_set.model()
                                eMigrantePersona.persona = ePersona
                            eMigrantePersona.paisresidencia_id = int(encrypt(eRequest['pais_residencia']))
                            eMigrantePersona.estadopermanencia = int(eRequest['estado_permanencia'])
                            eMigrantePersona.fecharetorno = eRequest['fecha_retorno'] if eRequest['fecha_retorno'] else None
                            eMigrantePersona.anioresidencia = anios_residencia
                            eMigrantePersona.mesresidencia = meses_residencia
                            eMigrantePersona.archivo = nfileMigrante
                            eMigrantePersona.estadoarchivo = 1
                            eMigrantePersona.save(request)
                            log(u'%s registro Migrante Persona desde matrícula admisión: %s' % ('Adiciono' if es_nuevo else 'Edito', ePersona), request, "add" if es_nuevo else "edit")
                        if not 'es_ppl' in eRequest:
                            raise NameError(u"Favor complete el campo de PPL")
                        es_ppl = eRequest['es_ppl'] == 'true'
                        ePersona.ppl = es_ppl
                        if es_ppl:
                            if not 'filePPL' in eFiles:
                                raise NameError(u"Por favor suba documento de persona privadad de la libertad")
                            nfilePPL = None
                            nfilePPL = eFiles['filePPL']
                            extensionPPL = nfilePPL._name.split('.')
                            tamPPL = len(extensionPPL)
                            extePLL = extensionPPL[tamPPL - 1]
                            if nfilePPL.size > 15000000:
                                raise NameError(u"Error al cargar el documento de persona privada de libertad, el tamaño del archivo es mayor a 4 Mb.")
                            if not extePLL.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de persona privada de libertad, solo se permiten archivos .pdf")
                            nfilePPL = eFiles['filePPL']
                            nfilePPL._name = generar_nombre("archivoppl_", nfilePPL._name)
                            if not 'fecha_ingreso' in eRequest:
                                raise NameError(u"Favor complete el campo de fecha de ingreso al centro de rehabilitación social")
                            if not 'centro_rehabilitacion_social' in eRequest:
                                raise NameError(u"Favor complete el campo de fecha del centro de rehabilitación social")
                            if not 'lider_educativo' in eRequest:
                                raise NameError(u"Favor complete el campo del lider educativo del centro de rehabilitación social")
                            if not 'lider_educativo_correo' in eRequest:
                                raise NameError(u"Favor complete el campo del correo del lider educativo")
                            if not 'lider_educativo_telefono' in eRequest:
                                raise NameError(u"Favor complete el campo del teléfono del lider educativo")
                            ppl_observacion = None
                            if 'ppl_observacion' in eRequest:
                                ppl_observacion = eRequest['ppl_observacion']
                            fecha_ingreso = convertir_fecha_invertida(eRequest['fecha_ingreso'])
                            centro_rehabilitacion_social = eRequest['centro_rehabilitacion_social']
                            lider_educativo = eRequest['lider_educativo']
                            lider_educativo_correo = eRequest['lider_educativo_correo']
                            lider_educativo_telefono = eRequest['lider_educativo_telefono']
                            if HistorialPersonaPPL.objects.values("id").filter(persona=ePersona, fechaingreso=fecha_ingreso).exists():
                                historialppl = HistorialPersonaPPL.objects.filter(persona=ePersona, fechaingreso=fecha_ingreso)[0]
                                historialppl.observacion = ppl_observacion if ppl_observacion else None
                                historialppl.archivo = nfilePPL
                                historialppl.centrorehabilitacion = centro_rehabilitacion_social if centro_rehabilitacion_social else None
                                historialppl.lidereducativo = lider_educativo if lider_educativo else None
                                historialppl.correolidereducativo = lider_educativo_correo if lider_educativo_correo else None
                                historialppl.telefonolidereducativo = lider_educativo_telefono if lider_educativo_telefono else None
                            else:
                                historialppl = HistorialPersonaPPL(persona=ePersona,
                                                                   observacion=ppl_observacion if ppl_observacion else None,
                                                                   archivo=nfilePPL,
                                                                   fechaingreso=fecha_ingreso,
                                                                   fechasalida=None,
                                                                   centrorehabilitacion=centro_rehabilitacion_social if centro_rehabilitacion_social else None,
                                                                   lidereducativo=lider_educativo if lider_educativo else None,
                                                                   correolidereducativo=lider_educativo_correo if lider_educativo_correo else None,
                                                                   telefonolidereducativo=lider_educativo_telefono if lider_educativo_telefono else None,
                                                                   )
                                historialppl.save(request)
                                log(u'Adiciono registro PPL desde matrícula admisión: %s' % historialppl, request, "add")
                        if ePersona.ppl:
                            ePersona.ppl = False
                            ePersona.observacionppl = None
                            log(u'Edito registro PPL desde matrícula admisión: %s' % ePersona, request, "edit")

                        if not 'credo_id' in eRequest:
                            raise NameError(u"Favor complete el campo de religión")
                        credo_id = int(eRequest.get('credo_id'))
                        ePersona.credo_id = credo_id
                        credo_prohibe = eRequest.get('credo_prohibe') == 'true'
                        if credo_prohibe:
                            if not 'credo_iglesia' in eRequest:
                                raise NameError(u"Favor complete el campo de inglesia/institución")
                            credo_iglesia = eRequest.get('credo_iglesia')
                            if not 'credo_dias' in eRequest:
                                raise NameError(u"Favor complete el campo de días")
                            credo_dias = eRequest.get('credo_dias')
                            credo_observacion = ''
                            if 'credo_observacion' in eRequest:
                                credo_observacion = eRequest.get('credo_observacion')

                            if not 'fileCredo' in eFiles:
                                raise NameError(u"Favor complete el campo archivo de religión")
                            nfileCredo = eFiles['fileCredo']
                            extensionCredo = nfileCredo._name.split('.')
                            tamCredo = len(extensionCredo)
                            exteEtnia = extensionCredo[tamCredo - 1]
                            if nfileCredo.size > 15000000:
                                raise NameError(u"Error al cargar el documento de religión, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteEtnia.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de religión, solo se permiten archivos .pdf")
                            nfileCredo._name = generar_nombre("dp_religion", nfileCredo._name)
                            ePersonaReligion = ePersona.mi_religion()
                            ePersonaReligion.iglesia = credo_iglesia
                            ePersonaReligion.prohibe = credo_prohibe
                            ePersonaReligion.dias = credo_dias
                            ePersonaReligion.archivo = nfileCredo
                            ePersonaReligion.save(request)
                            ePersona.credo_id = credo_id
                            log(u'Actualiza campos de religión de persona en proceso de matrícula: %s' % ePersonaReligion, request, "edit")
                        ePersona.save(request)
                        log(u'Actualiza campos de persona en proceso de matrícula: %s' % ePersona, request, "edit")
                        ePerfilInscripcion = ePersona.mi_perfil()
                        if not 'raza_id' in eRequest:
                            raise NameError(u"Favor complete el campo de etnía")
                        if eRequest['raza_id'] is None or int(eRequest['raza_id']) == 10:
                            raise NameError(u"Favor complete el campo de etnía")
                        raza_id = int(eRequest['raza_id'])
                        ePerfilInscripcion.raza_id = int(eRequest['raza_id'])
                        ePerfilInscripcion.estadoarchivoraza = 4
                        if raza_id == 1:
                            if not 'nacionalidad_indigena_id' in eRequest:
                                raise NameError(u"Favor complete el campo de nacionalidad indigena")
                            if eRequest['nacionalidad_indigena_id'] is None:
                                raise NameError(u"Favor complete el campo de nacionalidad indigena")
                            ePerfilInscripcion.nacionalidadindigena_id = int(eRequest['nacionalidad_indigena_id'])
                            ePerfilInscripcion.estadoarchivoraza = 1

                        if 'fileEtnia' in eFiles:
                            nfileEtnia = eFiles['fileEtnia']
                            extensionEtnia = nfileEtnia._name.split('.')
                            tamEtnia = len(extensionEtnia)
                            exteEtnia = extensionEtnia[tamEtnia - 1]
                            if nfileEtnia.size > 15000000:
                                raise NameError(u"Error al cargar el documento de etnía, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteEtnia.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de etnía, solo se permiten archivos .pdf")
                            nfileEtnia._name = generar_nombre("dp_etnia", nfileEtnia._name)
                            ePerfilInscripcion.archivoraza = nfileEtnia
                            ePerfilInscripcion.estadoarchivoraza = 1

                        if not 'tieneDiscapacidad' in eRequest:
                            raise NameError(u"Favor complete el campo de discapacidad")
                        tieneDiscapacidad = eRequest['tieneDiscapacidad'] == 'true'
                        ePerfilInscripcion.tienediscapacidad = tieneDiscapacidad
                        if tieneDiscapacidad:
                            if not 'discapacidad_id' in eRequest:
                                raise NameError(u"Favor complete el campo del tipo de discapacidad")
                            if not 'porcentaje_discapacidad' in eRequest:
                                raise NameError(u"Favor complete el campo del porcentaje de discapacidad")
                            if not 'num_carnet_discapacidad' in eRequest:
                                raise NameError(u"Favor complete el campo del carné de discapacidad")
                            if not 'entidad_valida_discapacidad' in eRequest:
                                raise NameError(u"Favor complete el campo de la entidad que valida el carné de discapacidad")
                            discapacidad_id = int(eRequest['discapacidad_id'])
                            porcentaje_discapacidad = eRequest['porcentaje_discapacidad']
                            num_carnet_discapacidad = eRequest['num_carnet_discapacidad']
                            entidad_valida_discapacidad = int(eRequest['entidad_valida_discapacidad'])
                            ePerfilInscripcion.tipodiscapacidad_id = discapacidad_id
                            ePerfilInscripcion.porcientodiscapacidad = porcentaje_discapacidad
                            ePerfilInscripcion.carnetdiscapacidad = num_carnet_discapacidad
                            ePerfilInscripcion.institucionvalida_id = entidad_valida_discapacidad
                            if not 'fileDiscapacidad' in eFiles:
                                raise NameError(u"Favor complete el campo del documento de discapacidad")
                            nfileDiscapacidad = eFiles['fileDiscapacidad']
                            extensionDiscapacidad = nfileDiscapacidad._name.split('.')
                            tamDiscapacidad = len(extensionDiscapacidad)
                            exteDiscapacidad = extensionDiscapacidad[tamDiscapacidad - 1]
                            if nfileDiscapacidad.size > 15000000:
                                raise NameError(u"Error al cargar el documento de discpacidad, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteDiscapacidad.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de discpacidad, solo se permiten archivos .pdf")
                            nfileDiscapacidad._name = generar_nombre("dp_discapacidad", nfileDiscapacidad._name)
                            ePerfilInscripcion.archivo = nfileDiscapacidad
                            ePerfilInscripcion.estadoarchivodiscapacidad = 1
                        ePerfilInscripcion.save(request)
                        log(u'Actualiza campos de perfil en proceso de matrícula: %s' % ePerfilInscripcion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al guardar: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'aceptarAutomatricula':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id'])) if 'id' in eRequest and eRequest['id'] else 0
                        if not Inscripcion.objects.filter(pk=id):
                            raise NameError(u"No se reconocio al estudiante.")
                        termino = int(eRequest['termino']) if 'termino' in eRequest and eRequest['termino'] else 0
                        if not Inscripcion.objects.values("id").filter(pk=id):
                            raise NameError(u"No se reconocio al estudiante.")
                        if not termino:
                            raise NameError(u"Debe aceptar los terminos.")
                        inscripcion = Inscripcion.objects.get(pk=id)
                        if not inscripcion.matricula_set.values("id").filter(automatriculaadmision=True, termino=False, nivel__periodo=ePeriodo).exists():
                            raise NameError(u"Debe aceptar los terminos.")
                        matricula = inscripcion.matricula_set.filter(automatriculaadmision=True, termino=False, nivel__periodo=ePeriodo)[0]
                        matricula.termino = True
                        matricula.fechatermino = datetime.now()
                        matricula.save(request)
                        log(u'Acepto los terminos de la matricula: %s' % matricula, request, "edit")
                        if not matricula.confirmarmatricula_set.filter(matricula=matricula):
                            confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
                            confirmar.save(request)
                            log(u'Confirmo la matricula: %s' % confirmar, request, "add")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al guardar: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'rechazoAutomatricula':
                with transaction.atomic():
                    try:
                        id = int(encrypt(eRequest['id'])) if 'id' in eRequest and eRequest['id'] else 0
                        if not Inscripcion.objects.filter(pk=id):
                            raise NameError(u"No se reconocio al estudiante.")
                        inscripcion = Inscripcion.objects.get(pk=id)
                        if not inscripcion.matricula_set.values("id").filter(automatriculaadmision=True, termino=False, nivel__periodo=ePeriodo).exists():
                            raise NameError(u"Debe aceptar los terminos.")
                        matricula = inscripcion.matricula_set.filter(automatriculaadmision=True, termino=False, nivel__periodo=ePeriodo)[0]
                        rubro = Rubro.objects.filter(matricula=matricula, status=True)
                        if rubro:
                            if Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos():
                                raise NameError(u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados.")
                        delmatricula = matricula
                        auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                                       periodo=matricula.nivel.periodo,
                                                       tipo=3)
                        auditoria.save(request)
                        matricula.delete()
                        log(u'Elimino matricula: %s' % delmatricula, request, "del")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al rechazar: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        ahora = datetime.now()
        fecha_fin = datetime(ahora.year, ahora.month, ahora.day, 23, 59, 59)
        tiempo_cache = fecha_fin - ahora
        TIEMPO_ENCACHE = int(tiempo_cache.total_seconds())
        try:
            aData = {}
            hoy = datetime.now().date()
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            valid, msg_error = validate_entry_to_student_api(ePerfilUsuario, 'admision')
            if not valid:
                raise NameError(msg_error)
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            ePeriodoMatricula = None
            eMatricula = None
            ePeriodo = None
            if 'id' in payload['periodo']:
                if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                    ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                else:
                    if payload['periodo']['id'] is None:
                        if not PeriodoMatricula.objects.values("id").filter(tipo=2, activo=True).exists():
                            raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, el periodo de matriculación se encuentra inactivo")
                        ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, tipo=2, activo=True).order_by('-pk')[0]
                        ePeriodo = ePeriodoMatricula.periodo
                    else:
                        ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)

            if not PeriodoMatricula.objects.values('id').filter(status=True, activo=True, tipo=2).exists():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, el periodo de matriculación se encuentra inactivo")
            ePeriodoMatricula = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=2)
            if len(ePeriodoMatricula) > 1:
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, proceso de matriculación no se encuentra activo")
            ePeriodoMatricula = ePeriodoMatricula[0]
            if not ePeriodoMatricula.esta_periodoactivomatricula():
                raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, el periodo de matriculación se encuentra inactivo")
            if ePeriodoMatricula.valida_coordinacion:
                if not eInscripcion.coordinacion in ePeriodoMatricula.coordinaciones():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, su coordinación/facultad no esta permitida para la matriculación")
            if ePeriodoMatricula.periodo and eInscripcion.tiene_automatriculaadmision_por_confirmar(ePeriodoMatricula.periodo):
                eMatricula = Matricula.objects.filter(nivel__periodo=ePeriodoMatricula.periodo, inscripcion=eInscripcion, status=True)[0]
                eMalla = eInscripcion.mi_malla()
                tiene_rubro_pagado_matricula = False
                tiene_rubro_pagado_materias = False
                valor_pagados = 0.0
                valor_pendiente = 0.0
                if eMatricula.rubro_set.values("id").filter(status=True).exists():
                    tiene_rubro_pagado_materias = tiene_rubro_pagado_matricula = eMatricula.tiene_pagos_matricula()
                    valor_pagados = eMatricula.total_pagado_rubro()
                    valor_pendiente = eMatricula.total_saldo_rubro()
                ePersona_serializer = MatriPersonaSerializer(eInscripcion.persona)
                eInscripcion_serializer = MatriInscripcionSerializer(eInscripcion)
                eCarrera_serializer = MatriCarreraSerializer(eInscripcion.carrera)
                ePeriodoMatricula_serializer = MatriPeriodoMatriculaSerializer(ePeriodoMatricula)
                eInscripcionMalla_serializer = MatriInscripcionMallaSerializer(eInscripcion.malla_inscripcion())
                eMalla_serializer = MatriMallaSerializer(eMalla)
                eNivelMalla_serializer = MatriNivelMallaSerializer(eInscripcion.mi_nivel().nivel)
                eMatricula_serializer = MatriculaSerializer(eMatricula)
                eMateriaAsignada_serializer = MatriMateriaAsignadaSerializer(eInscripcion.materias_automatriculaadmision_por_confirmar(ePeriodoMatricula.periodo), many=True)
                eRazas = Raza.objects.filter(status=True)
                eDiscapacidades = Discapacidad.objects.filter(status=True)
                ePerfilInscripcion = PerfilInscripcion.objects.filter(persona=ePersona)
                eInstitucionDiscapacidades = InstitucionBeca.objects.filter(status=True, tiporegistro=2)
                eNacionalidadIndigenas = NacionalidadIndigena.objects.filter(status=True)
                eCredos = Credo.objects.filter(status=True)
                ePersonaReligion = ePersona.mi_religion()
                ePaisesResidenciales = Pais.objects.filter(status=True).exclude(pk=1)
                eMigrnatePersona = ePersona.migrantepersona_set.filter(status=True).first()
                es_admision = eInscripcion.mi_coordinacion().id == 9
                aData['es_admision'] = es_admision
                aData['eRazas'] = MatriRazaSerializer(eRazas, many=True).data if eRazas.values("id").exists() else []
                aData['eCredos'] = MatriCredoSerializer(eCredos, many=True).data if eCredos.values("id").exists() else []
                aData['eDiscapacidades'] = MatriDiscapacidadSerializer(eDiscapacidades, many=True).data if eDiscapacidades.values("id").exists() else []
                aData['lEstadosPermanencia'] = [{'id': id, 'name': name} for id, name in ESTADOS_PERMANENCIA]
                aData['ePaisesResidenciales'] = PaisSerializer(ePaisesResidenciales, many=True).data if ePaisesResidenciales.values("id").exists() else []
                aData['eMigrantePersona'] = MigrantePersonaSerializer(eMigrnatePersona).data if eMigrnatePersona is not None else {}
                aData['ePerfilInscripcion'] = MatriPerfilInscripcionSerializer(ePerfilInscripcion[0]).data if ePerfilInscripcion.values("id").exists() else None
                aData['eInstitucionDiscapacidades'] = MatriInstitucionBecaSerializer(eInstitucionDiscapacidades, many=True).data if eInstitucionDiscapacidades.values("id").exists() else []
                aData['eNacionalidadIndigenas'] = MatriNacionalidadIndigenaSerializer(eNacionalidadIndigenas, many=True).data if eNacionalidadIndigenas.values("id").exists() else []
                aData['ePersona'] = ePersona_serializer.data if ePersona_serializer else None
                aData['ePersonaReligion'] = MatriPersonaReligionSerializer(ePersonaReligion).data if ePersonaReligion else None
                aData['eInscripcion'] = eInscripcion_serializer.data if eInscripcion_serializer else None
                aData['eCarrera'] = eCarrera_serializer.data if eCarrera_serializer else None
                aData['eMalla'] = eMalla_serializer.data if eMalla_serializer else None
                aData['FichaSocioEconomicaINEC'] = ePersona.fichasocioeconomicainec()
                aData['ePeriodoMatricula'] = ePeriodoMatricula_serializer.data if ePeriodoMatricula_serializer else None
                aData['eInscripcionMalla'] = eInscripcionMalla_serializer.data if eInscripcionMalla_serializer else None
                aData['eNivelMalla'] = eNivelMalla_serializer.data if eNivelMalla_serializer else None
                aData['Title'] = "Confirmación de automatrícula"
                aData['eMatricula'] = eMatricula_serializer.data if eMatricula_serializer else None
                aData['eMateriasAsignadas'] = eMateriaAsignada_serializer.data if eMateriaAsignada_serializer else []
                # aData['tiene_rubro_pagado'] = tiene_rubro_pagado_matricula
                aData['valor_pagados'] = valor_pagados
                # aData['valor_pagados_str'] = str(floatformat(valor_pagados, 2))
                aData['valor_pendiente'] = valor_pendiente
                # aData['valor_pendiente_str'] = str(floatformat(valor_pendiente, 2))
                return Helper_Response(isSuccess=True, data={"tipo": "automatricula", "aData": aData}, status=status.HTTP_200_OK)

            if ePeriodo and ePeriodoMatricula and ePeriodoMatricula.periodo.id == ePeriodo.id and ePersona.tiene_matricula_periodo(ePeriodo):
                eMatricula = eInscripcion.matricula_periodo2(ePeriodo)
                if ConfirmarMatricula.objects.values('id').filter(matricula=eMatricula).exists():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, le informamos que ya se encuentra matriculado en el Periodo {ePeriodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")
            else:
                eMatricula = eInscripcion.matricula_periodo2(ePeriodoMatricula.periodo)
                if ConfirmarMatricula.objects.values('id').filter(matricula=eMatricula).exists():
                    raise NameError(f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, le informamos que ya se encuentra matriculado en el Periodo {ePeriodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")
            raise NameError(u"Funcionalidad no se encuentra activa para aspirantes")

            return Helper_Response(isSuccess=True, data={"tipo": "matricula", "aData": aData}, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
