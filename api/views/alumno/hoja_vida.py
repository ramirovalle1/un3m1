import json
from datetime import datetime
from django.db.models import Q
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, connections
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from api.forms.hoja_vida import DatosPersonalesBasicoForm, DatosPersonalesNacimientoForm, DatosPersonalesDomicilioForm, \
    DatosPersonalesFamiliarForm, DatosPersonalesDiscapacidadForm, DatosPersonalesEtniaForm, \
    DatosPersonalesSituacionLaboralForm, DatosPersonalesMedicosForm, DatosMedicosEnfermedadForm, DatosMedicosCovidForm, \
    FormacionAcademicaBachillerForm, FormacionAcademicaSuperiorForm, FormacionAcademicaCapacitacionForm, \
    FormacionAcademicaCertificacionForm, FormacionAcademicaIdiomaForm, DatosPersonalesMigranteForm, \
    DatosPersonalesEmbarazoForm, DeporteCulturaArtistaForm, DeporteCulturaDeportistaForm, \
    DatosMedicContactoEmergenciaForm, FormacionAcademicaBecaExternaForm
from api.helpers.decorators import api_security
from api.serializers.alumno.hoja_vida import DatosPersonalesSerializer, DatosPersonalesPersonaSerializer, \
    DatosPersonalesFamiliaresSerializer, DatosPersonalesDiscapacidadSerializer, DatosPersonalesEtniaSerializer, \
    DatosPersonalesSituacionLaboralSerializer, DatosPersonalesMedicosSerializer, \
    FormacionAcademicaMisTitulosSerializer, FormacionAcademicaMisCapacitacionesSerializer, \
    FormacionAcademicaCertificadosIdiomasSerializer, FormacionAcademicaCertificacionesPersonaSerializer, \
    DatosPersonalesMigrantePersonaSerializer, DatosPersonalesEmbarazoSerializer, ArtistaPersonaSerializer, \
    DeportistaPersonaSerializer, FormacionAcademicaParticipantesMatricesSerializer, \
    FormacionAcademicaBecaPersonaSerializer, FormacionAcademicaBecaAsignacionSerializer, \
    DatosPersonalesCuentaBancariaSerializer
from api.helpers.response_herlper import Helper_Response
from core.cache import get_cache_ePerfilUsuario
from med.models import PersonaExtension
from sagest.forms import CuentaBancariaPersonaForm
from sagest.models import VacunaCovid, VacunaCovidDosis
from sga.funciones import generar_nombre, log, elimina_tildes, convertir_fecha_invertida
from sga.models import Persona, PerfilUsuario, PersonaDocumentoPersonal, PersonaDatosFamiliares, \
    PersonaSituacionLaboral, Archivo, PersonaEnfermedad, Titulacion, DetalleTitulacionBachiller, Capacitacion, \
    CertificadoIdioma, CertificacionPersona, MigrantePersona, PersonaDetalleMaternidad, ArtistaPersona, CampoArtistico, \
    DeportistaPersona, DisciplinaDeportiva, ParticipantesMatrices, BecaPersona, BecaAsignacion, CuentaBancariaPersona
from sga.templatetags.sga_extras import encrypt


class HojaVidaAPIView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = 'ALUMNO_HOJA_VIDA'

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
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'saveDatosPersonalesBasico':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesBasicoForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
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
                        ePersona.paisnacionalidad = ePais = f.cleaned_data['paisnacionalidad']
                        ePersona.nacionalidad = ePais.nacionalidad if ePais.nacionalidad else None
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
                        log(u'Editó datos personales en hoja de vida: %s' % ePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesNacimiento':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesNacimientoForm(eRequest)
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
                        log(u'Editó datos de nacimiento en hoja de vida: %s' % ePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesDomicilio':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesDomicilioForm(eRequest, eFiles)
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
                        ePersona.ciudadela = f.cleaned_data['ciudadela']
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
                        log(u'Editó datos de domicilio v: %s' % ePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesFamiliar':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        f = DatosPersonalesFamiliarForm(eRequest, eFiles)
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
                            log(u'Adicion datos familiar en hoja de vida: %s' % ePersonaDatosFamiliar, request, "add")
                        else:
                            log(u'Editó datos familiar en hoja de vida: %s' % ePersonaDatosFamiliar, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosPersonalesFamiliar':
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
                        log(u'Elimino datos familiar en hoja de vida: %s' % deletePersonaDatosFamiliar, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos del familiar', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesDiscapacidad':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePerfilInscripcion = ePersona.mi_perfil()
                        if ePerfilInscripcion.estadoarchivodiscapacidad in (2, 5):
                            raise NameError(u"Estado de la discapacidad fue validado por Bienestar")
                        f = DatosPersonalesDiscapacidadForm(eRequest, eFiles)
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
                        log(u'Editó datos de discapacidad en hoja de vida: %s' % ePerfilInscripcion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

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

            elif action == 'saveDatosPersonalesMigrante':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eMigrantePersona = MigrantePersona.objects.filter(persona=ePersona).first()
                        f = DatosPersonalesMigranteForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        if eMigrantePersona is None:
                            eMigrantePersona = MigrantePersona(persona=ePersona)
                        eMigrantePersona.paisresidencia = f.cleaned_data['paisresidencia']
                        eMigrantePersona.anioresidencia = f.cleaned_data['anioresidencia']
                        eMigrantePersona.mesresidencia = f.cleaned_data['mesresidencia']
                        eMigrantePersona.fecharetorno = f.cleaned_data['fecharetorno']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre(f"archivomigrante_", archivo.name)
                            eMigrantePersona.archivo = archivo
                            eMigrantePersona.estadoarchivo = 1
                        eMigrantePersona.save(request)
                        log(u'Editó datos de migrante en hoja de vida: %s' % eMigrantePersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesEmbarazo':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesEmbarazoForm(eRequest)
                        isNew = False
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            ePersonaDetalleMaternidad = PersonaDetalleMaternidad.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            ePersonaDetalleMaternidad = PersonaDetalleMaternidad(persona=ePersona)
                            isNew = True

                        ePersonaDetalleMaternidad.gestacion = f.cleaned_data['gestacion']
                        ePersonaDetalleMaternidad.semanasembarazo = f.cleaned_data['semanasembarazo']
                        ePersonaDetalleMaternidad.lactancia = f.cleaned_data['lactancia']
                        ePersonaDetalleMaternidad.fechainicioembarazo = f.cleaned_data['fechainicioembarazo']
                        ePersonaDetalleMaternidad.fechaparto = f.cleaned_data['fechaparto']
                        ePersonaDetalleMaternidad.save(request)
                        if isNew is True:
                            log(u'Adiciono embarazo datos médicos en hoja de vida: %s' % ePersonaDetalleMaternidad, request, "add")
                        else:
                            log(u'Editó embarazo datos médicos en hoja de vida: %s' % ePersonaDetalleMaternidad, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosPersonalesEmbarazo':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            ePersonaDetalleMaternidad = PersonaDetalleMaternidad.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteDato = ePersonaDetalleMaternidad
                        ePersonaDetalleMaternidad.delete()
                        log(u'Elimino embarazo en hoja de vida: %s' % deleteDato, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente los datos del embarazo', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosPersonalesSituacionLaboral':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesSituacionLaboralForm(eRequest)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        ePersonaSituacionLaboral = ePersona.situacion_laboral()
                        ePersonaSituacionLaboral.disponetrabajo = f.cleaned_data['disponetrabajo']
                        ePersonaSituacionLaboral.tipoinstitucionlaboral = f.cleaned_data['tipoinstitucionlaboral']
                        ePersonaSituacionLaboral.lugartrabajo = f.cleaned_data['lugartrabajo']
                        ePersonaSituacionLaboral.buscaempleo = f.cleaned_data['buscaempleo']
                        ePersonaSituacionLaboral.tienenegocio = f.cleaned_data['tienenegocio']
                        ePersonaSituacionLaboral.negocio = f.cleaned_data['negocio']
                        ePersonaSituacionLaboral.save(request)
                        log(u'Editó datos de situación laboral en hoja de vida: %s' % ePersonaSituacionLaboral, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosMedicoBasico':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosPersonalesMedicosForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        ePersonaExtension = ePersona.datos_extension()
                        ePersonaExtension.carnetiess = f.cleaned_data['carnetiess']
                        ePersonaExamenFisico = ePersonaExtension.personaexamenfisico()
                        ePersonaExamenFisico.peso = f.cleaned_data['peso']
                        ePersonaExamenFisico.talla = f.cleaned_data['talla']
                        ePersonaExamenFisico.save(request)
                        ePersona.sangre = f.cleaned_data['sangre']
                        ePersona.save(request)
                        ePersonaExtension.save(request)
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre(f"tiposangre_", archivo.name)
                            ePersonaDocumentoPersonal = ePersona.documentos_personales()
                            if ePersonaDocumentoPersonal is None:
                                ePersonaDocumentoPersonal = PersonaDocumentoPersonal(persona=ePersona,
                                                                                     tiposangre=archivo,
                                                                                     estadotiposangre=1
                                                                                     )
                            else:
                                ePersonaDocumentoPersonal.tiposangre = archivo
                                ePersonaDocumentoPersonal.estadotiposangre = 1
                            ePersonaDocumentoPersonal.save(request)
                        log(u'Editó datos básicos médicos en hoja de vida: %s' % ePersonaExtension, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosMedicoContactoEmergencia':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosMedicContactoEmergenciaForm(eRequest, eFiles)
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        ePersonaExtension = ePersona.datos_extension()
                        ePersonaExtension.contactoemergencia = f.cleaned_data['contactoemergencia']
                        ePersonaExtension.telefonoemergencia = f.cleaned_data['telefonoemergencia']
                        ePersonaExtension.parentescoemergencia = f.cleaned_data['parentescoemergencia']
                        ePersonaExtension.save(request)
                        log(u'Editó contacto de emergencia de datos médicos en hoja de vida: %s' % ePersonaExtension, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosMedicoEnfermedad':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosMedicosEnfermedadForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            ePersonaEnfermedad = PersonaEnfermedad.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            ePersonaEnfermedad = PersonaEnfermedad(persona=ePersona)
                            isNew = True
                        ePersonaEnfermedad.enfermedad = f.cleaned_data['enfermedad']
                        archivomedico = f.files.get('archivomedico', None)
                        if archivomedico:
                            archivomedico.name = generar_nombre(str(elimina_tildes(ePersonaEnfermedad.enfermedad)), archivomedico.name)
                            ePersonaEnfermedad.archivomedico = archivomedico
                            ePersonaEnfermedad.estadoarchivo = 1
                        ePersonaEnfermedad.save(request)
                        if isNew is True:
                            log(u'Adiciono enfermedad datos médicos en hoja de vida: %s' % ePersonaEnfermedad, request, "add")
                        else:
                            log(u'Editó enfermedad datos médicos en hoja de vida: %s' % ePersonaEnfermedad, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosMedicoEnfermedad':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            ePersonaEnfermedad = PersonaEnfermedad.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deletePersonaEnfermedad = ePersonaEnfermedad
                        ePersonaEnfermedad.delete()
                        log(u'Elimino enfermedad de datos médicos en hoja de vida: %s' % deletePersonaEnfermedad, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente la enfermedad', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDatosMedicoCovid':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DatosMedicosCovidForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eVacunaCovid = VacunaCovid.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eVacunaCovid = VacunaCovid(persona=ePersona)
                            isNew = True
                        eVacunaCovid.recibiovacuna = f.cleaned_data['recibiovacuna']
                        eVacunaCovid.tipovacuna = f.cleaned_data['tipovacuna']
                        eVacunaCovid.recibiodosiscompleta = f.cleaned_data['recibiodosiscompleta']
                        eVacunaCovid.deseavacunarse = f.cleaned_data['deseavacunarse']
                        certificado = f.files.get('certificado', None)
                        if certificado:
                            certificado.name = generar_nombre("certificado_covid_", certificado.name)
                            eVacunaCovid.certificado = certificado
                        eVacunaCovid.save(request)
                        dosis = json.loads(eRequest.get('dosis', []))
                        for eDosis in VacunaCovidDosis.objects.filter(cabvacuna=eVacunaCovid):
                            tiene = False
                            for d in dosis:
                                if eDosis.id == d.get('pk', 0):
                                    tiene = True
                            if tiene is False:
                                eDosis.delete()
                        contador = 0
                        for d in dosis:
                            contador += 1
                            try:
                                eVacunaCovidDosis = VacunaCovidDosis.objects.get(cabvacuna=eVacunaCovid, pk=d.get('pk', 0))
                            except ObjectDoesNotExist:
                                eVacunaCovidDosis = VacunaCovidDosis(cabvacuna=eVacunaCovid)
                            eVacunaCovidDosis.numdosis = d.get('numdosis', contador)
                            fechadosis = d.get('fechadosis', None)
                            if fechadosis is None:
                                raise NameError(f"No se encontro fecha de dosis")
                            eVacunaCovidDosis.fechadosis = convertir_fecha_invertida(fechadosis)
                            eVacunaCovidDosis.save(request)
                        if isNew is True:
                            log(u'Adiciono datos médicos de covid-19 en hoja de vida: %s' % eVacunaCovid, request, "add")
                        else:
                            log(u'Editó datos médicos de covid-19 en hoja de vida: %s' % eVacunaCovid, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosMedicoCovid':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eVacunaCovid = VacunaCovid.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteeVacunaCovid = eVacunaCovid
                        eVacunaCovid.delete()
                        log(u'Elimino datos médicos de covid-19 en hoja de vida: %s' % deleteeVacunaCovid, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente la enfermedad', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteFormacionAcademicaMisTitulos':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eTitulacion = Titulacion.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteTitulacion = eTitulacion
                        eTitulacion.delete()
                        log(u'Elimino registro de titulación de formación académica en hoja de vida: %s' % deleteTitulacion, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente la formación académica', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormacionAcademicaBachiller':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = FormacionAcademicaBachillerForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eTitulacion = Titulacion.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eTitulacion = Titulacion(persona=ePersona)
                            isNew = True
                        eTitulacion.titulo = f.cleaned_data['titulo']
                        eTitulacion.colegio = f.cleaned_data['colegio']
                        eTitulacion.save(request)
                        idd = eRequest.get('idd', 0)
                        try:
                            eDetalleTitulacionBachiller = DetalleTitulacionBachiller.objects.get(pk=idd)
                            eDetalleTitulacionBachiller.calificacion = f.cleaned_data['calificacion']
                            eDetalleTitulacionBachiller.anioinicioperiodograduacion = f.cleaned_data['anioinicioperiodograduacion']
                            eDetalleTitulacionBachiller.aniofinperiodograduacion = f.cleaned_data['aniofinperiodograduacion']
                        except ObjectDoesNotExist:
                            eDetalleTitulacionBachiller = DetalleTitulacionBachiller(titulacion=eTitulacion,
                                                                                     calificacion=f.cleaned_data['calificacion'],
                                                                                     anioinicioperiodograduacion=f.cleaned_data['anioinicioperiodograduacion'],
                                                                                     aniofinperiodograduacion=f.cleaned_data['aniofinperiodograduacion'],
                                                                                     )
                        eDetalleTitulacionBachiller.save(request)
                        actagrado = f.files.get('actagrado', None)
                        if actagrado:
                            actagrado.name = generar_nombre("actagrado_", actagrado.name)
                            eDetalleTitulacionBachiller.actagrado = actagrado
                            eArchivoActaGrdo = Archivo.objects.filter(tipo_id=16, inscripcion__persona=ePersona, status=True).last()
                            if eArchivoActaGrdo is None:
                                eArchivoActaGrdo = Archivo(tipo_id=16,
                                                           nombre=f'ACTA DE GRADO DE BACHILLER DE LA PERSONA: {ePersona}',
                                                           fecha=datetime.now().date(),
                                                           archivo=actagrado,
                                                           aprobado=True,
                                                           inscripcion=eInscripcion,
                                                           profesor=None,
                                                           sga=True
                                                           )
                            else:
                                eArchivoActaGrdo.nombre=f'ACTA DE GRADO DE BACHILLER DE LA PERSONA: {ePersona}'
                                eArchivoActaGrdo.archivo=actagrado
                            eArchivoActaGrdo.save(request)
                        reconocimientoacademico = f.files.get('reconocimientoacademico', None)
                        if reconocimientoacademico:
                            reconocimientoacademico.name = generar_nombre("actareconocimientobachiller_", reconocimientoacademico.name)
                            eDetalleTitulacionBachiller.reconocimientoacademico = reconocimientoacademico
                            eArchivoReconocimientoAcademico = Archivo.objects.filter(tipo_id=18, inscripcion__persona=ePersona, status=True).last()
                            if eArchivoReconocimientoAcademico is None:
                                eArchivoReconocimientoAcademico = Archivo(tipo_id=16,
                                                                          nombre=f'RECONOCIMIENTO ACADÉMICO DE LA PERSONA: {ePersona}',
                                                                          fecha=datetime.now().date(),
                                                                          archivo=reconocimientoacademico,
                                                                          aprobado=True,
                                                                          inscripcion=eInscripcion,
                                                                          profesor=None,
                                                                          sga=True
                                                                          )
                            else:
                                eArchivoReconocimientoAcademico.nombre=f'RECONOCIMIENTO ACADÉMICO DE LA PERSONA: {ePersona}'
                                eArchivoReconocimientoAcademico.reconocimientoacademico=reconocimientoacademico
                            eArchivoReconocimientoAcademico.save(request)
                        eDetalleTitulacionBachiller.save(request)
                        eTitulacion.save(request)
                        if isNew is True:
                            log(u'Adiciono datos médicos de covid-19 en hoja de vida: %s' % eTitulacion, request, "add")
                        else:
                            log(u'Editó datos médicos de covid-19 en hoja de vida: %s' % eTitulacion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormacionAcademicaSuperior':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = FormacionAcademicaSuperiorForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eTitulacion = Titulacion.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eTitulacion = Titulacion(persona=ePersona)
                            isNew = True
                        eTitulacion.titulo = f.cleaned_data['titulo']
                        eTitulacion.institucion = f.cleaned_data['institucion']
                        eTitulacion.areatitulo = f.cleaned_data['areatitulo']
                        eTitulacion.pais = f.cleaned_data['pais']
                        eTitulacion.provincia = f.cleaned_data['provincia']
                        eTitulacion.canton = f.cleaned_data['canton']
                        eTitulacion.parroquia = f.cleaned_data['parroquia']
                        eTitulacion.fechainicio = f.cleaned_data['fechainicio']
                        eTitulacion.cursando = f.cleaned_data['cursando']
                        eTitulacion.fechaobtencion = f.cleaned_data['fechaobtencion'] if f.cleaned_data['cursando'] is False else None
                        eTitulacion.fechaegresado = f.cleaned_data['fechaegresado'] if f.cleaned_data['cursando'] is False else None
                        eTitulacion.registro = f.cleaned_data['registro'] if f.cleaned_data['cursando'] is False else None
                        eTitulacion.fecharegistro = f.cleaned_data['fecharegistro'] if f.cleaned_data['cursando'] is False else None
                        archivo = f.files.get('archivo', None)
                        registroarchivo = f.files.get('registroarchivo', None)
                        if archivo:
                            archivo.name = generar_nombre("titulosuperior_", archivo.name)
                            eTitulacion.archivo = archivo
                        if registroarchivo:
                            registroarchivo.name = generar_nombre("certificadosenescyt_", registroarchivo.name)
                            eTitulacion.registroarchivo = registroarchivo
                        eTitulacion.save(request)
                        if isNew is True:
                            log(u'Adiciono formación académica de tipo bachiller en hoja de vida: %s' % eTitulacion, request, "add")
                        else:
                            log(u'Editó formación académica de tipo bachiller en hoja de vida: %s' % eTitulacion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormacionAcademicaCapacitacion':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = FormacionAcademicaCapacitacionForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eCapacitacion = Capacitacion.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eCapacitacion = Capacitacion(persona=ePersona)
                            isNew = True
                        eCapacitacion.institucion = f.cleaned_data['institucion']
                        eCapacitacion.nombre = f.cleaned_data['nombre']
                        eCapacitacion.descripcion = f.cleaned_data['descripcion']
                        eCapacitacion.tipo = f.cleaned_data['tipo']
                        eCapacitacion.tipocurso = f.cleaned_data['tipocurso']
                        eCapacitacion.tipoparticipacion = f.cleaned_data['tipoparticipacion']
                        eCapacitacion.tipocapacitacion = f.cleaned_data['tipocapacitacion']
                        eCapacitacion.modalidad = f.cleaned_data['modalidad']
                        eCapacitacion.otramodalidad = f.cleaned_data['otramodalidad']
                        eCapacitacion.tipocertificacion = f.cleaned_data['tipocertificacion']
                        eCapacitacion.contexto = f.cleaned_data['contexto']
                        eCapacitacion.detallecontexto = f.cleaned_data['detallecontexto']
                        eCapacitacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                        eCapacitacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                        eCapacitacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                        eCapacitacion.auspiciante = f.cleaned_data['auspiciante']
                        eCapacitacion.expositor = f.cleaned_data['expositor']
                        eCapacitacion.pais = f.cleaned_data['pais']
                        eCapacitacion.provincia = f.cleaned_data['provincia']
                        eCapacitacion.canton = f.cleaned_data['canton']
                        eCapacitacion.parroquia = f.cleaned_data['parroquia']
                        eCapacitacion.fechainicio = f.cleaned_data['fechainicio']
                        eCapacitacion.fechafin = f.cleaned_data['fechafin']
                        eCapacitacion.horas = f.cleaned_data['horas']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre("capacitacion_", archivo.name)
                            eCapacitacion.archivo = archivo
                        eCapacitacion.save(request)
                        if isNew is True:
                            log(u'Adiciono capacitación en hoja de vida: %s' % eCapacitacion, request, "add")
                        else:
                            log(u'Editó capacitación en hoja de vida: %s' % eCapacitacion, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteFormacionAcademicaMisCapacitaciones':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eCapacitacion = Capacitacion.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteCapacitacion = eCapacitacion
                        eCapacitacion.delete()
                        log(u'Elimino registro de capacitación de formación académica en hoja de vida: %s' % deleteCapacitacion, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente la capacitación', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormacionAcademicaCertificacion':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = FormacionAcademicaCertificacionForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eCertificacionPersona = CertificacionPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eCertificacionPersona = CertificacionPersona(persona=ePersona)
                            isNew = True
                        eCertificacionPersona.nombres = f.cleaned_data['nombres']
                        eCertificacionPersona.autoridad_emisora = f.cleaned_data['autoridad_emisora']
                        eCertificacionPersona.numerolicencia = f.cleaned_data['numerolicencia']
                        eCertificacionPersona.fechadesde = f.cleaned_data['fechadesde']
                        eCertificacionPersona.fechahasta = None if f.cleaned_data['vigente'] else f.cleaned_data['fechahasta']
                        eCertificacionPersona.enlace = f.cleaned_data['enlace']
                        eCertificacionPersona.vigente = f.cleaned_data['vigente']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre("certificacion_", archivo.name)
                            eCertificacionPersona.archivo = archivo
                        eCertificacionPersona.save(request)
                        if isNew is True:
                            log(u'Adiciono certificación internacional en hoja de vida: %s' % eCertificacionPersona, request, "add")
                        else:
                            log(u'Editó certificación internacional en hoja de vida: %s' % eCertificacionPersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteFormacionAcademicaCertificacion':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eCertificacionPersona = CertificacionPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteCertificacionPersona = eCertificacionPersona
                        eCertificacionPersona.delete()
                        log(u'Elimino registro de certificación internacional de formación académica en hoja de vida: %s' % deleteCertificacionPersona, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente la certificación', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormacionAcademicaIdioma':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = FormacionAcademicaIdiomaForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eCertificadoIdioma = CertificadoIdioma.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eCertificadoIdioma = CertificadoIdioma(persona=ePersona)
                            isNew = True
                        eCertificadoIdioma.idioma = f.cleaned_data['idioma']
                        eCertificadoIdioma.institucioncerti = None if f.cleaned_data['validainst'] else f.cleaned_data['institucioncerti']
                        eCertificadoIdioma.validainst = f.cleaned_data['validainst']
                        eCertificadoIdioma.otrainstitucion = f.cleaned_data['otrainstitucion']
                        eCertificadoIdioma.fechacerti = f.cleaned_data['fechacerti']
                        eCertificadoIdioma.nivelsuficencia = f.cleaned_data['nivelsuficencia']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre("certificacion_", archivo.name)
                            eCertificadoIdioma.archivo = archivo
                        eCertificadoIdioma.save(request)
                        if isNew is True:
                            log(u'Adiciono certificación internacional en hoja de vida: %s' % eCertificadoIdioma, request, "add")
                        else:
                            log(u'Editó certificación internacional en hoja de vida: %s' % eCertificadoIdioma, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormCuentaBancaria':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = CuentaBancariaPersonaForm(eRequest, eFiles)
                        isNew = False
                        # f.initQuerySet(eRequest)
                        if not f.is_valid():
                            raise NameError(u"Error en los datos del formulario.")
                        id = eRequest.get('id', '0')
                        if id != '0':
                            id = encrypt(id)
                        try:
                            eCuentaBancaria = CuentaBancariaPersona.objects.get(persona=ePersona, pk=int(id), status=True)
                        except ObjectDoesNotExist:
                            eCuentaBancaria = CuentaBancariaPersona(persona=ePersona, estadorevision=1)
                            isNew = True

                        if ePersona.cuentabancariapersona_set.filter(numero=f.cleaned_data['numero'].strip(), status=True).exclude(
                                id=eCuentaBancaria.id).exists():
                            raise NameError(u"La cuenta bancaria ya se encuentra registrada.")

                        if eCuentaBancaria.verificado or eCuentaBancaria.estadorevision == 2:
                            raise NameError(u"No puede modificar la cuenta bancaria.")

                        eCuentaBancaria.estadorevision = 1

                        eCuentaBancaria.tipocuentabanco = f.cleaned_data['tipocuentabanco']
                        eCuentaBancaria.banco = f.cleaned_data['banco']
                        eCuentaBancaria.numero = f.cleaned_data['numero']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre("cuentabancaria_", archivo.name)
                            eCuentaBancaria.archivo = archivo

                        activopagobeca = f.cleaned_data['activapago']
                        if activopagobeca:
                            for cuentas in ePersona.cuentabancariapersona_set.filter(activapago=True, status=True).exclude(
                                    id=eCuentaBancaria.id):
                                cuentas.activapago = False
                                cuentas.save(request)

                        eCuentaBancaria.activapago = activopagobeca
                        eCuentaBancaria.save(request)
                        if isNew is True:
                            log(u'Adiciono cuenta bancaria en hoja de vida: %s' % eCuentaBancaria, request, "add")
                        else:
                            log(u'Editó cuenta bancaria en hoja de vida: %s' % eCuentaBancaria, request, "edit")

                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteCuentaBancaria':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', '0')
                        if id != '0':
                            id = encrypt(id)
                        try:
                            eCuentaBancaria = CuentaBancariaPersona.objects.get(persona=ePersona, pk=int(id))
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        if eCuentaBancaria.verificado or eCuentaBancaria.estadorevision == 2:
                            raise NameError(u"No puede eliminar la cuenta bancaria.")
                        if eCuentaBancaria.activapago:
                            raise NameError(u"No puede eliminar la cuenta bancaria, se encuentra asignada al proceso de beca.")

                        eCuentaBancaria.status = False
                        eCuentaBancaria.save(request)
                        log(u'Elimino registro de cuenta bancaria en hoja de vida: %s' % eCuentaBancaria, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se eliminó correctamente la cuenta bancaria', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'activaPagoBecaCuentaBancaria':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        check = eRequest.get('check', None)
                        id = eRequest.get('id', '0')
                        if id != '0':
                            id = encrypt(id)
                        try:
                            eCuentaBancaria = CuentaBancariaPersona.objects.get(persona=ePersona, pk=int(id), status=True)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")

                        if check is not None:
                            if check:
                                for cuentas in ePersona.cuentabancariapersona_set.filter(activapago=True, status=True).exclude(id=eCuentaBancaria.id):
                                    cuentas.activapago = False
                                    cuentas.save(request)
                            eCuentaBancaria.activapago = check
                            eCuentaBancaria.save(request)
                        else:
                            raise NameError(u"Error al guardar los datos")
                        log(u'Cambio estado de activo pago beca de cuenta bancaria en hoja de vida: %s' % eCuentaBancaria, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteFormacionAcademicaIdioma':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eCertificadoIdioma = CertificadoIdioma.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteCertificadoIdioma = eCertificadoIdioma
                        eCertificadoIdioma.delete()
                        log(u'Elimino registro de certificación idioma de formación académica en hoja de vida: %s' % deleteCertificadoIdioma, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente la certificación', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDeporteCulturaArtista':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DeporteCulturaArtistaForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eArtistaPersona = ArtistaPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eArtistaPersona = ArtistaPersona(persona=ePersona)
                            isNew = True                        
                        eArtistaPersona.grupopertenece = f.cleaned_data['grupopertenece']
                        eArtistaPersona.fechainicioensayo = f.cleaned_data['fechainicioensayo']
                        eArtistaPersona.fechafinensayo = f.cleaned_data['fechafinensayo']
                        archivo = f.files.get('archivo', None)
                        if not eArtistaPersona.archivo:
                            if archivo is None:
                                raise NameError(u"Archivo de artista no se encontro")
                        if archivo:
                            archivo.name = generar_nombre(f"archivoartista_", archivo.name)
                            eArtistaPersona.archivo = archivo
                            eArtistaPersona.estadoarchivo = 1
                        eArtistaPersona.save(request)
                        if eArtistaPersona.id:
                            eArtistaPersona.campoartistico.clear()
                        campoartistico = f.data.get('campoartistico', None)
                        if campoartistico is not None:
                            for id in json.loads(campoartistico):
                                eArtistaPersona.campoartistico.add(CampoArtistico.objects.get(pk=id))
                        eArtistaPersona.save(request)
                        if isNew is True:
                            log(u'Adiciono artista en hoja de vida: %s' % eArtistaPersona, request, "add")
                        else:
                            log(u'Editó artista en hoja de vida: %s' % eArtistaPersona, request, "edit")

                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosArtista':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eArtistaPersona = ArtistaPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteArtistaPersona = eArtistaPersona
                        eArtistaPersona.delete()
                        log(u'Elimino registro de artista en hoja de vida: %s' % deleteArtistaPersona, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente artista', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveDeporteCulturaDeportista':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = DeporteCulturaDeportistaForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eDeportistaPersona = DeportistaPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eDeportistaPersona = DeportistaPersona(persona=ePersona)
                            isNew = True
                        eDeportistaPersona.representapais = f.cleaned_data['representapais']
                        eDeportistaPersona.evento = f.cleaned_data['evento']
                        eDeportistaPersona.paisevento = f.cleaned_data['paisevento']
                        eDeportistaPersona.equiporepresenta = f.cleaned_data['equiporepresenta']
                        eDeportistaPersona.fechainicioevento = f.cleaned_data['fechainicioevento']
                        eDeportistaPersona.fechafinevento = f.cleaned_data['fechafinevento']
                        eDeportistaPersona.fechainicioentrena = f.cleaned_data['fechainicioentrena']
                        eDeportistaPersona.fechafinentrena = f.cleaned_data['fechafinentrena']
                        archivoevento = f.files.get('archivoevento', None)
                        if not eDeportistaPersona.archivoevento:
                            if archivoevento is None:
                                raise NameError(u"Archivo de evento no se encontro")
                        if archivoevento:
                            archivoevento.name = generar_nombre(f"archivo_deportista_evento_", archivoevento.name)
                            eDeportistaPersona.archivoevento = archivoevento
                            eDeportistaPersona.estadoarchivoevento = 1
                        archivoentrena = f.files.get('archivoentrena', None)
                        if not eDeportistaPersona.archivoentrena:
                            if archivoentrena is None:
                                raise NameError(u"Archivo de entrenamiento no se encontro")
                        if archivoentrena:
                            archivoentrena.name = generar_nombre(f"archivo_deportista_entrena_", archivoentrena.name)
                            eDeportistaPersona.archivoentrena = archivoentrena
                            eDeportistaPersona.estadoarchivoentrena = 1
                        eDeportistaPersona.save(request)
                        if eDeportistaPersona.id:
                            eDeportistaPersona.disciplina.clear()
                        disciplina = f.data.get('disciplina', None)
                        if disciplina is not None:
                            for id in json.loads(disciplina):
                                eDeportistaPersona.disciplina.add(DisciplinaDeportiva.objects.get(pk=id))
                        eDeportistaPersona.save(request)
                        if isNew is True:
                            log(u'Adiciono deportista en hoja de vida: %s' % eDeportistaPersona, request, "add")
                        else:
                            log(u'Editó deportista en hoja de vida: %s' % eDeportistaPersona, request, "edit")

                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteDatosDeportista':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eDeportistaPersona = DeportistaPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteDeportistaPersona = eDeportistaPersona
                        eDeportistaPersona.delete()
                        log(u'Elimino registro de deportista en hoja de vida: %s' % deleteDeportistaPersona, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente artista', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'saveFormacionAcademicaBecaExterna':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        f = FormacionAcademicaBecaExternaForm(eRequest, eFiles)
                        isNew = False
                        f.initQuerySet(eRequest)
                        if not f.is_valid():
                            errors = []
                            for k, v in f.errors.items():
                                errors.append({'field': k, 'message': v[0]})
                            f.addErrors(errors)
                            form = f.toArray()
                            transaction.set_rollback(True)
                            return Helper_Response(isSuccess=False, data={'form': form}, message=f'Debe ingresar la información en todos los campos requeridos', status=status.HTTP_200_OK)
                        id = eRequest.get('id', 0)
                        try:
                            eBecaPersona = BecaPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            eBecaPersona = BecaPersona(persona=ePersona)
                            isNew = True
                        eBecaPersona.tipoinstitucion = f.cleaned_data['tipoinstitucion']
                        eBecaPersona.institucion = f.cleaned_data['institucion']
                        eBecaPersona.fechainicio = f.cleaned_data['fechainicio']
                        eBecaPersona.fechafin = f.cleaned_data['fechafin']
                        archivo = f.files.get('archivo', None)
                        if archivo:
                            archivo.name = generar_nombre("certificacion_", archivo.name)
                            eBecaPersona.archivo = archivo
                        eBecaPersona.save(request)
                        if isNew is True:
                            log(u'Adiciono beca externa en hoja de vida: %s' % eBecaPersona, request, "add")
                        else:
                            log(u'Editó beca externa en hoja de vida: %s' % eBecaPersona, request, "edit")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se guardo correctamente los datos', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'deleteFormacionAcademicaBecaExterna':
                with transaction.atomic():
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        id = eRequest.get('id', 0)
                        try:
                            eBecaPersona = BecaPersona.objects.get(persona=ePersona, pk=id)
                        except ObjectDoesNotExist:
                            raise NameError(u"Datos no encontrados")
                        deleteBecaPersona = eBecaPersona
                        eBecaPersona.delete()
                        log(u'Elimino registro de beca externa en hoja de vida: %s' % deleteBecaPersona, request, "del")
                        return Helper_Response(isSuccess=True, data={}, message=f'Se elimino correctamente registro', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Error al guardar los datos: {ex.__str__()}', status=status.HTTP_200_OK)


            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):

        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            # if not ePerfilUsuario.es_estudiante():
            #     raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')

            eRequest = request.query_params
            if 'action' in eRequest:
                action = request.query_params['action']
                # ePersona = ePerfilUsuario.persona
                if action == 'loadDatosPersonales':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = DatosPersonalesSerializer(eInscripcion.persona).data
                        return Helper_Response(isSuccess=True, data={'ePersona': ePersona}, message=f'',
                                               status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesFamiliares':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = eInscripcion.persona
                        ePersonaDatosFamiliares = ePersona.familiares()
                        ePersonaSerializer = DatosPersonalesPersonaSerializer(ePersona).data
                        ePersonaDatosFamiliares = DatosPersonalesFamiliaresSerializer(ePersona.familiares(), many=True).data if ePersonaDatosFamiliares.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'ePersonaDatosFamiliares': ePersonaDatosFamiliares, 'ePersona': ePersonaSerializer}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePersonaDatosFamiliares': [], 'ePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

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
                        ePersona = Persona.objects.filter(
                            Q(cedula=identificacion) | Q(pasaporte=identificacion)).first()
                        ePersona = DatosPersonalesPersonaSerializer(ePersona).data if ePersona else {}
                        return Helper_Response(isSuccess=True, data={'ePersona': ePersona}, message=f'',
                                               status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePersona': {}},
                                               message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesDiscapacidad':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePerfilInscripcion = ePersona.mi_perfil()
                        ePerfilInscripcion = DatosPersonalesDiscapacidadSerializer(ePerfilInscripcion).data if ePerfilInscripcion else {}
                        return Helper_Response(isSuccess=True, data={'ePerfilInscripcion': ePerfilInscripcion}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesEtnia':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePerfilInscripcion = ePersona.mi_perfil()
                        ePerfilInscripcion = DatosPersonalesEtniaSerializer(ePerfilInscripcion).data if ePerfilInscripcion else {}
                        return Helper_Response(isSuccess=True, data={'ePerfilInscripcion': ePerfilInscripcion}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePerfilInscripcion': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesFinanzas':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eCuentasBancarias = ePersona.cuentasbancarias()
                        eCuentasBancarias = DatosPersonalesCuentaBancariaSerializer(eCuentasBancarias, many=True).data if eCuentasBancarias else []
                        return Helper_Response(isSuccess=True, data={'eCuentasBancarias': eCuentasBancarias}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eCuentasBancarias': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesMigrante':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eMigrantePersona = MigrantePersona.objects.filter(persona=ePersona).first()
                        eMigrantePersona = DatosPersonalesMigrantePersonaSerializer(eMigrantePersona).data if eMigrantePersona else {}
                        return Helper_Response(isSuccess=True, data={'eMigrantePersona': eMigrantePersona}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eMigrantePersona': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesEmbarazo':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePersonaDetalleMaternidades = ePersona.personadetallematernidad_set.filter(status=True).order_by('-pk')
                        ePersonaDetalleMaternidades = DatosPersonalesEmbarazoSerializer(ePersonaDetalleMaternidades, many=True).data if ePersonaDetalleMaternidades.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'ePersonaDetalleMaternidades': ePersonaDetalleMaternidades}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePersonaDetalleMaternidades': []}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesSituacionLaboral':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePersonaSituacionLaboral = DatosPersonalesSituacionLaboralSerializer(ePersona.situacion_laboral()).data
                        return Helper_Response(isSuccess=True, data={'ePersonaSituacionLaboral': ePersonaSituacionLaboral}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePersonaSituacionLaboral': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDatosPersonalesMedicos':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        ePersonaExtension = ePersona.datos_extension()
                        ePersonaExtension = DatosPersonalesMedicosSerializer(ePersonaExtension).data if ePersonaExtension else {}
                        return Helper_Response(isSuccess=True, data={'ePersonaExtension': ePersonaExtension}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'ePersonaExtension': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadFormacionAcademicaMisTitulos':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eTitulaciones = ePersona.titulacion_set.filter(status=True)
                        aData = {}
                        # if eTitulaciones.values("id").filter(titulo__nivel__nivel=1).exists():
                        #     aData['eNivelPrimaria'] = FormacionAcademicaMisTitulosSerializer(eTitulaciones.filter(titulo__nivel__nivel=1), many=True).data
                        if eTitulaciones.values("id").filter(titulo__nivel__nivel=2).exists():
                            aData['eNivelBachilleres'] = FormacionAcademicaMisTitulosSerializer(eTitulaciones.filter(titulo__nivel__nivel=2).order_by('fechainicio'), many=True).data
                        if eTitulaciones.values("id").filter(titulo__nivel__nivel__in=[3, 4, 5]).exists():
                            aData['eNivelSuperiores'] = FormacionAcademicaMisTitulosSerializer(eTitulaciones.filter(titulo__nivel__nivel__in=[3, 4, 5]).order_by('fechainicio'), many=True).data
                        return Helper_Response(isSuccess=True, data={'eTitulaciones': aData}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eTitulaciones': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadFormacionAcademicaMisCapacitaciones':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eCapacitaciones = ePersona.mis_capacitaciones()
                        eCapacitaciones = FormacionAcademicaMisCapacitacionesSerializer(eCapacitaciones, many=True).data if eCapacitaciones.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eCapacitaciones': eCapacitaciones}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eCapacitaciones': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadFormacionAcademicaMisCertificaciones':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eCertificadosIdiomas = CertificadoIdioma.objects.filter(persona=ePersona)
                        eCertificadosIdiomas = FormacionAcademicaCertificadosIdiomasSerializer(eCertificadosIdiomas, many=True).data if eCertificadosIdiomas.values("id").exists() else []
                        eCertificacionesPersona = CertificacionPersona.objects.filter(persona=ePersona)
                        eCertificacionesPersona = FormacionAcademicaCertificacionesPersonaSerializer(eCertificacionesPersona, many=True).data if eCertificacionesPersona.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eCertificaciones': {'eCertificadosIdiomas': eCertificadosIdiomas,
                                                                                          'eCertificacionesPersona': eCertificacionesPersona}}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eCapacitaciones': {}}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDeporteCulturaArtistas':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eArtistas = ArtistaPersona.objects.filter(persona=ePersona, status=True).order_by('-id')
                        eArtistas = ArtistaPersonaSerializer(eArtistas, many=True).data if eArtistas.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eArtistas': eArtistas}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eArtistas': []}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadDeporteCulturaDeportistas':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eDeportistas = DeportistaPersona.objects.filter(persona=ePersona, status=True).order_by('-id')
                        eDeportistas = DeportistaPersonaSerializer(eDeportistas, many=True).data if eDeportistas.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eDeportistas': eDeportistas}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eDeportistas': []}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadFormacionAcademicaProyectos':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        filtro = Q(matrizevidencia_id=2) & Q(status=True) & Q(inscripcion__persona=ePersona) & Q(proyecto__status=True) & Q(Q(actividad__isnull=True) | Q(actividad__isnull=False))
                        eParticipantesMatrices = ParticipantesMatrices.objects.filter(filtro)
                        eProyectos = FormacionAcademicaParticipantesMatricesSerializer(eParticipantesMatrices, many=True).data if eParticipantesMatrices.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eProyectos': eProyectos}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eProyectos': []}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

                elif action == 'loadFormacionAcademicaBecas':
                    try:
                        eInscripcion = ePerfilUsuario.inscripcion
                        ePersona = Persona.objects.get(pk=eInscripcion.persona_id)
                        eBecas_1 = BecaAsignacion.objects.filter(Q(solicitud__inscripcion__persona=ePersona, status=True))
                        eBecas_1 = FormacionAcademicaBecaAsignacionSerializer(eBecas_1, many=True).data if eBecas_1.values("id").exists() else []
                        eBecas_2 = BecaPersona.objects.filter(Q(status=True, persona=ePersona))
                        eBecas_2 = FormacionAcademicaBecaPersonaSerializer(eBecas_2, many=True).data if eBecas_2.values("id").exists() else []
                        return Helper_Response(isSuccess=True, data={'eBecasInternas': eBecas_1, 'eBecasExternas': eBecas_2}, message=f'', status=status.HTTP_200_OK)
                    except Exception as ex:
                        return Helper_Response(isSuccess=False, data={'eBecasInternas': [], 'eBecasExternas': []}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)