import json
from datetime import datetime

from djcelery.admin_utils import action
from docutils.nodes import acronym
from rest_framework import status, serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from xlrd.book import Name

from api.serializers.alumno.hojadevida import HojaVidaPersonaSerializer, \
    PersonaExtensionSerializer, PerfilInscripcionSerializer, \
    PersonaEstadoCivilSerializer, PersonaDatosFamiliaresSerializer, \
    PersonaDocumentoPersonalSerializer, PaisSerializer, ProvinciaSerializer, \
    CantonSerializer, ParroquiaSerializer, ParentescoPersonaSerializer, TipoDiscapacidadSerializer, \
    InstitucionBecaSerializer, NivelTitulacionSerializer, FormaTrabajoSerializer, NacionalidadIndigenaSerializer, \
    RazaSerializer, SubTipoDiscapacidadSerializer, PersonaSituacionLaboralSerializer, \
    ArchivoSerializer, TipoArchivoSerializer, CuentaBancariaPersonaSerializer, BancoSerializer, \
    TipoCuentaBancoSerializer, PersonaExamenFisicoSerializer, TipoSangreSerializer, PersonaSangreSerializer, \
    PersonaEnfermedadSerializer, EnfermedadSerializer, VacunaCovidSerializer, TipoVacunaCovidSerializer, \
    TitulacionSerializer, TituloSerializer, AreaTituloSerializer, InstitucionEducacionSuperiorSerializer, \
    ColegioSerializer, AreaConocimientoTitulacionSerializer, CapacitacionSerializer, TipoCursoSerializer, \
    TipoCertificacionSerializer, TipoParticipacionSerializer, ContextoCapacitacionSerializer, \
    DetalleContextoCapacitacionSerializer, SubAreaConocimientoTitulacionSerializer, \
    SubAreaEspecificaConocimientoTitulacionSerializer, TipoCapacitacionSerializer, CertificadoIdiomaSerializer, \
    IdiomaSerializer, InstitucionCertificadoraSerializer, NivelSuficenciaSerializer, CertificadoPersonaSerializer, \
    ExperienciaLaboralSerializer, OtroRegimenLaboralSerializer, ActividadLaboralSerializer, MotivoSalidaSerializer, \
    DedicacionLaboralSerializer, OtroMeritoSerializer, ReferenciaPersonaSerializer, RelacionSerializer, \
    BecaPersonaSerializer, \
    MigrantePersonaSerializer, ArtistaPersonaSerializer, CampoArtisticoSerializer, DeportistaPersonaSerializer, \
    DisciplinaDeportivaSerializer, VacunaCovidDosisSerializer

from api.helpers.response_herlper import Helper_Response
from med.models import Enfermedad
from sagest.models import Banco, TipoCuentaBanco, VacunaCovid, TipoVacunaCovid, VacunaCovidDosis, ExperienciaLaboral, \
    MotivoSalida, OtroRegimenLaboral, ActividadLaboral, DedicacionLaboral, OtroMerito
from sga.funciones import generar_nombre, log

from sga.models import Persona, PerfilUsuario, PersonaEstadoCivil, \
    Pais, Provincia, Canton, Parroquia, ParentescoPersona, Discapacidad, \
    InstitucionBeca, PersonaDatosFamiliares, NivelTitulacion, Raza, NacionalidadIndigena, \
    SubTipoDiscapacidad, PersonaSituacionLaboral, Archivo, Inscripcion, TipoArchivo, CuentaBancariaPersona, TipoSangre, \
    PersonaEnfermedad, Titulacion, Titulo, AreaTitulo, InstitucionEducacionSuperior, Colegio, \
    AreaConocimientoTitulacion, SubAreaConocimientoTitulacion, Capacitacion, TipoCurso, TipoCertificacion, \
    TipoParticipacion, TipoCapacitacion, ContextoCapacitacion, DetalleContextoCapacitacion, \
    SubAreaEspecificaConocimientoTitulacion, CertificadoIdioma, Idioma, InstitucionCertificadora, NivelSuficencia, \
    CertificacionPersona, ReferenciaPersona, Relacion, BecaAsignacion, BecaPersona, MigrantePersona, ArtistaPersona, \
    CampoArtistico, DeportistaPersona, DisciplinaDeportiva, CamposTitulosPostulacion, PersonaDocumentoPersonal
from sga.templatetags.sga_extras import encrypt
from socioecon.models import FormaTrabajo


class HojaVidaAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        payload = request.auth.payload
        ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
        if not ePerfilUsuario.es_estudiante():
            raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
        action = None

        ePersona = ePerfilUsuario.persona
        eInscripcion = ePerfilUsuario.inscripcion
        date_format = "%Y-%m-%d"

        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de accion no encontrado')
            action = eRequest['action']

            if action == 'datosbasicos':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')
                    persona_serializer = HojaVidaPersonaSerializer(ePersona)
                    eDocumentosPersonales = ePersona.documentos_personales()
                    documentopersonales_serializer = PersonaDocumentoPersonalSerializer(eDocumentosPersonales)

                    idpais = None
                    idprovincia = provincia = provincia_seria = None
                    idcanton = canton = canton_seria = None
                    idparroquia = parroquia = parroquia_seria = None

                    if 'nacimiento' in eRequest:
                        idpais = ePersona.paisnacimiento
                        idprovincia = ePersona.provincianacimiento
                        idcanton = ePersona.cantonnacimiento
                        idparroquia = ePersona.parroquianacimiento



                    if 'domicilio' in eRequest:
                        pass

                    paises = Pais.objects.filter(status=True)
                    pais_serializer = PaisSerializer(paises, many=True)

                    if idprovincia or idpais:
                        provincia = Provincia.objects.filter(pais=idpais)
                        provincia_serializer = ProvinciaSerializer(provincia, many=True)
                    if idcanton or idprovincia:
                        canton = Canton.objects.filter(provincia=idprovincia)
                        canton_serializer = CantonSerializer(canton, many=True)
                    if idparroquia or idcanton:
                        parroquia = Parroquia.objects.filter(canton=idcanton)
                        parroquia_serializer = ParroquiaSerializer(parroquia, many=True)

                    aData = {
                        'ePersona': persona_serializer.data,
                        'eDocumento': documentopersonales_serializer.data,
                        'ePaises': pais_serializer.data if paises else [],
                        'eProvincia': provincia_serializer.data if provincia else [],
                        'eCanton': canton_serializer.data if canton else [],
                        'eParroquia': parroquia_serializer.data if parroquia else [],
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'savedatosbasicos':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    #eRequest = json.loads(eRequest['data'])
                    if 'id' in eRequest:
                        idpersona = int(encrypt(eRequest['id']))

                    if idpersona > 0:
                        if ePerfilUsuario.persona.id == idpersona:
                            ePersona = Persona.objects.get(id=idpersona)
                            ePersona.nombres = eRequest['eNombres']
                            ePersona.apellido1 = eRequest['eApellido1']
                            ePersona.apellido2 = eRequest['eApellido2']
                            ePersona.nacimiento = eRequest['eNacimiento']
                            ePersona.libretamilitar = eRequest.get('eLibreta', 'S/N')
                            ePersona.anioresidencia = eRequest['eTiempoRecidencia']
                            ePersona.email = eRequest['eCorreoPersonal']
                            ePersona.emailinst = eRequest['eCorreoInstitucional']
                            ePersona.lgtbi = eRequest.get("eLgbti") == 'on'
                            ePersona.eszurdo = eRequest.get("eZurdo") == 'on'

                            if 'valdoc' in eRequest:
                                if 'tipdoc' in eRequest:
                                    doc = int(eRequest['tipdoc'])
                                    if doc != 0:
                                        if doc == 1:
                                            ePersona.cedula = eRequest['valdoc']
                                        else:
                                            ePersona.pasaporte = eRequest['valdoc']
                                    else:
                                        raise NameError('Error no se encuentra tipo de documento')

                            ePersona.save()

                        fileCedula = None
                        filePapeleta = None
                        fileLibreta = None

                        if 'fileCedula' in eFiles:
                            fileCedula = eFiles['fileCedula']
                            extensionDocumento = fileCedula._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento -1]
                            if fileCedula.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            fileCedula._name = generar_nombre("cedula", fileCedula._name)
                        if 'filePapeleta' in eFiles:
                            filePapeleta = eFiles['filePapeleta']
                            extensionDocumento = filePapeleta._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento -1]
                            if filePapeleta.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            filePapeleta._name = generar_nombre("papeleta", filePapeleta._name)
                        if 'fileLibreta' in eFiles:
                            fileLibreta = eFiles['fileLibreta']
                            extensionDocumento = fileLibreta._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento -1]
                            if fileLibreta.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            fileLibreta._name = generar_nombre("libretamilitar", fileLibreta._name)

                        eDocPersonal = ePersona.documentos_personales()

                        if fileCedula:
                            eDocPersonal.cedula = fileCedula
                        if filePapeleta:
                            eDocPersonal.papeleta = filePapeleta
                        if fileLibreta:
                            eDocPersonal.libretamilitar = fileLibreta
                        eDocPersonal.save()


                    if 'name' in eRequest:
                        pass

                    if 'description' in eRequest:
                        pass



                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                     return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedatosnacimiento':
                try:

                    ePersona.paisnacimiento_id = int(eRequest['ePais'])
                    if ePersona.paisnacimiento_id == 1:
                        ePersona.provincianacimiento_id = int(eRequest['eProvincia'])
                        ePersona.cantonnacimiento_id = int(eRequest['canton'])
                        ePersona.parroquianacimiento_id = int(eRequest['parroquia'])
                    else:
                        if 'eProvincia' in eRequest:
                            ePersona.provincianacimiento_id = int(eRequest['eProvincia'])
                        else:
                            ePersona.provincianacimiento = None
                        if 'canton' in eRequest:
                            ePersona.cantonnacimiento_id = int(eRequest['canton'])
                        else:
                            ePersona.cantonnacimiento = None
                        if 'parroquia' in eRequest:
                            ePersona.parroquianacimiento_id = int(eRequest['parroquia'])
                        else:
                            ePersona.parroquianacimiento = None
                    ePersona.nacionalidad = eRequest.get('eNacionalidad', '')
                    ePersona.save()

                    log(u"Editó datos nacimiento: %s" % ePersona, request, "edit")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedatosdomicilio':
                try:

                    ePersona.pais_id = int(eRequest['ePais'])
                    if ePersona.pais_id == 1:
                        ePersona.provincia_id = int(eRequest['eProvincia'])
                        ePersona.canton_id = int(eRequest['eCanton'])
                        ePersona.parroquia_id = int(eRequest['eParroquia'])
                    else:
                        if 'eProvincia' in eRequest:
                            ePersona.provincia_id = int(eRequest['eProvincia'])
                        else:
                            ePersona.provincia = None
                        if 'eCanton' in eRequest:
                            ePersona.canton_id = int(eRequest['eCanton'])
                        else:
                            ePersona.canton = None
                        if 'eParroquia' in eRequest:
                            ePersona.parroquia_id = int(eRequest['eParroquia'])
                        else:
                            ePersona.parroquia = None

                    ePersona.direccion = eRequest['calleprincipal']
                    ePersona.direccion2 = eRequest['callesecundaria']
                    ePersona.ciudadela = eRequest['eCiudadela']
                    ePersona.num_direccion = eRequest['numcasa']
                    ePersona.referencia = eRequest['referencia']
                    ePersona.sector = eRequest['sector']
                    ePersona.telefono = eRequest['telefono']
                    ePersona.telefono_conv = eRequest['tel_fijo']
                    ePersona.zona = int(eRequest['zonaresidencia'])

                    fileCroquis = None
                    filePlanilla = None

                    if 'fileCroquis' in eFiles:
                        fileCroquis = eFiles['fileCroquis']
                        extensionDocumento = fileCroquis._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileCroquis.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileCroquis._name = generar_nombre("croquis", fileCroquis._name)
                    if 'filePapeleta' in eFiles:
                        filePlanilla = eFiles['filePapeleta']
                        extensionDocumento = filePlanilla._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if filePlanilla.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        filePlanilla._name = generar_nombre("planilla", filePlanilla._name)

                    if filePlanilla:
                        ePersona.archivoplanillaluz = filePlanilla
                    if fileCroquis:
                        ePersona.archivocroquis = fileCroquis


                    ePersona.save()
                    log(u"Editó datos de domicilio: %s" % ePersona, request, "edit")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'filtra_provincia':
                try:
                    provincias = None
                    pais = None
                    provincia_serializer = {}
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        pais = Pais.objects.get(pk=id)
                        provincias = Provincia.objects.filter(status=True, pais=pais)
                        provincia_serializer = ProvinciaSerializer(provincias, many=True)

                    aData = {
                        'eProvincia': provincia_serializer.data if provincias.exists() else [],
                        'eNacionalidad': pais.nacionalidad if pais and pais.nacionalidad else ''
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'filtra_canton':
                try:
                    cantones = None
                    provincia = None
                    canton_seria = {}
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        provincia = Provincia.objects.get(pk=id)
                        cantones = Canton.objects.filter(status=True, provincia=provincia)
                        canton_seria = CantonSerializer(cantones, many=True)

                    aData = {
                        'eCanton': canton_seria.data if cantones.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            if action == 'filtra_parroquia':
                try:
                    canton = None
                    parroquias = None
                    parroquia_seria = {}
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        canton = Canton.objects.get(pk=id)
                        parroquias = Parroquia.objects.filter(status=True, canton=canton)
                        parroquia_seria = ParroquiaSerializer(parroquias, many=True)

                    aData = {
                        'eParroquia': parroquia_seria.data if parroquias.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


            if action == 'savecontacto':
                try:
                    datos_extension = ePersona.datos_extension()

                    datos_extension.contactoemergencia = eRequest['eContacto']
                    datos_extension.telefonoemergencia = eRequest['eContactoTelefono']
                    datos_extension.parentescoemergencia_id = int(eRequest['eParentesco'])

                    datos_extension.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savefamiliar':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eFamiliar = PersonaDatosFamiliares.objects.get(id=id)

                        eFamiliar.persona=ePersona
                        eFamiliar.identificacion = eRequest['eIdentificacion']
                        eFamiliar.parentesco_id = int(eRequest['eParentesco'])
                        eFamiliar.nombre = eRequest['eNombreFamiliar']
                        eFamiliar.nacimiento= eRequest['eFechaNac']
                        eFamiliar.fallecido = eRequest.get("eFallecido") == 'on'
                        eFamiliar.telefono=eRequest['eCelular']
                        eFamiliar.telefono_conv=eRequest['eCelFjo']
                        eFamiliar.convive=eRequest.get("eConvive") == 'on'
                        eFamiliar.sustentohogar=eRequest.get("eSustento") == 'on'
                        eFamiliar.tipoinstitucionlaboral = int(eRequest['eInstitucionLaboral'])
                        eFamiliar.tienenegocio = eRequest.get("eNegocio") == 'on'
                        eFamiliar.negocio = eRequest.get('eNegocioDes', '')
                        eFamiliar.niveltitulacion_id = int(eRequest['eNivelTitulacion'])
                        eFamiliar.ingresomensual = float(eRequest.get('eIngresoM', 0))
                        eFamiliar.formatrabajo_id = int(eRequest['eFormaTrabajo'])

                    else:

                        if ePersona.personadatosfamiliares_set.filter(
                                identificacion=eRequest['eIdentificacion']).exists():
                            return Helper_Response(isSuccess=False, data={}, message=f'Familiar ya se encuentra registado',
                                                   status=status.HTTP_200_OK)
                        eFamiliar = PersonaDatosFamiliares(persona=ePersona,
                                                          identificacion= eRequest['eIdentificacion'],
                                                          parentesco_id=int(eRequest['eParentesco']),
                                                          nombre=eRequest['eNombreFamiliar'],
                                                          nacimiento=eRequest['eFechaNac'],
                                                          fallecido= eRequest.get("eFallecido") == 'on',
                                                          telefono=eRequest['eCelular'],
                                                          telefono_conv=eRequest['eCelFjo'],
                                                          convive=eRequest.get("eConvive") == 'on',
                                                          sustentohogar=eRequest.get("eSustento") == 'on',
                                                          tipoinstitucionlaboral=int(eRequest['eInstitucionLaboral']),
                                                          tienenegocio=eRequest.get("eNegocio") == 'on',
                                                          negocio=eRequest.get('eNegocioDes', ''),
                                                          niveltitulacion_id= int(eRequest['eNivelTitulacion']),
                                                          ingresomensual= float(eRequest.get('eIngresoM', 0)),
                                                          formatrabajo_id= int(eRequest['eFormaTrabajo']),
                                                          # trabajo= eRequest['eIdentificacion'],
                                                          # rangoedad= eRequest['eIdentificacion'],
                                                           )
                        #eFamiliar.save()
                    eFamiliar.tienediscapacidad = eRequest.get("eDiscapacidad") == 'on'
                    if eFamiliar.tienediscapacidad:
                        eFamiliar.tipodiscapacidad_id = int(eRequest['eTipoDiscapacidad'])
                        eFamiliar.carnetdiscapacidad = eRequest.get('eNumDiscapacidad', '')
                        eFamiliar.essustituto = eRequest.get("eSustito") == 'on',
                        eFamiliar.autorizadoministerio = eRequest.get("eCheckAutorizado") == 'on',
                        eFamiliar.porcientodiscapacidad = float(eRequest.get('ePorcentaje', 0)),

                    fileCedula = None
                    fileCarnet = None
                    fileAutorizado = None
                    if 'fileCedula' in eFiles:
                        fileCedula = eFiles['fileCedula']
                        extensionDocumento = fileCedula._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileCedula.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileCedula._name = generar_nombre("cedulaidentidad", fileCedula._name)
                    if 'fileCarnet' in eFiles:
                        fileCarnet = eFiles['fileCarnet']
                        extensionDocumento = fileCarnet._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileCarnet.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileCarnet._name = generar_nombre("ceduladiscapacidad", fileCarnet._name)
                    if 'fileAutorizado' in eFiles:
                        fileAutorizado = eFiles['fileAutorizado']
                        extensionDocumento = fileCarnet._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileAutorizado.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileAutorizado._name = generar_nombre("archivoautorizado", fileAutorizado._name)

                    if fileCedula:
                        eFamiliar.cedulaidentidad = fileCedula
                    if fileCarnet:
                        eFamiliar.ceduladiscapacidad = fileCarnet
                    if fileAutorizado:
                        eFamiliar.archivoautorizado = fileAutorizado

                    eFamiliar.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deletefamiliar':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eFamiliar = PersonaDatosFamiliares.objects.get(id=id)
                        eFamiliar.status = False
                        eFamiliar.save()

                    else:
                        raise NameError(u"Error al elimanar")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedatosetnia':
                try:
                    ePerfil = ePersona.mi_perfil()

                    ePerfil.raza_id = eRequest['eRaza'];
                    ePerfil.nacionalidadindigena_id = eRequest.get('eNacionalidadIn','')

                    fileArchivoRaza = None

                    if 'fileDocG' in eFiles:
                        fileArchivoRaza = eFiles['fileDocG']
                        extensionDocumento = fileArchivoRaza._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivoRaza.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivoRaza._name = generar_nombre("archivosraza", fileArchivoRaza._name)

                    if fileArchivoRaza:
                        ePerfil.archivoraza = fileArchivoRaza

                    ePerfil.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Actualizados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savediscapacidad':

                try:

                    ePerfil = ePersona.mi_perfil()

                    ePerfil.tienediscapacidad = eRequest.get("eDiscapacidad") == 'on'


                    if ePerfil.tienediscapacidad:
                        ePerfil.tipodiscapacidad_id = eRequest['eTipoDiscapacidad']
                        ePerfil.carnetdiscapacidad = eRequest['eNumDiscapacidad']
                        ePerfil.porcientodiscapacidad = eRequest['ePorcentaje']
                        ePerfil.institucionvalida_id = eRequest['eInstitucion']
                        ePerfil.tienediscapacidadmultiple =eRequest.get('eCheckDiscMultiple') == 'on'
                        ePerfil.grado = eRequest['eGrado']
                        ePerfil.save()


                        ePerfil.tipodiscapacidadmultiple.clear()
                        ePerfil.subtipodiscapacidad.clear()

                        if ePerfil.tienediscapacidadmultiple:
                            if eRequest['eDiscMultiple']:
                                tipos = json.loads(eRequest['eDiscMultiple'])
                                for tipo in tipos:
                                    tipo['id'] = int(encrypt(tipo['id']))
                                    id = tipo['id']
                                    dis = Discapacidad.objects.get(id=id)
                                    ePerfil.tipodiscapacidadmultiple.add(dis)

                        if eRequest['eSubTipo']:
                            subtipos = json.loads(eRequest['eSubTipo'])
                            for subtipo in subtipos:

                                subtipo['id'] = int(encrypt(subtipo['id']))
                                id = tipo['id']
                                dis = Discapacidad.objects.get(id=id)
                                ePerfil.subtipodiscapacidad.add(dis)


                        fileCarnet = None
                        fileAutorizado = None
                        if 'fileCarnet' in eFiles:
                            fileCarnet = eFiles['fileCarnet']
                            extensionDocumento = fileCarnet._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if fileCarnet.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            fileCarnet._name = generar_nombre("archivosdiscapacidad", fileCarnet._name)
                        if 'fileAutorizado' in eFiles:
                            fileAutorizado = eFiles['fileAutorizado']
                            extensionDocumento = fileAutorizado._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if fileAutorizado.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            fileAutorizado._name = generar_nombre("archivosdiscapacidadvaloracion", fileAutorizado._name)

                        if fileCarnet:
                            ePerfil.archivo = fileCarnet
                        if fileAutorizado:
                            ePerfil.archivovaloracion = fileAutorizado
                    else:
                        ePerfil.tienediscapacidad = False
                    ePerfil.save()
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedatoslaborales':
                try:

                    situacionlaboral = PersonaSituacionLaboral.objects.filter(persona=ePersona)
                    if situacionlaboral:
                        eSituacionlaboral = situacionlaboral.first()
                        eSituacionlaboral.disponetrabajo = eRequest.get('eTieneEmpleo') == 'on'
                        if eSituacionlaboral.disponetrabajo:
                            eSituacionlaboral.tipoinstitucionlaboral = int(eRequest['eInstitucionLaboral'])
                            eSituacionlaboral.lugartrabajo = eRequest.get('eLugarTrabajo', '')
                        eSituacionlaboral.buscaempleo = eRequest.get('eBuscaEmpleo') == 'on'
                        eSituacionlaboral.tienenegocio = eRequest.get('eTieneNegocio') == 'on'
                        if eSituacionlaboral.tienenegocio:
                            eSituacionlaboral.negocio = eRequest.get('eNegocioDes', '')

                        eSituacionlaboral.save()
                        log(u'Actualizó datos laborales: %s' % ePersona, request, "edit")
                    else:
                        eSituacionlaboral = PersonaSituacionLaboral(
                            persona=ePersona,
                            disponetrabajo=eRequest.get('eTieneEmpleo') == 'on'
                        )
                        if eSituacionlaboral.disponetrabajo:
                            eSituacionlaboral.tipoinstitucionlaboral = int(eRequest['eInstitucionLaboral'])
                            eSituacionlaboral.lugartrabajo = eRequest.get('eLugarTrabajo', '')
                        eSituacionlaboral.buscaempleo = eRequest.get('eBuscaEmpleo') == 'on'
                        eSituacionlaboral.tienenegocio = eRequest.get('eTieneNegocio') == 'on'
                        if eSituacionlaboral.tienenegocio:
                            eSituacionlaboral.negocio = eRequest.get('eNegocioDes', '')
                        eSituacionlaboral.save()
                        #log(u'Actualizó datos laborales: %s' % ePersona, request, "add")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savearchivo':
                try:

                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eArchivo = Archivo.objects.get(id=id)

                        eArchivo.tipo_id = int(eRequest['tipoArchivo'])
                        eArchivo.fecha = datetime.now().date()
                        eArchivo.inscripcion = eInscripcion

                    else:

                        eArchivo = Archivo(
                                tipo_id=int(eRequest['tipoArchivo']),
                                fecha = datetime.now().date(),
                                inscripcion=eInscripcion
                        )

                    fileArchivo = None

                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("documento", fileArchivo._name)

                    if fileArchivo:
                        eArchivo.archivo = fileArchivo

                    eArchivo.save()

                    log(u'Añadió nuevo archivo: %s' % ePersona, request, "add")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Actualizados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deletearchivo':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eArchivo = Archivo.objects.get(id=id)
                        eArchivo.status = False
                        eArchivo.save()

                    else:
                        raise NameError(u"Error al eliminar")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Eliminados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savecuentabanco':
                try:

                    if 'id' in eRequest:
                        id=int(encrypt(eRequest['id']))
                        eCuentaBanco=CuentaBancariaPersona.objects.get(id=id)
                        eCuentaBanco.banco_id = int(eRequest['eBanco'])
                        eCuentaBanco.tipocuentabanco_id = int(eRequest['eTipoCuenta'])
                        eCuentaBanco.numero = eRequest['eNumCuenta']


                    else:

                        eCuentaBanco=CuentaBancariaPersona(
                            persona=ePersona,
                            banco_id=int(eRequest['eBanco']),
                            tipocuentabanco_id=int(eRequest['eTipoCuenta']),
                            numero=eRequest['eNumCuenta']
                        )


                    fileArchivo = None

                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("cuentabancariaarchivo", fileArchivo._name)

                    if fileArchivo:
                        eCuentaBanco.archivo = fileArchivo

                    eCuentaBanco.save()

                    log(u'Añadió cuenta Bancaria: %s' % ePersona, request, "add")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'activopagobeca':
                try:

                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        eCuentaBanco = CuentaBancariaPersona.objects.get(id=id)
                        eCuentaBanco.activapago = True
                        eCuentaBanco.save()
                        log(u'Activó cuenta Bancaria para pago de beca: %s' % ePersona, request, "edit")

                    else:
                        raise NameError(u"Error al activar")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deletecuentabanco':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))

                        eCuentaBanco = CuentaBancariaPersona.objects.get(id=id)
                        eCuentaBanco.status = False
                        eCuentaBanco.save()
                        log(u'Eliminó cuenta Bancaria: %s' % ePersona, request, "del")
                    else:
                        raise NameError(u"Error al eliminar")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Eliminados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedatosmedicos':
                try:
                    eDatoExentsion = ePersona.datos_extension()
                    eDatoExentsion.carnetiess = eRequest['eCarmetIess']
                    eDatoExentsion.save()

                    ePersona.sangre_id = int(eRequest['eTipoSangre'])
                    ePersona.save()

                    eExamFisico = eDatoExentsion.personaexamenfisico()
                    eExamFisico.peso = eRequest['ePeso']
                    eExamFisico.tall = eRequest['eTalla']

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("dptiposangre", fileArchivo._name)
                    if fileArchivo:
                        eDocumento = None
                        if  ePersona.documentos_personales():
                            eDocumento = ePersona.documentos_personales()
                        else:
                            eDocumento = PersonaDocumentoPersonal(persona=ePersona)
                        eDocumento.tiposangre = fileArchivo
                        eDocumento.save()


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'saveenfermedad':
                try:

                    if 'id' in eRequest:
                        id=int(encrypt(eRequest['id']))
                        ePersonaEnfermedad=PersonaEnfermedad.objects.get(id=id)
                        ePersonaEnfermedad.enfermedad_id = int(eRequest['eEnfermedad'])

                    else:
                        ePersonaEnfermedad=PersonaEnfermedad(
                            persona=ePersona,
                            enfermedad_id=int(eRequest['eEnfermedad'])
                        )

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("archivomedico", fileArchivo._name)
                    if fileArchivo:
                        ePersonaEnfermedad.archivomedico = fileArchivo
                    ePersonaEnfermedad.save()

                    log(u'Añadió Enfermedad: %s' % ePersona, request, "add")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deleteenfermedad':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))

                        ePersonaEnfermedad = PersonaEnfermedad.objects.get(id=id)
                        ePersonaEnfermedad.status = False
                        ePersonaEnfermedad.save()
                        log(u'Eliminó enfermedad: %s' % ePersona, request, "del")
                    else:
                        raise NameError(u"Error al eliminar")

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Eliminados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savevacuna':
                try:

                    if 'id_dosis' in eRequest:
                        id_dosis = int(eRequest['id_dosis'])
                        eVacuna = VacunaCovid.objects.get(id=id_dosis)
                        eVacunaDosis = VacunaCovidDosis.objects.filter(status= True, cabvacuna=eVacuna)

                        if 'recibiodosiscompleta' in eRequest:
                            eVacuna.recibiodosiscompleta = eRequest['recibiodosiscompleta']
                            eVacuna.save()
                        VacunaCovidDosis.objects.filter(cabvacuna=eVacuna).delete()
                        if 'cantidaddosis' in eRequest:
                            numdosis = int(eRequest['cantidaddosis'])
                            if numdosis > 0:
                                cf = 1
                                cn = 1
                                date_format = "%Y-%m-%d"
                                eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                for res in eRequest:
                                    comp_numd = 'num_dosis' + str(cn)
                                    if res == comp_numd:
                                        eVacunaDosis.numdosis = int(eRequest[res])
                                        comp_f = ('fecha' + str(cn))
                                        if comp_f in eRequest:
                                            eVacunaDosis.fechadosis = datetime.strptime(eRequest[comp_f], date_format)
                                            eVacunaDosis.save()
                                            eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                        cn += 1
                    else:


                        eVacuna= VacunaCovid(persona=ePersona)
                        if 'recibiciovacuna' in eRequest:
                            eVacuna.recibiovacuna = eRequest.get('recibiciovacuna') == 'on'
                        if 'tipoVacuna' in eRequest:
                            eVacuna.tipovacuna_id = int(eRequest['tipoVacuna'])
                        if 'dosiscompleta' in eRequest:
                            eVacuna.recibiodosiscompleta = eRequest.get('dosiscompleta') == 'on'
                        if 'deseavacuna' in eRequest:
                            eVacuna.deseavacunarse = eRequest.get('deseavacuna') == 'on'
                        eVacuna.save()

                        if 'cantidaddosis' in eRequest:
                            numdosis = int(eRequest['cantidaddosis'])
                            if numdosis > 0:
                                cf = 1
                                cn = 1
                                date_format = "%Y-%m-%d"
                                eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                for res in eRequest:
                                    comp_numd = 'num_dosis' + str(cn)
                                    if res == comp_numd:
                                        eVacunaDosis.numdosis = int(eRequest[res])
                                        comp_f = ('fecha' + str(cn))
                                        if comp_f in eRequest:
                                            eVacunaDosis.fechadosis = datetime.strptime(eRequest[comp_f], date_format)
                                            eVacunaDosis.save()
                                            eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                        cn += 1


                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("certificado", fileArchivo._name)
                    if fileArchivo:
                        eVacuna.certificado = fileArchivo
                        eVacuna.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedosis':
                try:
                    if 'id' in eRequest:
                        id_dosis = int(encrypt(eRequest['id']))
                        eVacuna = VacunaCovid.objects.get(id=id_dosis)
                        eVacunaDosis = VacunaCovidDosis.objects.filter(status= True, cabvacuna=eVacuna)

                        if 'recibiodosiscompleta' in eRequest:
                            eVacuna.recibiodosiscompleta = eRequest['recibiodosiscompleta']
                            eVacuna.save()
                        VacunaCovidDosis.objects.filter(cabvacuna=eVacuna).delete()
                        if 'cantidaddosis' in eRequest:
                            numdosis = int(eRequest['cantidaddosis'])
                            if numdosis > 0:
                                cf = 1
                                cn = 1
                                date_format = "%Y-%m-%d"
                                eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                for res in eRequest:
                                    comp_numd = 'num_dosis' + str(cn)
                                    if res == comp_numd:
                                        eVacunaDosis.numdosis = int(eRequest[res])
                                        comp_f = ('fecha' + str(cn))
                                        if comp_f in eRequest:
                                            eVacunaDosis.fechadosis = datetime.strptime(eRequest[comp_f], date_format)
                                            eVacunaDosis.save()
                                            eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                        cn += 1

                        fileArchivo = None
                        if 'fileArchivo' in eFiles:
                            fileArchivo = eFiles['fileArchivo']
                            extensionDocumento = fileArchivo._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if fileArchivo.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            fileArchivo._name = generar_nombre("certificado", fileArchivo._name)
                        if fileArchivo:
                            eVacuna.certificado = fileArchivo
                            eVacuna.save()

                    else:
                        raise NameError('Error al guardar los datos')
                    


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)



            if action == 'deletevacuna':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eVacuna = VacunaCovid.objects.get(id=id)
                        eVacuna.status = False
                        eVacuna.save()
                        log(u'Eliminó Vacuna: %s' % ePersona, request, "del")
                    else:
                        raise NameError(u"Error al eliminar")


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Eliminados')

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)

            if action == 'editdosis':
                try:

                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eVacuna = VacunaCovid.objects.get

                    eVacuna= VacunaCovid(persona=ePersona)
                    eVacuna.recibiovacuna = eRequest.get('recibiciovacuna') == 'on'
                    if 'tipoVacuna' in eRequest:
                        eVacuna.tipovacuna_id = int(eRequest['tipoVacuna'])
                    if 'dosiscompleta' in eRequest:
                        eVacuna.recibiodosiscompleta = eRequest.get('dosiscompleta') == 'on'
                    if 'deseavacuna' in eRequest:
                        eVacuna.deseavacunarse = eRequest.get('deseavacuna') == 'on'
                    eVacuna.save()

                    if 'cantidaddosis' in eRequest:
                        numdosis = int(eRequest['cantidaddosis'])
                        if numdosis > 0:
                            cf = 1
                            cn = 1
                            date_format = "%Y-%m-%d"
                            eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                            for res in eRequest:
                                comp_numd = 'num_dosis' + str(cn)
                                if res == comp_numd:
                                    eVacunaDosis.numdosis = int(eRequest[res])
                                    comp_f = ('fecha' + str(cn))
                                    if comp_f in eRequest:
                                        eVacunaDosis.fechadosis = datetime.strptime(eRequest[comp_f], date_format)
                                        eVacunaDosis.save()
                                        eVacunaDosis = VacunaCovidDosis(cabvacuna=eVacuna)
                                    cn += 1

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("certificado", fileArchivo._name)
                    if fileArchivo:
                        eVacuna.certificado = fileArchivo
                        eVacuna.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savecapacitacion':
                try:
                    date_format = "%Y-%m-%d"
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eCapacitacion = Capacitacion.objects.get(id=id)
                        eCapacitacion.institucion = eRequest['institucion']
                        eCapacitacion.nombre = eRequest['nomEvento']
                        eCapacitacion.descripcion=eRequest['descrEvento']
                        eCapacitacion.tipo=int(eRequest['tipocap'])
                        eCapacitacion.tipocurso_id=int(eRequest['tipocursocap'])
                        eCapacitacion.tipocertificacion_id=int(eRequest['tipoCertificacion'])
                        eCapacitacion.tipocapacitacion_id=int(eRequest['tipoCapacitacion'])
                        eCapacitacion.tipoparticipacion_id=int(eRequest['tipoParticipacion'])
                        if 'aniocap' in eRequest:
                            eCapacitacion.anio=int(eRequest['aniocap'])
                        eCapacitacion.contextocapacitacion_id=int(eRequest['contextoCap'])
                        eCapacitacion.detallecontextocapacitacion_id=int(eRequest['detalleContexCap'])
                        eCapacitacion.auspiciante=eRequest['auspiciante']
                        eCapacitacion.areaconocimiento_id=int(eRequest['areaconocimiento'])
                        eCapacitacion.subareaconocimiento_id=int(eRequest['subareacononcimiento'])
                        eCapacitacion.subareaespecificaconocimiento_id=int(eRequest['areaespecifica'])
                        eCapacitacion.expositor=eRequest['expositor']
                        eCapacitacion.modalidad=int(eRequest['modalidadcap'])
                        eCapacitacion.otramodalidad= eRequest.get('otramodalidad', '')
                        eCapacitacion.fechainicio= datetime.strptime(eRequest['fechainicio_cap'], date_format)
                        eCapacitacion.fechafin= datetime.strptime(eRequest['fechafin_cap'], date_format)
                        eCapacitacion.horas = float(eRequest['horas_cap'])
                        eCapacitacion.pais_id=int(eRequest['paiscap'])

                    else:
                        eCapacitacion = Capacitacion(
                            persona=ePersona,
                            institucion=eRequest['institucion'],
                            nombre=eRequest['nomEvento'],
                            descripcion=eRequest['descrEvento'],
                            tipo=int(eRequest['tipocap']),
                            tipocurso_id=int(eRequest['tipocursocap']),
                            tipocertificacion_id=int(eRequest['tipoCertificacion']),
                            tipocapacitacion_id=int(eRequest['tipoCapacitacion']),
                            tipoparticipacion_id=int(eRequest['tipoParticipacion']),
                            anio=int(eRequest['aniocap']),
                            contextocapacitacion_id=int(eRequest['contextoCap']),
                            detallecontextocapacitacion_id=int(eRequest['detalleContexCap']),
                            auspiciante=eRequest['auspiciante'],
                            areaconocimiento_id=int(eRequest['areaconocimiento']),
                            subareaconocimiento_id=int(eRequest['subareacononcimiento']),
                            subareaespecificaconocimiento_id=int(eRequest['areaespecifica']),
                            expositor=eRequest['expositor'],
                            modalidad=int(eRequest['modalidadcap']),
                            otramodalidad=eRequest.get('otramodalidad', ''),
                            fechainicio=datetime.strptime(eRequest['fechainicio_cap'], date_format),
                            fechafin=datetime.strptime(eRequest['fechafin_cap'], date_format),
                            horas=float(eRequest['horas_cap']),
                            pais_id=int(eRequest['paiscap']),

                        )


                    if 'provinciacap' in eRequest:
                        eCapacitacion.provincia_id = int(eRequest['provinciacap'])
                    else:
                        eCapacitacion.provincia = None
                    if 'cantoncap' in eRequest:
                        eCapacitacion.canton_id = int(eRequest['cantoncap'])
                    else:
                        eCapacitacion.canton = None
                    if 'parroquiacap' in eRequest:
                        eCapacitacion.parroquia_id = int(eRequest['parroquiacap'])
                    else:
                        eCapacitacion.parroquia = None

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("archivo", fileArchivo._name)
                    if fileArchivo:
                        eCapacitacion.archivo = fileArchivo

                    eCapacitacion.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)


            if action == 'deletecapacitacion':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eCapacitacion = Capacitacion.objects.get(id=id)
                        eCapacitacion.status=False
                        eCapacitacion.save()

                    else:
                        raise NameError('Error al eliminar')


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

            if action == 'savecertiidioma':
                try:
                    date_format = "%Y-%m-%d"
                    insitucioncerti = None
                    if 'institucioncerti' in eRequest:
                        insitucioncerti = int(eRequest['institucioncerti'])

                    if 'id' in eRequest:
                        id =  int(encrypt(eRequest['id']))
                        eCertiIdioma = CertificadoIdioma.objects.get(id=id)
                        eCertiIdioma.idioma_id= int(eRequest['idioma'])
                        eCertiIdioma.institucioncerti_id= insitucioncerti
                        eCertiIdioma.validainst=eRequest.get("validainst") == 'on'
                        eCertiIdioma.otrainstitucion= eRequest.get('otraInstitucion', '')
                        eCertiIdioma.nivelsuficencia_id=int(eRequest['nivelsuficencia'])
                        eCertiIdioma.fechacerti= datetime.strptime(eRequest['fechacertificacion'], date_format)
                    else:
                        eCertiIdioma = CertificadoIdioma(
                            idioma_id= int(eRequest['idioma']),
                            institucioncerti_id= insitucioncerti,
                            validainst=eRequest.get("validainst") == 'on',
                            otrainstitucion= eRequest.get('otraInstitucion', ''),
                            nivelsuficencia_id=int(eRequest['nivelsuficencia']),
                            persona=ePersona,
                            fechacerti= datetime.strptime(eRequest['fechacertificacion'], date_format)

                        )
                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("certificados", fileArchivo._name)
                    if fileArchivo:
                        eCertiIdioma.archivo = fileArchivo

                    eCertiIdioma.save()


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK, message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)


            if action == 'deleteCertiIdioma':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eCertiIdioma = CertificadoIdioma.objects.get(id= id)
                        eCertiIdioma.status = True
                        eCertiIdioma.save()
                    else:
                        raise NameError('Error al eliminar')


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savecertiinternacional':
                try:
                    date_format = "%Y-%m-%d"
                    fechahasta = None
                    if 'fechahasta' in eRequest:
                        fechahasta = datetime.strptime(eRequest['fechahasta'], date_format)

                    if 'id' in eRequest:
                        eCertificadoPersona = CertificacionPersona.objects.get(id=int(encrypt(eRequest['id'])))
                        eCertificadoPersona.nombres = eRequest['nombreinstitucion']
                        eCertificadoPersona.autoridad_emisora = eRequest['autoridademisora']
                        eCertificadoPersona.numerolicencia = eRequest['numlicencia']
                        eCertificadoPersona.enlace = eRequest['enlace']
                        eCertificadoPersona.vigente = eRequest.get('vigente') == 'on'
                        eCertificadoPersona.fechadesde = datetime.strptime(eRequest['fechadesde'], date_format)
                        eCertificadoPersona.fechahasta = fechahasta
                    else:
                        eCertificadoPersona = CertificacionPersona(
                            persona=ePersona,
                            nombres= eRequest['nombreinstitucion'],
                            autoridad_emisora = eRequest['autoridademisora'],
                            numerolicencia=eRequest['numlicencia'],
                            enlace=eRequest['enlace'],
                            vigente=eRequest.get('vigente') == 'on',
                            fechadesde=datetime.strptime(eRequest['fechadesde'], date_format),
                            fechahasta=fechahasta
                        )
                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("certificados", fileArchivo._name)
                    if fileArchivo:
                        eCertificadoPersona.archivo = fileArchivo

                    eCertificadoPersona.save()


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deleteCertiinternacional':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eCertiInternacional = CertificacionPersona.objects.get(id=id)
                        eCertiInternacional.status=False
                        eCertiInternacional.save()
                    else:
                        raise NameError('Error al eliminar')


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'saveexperiencia':
                try:
                    fechafin = None
                    motivosalida = None
                    if not eRequest.get('expvigente') == 'on':
                        fechafin = datetime.strptime(eRequest['fechafinexp'],date_format)
                        motivosalida = int(eRequest['motivosalida'])

                    if 'id' in eRequest:
                        eExperiencia = ExperienciaLaboral.objects.get(id=int(encrypt(eRequest['id'])))
                        eExperiencia.tipoinstitucion = eRequest['tipoinstiexp']
                        eExperiencia.institucion = eRequest['institucionexp']
                        eExperiencia.cargo = eRequest['cargoexp']
                        eExperiencia.departamento = eRequest['departamenteoexp']
                        eExperiencia.pais_id = eRequest['paisexp']
                        eExperiencia.provincia_id = eRequest['provinciaexp']
                        eExperiencia.canton_id = eRequest['cantonexp']
                        eExperiencia.parroquia_id = eRequest['parroquiaexp']
                        eExperiencia.fechainicio = datetime.strptime(eRequest['fechainicioexp'], date_format)
                        eExperiencia.fechafin = fechafin
                        eExperiencia.motivosalida_id = motivosalida
                        eExperiencia.regimenlaboral_id = int(eRequest['regimenlaboral'])
                        eExperiencia.horassemanales = eRequest['horassemanalexp']
                        eExperiencia.observaciones = eRequest['observaciones_exp']
                        eExperiencia.actividadlaboral_id = int(eRequest['actividadlaboral'])
                        eExperiencia.dedicacionlaboral_id = int(eRequest['dedicacionlaboral'])

                    else:
                        eExperiencia = ExperienciaLaboral(
                            persona=ePersona,
                            tipoinstitucion=eRequest['tipoinstiexp'],
                            institucion=eRequest['institucionexp'],
                            cargo=eRequest['cargoexp'],
                            departamento=eRequest['departamenteoexp'],
                            pais_id=int(eRequest['paisexp']),
                            provincia_id=int(eRequest['provinciaexp']),
                            canton_id=int(eRequest['cantonexp']),
                            parroquia_id=int(eRequest['parroquiaexp']),
                            fechainicio= datetime.strptime(eRequest['fechainicioexp'],date_format),
                            fechafin=fechafin,
                            motivosalida_id=motivosalida,
                            regimenlaboral_id=int(eRequest['regimenlaboral']),
                            horassemanales=eRequest['horassemanalexp'],
                            observaciones=eRequest['observaciones_exp'],
                            actividadlaboral_id=int(eRequest['actividadlaboral']),
                            dedicacionlaboral_id=int(eRequest['dedicacionlaboral'])
                        )

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("archivo", fileArchivo._name)
                    if fileArchivo:
                        eExperiencia.archivo = fileArchivo

                    eExperiencia.save()


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                       message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)

            if action == 'deleteexperiencia':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eExperiencia = ExperienciaLaboral.objects.get(id=id)
                        eExperiencia.status = False
                        eExperiencia.save()
                    else:
                        raise NameError('Error al eliminar')
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'saveotromerito':
                try:
                    if 'id' in eRequest:
                        eOtromerito = OtroMerito.objects.filter(id=int(encrypt(eRequest['id'])))[0]
                        eOtromerito.nombre=eRequest['nombremerito']
                        eOtromerito.institucion=eRequest['institucionmerito']
                        eOtromerito.fecha=datetime.strptime(eRequest['fechamerito'], date_format)
                    else:
                        eOtromerito = OtroMerito(
                            persona=ePersona,
                            nombre=eRequest['nombremerito'],
                            fecha=datetime.strptime(eRequest['fechamerito'], date_format),
                            institucion=eRequest['institucionmerito']
                        )

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("OtroMerito", fileArchivo._name)
                    if fileArchivo:
                        eOtromerito.archivo = fileArchivo

                    eOtromerito.save()


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deletemerito':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eMerito = OtroMerito.objects.get(id=id)
                        eMerito.status = False
                        eMerito.save()
                    else:
                        raise NameError('Error al eliminar')
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savereferencia':
                try:
                    if 'id' in eRequest:
                        eReferencia = ReferenciaPersona.objects.filter(id=int(encrypt(eRequest['id'])))[0]
                        eReferencia.nombres = eRequest['nombresref']
                        eReferencia.apellidos = eRequest['apellidosref']
                        eReferencia.email = eRequest['emailref']
                        eReferencia.telefono = eRequest['telefonoref']
                        eReferencia.institucion = eRequest['institucionref']
                        eReferencia.cargo = eRequest['cargoref']
                        eReferencia.relacion_id = int(eRequest['relacion_ref'])
                    else:
                        eReferencia = ReferenciaPersona(
                            persona=ePersona,
                            nombres=eRequest['nombresref'],
                            apellidos=eRequest['apellidosref'],
                            email=eRequest['emailref'],
                            telefono=eRequest['telefonoref'],
                            institucion=eRequest['institucionref'],
                            cargo=eRequest['cargoref'],
                            relacion_id=int(eRequest['relacion_ref'])
                        )
                    eReferencia.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deletereferencia':
                try:
                    if 'id' in eRequest:
                        eReferencia = ReferenciaPersona.objects.get(id=int(encrypt(eRequest['id'])))
                        eReferencia.status = False
                        eReferencia.save()
                    else:
                        raise NameError('Error al eliminar')
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                       message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)

            if action == 'savebeca':
                try:
                    if 'id' in eRequest:
                        eBeca = BecaPersona.objects.filter(id = int(encrypt(eRequest['id'])))[0]
                        eBeca.tipoinstitucion = eRequest['tipoinstitucion']
                        eBeca.institucion_id = int(eRequest['institucionbeca'])
                        eBeca.fechainicio = datetime.strptime(eRequest['fecharige'], date_format)


                    else:
                        eBeca = BecaPersona(
                            persona=ePersona,
                            tipoinstitucion= eRequest['tipoinstitucion'],
                            institucion_id=int(eRequest['institucionbeca']),
                            fechainicio=datetime.strptime(eRequest['fecharige'], date_format)
                        )
                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("beca", fileArchivo._name)
                    if fileArchivo:
                        eBeca.archivo = fileArchivo

                    eBeca.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'deletebeca':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eBeca = BecaPersona.objects.get(id=id)
                        eBeca.status=False
                        eBeca.save()
                    else:
                        raise NameError('Error al eliminar')
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savemigrante':
                try:
                    if not MigrantePersona.objects.filter(status=True, persona=ePersona).exists():

                        eMigrante = MigrantePersona(
                            persona=ePersona,
                            paisresidencia_id=int(eRequest['paismigrante']),
                            anioresidencia=int(eRequest['anioresiex']),
                            mesresidencia=int(eRequest['mesresiex']),
                            fecharetorno=datetime.strptime(eRequest['fecharetorno'], date_format),
                        )
                    else:
                        eMigrante = MigrantePersona.objects.filter(persona=ePersona)[0]
                        eMigrante.paisresidencia_id = int(eRequest['paismigrante'])
                        eMigrante.anioresidencia = int(eRequest['anioresiex'])
                        eMigrante.mesresidencia = int(eRequest['mesresiex'])
                        eMigrante.fecharetorno = datetime.strptime(eRequest['fecharetorno'], date_format)

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("migrante", fileArchivo._name)
                    if fileArchivo:
                        eMigrante.archivo = fileArchivo

                    eMigrante.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                       message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)


            if action == 'saveartista':
                try:

                    eArtista =None

                    if 'id' in eRequest:
                        eArtista = ArtistaPersona.objects.filter(id = int(encrypt(eRequest['id'])))[0]
                        eArtista.grupopertenece=eRequest['grupoartista']
                        eArtista.fechainicioensayo=datetime.strptime(eRequest['fechainicioensayo'], date_format)
                        eArtista.fechafinensayo=datetime.strptime(eRequest['fechafinensayo'], date_format)
                        eArtista.vigente= eRequest.get('vigente',1)

                    else:
                        eArtista = ArtistaPersona(
                            persona= ePersona,
                            grupopertenece=eRequest['grupoartista'],
                            fechainicioensayo=datetime.strptime(eRequest['fechainicioensayo'], date_format),
                            fechafinensayo=datetime.strptime(eRequest['fechafinensayo'], date_format),
                            vigente=1
                        )
                    eArtista.save()

                    if 'camposartisticos' in eRequest:
                        campos = json.loads(eRequest['camposartisticos'])
                        eArtista.campoartistico.clear()
                        for campo in campos:
                            campo['id'] = int(encrypt(campo['id']))
                            id = campo['id']
                            cam = CampoArtistico.objects.get(id=id)
                            eArtista.campoartistico.add(cam)

                    if 'vigente' in eRequest:
                        eArtista.vigente=int(eRequest['vigente'])

                    fileArchivo = None
                    if 'fileArchivo' in eFiles:
                        fileArchivo = eFiles['fileArchivo']
                        extensionDocumento = fileArchivo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivo._name = generar_nombre("artista", fileArchivo._name)
                    if fileArchivo:
                        eArtista.archivo = fileArchivo


                    eArtista.save()

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                       message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)

            if action == 'deleteartista':
                try:
                    if 'id' in eRequest:
                        id = int(encrypt(eRequest['id']))
                        eArtista = ArtistaPersona.objects.get(id=id)
                        eArtista.status=False
                        eArtista.save()
                    else:
                        raise NameError('Error al eliminar')
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'savedeportista':
                try:
                    eDeportista = None
                    if 'id' in eRequest and eRequest['id'] != 'null':
                        eDeportista = DeportistaPersona.objects.filter(id = int(encrypt(eRequest['id'])))[0]
                        eDeportista.representapais = int(eRequest['representapais'])
                        eDeportista.evento = eRequest['evento']
                        eDeportista.paisevento_id = int(eRequest['pais'])
                        eDeportista.equiporepresenta = eRequest['equiporepresenta']
                        eDeportista.fechainicioevento = datetime.strptime(eRequest['fechainicioevento'], date_format)
                        eDeportista.fechafinevento = datetime.strptime(eRequest['fechafinevento'], date_format)
                        eDeportista.fechainicioentrena = datetime.strptime(eRequest['fechainicioentrena'], date_format)
                        eDeportista.fechafinentrena = datetime.strptime(eRequest['fechafinentrena'], date_format)
                        eDeportista.vigente = int(eRequest.get('vigente',1))
                    else:
                        eDeportista = DeportistaPersona(
                            persona= ePersona,
                            representapais = int(eRequest['representapais']),
                            evento=eRequest['evento'],
                            paisevento_id = int(eRequest['pais']),
                            equiporepresenta=eRequest['equiporepresenta'],
                            fechainicioevento=datetime.strptime(eRequest['fechainicioevento'], date_format),
                            fechafinevento=datetime.strptime(eRequest['fechafinevento'], date_format),
                            fechainicioentrena=datetime.strptime(eRequest['fechainicioentrena'], date_format),
                            fechafinentrena=datetime.strptime(eRequest['fechafinentrena'], date_format),
                            vigente = 1

                        )

                    eDeportista.save()

                    if 'disciplinas' in eRequest:
                        campos = json.loads(eRequest['disciplinas'])
                        eDeportista.disciplina.clear()
                        for campo in campos:
                            campo['id'] = int(encrypt(campo['id']))
                            id = campo['id']
                            cam = DisciplinaDeportiva.objects.get(id=id)
                            eDeportista.disciplina.add(cam)

                    fileArchivoEvento = None
                    fileArchivoEntrena = None
                    if 'fileArchivoEvento' in eFiles:
                        fileArchivoEvento = eFiles['fileArchivoEvento']
                        extensionDocumento = fileArchivoEvento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivoEvento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivoEvento._name = generar_nombre("deportista", fileArchivoEvento._name)
                    if 'fileArchivoEntrena' in eFiles:
                        fileArchivoEntrena = eFiles['fileArchivoEntrena']
                        extensionDocumento = fileArchivoEntrena._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivoEntrena.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivoEntrena._name = generar_nombre("deportista", fileArchivoEntrena._name)


                    if fileArchivoEvento:
                        eDeportista.archivoevento = fileArchivoEvento

                    if fileArchivoEntrena:
                        eDeportista.archivoentrena = fileArchivoEntrena

                    eDeportista.save()
                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action == 'filtrasubcampo':
                try:
                    if 'id' in eRequest:
                        campos_id = json.loads((eRequest['id']))
                        subcampo_id = []
                        for camp_id in campos_id:
                            id = int(encrypt(camp_id))
                            subcampo_id.append(id)

                        eSubCampos = None

                        if subcampo_id:
                            eSubCampos = SubAreaConocimientoTitulacion.objects.filter(status=True, areaconocimiento_id__in=subcampo_id)
                            eSubcampos_serializer = SubAreaConocimientoTitulacionSerializer(eSubCampos, many=True)


                    aData = {
                        'subcampos': eSubcampos_serializer.data if eSubCampos else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)


            if action == 'filtracampdet':
                try:
                    if 'id' in eRequest:
                        campos_id = json.loads((eRequest['id']))
                        subcampo_id = []
                        for camp_id in campos_id:
                            id = int(encrypt(camp_id))
                            subcampo_id.append(id)

                        eSubCampos = None

                        if subcampo_id:
                            eSubCampos = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True, areaconocimiento_id__in=subcampo_id)
                            eSubcampos_serializer = SubAreaEspecificaConocimientoTitulacionSerializer(eSubCampos, many=True)


                    aData = {
                        'subcampos': eSubcampos_serializer.data if eSubCampos.exists() else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            if action== 'savetitulacion':
                try:
                    if 'id' in eRequest:
                        eTitulacion = Titulacion.objects.filter(id=int(encrypt(eRequest['id'])))[0]
                        eTitulacion.titulo_id=int(eRequest['titulo'])
                        eTitulacion.areatitulo_id=int(eRequest['tituloarea'])
                        eTitulacion.fechainicio=datetime.strptime(eRequest['fechaInicioEstudios'], date_format)
                        eTitulacion.pais_id=int(eRequest['pais'])
                        eTitulacion.cursando = eRequest.get('cursando') == 'on'

                    else:
                        eTitulacion = Titulacion(
                            persona=ePersona,
                            titulo_id=int(eRequest['titulo']),
                            areatitulo_id=int(eRequest['tituloarea']),
                            fechainicio=datetime.strptime(eRequest['fechaInicioEstudios'], date_format),
                            pais_id=int(eRequest['pais']),
                            cursando=eRequest.get('cursando') == 'on'
                        )

                    if 'provincia' in eRequest:
                        eTitulacion.provincia_id = int(eRequest['provincia'])
                    else:
                        eTitulacion.provincia =  None
                    if 'canton' in eRequest:
                        eTitulacion.canton_id = int(eRequest['canton'])
                    else:
                        eTitulacion.canton = None
                    if 'parroquia' in eRequest:
                        eTitulacion.parroquia_id = int(eRequest['parroquia'])
                    else:
                        eTitulacion.parroquia = None
                    if 'institucionsup' in eRequest:
                        eTitulacion.institucion_id = int(eRequest['institucionsup'])
                    if 'colegio' in eRequest:
                        eTitulacion.colegio_id=int(eRequest['colegio'])

                    if 'fechaobtencion' in eRequest:
                        eTitulacion.fechaobtencion = datetime.strptime(eRequest['fechaobtencion'], date_format)
                    if 'fechaegreso' in eRequest:
                        eTitulacion.fechaegresado = datetime.strptime(eRequest['fechaegreso'], date_format)

                    fileArchivoSenescyt = None
                    fileArchivoTitulo = None
                    if 'fileArchivoSenescyt' in eFiles:
                        fileArchivoSenescyt = eFiles['fileArchivoSenescyt']
                        extensionDocumento = fileArchivoSenescyt._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivoSenescyt.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivoSenescyt._name = generar_nombre("senescyt", fileArchivoSenescyt._name)
                    if 'fileArchivoTitulo' in eFiles:
                        fileArchivoTitulo = eFiles['fileArchivoTitulo']
                        extensionDocumento = fileArchivoTitulo._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if fileArchivoTitulo.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() in ['pdf']:
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        fileArchivoTitulo._name = generar_nombre("titulo", fileArchivoTitulo._name)

                    if fileArchivoSenescyt:
                        eTitulacion.registroarchivo = fileArchivoSenescyt

                    if fileArchivoTitulo:
                        eTitulacion.archivo = fileArchivoTitulo


                    eTitulacion.save()

                    if not CamposTitulosPostulacion.objects.filter(titulo_id=int(eRequest['titulo'])).exists():
                        eCampoDetalle = CamposTitulosPostulacion(titulo_id=int(eRequest['titulo']))
                    else:
                        eCampoDetalle = CamposTitulosPostulacion.objects.filter(titulo_id=int(eRequest['titulo']))[0]
                    eCampoDetalle.save()
                    if 'selectcampoamplio' in eRequest:
                        campos = json.loads(eRequest['selectcampoamplio'])
                        eCampoDetalle.campoamplio.clear()
                        for campo in campos:
                            campo['id'] = int(encrypt(campo['id']))
                            id = campo['id']
                            cam = AreaConocimientoTitulacion.objects.get(id=id)
                            eCampoDetalle.campoamplio.add(cam)

                    if 'campoespecif' in eRequest:
                        campos = json.loads(eRequest['campoespecif'])
                        eCampoDetalle.campoespecifico.clear()
                        for campo in campos:
                            campo['id'] = int(encrypt(campo['id']))
                            id = campo['id']
                            cam = SubAreaConocimientoTitulacion.objects.get(id=id)
                            eCampoDetalle.campoespecifico.add(cam)

                    if 'camposdet' in eRequest:
                        campos = json.loads(eRequest['camposdet'])
                        eCampoDetalle.campodetallado.clear()
                        for campo in campos:
                            id = int(encrypt(campo['id']))
                            cam = SubAreaEspecificaConocimientoTitulacion.objects.get(id=id)
                            eCampoDetalle.campodetallado.add(cam)

                    eCampoDetalle.save()


                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Actualizados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)


            if action == 'deletetitulacion':
                try:
                    if 'id' in eRequest:
                        eTitulacion = Titulacion.objects.get(id=int(encrypt(eRequest['id'])))
                        if eTitulacion.verificado:
                            raise NameError('No puede eliminar el titulo')
                        eTitulacion.status= False
                        eTitulacion.save()
                    else:
                        raise NameError('Error al eliminar titulo')

                    return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK,
                                           message=f'Datos Eliminados')
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            #ACCION NO ENCONTRADA - ELSE
            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)

    def get(self, request):

        try:

            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')

            action = ''
            eRequest = request.query_params
            if 'action' in request.query_params:
                action = request.query_params['action']
            ePersona = ePerfilUsuario.persona
            if action == 'datoscontacto':
                try:

                    datos_extension = ePersona.datos_extension()
                    datos_extension_serializer = PersonaExtensionSerializer(datos_extension, many=False)

                    parentescos = ParentescoPersona.objects.filter(status=True)
                    parentesco_serializer = ParentescoPersonaSerializer(parentescos, many=True)


                    aData = {
                        'eContacto': datos_extension_serializer.data,
                        'eParentesco': parentesco_serializer.data
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'addfamiliar':
                try:

                    eFamiliares = ePersona.familiares()
                    familiares_serializer = PersonaDatosFamiliaresSerializer(eFamiliares, many=True)

                    parentescos = ParentescoPersona.objects.filter(status=True)
                    parentesco_serializer = ParentescoPersonaSerializer(parentescos, many=True)

                    discapacidad = Discapacidad.objects.filter(status=True)
                    discapacidad_serializer = TipoDiscapacidadSerializer(discapacidad, many=True)

                    institucion = InstitucionBeca.objects.filter(tiporegistro=2, status=True)
                    institucion_serializer = InstitucionBecaSerializer(institucion, many=True)

                    niveltitulacion = NivelTitulacion.objects.filter(status=True)
                    niveltitulacion_serializer = NivelTitulacionSerializer(niveltitulacion, many= True)

                    forma_trabajo = FormaTrabajo.objects.filter(status=True)
                    forma_trabajo_serializer = FormaTrabajoSerializer(forma_trabajo, many=True)

                    aData = {
                        'eParentesco': parentesco_serializer.data,
                        'eDiscapacidad': discapacidad_serializer.data,
                        'eInstitucion': institucion_serializer.data,
                        'eFormaTrabajo': forma_trabajo_serializer.data,
                        'eNivelTitulacion': niveltitulacion_serializer.data,

                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'editfamiliar':
                try:

                    eFamiliar = None
                    eFamiliar_serializer = None
                    if 'id' in eRequest:
                        id = int(eRequest['id'])

                        eFamiliar = PersonaDatosFamiliares.objects.filter(id=id)[0]
                        eFamiliar_serializer = PersonaDatosFamiliaresSerializer(eFamiliar)


                    eFamiliares = ePersona.familiares()
                    familiares_serializer = PersonaDatosFamiliaresSerializer(eFamiliares, many=True)
                    parentescos = ParentescoPersona.objects.filter(status=True)
                    parentesco_serializer = ParentescoPersonaSerializer(parentescos, many=True)
                    discapacidad = Discapacidad.objects.filter(status=True)
                    discapacidad_serializer = TipoDiscapacidadSerializer(discapacidad, many=True)
                    institucion = InstitucionBeca.objects.filter(tiporegistro=2, status=True)
                    institucion_serializer = InstitucionBecaSerializer(institucion, many=True)
                    niveltitulacion = NivelTitulacion.objects.all()
                    niveltitulacion_serializer = NivelTitulacionSerializer(niveltitulacion, many= True)
                    forma_trabajo = FormaTrabajo.objects.all()
                    forma_trabajo_serializer = FormaTrabajoSerializer(forma_trabajo, many=True)

                    aData = {
                        'eParentesco': parentesco_serializer.data,
                        'eDiscapacidad': discapacidad_serializer.data,
                        'eInstitucion': institucion_serializer.data,
                        'eFormaTrabajo': forma_trabajo_serializer.data,
                        'eNivelTitulacion': niveltitulacion_serializer.data,
                        'eFamiliar': eFamiliar_serializer.data if eFamiliar else [],

                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'formdireccion':
                try:
                    persona_serializer = HojaVidaPersonaSerializer(ePersona)
                    ePais = Pais.objects.filter(status=True)
                    ePais_serializer = PaisSerializer(ePais, many=True)
                    aData = {
                        'ePersona': persona_serializer.data if ePersona else [],
                        'paises': ePais_serializer.data if ePais.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosetnia':
                try:
                    ePerfil = ePersona.mi_perfil()
                    perfil_serializer = PerfilInscripcionSerializer(ePerfil)
                    razas = Raza.objects.all()
                    raza_serializer = RazaSerializer(razas, many= True)
                    nacionalidades = NacionalidadIndigena.objects.all()
                    nacionalidades_serializer = NacionalidadIndigenaSerializer(nacionalidades, many=True)

                    aData = {
                        'ePerfil': perfil_serializer.data,
                        'razas': raza_serializer.data,
                        'nacionalidades': nacionalidades_serializer.data,
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'datosdiscapacidad':
                try:
                    ePerfil = ePersona.mi_perfil()
                    perfil_serializer = PerfilInscripcionSerializer(ePerfil)
                    tipos_discapacidad = Discapacidad.objects.filter(status=True)
                    tipos_discapacidad_serializer = TipoDiscapacidadSerializer(tipos_discapacidad, many=True)

                    subtipo_discapacidad = SubTipoDiscapacidad.objects.filter(status=True)
                    subtipo_discapacidad_serializer = SubTipoDiscapacidadSerializer(subtipo_discapacidad, many=True)

                    institucion = InstitucionBeca.objects.filter(tiporegistro=2, status=True)
                    institucion_serializer = InstitucionBecaSerializer(institucion, many=True)

                    discapacidad_multiple = ePerfil.tipodiscapacidadmultiple.all()
                    discapacidad_multiple_serializer = TipoDiscapacidadSerializer(discapacidad_multiple, many=True)

                    aData = {
                        'ePerfil': perfil_serializer.data,
                        'tiposdiscapacidad': tipos_discapacidad_serializer.data,
                        'subtipodiscapacidad': subtipo_discapacidad_serializer.data,
                        'instituciones': institucion_serializer.data,
                        'discapacidadmulitple': discapacidad_multiple_serializer.data if discapacidad_multiple.exists() else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'subtipodiscapacidad':
                try:
                    ePerfil = ePersona.mi_perfil()
                    subtipo_discapacidad = None
                    discapacidad = None
                    subtipo_discapacidad_serializer = {}
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        discapacidad = Discapacidad.objects.get(id=id)
                        subtipo_discapacidad = SubTipoDiscapacidad.objects.filter(discapacidad=discapacidad, status=True)
                        subtipo_discapacidad_serializer = SubTipoDiscapacidadSerializer(subtipo_discapacidad, many=True)

                        discapacidades = Discapacidad.objects.all().exclude(id=id)
                        discapacidad_serializer = TipoDiscapacidadSerializer(discapacidades, many=True)

                    aData = {
                        'eSubTipos': subtipo_discapacidad_serializer.data if subtipo_discapacidad.exists() else [],
                        'eDiscapacidades': discapacidad_serializer.data if discapacidades.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datoslaborales':
                try:

                    situacionlaboral = PersonaSituacionLaboral.objects.filter(persona=ePersona, status=True)
                    if situacionlaboral:
                        situacionlaboral = situacionlaboral.first()
                    situacionlaboral_serializer = PersonaSituacionLaboralSerializer(situacionlaboral)


                    aData = {
                        'eSitLaboral': situacionlaboral_serializer.data if situacionlaboral else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'addarchivos':
                try:
                    eTipoArchivo = TipoArchivo.objects.filter(id__in=(5,15,16,18))
                    tipoarchivo_serializer = TipoArchivoSerializer(eTipoArchivo, many=True)
                    aData = {
                        'tiposArchivos': tipoarchivo_serializer.data if eTipoArchivo.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'datosarchivos':
                try:
                    if 'id' in eRequest:
                        id = int(eRequest['id'])

                    eArchivo = Archivo.objects.get(id=id)
                    archivo_serializer = ArchivoSerializer(eArchivo)
                    eTipoArchivo = TipoArchivo.objects.filter(id__in=(5,15,16,18))
                    tipoarchivo_serializer = TipoArchivoSerializer(eTipoArchivo, many=True)
                    aData = {
                        'eArchivo': archivo_serializer.data if eArchivo else [],
                        'tiposArchivos': tipoarchivo_serializer.data if eTipoArchivo.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'addcuentabanco':
                try:

                    bancos = Banco.objects.filter(status=True)
                    bancos_serializer = BancoSerializer(bancos, many=True)
                    tiposCuentas = TipoCuentaBanco.objects.filter(status=True)
                    tiposCuentas_serializer = TipoCuentaBancoSerializer(tiposCuentas, many=True)

                    aData = {
                        'eBancos': bancos_serializer.data if bancos.exists() else [],
                        'eTipoCuentas': tiposCuentas_serializer.data if tiposCuentas.exists() else []

                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'datoscuentabanco':
                try:

                    if 'id' in eRequest:
                        id = int(eRequest['id'])

                    eCuentaBanco = CuentaBancariaPersona.objects.get(id=id)
                    eCuentaBanco_serializer = CuentaBancariaPersonaSerializer(eCuentaBanco)
                    bancos = Banco.objects.filter(status=True)
                    bancos_serializer = BancoSerializer(bancos, many=True)
                    tiposCuentas = TipoCuentaBanco.objects.filter(status=True)
                    tiposCuentas_serializer = TipoCuentaBancoSerializer(tiposCuentas, many=True)

                    aData = {
                        'eCuentaBanco': eCuentaBanco_serializer.data if eCuentaBanco else [],
                        'eBancos': bancos_serializer.data if bancos.exists() else [],
                        'eTipoCuentas': tiposCuentas_serializer.data if tiposCuentas.exists() else []

                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'datosmedicos':
                try:
                    person_serializer = PersonaSangreSerializer(ePersona)

                    document = ePersona.documentos_personales()
                    urlsangre = None
                    if document and document.tiposangre:
                        urlsangre = document.tiposangre.url


                    tiposSangre = TipoSangre.objects.filter(status=True)
                    tiposangre_serializer = TipoSangreSerializer(tiposSangre, many=True)

                    datos_extension = ePersona.datos_extension()
                    datos_extension_serializer = PersonaExtensionSerializer(datos_extension, many=False)

                    examenFisico = datos_extension.personaexamenfisico()
                    examenFisico_serializer = PersonaExamenFisicoSerializer(examenFisico)

                    aData = {
                        'ePersona': person_serializer.data,
                        'eDatosExtension': datos_extension_serializer.data if datos_extension else [],
                        'eXamenFisico': examenFisico_serializer.data if examenFisico else [],
                        'eTiposSangre': tiposangre_serializer.data if tiposSangre.exists() else [],
                        'urlsangre': urlsangre


                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'addenfermedad':
                try:

                    eEnfermedades = Enfermedad.objects.filter(status=True)
                    enfermedades_serializer = EnfermedadSerializer(eEnfermedades, many=True)

                    ePersonaEnfermedad = None
                    id = None

                    if eRequest['id'] != 'null':
                        id = int(eRequest['id'])
                        if id > 0:
                            ePersonaEnfermedad = PersonaEnfermedad.objects.get(id=id)


                    personaenfermedad_serializer = PersonaEnfermedadSerializer(ePersonaEnfermedad)

                    aData = {
                        'eEnfermedades': enfermedades_serializer.data if eEnfermedades.exists() else [],
                        'ePersonaEnfermdad' : personaenfermedad_serializer.data if ePersonaEnfermedad else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'addvacuna':
                try:

                    eVacunas = TipoVacunaCovid.objects.filter(status=True)
                    vacunas_serializer = TipoVacunaCovidSerializer(eVacunas, many=True)


                    aData = {
                        'eTiposVacunas': vacunas_serializer.data if eVacunas.exists() else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'adddosis':
                try:
                    eVacuna = None
                    if 'id'in eRequest:
                        eVacuna = VacunaCovid.objects.filter(id=int(encrypt(eRequest['id'])))[0]
                        vacunas_serializer = VacunaCovidSerializer(eVacuna)
                        eDosis = VacunaCovidDosis.objects.filter(cabvacuna=eVacuna)
                        dosis_serializer = VacunaCovidDosisSerializer(eDosis, many=True)

                    aData = {
                        'eVacuna': vacunas_serializer.data if eVacuna else [],
                        'eDosis' : dosis_serializer.data if eDosis else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)



            elif action == 'detalletitulo':
                try:

                    if 'id' in eRequest:
                        id = int(eRequest['id'])

                        eTitulacion = Titulacion.objects.get(id=id)
                        titulacion_serializer = TitulacionSerializer(eTitulacion)

                    else:
                        raise NameError(u'Error al buscar detalle')


                    aData = {
                        'datosTitulo': titulacion_serializer.data if eTitulacion else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


            elif action == 'formtitulacion':
                try:
                    eTitulacion = None
                    eTitulo = None
                    if 'id' in eRequest and  eRequest['id'] != 'null':
                        id = int(eRequest['id'])
                        eTitulacion = Titulacion.objects.get(id=id)
                        titulacion_serializer = TitulacionSerializer(eTitulacion)
                        eTitulo = eTitulacion.titulo
                        eTitulo_serializer = TituloSerializer(eTitulo)

                    eTitulos = Titulo.objects.filter(status=True)
                    titulos_serializer = TituloSerializer(eTitulos, many=True)
                    eAreasTitulo = AreaTitulo.objects.filter(status=True)
                    areastitulo_serializer = AreaTituloSerializer(eAreasTitulo,many=True)
                    eInstituciones = InstitucionEducacionSuperior.objects.filter(status=True)
                    instituciones_serializer = InstitucionEducacionSuperiorSerializer(eInstituciones, many=True)
                    eColegios = Colegio.objects.filter(status=True)
                    colegios_serializer = ColegioSerializer(eColegios, many=True)
                    ePaises = Pais.objects.filter(status=True)
                    paises_serializer = PaisSerializer(ePaises, many=True)
                    eProvincias = Provincia.objects.filter(status=True)
                    provincias_serializer = ProvinciaSerializer(eProvincias, many=True)
                    eCantones = Canton.objects.filter(status=True)
                    cantones_serializer = CantonSerializer(eCantones,many=True)
                    eParroquias = Parroquia.objects.filter(status=True)
                    parroquias_serializer = ParroquiaSerializer(eParroquias, many=True)

                    eCampoAmplio = AreaConocimientoTitulacion.objects.filter(status=True, tipo=1)
                    campoAmplio_serializer= AreaConocimientoTitulacionSerializer(eCampoAmplio, many=True)




                    aData = {
                        'titulos' : titulos_serializer.data if eTitulos.exists() else [],
                        'areasTitulo': areastitulo_serializer.data if eAreasTitulo.exists() else [],
                        'instituciones': instituciones_serializer.data if eInstituciones.exists() else [],
                        'colegios': colegios_serializer.data if eColegios.exists() else [],
                        'paises': paises_serializer.data,
                        'provincias': provincias_serializer.data,
                        'cantones': cantones_serializer.data,
                        'parroquias': parroquias_serializer.data,
                        'camposAmplio': campoAmplio_serializer.data if eCampoAmplio.exists() else [],
                        'dTitulacion': titulacion_serializer.data if eTitulacion else [],
                        'dTitulo': eTitulo_serializer.data if eTitulo else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)





            elif action == 'detallecap':
                try:

                    if 'id' in eRequest:
                        id = int(eRequest['id'])

                        eCapacitacion = Capacitacion.objects.get(id=id)
                        capacitacion_serializer = CapacitacionSerializer(eCapacitacion)

                    else:
                        raise NameError(u'Error al buscar detalle')




                    aData = {
                        'datosCapacitacion': capacitacion_serializer.data if eCapacitacion else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'formcapacitacion':
                try:
                    id = None
                    dCapacitacion = None
                    if eRequest['id'] != 'null' and not None:
                        id = eRequest['id']
                        dCapacitacion = Capacitacion.objects.get(id=id)
                        dCapacitacion_serializer = CapacitacionSerializer(dCapacitacion)

                    eTipoCurso = TipoCurso.objects.filter(status=True)
                    tipocurso_serializer = TipoCursoSerializer(eTipoCurso, many=True)
                    eTipoCertificacion = TipoCertificacion.objects.filter(status=True)
                    eTipoCertificacion_serializer = TipoCertificacionSerializer(eTipoCertificacion, many=True)
                    eTipoParticipacion = TipoParticipacion.objects.filter(status=True)
                    eTipoParticipacion_serializer = TipoParticipacionSerializer(eTipoParticipacion, many=True)
                    eTipoCapacitacion = TipoCapacitacion.objects.filter(status=True)
                    eTipoCapacitacion_serializer = TipoCapacitacionSerializer(eTipoCapacitacion, many=True)
                    eContextoCapacitacion = ContextoCapacitacion.objects.filter(status=True)
                    eContextoCapacitacion_serializer = ContextoCapacitacionSerializer(eContextoCapacitacion, many=True)
                    eDetalleContextoCapacitacion = DetalleContextoCapacitacion.objects.filter(status=True)
                    eDetalleContextoCapacitacion_serializer = DetalleContextoCapacitacionSerializer(eDetalleContextoCapacitacion, many=True)
                    eAreaConocimientoTitulacion = AreaConocimientoTitulacion.objects.filter(status=True)
                    eAreaConocimientoTitulacion_serializer = AreaConocimientoTitulacionSerializer(eAreaConocimientoTitulacion, many=True)
                    eSubAreaConocimientoTitulacion = SubAreaConocimientoTitulacion.objects.filter(status=True)
                    eSubAreaConocimientoTitulacion_serializer = SubAreaConocimientoTitulacionSerializer(eSubAreaConocimientoTitulacion, many=True)
                    eSubAreaEspecificaConocimientoTitulacion = SubAreaEspecificaConocimientoTitulacion.objects.filter(status=True)
                    eSubAreaEspecificaConocimientoTitulacion_serializer = SubAreaEspecificaConocimientoTitulacionSerializer(eSubAreaEspecificaConocimientoTitulacion, many=True)
                    ePais = Pais.objects.filter(status=True)
                    ePais_serializer = PaisSerializer(ePais, many=True)

                    aData = {
                        'tiposCursos': tipocurso_serializer.data if eTipoCurso.exists() else [],
                        'tipoCertificacion': eTipoCertificacion_serializer.data if eTipoCertificacion.exists() else [],
                        'tipoParticipacion': eTipoParticipacion_serializer.data if eTipoParticipacion.exists() else [],
                        'tipoCapacitacion': eTipoCapacitacion_serializer.data if eTipoCapacitacion.exists() else [],
                        'contextoCapacitacion': eContextoCapacitacion_serializer.data if eContextoCapacitacion.exists() else [],
                        'detalleCapacitacion': eDetalleContextoCapacitacion_serializer.data if eDetalleContextoCapacitacion.exists() else [],
                        'areaConocimiento': eAreaConocimientoTitulacion_serializer.data if eAreaConocimientoTitulacion.exists() else [],
                        'subAreaConocimiento': eSubAreaConocimientoTitulacion_serializer.data if eSubAreaConocimientoTitulacion.exists() else [],
                        'subAreaEspecifica': eSubAreaEspecificaConocimientoTitulacion_serializer.data if eSubAreaEspecificaConocimientoTitulacion.exists() else [],
                        'paises': ePais_serializer.data if ePais.exists() else [],
                        'dCapacitacion': dCapacitacion_serializer.data if dCapacitacion else None,

                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'datoscapacitacion':
                try:
                    id = None
                    dCapacitacion = None
                    if 'id' in eRequest:
                        id = eRequest['id']
                        dCapacitacion = Capacitacion.objects.get(id=id)
                        dCapacitacion_serializer = CapacitacionSerializer(dCapacitacion)


                    aData={
                        'dCapacitacion': dCapacitacion_serializer.data if dCapacitacion else [],
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'filtra_subareaconocimiento':
                try:
                    eSubAreaConocimiento = None
                    eSubAreaConocimiento_serializer = {}

                    if 'id' in eRequest:
                        id = eRequest['id']

                        eSubAreaConocimiento = SubAreaConocimientoTitulacion.objects.filter(areaconocimiento_id=id)
                        eSubAreaConocimiento_serializer = SubAreaConocimientoTitulacionSerializer(eSubAreaConocimiento, many=True)

                    aData = {
                        'subAreaConocimiento': eSubAreaConocimiento_serializer.data if eSubAreaConocimiento.exists() else []

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'filtra_subareaespecifica':
                try:
                    eSubAreaEspecifica = None
                    eSubAreaEspecifica_serializer = {}

                    if 'id' in eRequest:
                        id = eRequest['id']
                        eSubAreaEspecifica = SubAreaEspecificaConocimientoTitulacion.objects.filter(areaconocimiento_id=id)
                        eSubAreaEspecifica_serializer = SubAreaEspecificaConocimientoTitulacionSerializer(eSubAreaEspecifica, many=True)

                    aData = {
                        'subAreaEspecifica': eSubAreaEspecifica_serializer.data if eSubAreaEspecifica.exists() else []

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datoscertifidiomas':
                try:
                    if 'persona' in eRequest:
                        eCertificado = CertificadoIdioma.objects.filter(status=True, persona=ePersona)
                        eCertificado_serializer = CertificadoIdiomaSerializer(eCertificado, many=True)

                        eCertificacionPersona = CertificacionPersona.objects.filter(status=True, persona=ePersona)
                        eCertificacionPersona_serializer = CertificadoPersonaSerializer(eCertificacionPersona, many=True)


                    aData={
                        'certificadoIdioma': eCertificado_serializer.data if eCertificado.exists() else [],
                        'certificacionInternacional': eCertificacionPersona_serializer.data if eCertificacionPersona.exists() else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'formcertifidiomas':
                try:
                    eCertiIdioma = None
                    id = None
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        eCertiIdioma = CertificadoIdioma.objects.filter(id=id)[0]
                        eCertiIdioma_serializer = CertificadoIdiomaSerializer(eCertiIdioma)
                    eIdioma = Idioma.objects.filter(status=True)
                    eIdioma_serializer = IdiomaSerializer(eIdioma, many=True)
                    eInstitucioncerti = InstitucionCertificadora.objects.filter(status=True)
                    eInstitucioncerti_serializer = InstitucionCertificadoraSerializer(eInstitucioncerti, many=True)
                    eNivelSuficencia = NivelSuficencia.objects.filter(status=True)
                    eNivelSuficencia_serializer = NivelSuficenciaSerializer(eNivelSuficencia, many=True)
                    aData={
                        'eIdiomas': eIdioma_serializer.data if eIdioma.exists() else [],
                        'eInstituciones': eInstitucioncerti_serializer.data if eInstitucioncerti.exists() else [],
                        'eNivelesSuficencia': eNivelSuficencia_serializer.data if eNivelSuficencia.exists() else [],
                        'dCertiIdioma': eCertiIdioma_serializer.data if eCertiIdioma else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'detalleCertiIdioma':
                try:
                    if 'id' in eRequest:
                        eCertiIdioma = CertificadoIdioma.objects.get(id= int(eRequest['id']))
                        eCertiIdioma_serializer = CertificadoIdiomaSerializer(eCertiIdioma)
                        
                        aData = {
                            'eCertiIdioma': eCertiIdioma_serializer.data if eCertiIdioma else []
                        }
                    else:
                        raise NameError('Error al encontrar Certificado de Idioma')

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'formcertifinternacional':
                try:
                    eCertificadoPersona = None
                    id = None
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        eCertificadoPersona = CertificacionPersona.objects.get(id=id)
                        eCertificadoPersona_serializer = CertificadoPersonaSerializer(eCertificadoPersona)

                    aData = {
                        'dCertiinternacional': eCertificadoPersona_serializer.data if eCertificadoPersona else[]
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosexperiencialab':
                try:
                    if 'persona' in eRequest:
                        eExperiencia = ExperienciaLaboral.objects.filter(status=True, persona=ePersona)
                        eExperiencia_serializer = ExperienciaLaboralSerializer(eExperiencia, many=True)


                    aData = {
                        'dExperiencia': eExperiencia_serializer.data if eExperiencia else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'formdatosexp':
                try:
                    eExperiencia = None
                    if 'id' in eRequest:
                        eExperiencia = ExperienciaLaboral.objects.get(id=int(eRequest['id']))
                        eExperiencia_serializer = ExperienciaLaboralSerializer(eExperiencia)

                    ePais = Pais.objects.filter(status=True)
                    ePais_serializer = PaisSerializer(ePais, many=True)
                    eMotivoSalidas = MotivoSalida.objects.filter(status=True)
                    eMotivosalida_serializer = MotivoSalidaSerializer(eMotivoSalidas, many=True)
                    eRegimenLaborales = OtroRegimenLaboral.objects.filter(status=True)
                    eRegimenLaboral_Serializer = OtroRegimenLaboralSerializer(eRegimenLaborales,many=True)
                    eActividadLaboral = ActividadLaboral.objects.filter(status=True)
                    eActividadLaboral_serializer = ActividadLaboralSerializer(eActividadLaboral, many=True)
                    eDedicacionLaboral = DedicacionLaboral.objects.filter(status=True)
                    eDedicacionLaboral_serializer = DedicacionLaboralSerializer(eDedicacionLaboral, many=True)



                    aData = {
                        'dExperiencia': eExperiencia_serializer.data if eExperiencia else [],
                        'paises': ePais_serializer.data if ePais.exists() else [],
                        'motivossalidas': eMotivosalida_serializer.data if eMotivoSalidas else[],
                        'regimeneslaborales':eRegimenLaboral_Serializer.data if eRegimenLaborales else [],
                        'actividadlaborales': eActividadLaboral_serializer.data if eActividadLaboral else [],
                        'dedicacionlaborales': eDedicacionLaboral_serializer.data if eDedicacionLaboral else []

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosotromerito':
                try:
                    eOtroMerito = None
                    if 'persona' in eRequest:
                        eOtroMerito = OtroMerito.objects.filter(persona=ePersona)
                        eOtroMerito_Serializer = OtroMeritoSerializer(eOtroMerito,many=True)
                    else:
                        raise NameError('Error al encontrar otros meritos')

                    aData = {
                        'eOtrosMeritos': eOtroMerito_Serializer.data if eOtroMerito else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'formotromerito':
                try:
                    eOtroMerito = None
                    if 'id' in eRequest and eRequest['id'] != 'null':
                        eOtroMerito = OtroMerito.objects.get(id = int(eRequest['id']))
                        eOtroMerito_serializer = OtroMeritoSerializer(eOtroMerito)

                    # else:
                    #     raise   NameError('Error al encontrar Merito')

                    aData = {
                        'eOtroMerito': eOtroMerito_serializer.data if eOtroMerito else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosreferencia':
                try:
                    eReferencias = None
                    if 'persona' in eRequest:
                        eReferencias = ReferenciaPersona.objects.filter(status=True, persona=ePersona)
                        eReferencias_serializer = ReferenciaPersonaSerializer(eReferencias, many=True)

                    aData = {
                        'eReferencias': eReferencias_serializer.data if eReferencias.exists() else []
                    }


                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'formreferencia':
                try:
                    eReferencia = None
                    if 'id' in eRequest and eRequest['id'] != 'null':
                        eReferencia = ReferenciaPersona.objects.filter(id=int(encrypt(eRequest['id'])))[0]
                        eReferencia_serializer = ReferenciaPersonaSerializer(eReferencia)

                    eRelaciones = Relacion.objects.filter(status=True)
                    eRelaciones_serializer = RelacionSerializer(eRelaciones, many=True)

                    aData={
                        'eRefencias': eReferencia_serializer.data if eReferencia else [],
                        'eRelaciones': eRelaciones_serializer.data if eRelaciones.exists() else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                       status=status.HTTP_200_OK)

            elif action == 'datosbeca':
                try:
                    lista_becas = []
                    becasinternas = BecaAsignacion.objects.filter(solicitud__inscripcion__persona=ePersona, status=True)
                    for beca in becasinternas:
                        lista_becas.append(
                            ['INTERNA', 'PÚBLICA', 'UNIVERSIDAD ESTATAL DE MILAGRO', beca.solicitud.periodo,
                             beca.solicitud.becatipo, None, beca.fecha,
                             'NO' if beca.solicitud.periodo.finalizo() else 'SI', None, None, None, None])

                    becasexternas = BecaPersona.objects.filter(persona=ePersona, status=True)
                    for beca in becasexternas:
                        becaarchivo = None
                        becafechainicio = None
                        if beca.archivo:
                            becaarchivo = beca.archivo.url
                        if beca.fechainicio:
                            becafechainicio = beca.fechainicio
                        lista_becas.append(
                            ['EXTERNA', beca.get_tipoinstitucion_display(), beca.institucion.nombre, None, None,
                             becaarchivo,
                             becafechainicio, 'NO' if beca.fechafin else 'SI', beca.estadoarchivo,
                             beca.get_estadoarchivo_display(), beca.observacion, encrypt(beca.id)])

                    aData = {
                        'becas': lista_becas
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'formbeca':
                try:

                    eBeca = None
                    if 'id' in eRequest and eRequest['id'] != 'null':
                        eBeca  = BecaPersona.objects.filter(id= int(encrypt(eRequest['id'])))[0]
                        eBeca_serializer = BecaPersonaSerializer(eBeca)

                    eInstitucionBeca = InstitucionBeca.objects.filter(status=True)
                    eInstitucionBeca_serializer = InstitucionBecaSerializer(eInstitucionBeca,many=True)

                    aData={
                        'instituciobecas' : eInstitucionBeca_serializer.data if eInstitucionBeca.exists() else [],
                        'becas': eBeca_serializer.data if eBeca else[]
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosextranjero':
                try:

                    eMigrante = None
                    if MigrantePersona.objects.filter(persona=ePersona).exists():
                        eMigrante = MigrantePersona.objects.filter(persona=ePersona)[0]
                        eMigrante_serializer = MigrantePersonaSerializer(eMigrante)

                    aData = {
                        'direccionextranjero': eMigrante_serializer.data if eMigrante else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'formextranjero':
                try:
                    eMigrante = None
                    if MigrantePersona.objects.filter(persona=ePersona).exists():
                        eMigrante = MigrantePersona.objects.filter(persona=ePersona)[0]
                        eMigrante_serializer = MigrantePersonaSerializer(eMigrante)
                    ePais = Pais.objects.filter(status=True)
                    ePais_serializer = PaisSerializer(ePais, many=True)

                    aData={
                        'paises': ePais_serializer.data if ePais.exists() else [],
                        'eMigrante': eMigrante_serializer.data if eMigrante else []
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosartista':
                try:
                    eArtista = None
                    artista_vigente = False
                    if ArtistaPersona.objects.filter(status=True, persona= ePersona).exists():
                        eArtista = ArtistaPersona.objects.filter(status=True, persona= ePersona)
                        eArtista_serializer = ArtistaPersonaSerializer(eArtista, many=True)


                        for art in eArtista:
                            if art.vigente == 1:
                                artista_vigente = True
                                break

                    aData = {
                        'datosartista': eArtista_serializer.data if eArtista else [],
                        'artista_vigente': artista_vigente


                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)


            elif action == 'formartista':
                try:
                    eArtista = None
                    if 'id' in eRequest  and eRequest['id'] != 'null':
                        eArtista = ArtistaPersona.objects.filter(id= int(encrypt(eRequest['id'])))[0]
                        eArtista_serializer = ArtistaPersonaSerializer(eArtista)
                        campos = eArtista.campoartistico.all()
                        idcampo = []
                        for camp in campos:
                            idcampo.append(camp.id)


                    camposArtisticos = CampoArtistico.objects.filter(status= True)
                    camposArtisticos_serializer = CampoArtisticoSerializer(camposArtisticos, many=True)


                    aData = {
                        'datosartista': eArtista_serializer.data if eArtista else [],
                        'camposartisticos': camposArtisticos_serializer.data if camposArtisticos else [],
                        'idcampo' : idcampo if eArtista else [],

                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'datosdeportista':
                try:
                    eDeportista = None
                    reportista_vigente = False
                    if DeportistaPersona.objects.filter(status=True, persona= ePersona).exists():
                        eDeportista = DeportistaPersona.objects.filter(status=True, persona= ePersona)
                        eDeportista_serializer = DeportistaPersonaSerializer(eDeportista, many=True)

                        for dep in eDeportista:
                            if dep.vigente == 1:
                                reportista_vigente = True
                                break


                    aData = {
                        'datosdeportista': eDeportista_serializer.data if eDeportista else [],
                        'dep_vigente': reportista_vigente
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)
            elif action == 'formdeportista':
                try:
                    eDeportista = None
                    if 'id' in eRequest and eRequest['id'] != 'null':
                        eDeportista = DeportistaPersona.objects.filter(id= int(encrypt(eRequest['id'])))[0]
                        eDeportista_serializer =DeportistaPersonaSerializer(eDeportista)

                    eDisciplinaDeportivas = DisciplinaDeportiva.objects.filter(status=True)
                    eDisciplinaDeportiva_serializer = DisciplinaDeportivaSerializer(eDisciplinaDeportivas, many=True)
                    ePaises = Pais.objects.filter(status=True)
                    ePaises_serializer = PaisSerializer(ePaises, many=True)

                    aData = {
                        'datosdeportista': eDeportista_serializer.data if eDeportista else [],
                        'disciplinas' : eDisciplinaDeportiva_serializer.data if eDisciplinaDeportivas else [],
                        'paises' : ePaises_serializer.data if ePaises else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            else:

                persona_serializer = HojaVidaPersonaSerializer(ePersona)

                # --------- DATOS PERSONALES
                eDocumentosPersonales = ePersona.documentos_personales()
                documentopersonales_serializer =  PersonaDocumentoPersonalSerializer(eDocumentosPersonales)
                datos_extension = ePersona.datos_extension()
                datos_extension_serializer = PersonaExtensionSerializer(datos_extension,many=False)
                ePerfil = ePersona.mi_perfil()
                perfil_serializer = PerfilInscripcionSerializer(ePerfil)
                eEstadosCiviles = PersonaEstadoCivil.objects.all()
                estadocivil_serializer = PersonaEstadoCivilSerializer(eEstadosCiviles, many=True)
                eFamiliares = ePersona.familiares().filter(status=True)
                familiares_serializer = PersonaDatosFamiliaresSerializer(eFamiliares, many= True)
                ingresos = 0
                for fam in eFamiliares:
                    ingresos += fam.ingresomensual
                situacionlaboral_serializer = {}
                situacionlaboral = PersonaSituacionLaboral.objects.filter(status= True, persona= ePersona).first()
                if situacionlaboral:
                #    eSituacionlaboral = situacionlaboral.first()
                    situacionlaboral_serializer = PersonaSituacionLaboralSerializer(situacionlaboral)
                discapacidad_multiple = ePerfil.tipodiscapacidadmultiple.all()
                discapacidad_multiple_serializer = TipoDiscapacidadSerializer(discapacidad_multiple, many=True)
                eInscripcion = ePerfilUsuario.inscripcion
                eArchivos = Archivo.objects.filter(inscripcion=eInscripcion, status=True)
                archivos_serializer = ArchivoSerializer(eArchivos, many=True)
                #eCuentaBancaria = CuentaBancariaPersona.objects.filter(persona=ePersona, status=True)
                eCuentaBancaria = ePersona.cuentasbancarias()
                cuentabancaria_serializer = CuentaBancariaPersonaSerializer(eCuentaBancaria, many=True)
                examenFisico = datos_extension.personaexamenfisico()
                examenFisico_serializer = PersonaExamenFisicoSerializer(examenFisico)
                eEnfermedades = ePersona.mis_enfermedades()
                enfermedades_serializer = PersonaEnfermedadSerializer(eEnfermedades, many=True)
                eVacunasCovid = VacunaCovid.objects.filter(persona=ePersona, status=True)
                vacunascovid_serializer = VacunaCovidSerializer(eVacunasCovid, many=True)
                capacitaciones = Capacitacion.objects.filter(status= True, persona=ePersona)
                capacitaciones_serializer = CapacitacionSerializer(capacitaciones, many=True)

                data = {
                    'ePersona': persona_serializer.data,
                    'eDocumentoPersonales': documentopersonales_serializer.data,
                    'datosextension': datos_extension_serializer.data,
                    'ePerfil': perfil_serializer.data,
                    'eFamiliares': familiares_serializer.data,
                    'eEstadosCivil': estadocivil_serializer.data,
                    'ingresos': ingresos,
                    'eSitLaboral': situacionlaboral_serializer.data if situacionlaboral else [],
                    'discapacidadmulitple': discapacidad_multiple_serializer.data if discapacidad_multiple.exists() else [],
                    'eArchivos': archivos_serializer.data if eArchivos.exists() else [],
                    'eCuentas': cuentabancaria_serializer.data if eCuentaBancaria.exists() else [],
                    'eXamenFisico' : examenFisico_serializer.data if examenFisico else [],
                    'eEnfermedades': enfermedades_serializer.data if eEnfermedades else [],
                    'eVacunasCovid': vacunascovid_serializer.data if eVacunasCovid.exists() else [],
                    'eCapacitaciones': capacitaciones_serializer.data if capacitaciones.exists() else []
                }

                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)

        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}',
                                   status=status.HTTP_200_OK)