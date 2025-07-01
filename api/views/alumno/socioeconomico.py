# coding=utf-8
import json
from datetime import datetime, timedelta
from decimal import Decimal
from collections import OrderedDict, namedtuple

from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, connections
from operator import itemgetter
from django.contrib.contenttypes.fields import ContentType, GenericForeignKey
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status, serializers

from api.forms.hoja_vida import DatosPersonalesEtniaForm
from api.forms.socioeconomica import DatosPersonalesForm, DatosFamiliarForm, DatosDiscapacidadForm, DatosNacimientoForm, \
    DatosDomicilioForm, DatosEstructuraFamiliarForm, DatosNivelEducacionForm, DatosCaracteristicaViviendaForm, \
    DatosHabitoConsumoForm, DatosPosesionBienesForm, DatosAccesoTecnologiaForm, DatosInstalacionesForm, \
    DatosActividadExtracurricularesForm, DatosRecursosEstudioForm, DatosSaludEstudianteForm
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.hoja_vida import DatosPersonalesEtniaSerializer
from api.serializers.alumno.socioeconomica import InscripcionSerializer, PersonaDatosPersonalesSerializer, \
    PersonaDatosFamiliaresSerializer, PersonaSerializer, PersonaDatosDiscapacidadSerializer, \
    PersonaDatosNacimientoSerializer, PersonaDatosDomicilioSerializer, PersonaEstructuraFamiliarSerializer, \
    PersonaNivelEducacionSerializer, PersonaCaracteristicaViviendaSerializer, PersonaHabitoConsumoSerializer, \
    PersonaPosesionBienesSerializer, PersonaAccesoTecnologiaSerializer, PersonaInstalacionesSerializer, \
    PersonaActividadExtracurricularesSerializer, PersonaRecursosEstudioSerializer, PersonaSaludEstudianteSerializer
from core.cache import get_cache_ePerfilUsuario
from med.models import PersonaExtension
from sga.funciones import generar_nombre, log

from sga.models import PerfilUsuario, Notificacion, Persona, PersonaDocumentoPersonal, PersonaDatosFamiliares
from sga.templatetags.sga_extras import encrypt, traducir_mes
from django.core.cache import cache

from socioecon.models import FichaSocioeconomicaINEC


class SocioEconAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_SOCIOECONOMICO'

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        try:
            payload = request.auth.payload
            ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
            if not 'action' in eRequest:
                raise NameError(u'Acción no permitida')
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'loadDatosPersonales':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = PersonaDatosPersonalesSerializer(eInscripcion.persona).data
                    return Helper_Response(isSuccess=True, data={'ePersona': ePersona}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonales':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                                # raise NameError(f"{v[0]}")
                            # f.addErrors(f.errors.get_json_data(escape_html=True))
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form},
                                                   message=f'Debe ingresar la información en todos los campos requeridos',
                                                   status=status.HTTP_200_OK)
                        ePersona.sexo = f.cleaned_data['sexo']
                        ePersona.nacimiento = f.cleaned_data['nacimiento']
                        ePersona.email = f.cleaned_data['email']
                        ePersona.libretamilitar = f.cleaned_data['libretamilitar']
                        ePersona.lgtbi = f.cleaned_data['lgtbi']
                        ePersona.eszurdo = f.cleaned_data['eszurdo']
                        ePersona.save(request)
                        try:
                            ePersonaExtension = PersonaExtension.objects.get(persona=ePersona)
                        except ObjectDoesNotExist:
                            ePersonaExtension = PersonaExtension(persona=ePersona)
                        ePersonaExtension.estadocivil = f.cleaned_data['estadocivil']
                        ePersonaExtension.save(request)

                        ePersonaDocumentoPersonal = ePersona.documentos_personales()
                        if ePersonaDocumentoPersonal is None:
                            ePersonaDocumentoPersonal = PersonaDocumentoPersonal(persona=ePersona)
                        nfileDocumento = eFiles.get('documento_archivo', None)
                        nfilePapeleta = eFiles.get('papeleta_archivo', None)
                        nfileLibretaMilitar = eFiles.get('libretamilitar_archivo', None)
                        if nfileDocumento is None and ePersonaDocumentoPersonal.cedula is None:
                            raise NameError(u"Archivo de documento es requerido")
                        if nfilePapeleta is None and ePersonaDocumentoPersonal.papeleta is None:
                            raise NameError(u"Archivo de papeleta de votación es requerido")
                        if nfileDocumento:
                            extensionDocumento = nfileDocumento._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if nfileDocumento.size > 15000000:
                                raise NameError(u"Archivo de documento, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() == 'pdf':
                                raise NameError(u"Archivo de documento, solo se permiten archivos formato pdf")
                        if nfilePapeleta:
                            extensionPapeleta = nfilePapeleta._name.split('.')
                            tamPapeleta = len(extensionPapeleta)
                            extePapeleta = extensionPapeleta[tamPapeleta - 1]
                            if nfilePapeleta.size > 15000000:
                                raise NameError(u"Archivo de papeleta de votación, el tamaño del archivo es mayor a 15 Mb.")
                            if not extePapeleta.lower() == 'pdf':
                                raise NameError(u"Archivo de papeleta de votación, solo se permiten archivos .pdf")
                        if nfileLibretaMilitar:
                            extensionLibretaMilitar = nfileLibretaMilitar._name.split('.')
                            tamLibretaMilitar = len(extensionLibretaMilitar)
                            exteLibretaMilitar = extensionLibretaMilitar[tamLibretaMilitar - 1]
                            if nfileLibretaMilitar.size > 15000000:
                                raise NameError(u"Archivo de libreta militar, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteLibretaMilitar.lower() == 'pdf':
                                raise NameError(u"Archivo de libreta militar, solo se permiten archivos .pdf")
                        if nfileDocumento:
                            nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)
                            ePersonaDocumentoPersonal.cedula = nfileDocumento
                            ePersonaDocumentoPersonal.estadocedula = 1
                        if nfilePapeleta:
                            nfilePapeleta._name = generar_nombre("dp_papeletavotacion", nfilePapeleta._name)
                            ePersonaDocumentoPersonal.papeleta = nfilePapeleta
                            ePersonaDocumentoPersonal.estadopapeleta = 1
                        if nfileLibretaMilitar:
                            nfileLibretaMilitar._name = generar_nombre("dp_libretamilitar", nfileLibretaMilitar._name)
                            ePersonaDocumentoPersonal.libretamilitar = nfileLibretaMilitar
                            ePersonaDocumentoPersonal.estadolibretamilitar = 1
                        ePersonaDocumentoPersonal.save(request)
                        log(u'Editó datos personales de ficha socioeconomica: %s' % ePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos personales', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosPersonalesEtnia':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    ePerfilInscripcion = ePersona.mi_perfil()
                    ePerfilInscripcion = DatosPersonalesEtniaSerializer(ePerfilInscripcion).data if ePerfilInscripcion else {}
                    return Helper_Response(isSuccess=True, data={'ePerfilInscripcion': ePerfilInscripcion}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesEtnia':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePerfilInscripcion = ePersona.mi_perfil()
                        if ePerfilInscripcion.estadoarchivoraza in (2, 5):
                            raise NameError(u"Estado de la étnia fue validado por Bienestar")
                        f = DatosPersonalesEtniaForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)

                        ePerfilInscripcion.raza = f.cleaned_data['raza']
                        ePerfilInscripcion.nacionalidadindigena = f.cleaned_data['nacionalidadindigena']
                        archivoraza = f.files.get('archivoraza', None)
                        # if ePerfilInscripcion.archivoraza is None:
                        #     if archivoraza is None:
                        #         raise NameError(u"Archivo de étnia no se encontro")
                        if archivoraza:
                            archivoraza.name = generar_nombre(f"archivosraza_", archivoraza.name)
                            ePerfilInscripcion.archivoraza = archivoraza
                            ePerfilInscripcion.estadoarchivoraza = 1
                        ePerfilInscripcion.save(request)
                        log(u'Editó datos de étnia en hoja de vida: %s' % ePerfilInscripcion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosFamiliares':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = eInscripcion.persona
                    ePersonaDatosFamiliares = ePersona.familiares()
                    ePersonaSerializer = PersonaSerializer(ePersona).data
                    ePersonaDatosFamiliares = PersonaDatosFamiliaresSerializer(ePersona.familiares(), many=True).data if ePersonaDatosFamiliares.values("id").exists() else []
                    return Helper_Response(isSuccess=True, data={'ePersonaDatosFamiliares': ePersonaDatosFamiliares, 'ePersona': ePersonaSerializer}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePersonaDatosFamiliares': [], 'ePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosFamiliar':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        f = DatosFamiliarForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        try:
                            ePersonaDatosFamiliar = PersonaDatosFamiliares.objects.get(persona=ePersona, pk=id)
                            new = False
                        except ObjectDoesNotExist:
                            ePersonaDatosFamiliar = PersonaDatosFamiliares(persona=ePersona)
                            new = True
                        ePersonaDatosFamiliares = ePersona.familiares()
                        if new is True:
                            if ePersonaDatosFamiliares.values("id").filter(identificacion=f.cleaned_data['identificacion']).exists():
                                raise NameError(u"Pariente ya existe")
                        else:
                            if ePersonaDatosFamiliares.values("id").filter(identificacion=f.cleaned_data['identificacion']).exclude(pk=id).exists():
                                raise NameError(u"Pariente ya existe")
                        ePersonaDatosFamiliar.personafamiliar = None
                        if (ePersonaPariente := Persona.objects.filter(Q(cedula=f.cleaned_data['identificacion']) | Q(pasaporte=f.cleaned_data['identificacion'])).first()) is not None:
                            ePersonaDatosFamiliar.personafamiliar = ePersonaPariente
                        ePersonaDatosFamiliar.identificacion = f.cleaned_data['identificacion']
                        ePersonaDatosFamiliar.nombre = f.cleaned_data['nombre']
                        ePersonaDatosFamiliar.parentesco = f.cleaned_data['parentesco']
                        ePersonaDatosFamiliar.nacimiento = f.cleaned_data['nacimiento']
                        ePersonaDatosFamiliar.rangoedad = f.cleaned_data['rangoedad']
                        ePersonaDatosFamiliar.fallecido = f.cleaned_data['fallecido']
                        ePersonaDatosFamiliar.telefono = f.cleaned_data['telefono']
                        ePersonaDatosFamiliar.telefono_conv = f.cleaned_data['telefono_conv']
                        ePersonaDatosFamiliar.trabajo = f.cleaned_data['trabajo']
                        ePersonaDatosFamiliar.convive = f.cleaned_data['convive']
                        ePersonaDatosFamiliar.sustentohogar = f.cleaned_data['sustentohogar']
                        ePersonaDatosFamiliar.niveltitulacion = f.cleaned_data['niveltitulacion']
                        ePersonaDatosFamiliar.formatrabajo = f.cleaned_data['formatrabajo']
                        ePersonaDatosFamiliar.ingresomensual = f.cleaned_data['ingresomensual']
                        ePersonaDatosFamiliar.tipoinstitucionlaboral = f.cleaned_data['tipoinstitucionlaboral']
                        ePersonaDatosFamiliar.tienenegocio = f.cleaned_data['tienenegocio']
                        ePersonaDatosFamiliar.negocio = f.cleaned_data['negocio']
                        tienediscapacidad = f.cleaned_data['tienediscapacidad']
                        if tienediscapacidad:
                            ePersonaDatosFamiliar.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                            ePersonaDatosFamiliar.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad']
                            ePersonaDatosFamiliar.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                            ePersonaDatosFamiliar.institucionvalida = f.cleaned_data['institucionvalida']
                        ePersonaDatosFamiliar.essustituto = f.cleaned_data['essustituto']
                        nfileIdentificacion = eFiles.get('cedulaidentidad', None)
                        if nfileIdentificacion:
                            extensionIdentificacion = nfileIdentificacion._name.split('.')
                            tamIdentificacion = len(extensionIdentificacion)
                            exteIdentificacion = extensionIdentificacion[tamIdentificacion - 1]
                            if nfileIdentificacion.size > 15000000:
                                raise NameError(u"Archivo de identificación, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteIdentificacion.lower() == 'pdf':
                                raise NameError(u"Archivo de identificación, solo se permiten archivos formato pdf")
                            nfileIdentificacion._name = generar_nombre(f"{f.cleaned_data['identificacion']}_identificacion_", nfileIdentificacion._name)
                            ePersonaDatosFamiliar.cedulaidentidad = nfileIdentificacion

                        if tienediscapacidad:
                            nfileDiscapacidad = eFiles.get('ceduladiscapacidad', None)
                            if nfileDiscapacidad:
                                extensionDiscapacidad = nfileDiscapacidad._name.split('.')
                                tamDiscapacidad = len(extensionDiscapacidad)
                                exteDiscapacidad = extensionDiscapacidad[tamDiscapacidad - 1]
                                if nfileDiscapacidad.size > 15000000:
                                    raise NameError(u"Archivo de discapacidad, el tamaño del archivo es mayor a 15 Mb.")
                                if not exteDiscapacidad.lower() == 'pdf':
                                    raise NameError(u"Archivo de discapacidad, solo se permiten archivos formato pdf")
                                nfileDiscapacidad._name = generar_nombre(f"{f.cleaned_data['identificacion']}_discapacidad_", nfileDiscapacidad._name)
                                ePersonaDatosFamiliar.ceduladiscapacidad = nfileDiscapacidad
                        nfileAutorizado = eFiles.get('autorizadoministerio', None)
                        if nfileAutorizado:
                            extensionAutorizado = nfileAutorizado._name.split('.')
                            tamAutorizado = len(extensionAutorizado)
                            exteAutorizado = extensionAutorizado[tamAutorizado - 1]
                            if nfileAutorizado.size > 15000000:
                                raise NameError(u"Archivo de autorizado, el tamaño del archivo es mayor a 15 Mb.")
                            if not exteAutorizado.lower() == 'pdf':
                                raise NameError(u"Archivo de autorizado, solo se permiten archivos formato pdf")
                            nfileAutorizado._name = generar_nombre(f"{f.cleaned_data['identificacion']}_autorizado_", nfileAutorizado._name)
                            ePersonaDatosFamiliar.archivoautorizado = nfileAutorizado
                        ePersonaDatosFamiliar.save(request)
                        if new:
                            log(u'Adicion datos familiar de ficha socioeconomica: %s' % ePersonaDatosFamiliar, request, "add")
                        else:
                            log(u'Editó datos familiar de ficha socioeconomica: %s' % ePersonaDatosFamiliar, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos del familiar', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosFamiliar':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            ePersonaDatosFamiliar = PersonaDatosFamiliares.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deletePersonaDatosFamiliar = ePersonaDatosFamiliar
                        ePersonaDatosFamiliar.delete()
                        log(u'Elimino datos familiar de ficha socioeconomica: %s' % deletePersonaDatosFamiliar, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos del familiar', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosPersona':
                try:
                    identificacion = eRequest.get('identificacion', None)
                    if identificacion is None:
                        raise NameError(u"No se encontro parametro")
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    ePersonaDatosFamiliares = ePersona.familiares()
                    if ePersonaDatosFamiliares.values("id").filter(identificacion=identificacion).exists():
                        raise NameError(u"Pariente ya existe")
                    ePersona = Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion)).first()
                    ePersona = PersonaSerializer(ePersona).data if ePersona else {}
                    return Helper_Response(isSuccess=True, data={'ePersona': ePersona}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosDiscapacidad':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    ePerfilInscripcion = ePersona.mi_perfil()
                    ePerfilInscripcion = PersonaDatosDiscapacidadSerializer(ePerfilInscripcion).data if ePerfilInscripcion else {}
                    return Helper_Response(isSuccess=True, data={'ePerfilInscripcion': ePerfilInscripcion}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosDiscapacidad':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePerfilInscripcion = ePersona.mi_perfil()
                        if ePerfilInscripcion.estadoarchivodiscapacidad in (2, 5):
                            raise NameError(u"Estado de la discapacidad fue validado por Bienestar")
                        f = DatosDiscapacidadForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)

                        ePerfilInscripcion.tienediscapacidad = tienediscapacidad = f.cleaned_data['tienediscapacidad']
                        if tienediscapacidad is False:
                            ePerfilInscripcion.tipodiscapacidad = None
                            ePerfilInscripcion.grado = 0
                            ePerfilInscripcion.carnetdiscapacidad = None
                            ePerfilInscripcion.porcientodiscapacidad = 0
                            ePerfilInscripcion.institucionvalida = None
                            ePerfilInscripcion.tienediscapacidadmultiple = False
                            ePerfilInscripcion.tipodiscapacidadmultiple.clear()
                            ePerfilInscripcion.subtipodiscapacidad.clear()
                            ePerfilInscripcion.verificadiscapacidad = False
                            ePerfilInscripcion.estadoarchivodiscapacidad = 0
                            ePerfilInscripcion.archivo = None
                        else:
                            ePerfilInscripcion.tipodiscapacidad = f.cleaned_data['tipodiscapacidad']
                            ePerfilInscripcion.grado = f.cleaned_data['grado']
                            ePerfilInscripcion.carnetdiscapacidad = f.cleaned_data['carnetdiscapacidad']
                            ePerfilInscripcion.porcientodiscapacidad = f.cleaned_data['porcientodiscapacidad']
                            ePerfilInscripcion.institucionvalida = f.cleaned_data['institucionvalida']
                            ePerfilInscripcion.tienediscapacidadmultiple = f.cleaned_data['tienediscapacidadmultiple']
                            ePerfilInscripcion.tipodiscapacidadmultiple.clear()
                            tipodiscapacidadmultiple = f.data.get('tipodiscapacidadmultiple', None)
                            if tipodiscapacidadmultiple is not None:
                                for id in json.loads(tipodiscapacidadmultiple):
                                    ePerfilInscripcion.tipodiscapacidadmultiple.add(int(id))
                            ePerfilInscripcion.subtipodiscapacidad.clear()
                            ePerfilInscripcion.verificadiscapacidad = False
                            archivo = f.files.get('archivo', None)
                            if ePerfilInscripcion.archivo is None:
                                if archivo is None:
                                    raise NameError(u"Archivo de discapacidad no se encontro")
                            if archivo:
                                archivo.name = generar_nombre(f"archivosdiscapacidad_", archivo.name)
                                ePerfilInscripcion.archivo = archivo
                                ePerfilInscripcion.estadoarchivodiscapacidad = 1
                        ePerfilInscripcion.save(request)
                        log(u'Editó datos de discapacidad de ficha socioeconomica: %s' % ePerfilInscripcion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos de discapacidad', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosNacimiento':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    ePersona = PersonaDatosNacimientoSerializer(ePersona).data if ePersona else {}
                    return Helper_Response(isSuccess=True, data={'ePersona': ePersona}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosNacimiento':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosNacimientoForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        ePersona.paisnacimiento = f.cleaned_data['paisnacimiento']
                        ePersona.provincianacimiento = f.cleaned_data['provincianacimiento']
                        ePersona.cantonnacimiento = f.cleaned_data['cantonnacimiento']
                        ePersona.parroquianacimiento = f.cleaned_data['parroquianacimiento']
                        ePersona.save(request)
                        log(u'Editó datos de nacimiento de ficha socioeconomica: %s' % ePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos de nacimiento', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosDomicilio':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    ePersona = PersonaDatosDomicilioSerializer(ePersona).data if ePersona else {}
                    return Helper_Response(isSuccess=True, data={'ePersona': ePersona}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosDomicilio':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosDomicilioForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        ePersona.pais = f.cleaned_data['pais']
                        ePersona.provincia = f.cleaned_data['provincia']
                        ePersona.canton = f.cleaned_data['canton']
                        ePersona.parroquia = f.cleaned_data['parroquia']
                        ePersona.direccion = f.cleaned_data['direccion']
                        ePersona.direccion2 = f.cleaned_data['direccion2']
                        ePersona.num_direccion = f.cleaned_data['num_direccion']
                        ePersona.sector = f.cleaned_data['sector']
                        ePersona.referencia = f.cleaned_data['referencia']
                        ePersona.tipocelular = f.cleaned_data['tipocelular']
                        ePersona.telefono = f.cleaned_data['telefono']
                        ePersona.telefono_conv = f.cleaned_data['telefono_conv']
                        ePersona.sectorlugar = f.cleaned_data['sectorlugar']
                        archivocroquis = f.files.get('archivocroquis', None)
                        archivoplanillaluz = f.files.get('archivoplanillaluz', None)
                        if ePersona.archivocroquis is None:
                            if archivocroquis is None:
                                raise NameError(u"Archivo de roquis no se encontro")
                        if archivocroquis:
                            archivocroquis.name = generar_nombre(f"archivocroquis_", archivocroquis.name)
                            ePersona.archivocroquis = archivocroquis

                        if ePersona.archivoplanillaluz is None:
                            if archivoplanillaluz is None:
                                raise NameError(u"Archivo de planilla de luz no se encontro")
                        if archivoplanillaluz:
                            archivoplanillaluz.name = generar_nombre(f"archivoplanillaluz_", archivoplanillaluz.name)
                            ePersona.archivoplanillaluz = archivoplanillaluz
                        ePersona.save(request)
                        log(u'Editó datos de domicilio de ficha socioeconomica: %s' % ePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos de domicilio', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosEstructuraFamiliar':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaEstructuraFamiliarSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosEstructuraFamiliar':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosEstructuraFamiliarForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tipohogar':
                            eFichaSocioeconomica.tipohogar = f.cleaned_data['tipohogar']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó tipo de hogar de estructura familiar de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        elif field == 'personacubregasto':
                            eFichaSocioeconomica.personacubregasto = f.cleaned_data['personacubregasto']
                            if eFichaSocioeconomica.personacubregasto.pk == 7:
                                eFichaSocioeconomica.otroscubregasto = f.cleaned_data['otroscubregasto']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó quien cubre gastos de estructura familiar de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        elif field == 'escabezafamilia':
                            eFichaSocioeconomica.escabezafamilia = f.cleaned_data['escabezafamilia']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó cabeza familia de estructura familiar de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        elif field == 'esdependiente':
                            eFichaSocioeconomica.esdependiente = f.cleaned_data['esdependiente']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó es dependiente de estructura familiar de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos de estructura familiar', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteEstructuraFamiliar':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'tipohogar':
                            eFichaSocioeconomica.tipohogar = None
                        elif field == 'personacubregasto':
                            eFichaSocioeconomica.personacubregasto = None
                            eFichaSocioeconomica.otroscubregasto = None
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(u'Quita dato de familiar de ficha socioeconomica: %s del campo %s' % (eFichaSocioeconomica, field), request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos del familiar', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosNivelEducacion':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaNivelEducacionSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosNivelEducacion':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosNivelEducacionForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'niveljefehogar':
                            eFichaSocioeconomica.niveljefehogar = f.cleaned_data['niveljefehogar']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó nivel de estudio del jefe de hogar de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        elif field == 'ocupacionjefehogar':
                            eFichaSocioeconomica.ocupacionjefehogar = f.cleaned_data['ocupacionjefehogar']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó ocupación de jefe de hogar de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        elif field == 'alguienafiliado':
                            eFichaSocioeconomica.alguienafiliado = f.cleaned_data['alguienafiliado']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó afiliado al IESS, ISSPOL, ISSFA de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        elif field == 'alguienseguro':
                            eFichaSocioeconomica.alguienseguro = f.cleaned_data['alguienseguro']
                            eFichaSocioeconomica.save(request)
                            log(u'Editó seguro privado de ficha socioeconomica: %s' % eFichaSocioeconomica, request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos de estructura familiar', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteNivelEducacion':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'niveljefehogar':
                            eFichaSocioeconomica.niveljefehogar = None
                        elif field == 'ocupacionjefehogar':
                            eFichaSocioeconomica.ocupacionjefehogar = None
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(u'Quita dato nivel de educación de ficha socioeconomica: %s del campo %s' % (eFichaSocioeconomica, field), request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosCaracteristicasVivienda':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaCaracteristicaViviendaSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosCaracteristicaVivienda':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosCaracteristicaViviendaForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tipovivienda':
                            eFichaSocioeconomica.tipovivienda = f.cleaned_data['tipovivienda']
                            eFichaSocioeconomica.val_tipovivienda = eFichaSocioeconomica.tipovivienda.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tipoviviendapro':
                            eFichaSocioeconomica.tipoviviendapro = f.cleaned_data['tipoviviendapro']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'materialpared':
                            eFichaSocioeconomica.materialpared = f.cleaned_data['materialpared']
                            eFichaSocioeconomica.val_materialpared = eFichaSocioeconomica.materialpared.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'materialpiso':
                            eFichaSocioeconomica.materialpiso = f.cleaned_data['materialpiso']
                            eFichaSocioeconomica.val_materialpiso = eFichaSocioeconomica.materialpiso.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'cantbannoducha':
                            eFichaSocioeconomica.cantbannoducha = f.cleaned_data['cantbannoducha']
                            eFichaSocioeconomica.val_cantbannoducha = eFichaSocioeconomica.cantbannoducha.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tiposervhig':
                            eFichaSocioeconomica.tiposervhig = f.cleaned_data['tiposervhig']
                            eFichaSocioeconomica.val_tiposervhig = eFichaSocioeconomica.tiposervhig.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteCaracteristicaVivivenda':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'tipovivienda':
                            eFichaSocioeconomica.tipovivienda = None
                            eFichaSocioeconomica.val_tipovivienda = 0
                        elif field == 'tipoviviendapro':
                            eFichaSocioeconomica.tipoviviendapro = None
                        elif field == 'materialpared':
                            eFichaSocioeconomica.materialpared = None
                            eFichaSocioeconomica.val_materialpared = 0
                        elif field == 'materialpiso':
                            eFichaSocioeconomica.materialpiso = None
                            eFichaSocioeconomica.val_materialpiso = 0
                        elif field == 'cantbannoducha':
                            eFichaSocioeconomica.cantbannoducha = None
                            eFichaSocioeconomica.val_cantbannoducha = 0
                        elif field == 'tiposervhig':
                            eFichaSocioeconomica.tiposervhig = None
                            eFichaSocioeconomica.val_tiposervhig = 0
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(f'Quita campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosHabitosConsumo':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaHabitoConsumoSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosHabitoConsumo':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosHabitoConsumoForm(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'compravestcc':
                            eFichaSocioeconomica.compravestcc = f.cleaned_data['compravestcc']
                            eFichaSocioeconomica.val_compravestcc = 6 if f.cleaned_data['compravestcc'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'usainternetseism':
                            eFichaSocioeconomica.usainternetseism = f.cleaned_data['usainternetseism']
                            eFichaSocioeconomica.val_usainternetseism = 26 if f.cleaned_data['usainternetseism'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'usacorreonotrab':
                            eFichaSocioeconomica.usacorreonotrab = f.cleaned_data['usacorreonotrab']
                            eFichaSocioeconomica.val_usacorreonotrab = 27 if f.cleaned_data['usacorreonotrab'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'registroredsocial':
                            eFichaSocioeconomica.registroredsocial = f.cleaned_data['registroredsocial']
                            eFichaSocioeconomica.val_registroredsocial = 28 if f.cleaned_data['registroredsocial'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'leidolibrotresm':
                            eFichaSocioeconomica.leidolibrotresm = f.cleaned_data['leidolibrotresm']
                            eFichaSocioeconomica.val_leidolibrotresm = 12 if f.cleaned_data['leidolibrotresm'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")

                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosPosesionBienes':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaPosesionBienesSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPosesionBienes':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosPosesionBienesForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tienetelefconv':
                            eFichaSocioeconomica.tienetelefconv = f.cleaned_data['tienetelefconv']
                            eFichaSocioeconomica.val_tienetelefconv = 19 if f.cleaned_data['tienetelefconv'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienecocinahorno':
                            eFichaSocioeconomica.tienecocinahorno = f.cleaned_data['tienecocinahorno']
                            eFichaSocioeconomica.val_tienecocinahorno = 29 if f.cleaned_data['tienecocinahorno'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienerefrig':
                            eFichaSocioeconomica.tienerefrig = f.cleaned_data['tienerefrig']
                            eFichaSocioeconomica.val_tienerefrig = 30 if f.cleaned_data['tienerefrig'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienelavadora':
                            eFichaSocioeconomica.tienelavadora = f.cleaned_data['tienelavadora']
                            eFichaSocioeconomica.val_tienelavadora = 18 if f.cleaned_data['tienelavadora'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienemusica':
                            eFichaSocioeconomica.tienemusica = f.cleaned_data['tienemusica']
                            eFichaSocioeconomica.val_tienemusica = 18 if f.cleaned_data['tienemusica'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'canttvcolor':
                            eFichaSocioeconomica.canttvcolor = f.cleaned_data['canttvcolor']
                            eFichaSocioeconomica.val_canttvcolor = eFichaSocioeconomica.canttvcolor.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'cantvehiculos':
                            eFichaSocioeconomica.cantvehiculos = f.cleaned_data['cantvehiculos']
                            eFichaSocioeconomica.val_cantvehiculos = eFichaSocioeconomica.cantvehiculos.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deletePosesionBienes':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'canttvcolor':
                            eFichaSocioeconomica.canttvcolor = None
                            eFichaSocioeconomica.val_canttvcolor = 0
                        elif field == 'cantvehiculos':
                            eFichaSocioeconomica.cantvehiculos = None
                            eFichaSocioeconomica.val_cantvehiculos = 0
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(f'Quita campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosAccesosTecnologia':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaAccesoTecnologiaSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosAccesoTecnologia':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosAccesoTecnologiaForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tieneinternet':
                            eFichaSocioeconomica.tieneinternet = f.cleaned_data['tieneinternet']
                            eFichaSocioeconomica.val_tieneinternet = 45 if f.cleaned_data['tieneinternet'] else 0
                            if eFichaSocioeconomica.tieneinternet is False:
                                eFichaSocioeconomica.internetpanf = False
                                eFichaSocioeconomica.proveedorinternet = None
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'internetpanf':
                            eFichaSocioeconomica.internetpanf = f.cleaned_data['internetpanf']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'proveedorinternet':
                            eFichaSocioeconomica.proveedorinternet = f.cleaned_data['proveedorinternet']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienedesktop':
                            eFichaSocioeconomica.tienedesktop = f.cleaned_data['tienedesktop']
                            eFichaSocioeconomica.val_tienedesktop = 35 if f.cleaned_data['tienedesktop'] else 0
                            if eFichaSocioeconomica.tienedesktop is False:
                                eFichaSocioeconomica.equipotienecamara = False
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'equipotienecamara':
                            eFichaSocioeconomica.equipotienecamara = f.cleaned_data['equipotienecamara']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienelaptop':
                            eFichaSocioeconomica.tienelaptop = f.cleaned_data['tienelaptop']
                            eFichaSocioeconomica.val_tienelaptop = 39 if f.cleaned_data['tienelaptop'] else 0
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'cantcelulares':
                            eFichaSocioeconomica.cantcelulares = f.cleaned_data['cantcelulares']
                            eFichaSocioeconomica.val_cantcelulares = eFichaSocioeconomica.cantcelulares.puntaje
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteAccesoTecnologia':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'cantcelulares':
                            eFichaSocioeconomica.cantcelulares = None
                            eFichaSocioeconomica.val_cantcelulares = 0
                        elif field == 'proveedorinternet':
                            eFichaSocioeconomica.proveedorinternet = None
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(f'Quita campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosInstalaciones':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaInstalacionesSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosInstalaciones':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosInstalacionesForm(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tienesala':
                            eFichaSocioeconomica.tienesala = f.cleaned_data['tienesala']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienecomedor':
                            eFichaSocioeconomica.tienecomedor = f.cleaned_data['tienecomedor']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienecocina':
                            eFichaSocioeconomica.tienecocina = f.cleaned_data['tienecocina']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienebanio':
                            eFichaSocioeconomica.tienebanio = f.cleaned_data['tienebanio']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tieneluz':
                            eFichaSocioeconomica.tieneluz = f.cleaned_data['tieneluz']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tieneagua':
                            eFichaSocioeconomica.tieneagua = f.cleaned_data['tieneagua']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienetelefono':
                            eFichaSocioeconomica.tienetelefono = f.cleaned_data['tienetelefono']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienealcantarilla':
                            eFichaSocioeconomica.tienealcantarilla = f.cleaned_data['tienealcantarilla']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosActividadesExtracurriculares':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaActividadExtracurricularesSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosActividadExtracurricular':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosActividadExtracurricularesForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'horastareahogar':
                            eFichaSocioeconomica.horastareahogar = f.cleaned_data['horastareahogar']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'horastrabajodomestico':
                            eFichaSocioeconomica.horastrabajodomestico = f.cleaned_data['horastrabajodomestico']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'horastrabajofuera':
                            eFichaSocioeconomica.horastrabajofuera = f.cleaned_data['horastrabajofuera']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'horashacertareas':
                            eFichaSocioeconomica.horashacertareas = f.cleaned_data['horashacertareas']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tipoactividad':
                            eFichaSocioeconomica.tipoactividad = f.cleaned_data['tipoactividad']
                            if eFichaSocioeconomica.tipoactividad == '7':
                                eFichaSocioeconomica.otrosactividad = f.cleaned_data['otrosactividad']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tipotarea':
                            eFichaSocioeconomica.tipotarea = f.cleaned_data['tipotarea']
                            if eFichaSocioeconomica.tipotarea == '8':
                                eFichaSocioeconomica.otrostarea = f.cleaned_data['otrostarea']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteActividadExtracurricular':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'horastareahogar':
                            eFichaSocioeconomica.horastareahogar = 0
                        elif field == 'horastrabajodomestico':
                            eFichaSocioeconomica.horastrabajodomestico = 0
                        elif field == 'horastrabajofuera':
                            eFichaSocioeconomica.horastrabajofuera = 0
                        elif field == 'horashacertareas':
                            eFichaSocioeconomica.horashacertareas = 0
                        elif field == 'tipoactividad':
                            eFichaSocioeconomica.tipoactividad = 0
                            eFichaSocioeconomica.otrosactividad = None
                        elif field == 'tipotarea':
                            eFichaSocioeconomica.tipotarea = 0
                            eFichaSocioeconomica.otrostarea = None
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(f'Quita campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosRecursosEstudio':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaRecursosEstudioSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosRecursosEstudios':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosRecursosEstudioForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tienefolleto':
                            eFichaSocioeconomica.tienefolleto = f.cleaned_data['tienefolleto']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienecomputador':
                            eFichaSocioeconomica.tienecomputador = f.cleaned_data['tienecomputador']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tieneenciclopedia':
                            eFichaSocioeconomica.tieneenciclopedia = f.cleaned_data['tieneenciclopedia']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'otrosrecursos':
                            eFichaSocioeconomica.otrosrecursos = f.cleaned_data['otrosrecursos']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienecyber':
                            eFichaSocioeconomica.tienecyber = f.cleaned_data['tienecyber']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienebiblioteca':
                            eFichaSocioeconomica.tienebiblioteca = f.cleaned_data['tienebiblioteca']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienemuseo':
                            eFichaSocioeconomica.tienemuseo = f.cleaned_data['tienemuseo']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienearearecreacion':
                            eFichaSocioeconomica.tienearearecreacion = f.cleaned_data['tienearearecreacion']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'otrossector':
                            eFichaSocioeconomica.otrossector = f.cleaned_data['otrossector']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteRecursosEstudio':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'otrosrecursos':
                            eFichaSocioeconomica.otrosrecursos = None
                        elif field == 'otrossector':
                            eFichaSocioeconomica.otrossector = None
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(f'Quita campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'loadDatosSaludEstudiante':
                try:
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                    if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                        eFichaSocioeconomica = eFicha
                    else:
                        eFichaSocioeconomica = ePersona.mi_ficha()
                    eFichaSocioeconomica = PersonaSaludEstudianteSerializer(eFichaSocioeconomica).data if eFichaSocioeconomica else {}
                    return Helper_Response(isSuccess=True, data={'eFichaSocioeconomica': eFichaSocioeconomica}, message=f'', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosSaludEstudiante':
                with transaction.atomic():
                    try:
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"No se encontro parametro del campo")
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        f = DatosSaludEstudianteForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if field == 'tienediabetes':
                            eFichaSocioeconomica.tienediabetes = f.cleaned_data['v']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienehipertencion':
                            eFichaSocioeconomica.tienehipertencion = f.cleaned_data['tienehipertencion']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tieneparkinson':
                            eFichaSocioeconomica.tieneparkinson = f.cleaned_data['tieneparkinson']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienecancer':
                            eFichaSocioeconomica.tienecancer = f.cleaned_data['tienecancer']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienealzheimer':
                            eFichaSocioeconomica.tienealzheimer = f.cleaned_data['tienealzheimer']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienevitiligo':
                            eFichaSocioeconomica.tienevitiligo = f.cleaned_data['tienevitiligo']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienedesgastamiento':
                            eFichaSocioeconomica.tienedesgastamiento = f.cleaned_data['tienedesgastamiento']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienepielblanca':
                            eFichaSocioeconomica.tienepielblanca = f.cleaned_data['tienepielblanca']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tienesida':
                            eFichaSocioeconomica.tienesida = f.cleaned_data['tienesida']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'otrasenfermedades':
                            eFichaSocioeconomica.otrasenfermedades = f.cleaned_data['otrasenfermedades']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'enfermedadescomunes':
                            eFichaSocioeconomica.enfermedadescomunes = f.cleaned_data['enfermedadescomunes']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'salubridadvida':
                            eFichaSocioeconomica.salubridadvida = f.cleaned_data['salubridadvida']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'estadogeneral':
                            eFichaSocioeconomica.estadogeneral = f.cleaned_data['estadogeneral']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        elif field == 'tratamientomedico':
                            eFichaSocioeconomica.tratamientomedico = f.cleaned_data['tratamientomedico']
                            eFichaSocioeconomica.save(request)
                            log(f'Editó campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        else:
                            raise NameError(u"No se encontro campo correcto")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteSaludEstudiante':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                        field = eRequest.get('field', None)
                        if field is None:
                            raise NameError(u"Parametro no encontrado")
                        if field == 'otrasenfermedades':
                            eFichaSocioeconomica.otrasenfermedades = None
                        elif field == 'enfermedadescomunes':
                            eFichaSocioeconomica.enfermedadescomunes = None
                        elif field == 'salubridadvida':
                            eFichaSocioeconomica.salubridadvida = 0
                        elif field == 'estadogeneral':
                            eFichaSocioeconomica.estadogeneral = 0
                        elif field == 'tratamientomedico':
                            eFichaSocioeconomica.tratamientomedico = None
                        else:
                            raise NameError(u"Campo no encontrado")
                        eFichaSocioeconomica.save(request)
                        log(f'Quita campo {field} de ficha socioeconomica: {eFichaSocioeconomica.__str__()}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveConfirmar':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        if (eFicha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True, confirmar=False).last()) is not None:
                            eFichaSocioeconomica = eFicha
                            replay = True
                        else:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                            replay = False
                        isError = False
                        errors = []
                        if ePersona.pais is None:
                            isError = True
                            errors.append(u"Registre el pais de residencia")
                        else:
                            if ePersona.pais_id == 1:
                                if ePersona.provincia is None:
                                    isError = True
                                    errors.append(u"Registre la provincia de residencia")
                                if ePersona.canton is None:
                                    isError = True
                                    errors.append(u"Registre el canton de residencia")
                                if ePersona.parroquia is None:
                                    isError = True
                                    errors.append(u"Registre la parroquia de residencia")
                        if ePersona.direccion == '':
                            isError = True
                            errors.append(u"Ingrese la calle principal de residencia")
                        if ePersona.direccion2 == '':
                            isError = True
                            errors.append(u"Ingrese la calle secundaria de residencia")
                        if eFichaSocioeconomica.tipohogar is None:
                            isError = True
                            errors.append(u"Registre el tipo de hogar")
                        if eFichaSocioeconomica.tipovivienda is None:
                            isError = True
                            errors.append(u"¿Cuál es el tipo de vivienda?")
                        if eFichaSocioeconomica.tipoviviendapro is None:
                            isError = True
                            errors.append(u"¿Su vivienda es?")
                        if eFichaSocioeconomica.materialpared is None:
                            isError = True
                            errors.append(u"Material Predominante en las paredes")
                        if eFichaSocioeconomica.materialpiso is None:
                            isError = True
                            errors.append(u"Material Predominante en el piso")
                        if eFichaSocioeconomica.cantbannoducha is None:
                            isError = True
                            errors.append(u"¿Cuántos cuartos de baño con ducha tiene el hogar?")
                        if eFichaSocioeconomica.tiposervhig is None:
                            isError = True
                            errors.append(u"El tipo de servicio higiénico con que cuenta el hogar es:")
                        if eFichaSocioeconomica.personacubregasto is None:
                            isError = True
                            errors.append(u"¿Quién cubre los gastos del estudiante?")
                        if eFichaSocioeconomica.niveljefehogar is None:
                            isError = True
                            errors.append(u"¿Cuál es el nivel de estudios del Jefe del Hogar?")
                        if eFichaSocioeconomica.ocupacionjefehogar is None:
                            isError = True
                            errors.append(u"¿Cuál es la ocupación del Jefe del Hogar?")
                        if eFichaSocioeconomica.canttvcolor is None:
                            isError = True
                            errors.append(u"¿Cuántos TV a color tienen en el hogar?")
                        if eFichaSocioeconomica.cantvehiculos is None:
                            isError = True
                            errors.append(u"¿Cuántos Vehículos de uso exclusivo tiene el hogar?")
                        if eFichaSocioeconomica.cantcelulares is None:
                            isError = True
                            errors.append(u"¿Cuántos celulares activados tienen en el hogar?")
                        if eFichaSocioeconomica.tieneinternet:
                            if eFichaSocioeconomica.proveedorinternet is None:
                                isError = True
                                errors.append(u"¿Cuál es su proveedor de servicio de internet?")
                        if eFichaSocioeconomica.tipoactividad == 0:
                            isError = True
                            errors.append(u"Actividades de recreación")
                        if eFichaSocioeconomica.tipotarea == 0:
                            isError = True
                            errors.append(u"Donde realiza las tareas")
                        if eFichaSocioeconomica.salubridadvida == 0:
                            isError = True
                            errors.append(u"Salubridad de las condiciones de vida")
                        if eFichaSocioeconomica.estadogeneral == 0:
                            isError = True
                            errors.append(u"Estado general de salud de el/la estudiante")
                        if isError is True:
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'errors': ", ".join(errors)}, message=f'Encuesta incompleta', status=status.HTTP_200_OK)
                        eFichaSocioeconomica.confirmar = True
                        eFichaSocioeconomica.save(request)
                        if replay:
                            eFichaSocioeconomica = ePersona.mi_ficha()
                            eFichaSocioeconomica.confirmar = True
                            eFichaSocioeconomica.save(request)
                            log(f'Confirmo ficha socioeconomica replica: {eFichaSocioeconomica.__str__()} {eFichaSocioeconomica.puntajetotal} {eFichaSocioeconomica.grupoeconomico.nombre}', request, "edit")
                        else:
                            log(f'Confirmo ficha socioeconomica: {eFichaSocioeconomica.__str__()} {eFichaSocioeconomica.puntajetotal} {eFichaSocioeconomica.grupoeconomico.nombre}', request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se confirmo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = get_cache_ePerfilUsuario(int(encrypt(payload['perfilprincipal']['id'])))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            eInscripcion = ePerfilUsuario.inscripcion
            ePersona = eInscripcion.persona
            if (ficha := ePersona.fichasocioeconomicareplayinec_set.filter(estadosolicitud=1, status=True).first()) is not None:
                if ficha.confirmar:
                    raise NameError(u"Usted ya ha confirmado sus datos en la encuesta de estratificación del nivel socioeconómico")
            elif (ficha := ePersona.fichasocioeconomicainec_set.filter(status=True).first()) is not None:
                if ficha.confirmar:
                    raise NameError(u"Usted ya ha confirmado sus datos en la encuesta de estratificación del nivel socioeconómico")
            eInscripcion = InscripcionSerializer(ePerfilUsuario.inscripcion).data
            aData = {'eInscripcion': eInscripcion}
            return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)
