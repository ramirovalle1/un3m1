from datetime import datetime
from django.db import  transaction
from django.db.models import Q
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status

from sga.funciones import log, generar_nombre
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.actualizadatos import MatriculaSerializer, DatosPersonaSerializer,  \
      PaisSerializer, ProvinciaSerializer, CantonSerializer, ParroquiaSerializer, PersonaEstadoCivilFinanzaSerializer,\
      MatriRazaSerializer, MatriNacionalidadIndigenaSerializer, PerfilSerializer, \
      InstitucionEducacionSuperiorSerializer, TituloSerializer, TitulacionSerializer, InscripcionCohorteSerializer, InscripcionSerializer

from sga.models import PerfilUsuario, Persona, Periodo,  Matricula,   PersonaEstadoCivil,  \
    Pais, Provincia, Canton, Parroquia, PerfilInscripcion, Raza, NacionalidadIndigena, Titulacion, Titulo, InstitucionEducacionSuperior
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache

class ActualizaDatosAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    api_key_module = 'ALUMNO_ACTUALIZADATOS'

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 15
        periodoEnCache = ePerfilUsuario = matriculaEnCache = eMatricula = None
        hoy = datetime.now()
        payload = request.auth.payload
        if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
            ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
        else:
            ePerfilUsuario = PerfilUsuario.objects.get(
                pk=encrypt(payload['perfilprincipal']['id']))
            cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario,
                      TIEMPO_ENCACHE)
        eInscripcion = ePerfilUsuario.inscripcion
        ePersona = eInscripcion.persona
        ePeriodo = None
        if 'id' in payload['periodo']:
            periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
            if periodoEnCache:
                ePeriodo = periodoEnCache
            else:
                if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                    ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                    if not ePeriodo:
                        raise NameError(u"Periodo no encontrado")
                # ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                    cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
        if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
            ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
            if not ePeriodo:
                raise NameError(u"Periodo no encontrado")
        # if 'id' in payload['matricula'] and payload['matricula']['id']:
        #     matriculaEnCache = cache.get(f"matricula_id_{payload['matricula']['id']}")
        #     if matriculaEnCache:
        #         eMatricula = matriculaEnCache
        #     else:
        #         eMatricula = Matricula.objects.db_manager("sga_select").get(pk=encrypt(payload['matricula']['id']))
        #         cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)
            # eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
            # ePeriodo = eMatricula.nivel.periodo

        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'datospersonales':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')
                    persona = DatosPersonaSerializer(ePersona).data

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
                        idpais = ePersona.pais
                        idprovincia = ePersona.provincia
                        idcanton = ePersona.canton
                        idparroquia = ePersona.parroquia

                    pais = Pais.objects.filter(status=True)
                    pais_seria = PaisSerializer(pais, many=True)

                    if idprovincia or idpais:
                        provincia = Provincia.objects.filter(pais=idpais)
                        provincia_seria = ProvinciaSerializer(provincia, many=True)
                    if idcanton or idprovincia:
                        canton = Canton.objects.filter(provincia=idprovincia)
                        canton_seria = CantonSerializer(canton, many=True)
                    if idparroquia or idcanton:
                        parroquia = Parroquia.objects.filter(canton=idcanton)
                        parroquia_seria = ParroquiaSerializer(parroquia, many=True)

                    aData = {
                        'ePersona': persona,
                        'ePais': pais_seria.data if pais else [],
                        'eProvincia': provincia_seria.data if provincia else [],
                        'eCanton': canton_seria.data if canton else [],
                        'eParroquia': parroquia_seria.data if parroquia else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'datosetnia':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')
                    persona = DatosPersonaSerializer(ePersona).data
                    ePerfilInscripcion = PerfilInscripcion.objects.filter(persona=ePersona)
                    eRazas = Raza.objects.filter(status=True).exclude(pk=10)
                    eNacionalidadIndigenas = NacionalidadIndigena.objects.filter(status=True)

                    aData = {}
                    aData['ePersona'] = persona if persona else None
                    aData['ePerfilInscripcion'] = PerfilSerializer(ePerfilInscripcion[0]).data if ePerfilInscripcion.values("id").exists() else None
                    aData['eRazas'] = MatriRazaSerializer(eRazas, many=True).data if eRazas.values("id").exists() else []
                    aData['eNacionalidadIndigenas'] = MatriNacionalidadIndigenaSerializer(eNacionalidadIndigenas, many=True).data if eNacionalidadIndigenas.values("id").exists() else []

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'datostitulacion':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')
                    persona = DatosPersonaSerializer(ePersona).data

                    idtitulacion = eTitulacion = None
                    if 'idtitulacion' in eRequest:
                        idtitulacion = int(encrypt(eRequest['idtitulacion']))

                    if idtitulacion > 0:
                        eTitulacion = Titulacion.objects.get(pk=idtitulacion)

                    aData = {}
                    aData['ePersona'] = persona if persona else None
                    aData['eTitulacion'] = TitulacionSerializer(eTitulacion).data if eTitulacion else None
                    aData['eTitulo'] = TituloSerializer(eTitulacion.titulo).data if eTitulacion.titulo else None
                    aData['eInstitucion'] = InstitucionEducacionSuperiorSerializer(eTitulacion.institucion).data if eTitulacion.institucion else None

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'filtra_provincia':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')

                    provincias = None
                    pais = None
                    provincia_seria = {}
                    if 'id' in eRequest:
                        id = int(eRequest['id'])
                        pais = Pais.objects.get(pk=id)
                        provincias = Provincia.objects.filter(status=True, pais=pais)
                        provincia_seria = ProvinciaSerializer(provincias, many=True)

                    aData = {
                        'eProvincia': provincia_seria.data if provincias.exists() else [],
                        'eNacionalidad': pais.nacionalidad if pais and pais.nacionalidad else ''
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'filtra_canton':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')

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
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'filtra_parroquia':
                try:
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')

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

            if action == "actualizardatospersonales":
                with transaction.atomic():
                    try:
                        # if not 'id_matri' in eRequest:
                        #     raise NameError(u"No se encuentra el código de la matricula.")
                        # idmatricula = int(encrypt(eRequest['id_matri']))
                        if 'id_persona' in eRequest:
                            idpersona = int(encrypt(eRequest['id_persona']))
                        # matricula = Matricula.objects.get(pk=idmatricula)

                        if idpersona > 0:
                            ePersona = Persona.objects.get(pk=idpersona)
                            # validación de cédula
                            # cedula = eRequest['eCedula'].strip()
                            # resp = validarcedula(cedula)
                            # if resp != 'Ok':
                            #     raise NameError(u"%s." % (resp))
                            ePersona.nombres = eRequest['eNombres']
                            ePersona.apellido1 = eRequest['eApellido1']
                            ePersona.apellido2 = eRequest['eApellido2']
                            # ePersona.cedula = eRequest['eCedula']
                            ePersona.pasaporte = eRequest['ePasaporte']
                            ePersona.sexo_id = int(eRequest['sexo'])
                            personaextension = ePersona.datos_extension()
                            personaextension.estadocivil_id = int(eRequest['estadocivil'])
                            personaextension.save()
                            ePersona.nacimiento = datetime.strptime(eRequest['eFechaNacimiento'], "%Y-%m-%d").date()
                            ePersona.anioresidencia = eRequest['eAniosResidencia']
                            ePersona.email = eRequest['eCorreoPersonal']
                            ePersona.emailinst = eRequest['eCorreoInstitucional']
                            ePersona.lgtbi = eRequest.get("eLgtbi") == 'true'
                            ePersona.save(request)
                            log(u"Editó datos personales: %s" % ePersona, request, "edit")

                        return Helper_Response(isSuccess=True,  data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == "actualizardatosnacimiento":
                with transaction.atomic():
                    try:
                        # if not 'id_matri' in eRequest:
                        #     raise NameError(u"No se encuentra el código de la matricula.")
                        # idmatricula = int(encrypt(eRequest['id_matri']))
                        if 'id_persona' in eRequest:
                            idpersona = int(encrypt(eRequest['id_persona']))
                        # matricula = Matricula.objects.get(pk=idmatricula)

                        if idpersona > 0:
                            ePersona = Persona.objects.get(pk=idpersona)
                            ePersona.paisnacimiento_id = int(eRequest['pais'])
                            ePersona.provincianacimiento_id = int(eRequest['provincia'])
                            ePersona.cantonnacimiento_id = int(eRequest['canton'])
                            ePersona.parroquianacimiento_id = int(eRequest['parroquia'])
                            ePersona.nacionalidad = eRequest['eNacionalidad']

                            ePersona.save(request)
                            log(u"Editó datos nacimiento: %s" % ePersona, request, "edit")

                        return Helper_Response(isSuccess=True,  data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == "actualizardatosdomicilio":
                with transaction.atomic():
                    try:
                        # if not 'id_matri' in eRequest:
                        #     raise NameError(u"No se encuentra el código de la matricula.")
                        # idmatricula = int(encrypt(eRequest['id_matri']))
                        if 'id_persona' in eRequest:
                            idpersona = int(encrypt(eRequest['id_persona']))
                        # matricula = Matricula.objects.get(pk=idmatricula)

                        if idpersona > 0:
                            ePersona = Persona.objects.get(pk=idpersona)
                            ePersona.pais_id = int(eRequest['pais'])
                            ePersona.provincia_id = int(eRequest['provincia'])
                            ePersona.canton_id = int(eRequest['canton'])
                            ePersona.parroquia_id = int(eRequest['parroquia'])
                            ePersona.direccion = eRequest['eCallePrincipal']
                            ePersona.direccion2 = eRequest['eCalleSecundaria']
                            ePersona.num_direccion = eRequest['eNumeroResidencia']
                            ePersona.referencia = eRequest['eReferencia']
                            ePersona.telefono = eRequest['eCelular']
                            ePersona.telefono_conv = eRequest['eTelefonoDomicilio']

                            ePersona.save(request)
                            log(u"Editó datos domicilio: %s" % ePersona, request, "edit")

                        return Helper_Response(isSuccess=True,  data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == "actualizardatosetnia":
                with transaction.atomic():
                    try:
                        # if not 'id_matri' in eRequest:
                        #     raise NameError(u"No se encuentra el código de la matricula.")
                        # idmatricula = int(encrypt(eRequest['id_matri']))
                        if 'id_perfilinscripcion' in eRequest:
                            id = int(encrypt(eRequest['id_perfilinscripcion']))
                        # matricula = Matricula.objects.get(pk=idmatricula)

                        if id > 0:
                            ePersonaInsc = PerfilInscripcion.objects.get(pk=id)
                            ePersonaInsc.raza_id = int(eRequest['raza'])
                            if 'nacionalidadindigena' in eRequest and int(eRequest['nacionalidadindigena']) > 0:
                                ePersonaInsc.nacionalidadindigena_id = int(eRequest['nacionalidadindigena'])
                            else:
                                ePersonaInsc.nacionalidadindigena_id = None
                            ePersonaInsc.save(request)
                            log(u"Editó datos Etnia: %s" % ePersonaInsc, request, "edit")

                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == "actualizardatostitulacion":
                with transaction.atomic():
                    try:
                        # if not 'id_matri' in eRequest:
                        #     raise NameError(u"No se encuentra el código de la matricula.")
                        # idmatricula = int(encrypt(eRequest['id_matri']))
                        id = 0
                        if 'id_titulacion' in eRequest and eRequest['id_titulacion']:
                            id = int(encrypt(eRequest['id_titulacion']))
                        # matricula = Matricula.objects.get(pk=idmatricula)

                        nfileDocumentoTitulo = None
                        if 'fileTitulo' in eFiles:
                            nfileDocumentoTitulo = eFiles['fileTitulo']
                            extensionDocumento = nfileDocumentoTitulo._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if nfileDocumentoTitulo.size > 4500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 45 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            nfileDocumentoTitulo._name = generar_nombre("titulacion_", nfileDocumentoTitulo._name)

                        nfileDocumentoSenescyt = None
                        if 'fileSenescyt' in eFiles:
                            nfileDocumentoSenescyt = eFiles['fileSenescyt']
                            extensionDocumento = nfileDocumentoSenescyt._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if nfileDocumentoSenescyt.size > 4500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 45 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            nfileDocumentoSenescyt._name = generar_nombre("titulacion_", nfileDocumentoSenescyt._name)

                        if id > 0:
                            eTitulacion = Titulacion.objects.get(pk=id)
                            eTitulacion.titulo_id = int(eRequest['titulo'])
                            eTitulacion.institucion_id = int(encrypt(eRequest['institucion']))
                            eTitulacion.registro = eRequest['eNumRegistro']
                            if nfileDocumentoTitulo:
                                eTitulacion.archivo = nfileDocumentoTitulo
                            if nfileDocumentoSenescyt:
                                eTitulacion.registroarchivo = nfileDocumentoSenescyt
                            eTitulacion.save(request)
                            log(u"Editó datos Titulación: %s de %s" % (eTitulacion, eTitulacion.persona ), request, "edit")
                        else:
                            eTitulacion = Titulacion(persona=ePersona,
                                                     titulo_id=int(eRequest['titulo']),
                                                     institucion_id = int(encrypt(eRequest['institucion'])),
                                                     registro = eRequest['eNumRegistro'])
                            eTitulacion.save(request)
                            if nfileDocumentoTitulo:
                                eTitulacion.archivo = nfileDocumentoTitulo
                            if nfileDocumentoSenescyt:
                                eTitulacion.registroarchivo = nfileDocumentoSenescyt
                            eTitulacion.save(request)
                            log(u"Adicionó datos Titulación: %s de %s" % (eTitulacion, eTitulacion.persona ), request, "add")

                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'deletetitulacion':
                with transaction.atomic():
                    try:
                        if not ePeriodo:
                            raise NameError(u"Periodo no encontrado")
                        if not eInscripcion:
                            raise NameError(u"Inscripción no encontrada")
                        if not 'id' in eRequest:
                            raise NameError(u"No se encontro parametro")
                        id = int(encrypt(eRequest['id']))
                        # ePersona = eInscripcion.persona

                        # eConfiguracionCarnet = ePeriodoMatricula.configuracion_carnet
                        dato = Titulacion.objects.get(pk=id)
                        if not dato:
                            raise NameError(u"No existe titulación a eliminar")
                        dato.delete()
                        log(u'Eliminó titulación posgrado: %s' % dato, request, "del")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={},
                                               message=f'Ocurrió un error al eliminar: {ex.__str__()}',
                                               status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']

            if action == 'buscartitulos':
                try:
                    q = request.GET['filterText'].upper().strip()
                    querybase = Titulo.objects.filter(nivel_id__in=[3], status=True)
                    datos = querybase.filter((Q(nombre__icontains=q) | Q(abreviatura__icontains=q)), Q(status=True)).distinct()[:30]

                    titulos_serializer = TituloSerializer(datos, many=True)
                    aData = {
                        'items': titulos_serializer.data if datos.exists() else {}
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al buscar título: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'confirmacion_datos':
                try:
                    hoy = datetime.now()
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    if not 'id' in payload['matricula']:
                        raise NameError(u'No se encuentra matriculado.')
                    eMatricula = None
                    ePeriodoMatricula = None
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = eInscripcion.persona
                    # if 'id' in payload['matricula'] and payload['matricula']['id']:
                    #     eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                    #     ePeriodo = eMatricula.nivel.periodo
                    # else:
                    #     if 'id_matri' in request.GET and request.GET['id_matri']:
                    #         eMatricula = Matricula.objects.get(pk=int(encrypt(request.GET['id_matri'])))

                    datospersonales, datosdomicilio, datosetnia, datostitulo, camposfaltantes, datosactualizados = eInscripcion.tiene_informacion_matriz_completa()
                    if datospersonales or datosdomicilio or datosetnia or datostitulo:
                        return Helper_Response(isSuccess=False, data={}, message=f'Aún existen campos por actualizar. {camposfaltantes}.', status=status.HTTP_200_OK)
                    else:
                        if ePersona.datosactualizados != 1:
                            ePersona.datosactualizados = 1
                            ePersona.save(request)
                        return Helper_Response(isSuccess=False, redirect="/", module_access=False, token=True, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            else:
                try:
                    TIEMPO_ENCACHE = 60 * 15
                    periodoEnCache = ePerfilUsuario = matriculaEnCache = eMatricula = None
                    hoy = datetime.now()
                    payload = request.auth.payload
                    if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                        ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
                    else:
                        ePerfilUsuario = PerfilUsuario.objects.get(
                            pk=encrypt(payload['perfilprincipal']['id']))
                        cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario,
                                  TIEMPO_ENCACHE)
                    eInscripcion = ePerfilUsuario.inscripcion
                    ePersona = eInscripcion.persona
                    ePeriodo = None
                    if  ePersona.datosactualizados == 1:
                        raise NameError(u"Sus datos ya se encuentran actualizados")


                    if 'id' in payload['periodo']:
                        periodoEnCache = cache.get(f"periodo_id_{payload['periodo']['id']}")
                        if periodoEnCache:
                            ePeriodo = periodoEnCache
                        else:
                            if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                                ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                                if not ePeriodo:
                                    raise NameError(u"Periodo no encontrado")
                            # ePeriodo = Periodo.objects.db_manager("sga_select").get(pk=encrypt(payload['periodo']['id']))
                                cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
                    if not ePeriodo and eInscripcion.inscripcioncohorte_set.values('id').filter(status=True).exists():
                        ePeriodo = eInscripcion.inscripcioncohorte_set.filter(status=True).last().cohortes.periodoacademico
                        if not ePeriodo:
                            raise NameError(u"Periodo no encontrado")

                    # if 'id' in payload['matricula'] and payload['matricula']['id']:
                    #     matriculaEnCache = cache.get(f"matricula_id_{payload['matricula']['id']}")
                    #     if matriculaEnCache:
                    #         eMatricula = matriculaEnCache
                    #     else:
                    #         eMatricula = Matricula.objects.db_manager("sga_select").get(pk=encrypt(payload['matricula']['id']))
                    #         cache.set(f"matricula_id_{payload['matricula']['id']}", eMatricula, TIEMPO_ENCACHE)

                    if not ePerfilUsuario.es_estudiante():
                        raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
                    # if not eMatricula:
                    #     raise NameError(u'No se encuentra matriculado.')

                    eInscohorte_data = eInscripcion_data = None
                    inscohorte = eInscripcion.inscripcioncohorte_set.filter(status=True).last()
                    if inscohorte:
                        eInscohorte_data = InscripcionCohorteSerializer(inscohorte).data

                    eInscripcion_data = InscripcionSerializer(eInscripcion).data

                    estado_civil = PersonaEstadoCivil.objects.all()
                    estado_civil_seria = PersonaEstadoCivilFinanzaSerializer(estado_civil, many = True)
                    eInstitucionEducacionSuperior = InstitucionEducacionSuperior.objects.filter(status=True)

                    aData = {'ePersona': DatosPersonaSerializer(ePersona).data,
                             'eInstitucionEducacionSuperior': InstitucionEducacionSuperiorSerializer(eInstitucionEducacionSuperior, many=True).data if eInstitucionEducacionSuperior.values("id").exists() else [],
                             'eMatricula': eInscripcion_data if eInscripcion else [],
                             'estado_civil': estado_civil_seria.data,
                             }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)