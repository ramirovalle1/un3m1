from datetime import datetime, date
from decimal import Decimal
import time as pausaparaemail
from django.db import connection, transaction, connections
from django.db.models import Q, Sum
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
import requests
from sga.funciones import log, generar_nombre, convertir_fecha_invertida, cuenta_email_disponible_para_envio
from decimal import Decimal

from matricula.models import PeriodoMatricula
from settings import COBRA_COMISION_BANCO, RUBRO_ARANCEL, RUBRO_MATRICULA
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.finanza import RubroSerializer, ReporteSerializer, MatriculaSerializer, \
    CompromisoPagoPosgradoSerializer, FinanzaPersonaSerializer, PagoSerializer, PeriodoMatriculaSerializer, ComprobanteAlumnoSerializer, ComprobantePersonaSerializer, CompromisoPagoPosgradoRecorridoSerializer, PersonaEstadoCivilFinanzaSerializer, CompromisoPagoPosgradoGaranteFinanzaSerializer,\
    CuentaBancoSerializer, HistorialComprobanteAlumnoSerializer
from sagest.models import Rubro, CompromisoPagoPosgrado, CompromisoPagoPosgradoRecorrido, ComprobanteAlumno, CompromisoPagoPosgradoGarante, CompromisoPagoPosgradoGaranteArchivo,\
    CuentaBanco,TIPO_COMPROBANTE,HistorialGestionComprobanteAlumno, ComprobanteAlumnoRubros
from sagest.commonviews import obtener_estado_solicitud, obtener_tipoarchivo_solicitud
from sga.commonviews import obtener_reporte
from sga.models import PerfilUsuario, Persona, Periodo, Reporte, Matricula, PersonaDocumentoPersonal, SolicitudRefinanciamientoPosgradoRecorrido, PersonaEstadoCivil, miinstitucion, CUENTAS_CORREOS, Sexo
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
import json
from settings import SIMPLE_JWT
from hashlib import md5
from bd.models import UserToken

class RubrosAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    api_key_module = 'ALUMNO_FINANZA'

    @api_security
    def post(self, request):
        urlepunemi = 'https://sagest.epunemi.gob.ec/'
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data

        TIEMPO_ENCACHE = 60 * 15
        try:
            if not 'action' in eRequest:
                raise NameError(u'Parametro de acciòn no encontrado')

            action = eRequest['action']

            if action == 'pay_pending_values':
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
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                    else:
                        if 'id' in request.data and request.data.get('id'):
                            ePersona = Persona.objects.get(pk=int(encrypt(request.data.get('id'))))

                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    fecha_hora = fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__() + hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()
                    token_ = md5(str(encrypt(ePersona.usuario.id) + fecha_hora).encode("utf-8")).hexdigest()
                    lifetime = SIMPLE_JWT['REFRESH_TOKEN_LIFETIME']
                    perfil_ = UserToken.objects.create(user=request.user, token=token_, action_type=5, app=5, isActive=True, date_expires=datetime.now() + lifetime)
                    return Helper_Response(isSuccess=True, redirect=f'http://epunemi.gob.ec/oauth2/?tknbtn={token_}&tkn={encrypt(ePersona.id)}', module_access=False, token=True, status=status.HTTP_200_OK)

                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'loadPagos':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de rubro.')
                    id = encrypt(request.data['id'])
                    eRubro = Rubro.objects.get(pk=id)
                    ePagos = eRubro.pago_set.filter(status=True).order_by('-fecha')
                    eReporte = eReporte = obtener_reporte('factura_reporte')
                    eReportes_Serializer = ReporteSerializer(eReporte)
                    eRubro_serializer = RubroSerializer(eRubro)
                    ePagos_serializer = PagoSerializer(ePagos, many=True)

                    aData = {
                        'eRubro': eRubro_serializer.data if eRubro else None,
                        'ePagos': ePagos_serializer.data if ePagos.values("id").exists() else [],
                        'eReporte': eReportes_Serializer.data if eReporte else None,

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'mostrardocumentos':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de rubro.')

                    if not 'idmatricula' in request.data:
                        raise NameError(u'No se encontro parametro de rubro.')

                    id = int(encrypt(eRequest['id']))
                    data = {}
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=int(id))
                    documentos = []

                    idmatricula = int(encrypt(eRequest['idmatricula']))

                    matricula = Matricula.objects.get(pk=idmatricula)

                    persona = Persona.objects.get(pk=matricula.inscripcion.persona.id)

                    # Consulto los documentos personales del alumnos: cedula y papeleta de votación
                    documentospersonales = persona.documentos_personales()
                    if documentospersonales:
                        documentos.append(['Cédula de ciudadanía', documentospersonales.cedula.url, documentospersonales.get_estadocedula_display(), documentospersonales.estadocedula, documentospersonales.observacioncedula])
                        documentos.append(['Papeleta de votación', documentospersonales.papeleta.url, documentospersonales.get_estadopapeleta_display(), documentospersonales.estadopapeleta, documentospersonales.observacionpapeleta])
                    else:
                        documentos.append(['Cédula de ciudadanía', None, None, None, None])
                        documentos.append(['Papeleta de votación', None, None, None, None])

                    # Si el compromiso de pago es por refinanciamiento
                    if compromisopago.tipo == 2:
                        documentos.append(['Comprobante de Pago', compromisopago.archivocomprobante.url, compromisopago.get_estadocomprobante_display(), compromisopago.estadocomprobante, compromisopago.observacioncomprobante])

                    # Consulto los documentos del conyuge
                    conyuge = compromisopago.datos_conyuge()
                    if conyuge:
                        archivocedula = conyuge.archivocedulaconyuge()
                        documentos.append([archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.observacion])
                        archivovotacion = conyuge.archivovotacionconyuge()
                        documentos.append([archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.observacion])

                    # Consulto los documentos del garante
                    garante = compromisopago.datos_garante()
                    if garante:
                        archivocedula = garante.archivocedulagarante()
                        documentos.append([archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.observacion])
                        archivovotacion = garante.archivovotaciongarante()
                        documentos.append([archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.observacion])

                        # Si no es persona juridica
                        if garante.personajuridica == 2:
                            # si trabaja bajo relacion de dependencia
                            if garante.relaciondependencia == 1:
                                archivorolpagos = garante.archivorolpagos()
                                arch = ''
                                if archivorolpagos.archivo:
                                    arch = archivorolpagos.archivo.url
                                documentos.append([archivorolpagos.tipoarchivo.descripcion,
                                                   arch,
                                                   archivorolpagos.get_estado_display(),
                                                   archivorolpagos.estado,
                                                   archivorolpagos.observacion])
                            else:
                                archivopredios = garante.archivoimpuestopredial()
                                documentos.append([archivopredios.tipoarchivo.descripcion, archivopredios.archivo.url, archivopredios.get_estado_display(), archivopredios.estado, archivopredios.observacion])
                                archivofacserv = garante.archivofacturaserviciobasico()
                                if archivofacserv:
                                    documentos.append([archivofacserv.tipoarchivo.descripcion, archivofacserv.archivo.url, archivofacserv.get_estado_display(), archivofacserv.estado, archivofacserv.observacion])
                                archivoriseruc = garante.archivoriseruc()
                                documentos.append([archivoriseruc.tipoarchivo.descripcion, archivoriseruc.archivo.url, archivoriseruc.get_estado_display(), archivoriseruc.estado, archivoriseruc.observacion])
                        else:
                            archivoconstitucion = garante.archivoconstitucion()
                            documentos.append([archivoconstitucion.tipoarchivo.descripcion, archivoconstitucion.archivo.url, archivoconstitucion.get_estado_display(), archivoconstitucion.estado, archivoconstitucion.observacion])
                            archivoexistencia = garante.archivoexistencialegal()
                            documentos.append([archivoexistencia.tipoarchivo.descripcion, archivoexistencia.archivo.url, archivoexistencia.get_estado_display(), archivoexistencia.estado, archivoexistencia.observacion])
                            archivorenta = garante.archivoimpuestorenta()
                            documentos.append([archivorenta.tipoarchivo.descripcion, archivorenta.archivo.url, archivorenta.get_estado_display(), archivorenta.estado, archivorenta.observacion])
                            archivorepresentante = garante.archivonombramientorepresentante()
                            documentos.append([archivorepresentante.tipoarchivo.descripcion, archivorepresentante.archivo.url, archivorepresentante.get_estado_display(), archivorepresentante.estado, archivorepresentante.observacion])
                            archivoacta = garante.archivojuntaaccionistas()
                            documentos.append([archivoacta.tipoarchivo.descripcion, archivoacta.archivo.url, archivoacta.get_estado_display(), archivoacta.estado, archivoacta.observacion])
                            archivoruc = garante.archivoruc()
                            documentos.append([archivoruc.tipoarchivo.descripcion, archivoruc.archivo.url, archivoruc.get_estado_display(), archivoruc.estado, archivoruc.observacion])

                        # Consulto los documentos del conyuge del garante
                        conyugegarante = compromisopago.datos_conyuge_garante()
                        if conyugegarante:
                            archivocedula = conyugegarante.archivocedulaconyugegarante()
                            documentos.append([archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.observacion])
                            archivovotacion = conyugegarante.archivovotacionconyugegarante()
                            documentos.append([archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.observacion])

                    # Consulto el compromiso, contrato y pagare
                    if compromisopago.archivopagare:
                        documentos.append(['Tabla de amortización', compromisopago.archivocompromiso.url, compromisopago.get_estadocompromiso_display(), compromisopago.estadocompromiso, compromisopago.observacioncompromiso])

                        if compromisopago.tipo == 1:
                            documentos.append(['Contrato de Maestría', compromisopago.archivocontrato.url, compromisopago.get_estadocontrato_display(), compromisopago.estadocontrato, compromisopago.observacioncontrato])

                        documentos.append(['Pagaré', compromisopago.archivopagare.url, compromisopago.get_estadopagare_display(), compromisopago.estadopagare, compromisopago.observacionpagare])

                    data['documentos'] = documentos

                    aData = {
                        'eDocumentos': documentos
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'registropago':
                try:
                    if not 'fileDocumento' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte")
                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código de la matricula.")
                    if not 'banco_id' in eRequest:
                        raise NameError(u"No se encuentra el banco.")
                    if not 'valor_pago' in eRequest:
                        raise NameError(u"No se encuentra el valor del pago.")
                    if not 'observacion' in eRequest:
                        raise NameError(u"No se encuentra la observación.")
                    if not 'comprobate_tipo' in eRequest:
                        raise NameError(u"No se encuentra el tipo de comprobante.")

                    id = int(eRequest['id'])

                    matricula = Matricula.objects.get(pk=id)

                    cuentadeposito = int(eRequest.get("banco_id"))
                    telefono = eRequest.get("telefono")
                    email = eRequest.get("email")
                    fechapago = eRequest.get("fecha_pago")
                    valor  = Decimal(eRequest.get("valor_pago"))
                    observacion = eRequest.get("observacion")
                    tipocomprobante = eRequest.get("comprobate_tipo")
                    id = int(eRequest['id'])

                    matricula = Matricula.objects.get(pk=id)

                    persona_get = Persona.objects.get(pk=matricula.inscripcion.persona.id)
                    persona_get.telefono = telefono
                    persona_get.email = email
                    persona_get.save()
                    cuentadepositoget = cuentadeposito

                    id = int(eRequest['id'])
                    nfileDocumento = None
                    if 'fileDocumento' in eFiles:
                        nfileDocumento = eFiles['fileDocumento']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)

                    if valor <= 0:
                        raise NameError(u"Error debe ser mayor a 0.")
                    nombrepersona = persona_get.__str__()
                    nombrepersona_str = persona_get.__str__().lower().replace(' ', '_')
                    comprobante = ComprobanteAlumno(persona=persona_get,
                                                    telefono=telefono,
                                                    email=email,
                                                    curso=matricula.inscripcion.carrera.nombre,
                                                    carrera=matricula.inscripcion.carrera.nombre,
                                                    cuentadeposito=cuentadepositoget,
                                                    valor=valor,
                                                    fechapago=fechapago,
                                                    observacion=observacion,
                                                    matricula=matricula,
                                                    tipocomprobante=tipocomprobante)
                    comprobante.comprobantes = nfileDocumento
                    comprobante.save()
                    if persona_get.cedula:
                        personacedula = str(persona_get.cedula)
                    if persona_get.pasaporte:
                        personacedula = str(persona_get.pasaporte)
                    if persona_get.ruc:
                        personacedula = str(persona_get.ruc)
                    url = urlepunemi + "api?a=apisavecomprobante" \
                                        "&tiporegistro=1&clavesecreta=unemiepunemi2022&personacedula=" + personacedula + "&cuentadeposito=" + str(cuentadeposito) + \
                           "&telefono=" + str(persona_get.telefono) + \
                           "&email=" + persona_get.email + \
                           "&fecha=" + str(comprobante.fechapago) + \
                           "&archivocomprobante=" + str(comprobante.comprobantes) + \
                           "&valor=" + str(comprobante.valor) + \
                           "&curso=" + comprobante.curso + \
                           "&carrera=" + comprobante.carrera + \
                           "&observacion=" + comprobante.observacion + \
                           "&codigocomprobante=" + str(comprobante.id) + \
                           "&tipocomprobante=" + str(comprobante.tipocomprobante)
                    print(url)
                    r = requests.get(url)
                    for lista in r.json():
                        comprobante.idcomprobanteepunemi = lista['codigocomprobante']
                        comprobante.save()

                    aData = {}
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'addDocumentosPersonales':
                try:
                    if not 'fileDocumento' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte.")

                    if not 'eFileDocumentoVotacion' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de votación.")

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")

                    if not 'id_matri' in eRequest:
                        raise NameError(u"No se encuentra el código de la matricula.")

                    nfileDocumento = None
                    if 'fileDocumento' in eFiles:
                        nfileDocumento = eFiles['fileDocumento']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)

                    nfileDocumentoVotacion = None
                    if 'eFileDocumentoVotacion' in eFiles:
                        nfileDocumentoVotacion = eFiles['eFileDocumentoVotacion']
                        extensionDocumentoVotacion = nfileDocumentoVotacion._name.split('.')
                        tamDocumentoVotacion = len(extensionDocumentoVotacion)
                        exteDocumentoVota = extensionDocumentoVotacion[tamDocumentoVotacion - 1]
                        if nfileDocumentoVotacion.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumentoVota.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumentoVotacion._name = generar_nombre("dp_documento", nfileDocumentoVotacion._name)

                    id = int(encrypt(eRequest['id']))
                    idmatricula = int(encrypt(eRequest['id_matri']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)

                    matricula = Matricula.objects.get(pk=idmatricula)
                    persona = Persona.objects.get(pk=matricula.inscripcion.persona.id)
                    documentospersonales = persona.documentos_personales()
                    if not documentospersonales:

                        documentospersonales = PersonaDocumentoPersonal(persona=persona,
                                                                        cedula=nfileDocumento,
                                                                        estadocedula=1,
                                                                        observacioncedula='',
                                                                        papeleta=nfileDocumentoVotacion,
                                                                        observacionpapeleta='',
                                                                        estadopapeleta=1)
                        documentospersonales.save(request)
                    else:
                        if 'fileDocumento' in eFiles:

                            documentospersonales.cedula = nfileDocumento
                            documentospersonales.estadocedula = 1
                            documentospersonales.observacioncedula = ''

                        if 'eFileDocumentoVotacion' in eFiles:

                            documentospersonales.papeleta = nfileDocumentoVotacion
                            documentospersonales.estadopapeleta = 1
                            documentospersonales.observacionpapeleta = ''

                        documentospersonales.save(request)

                        if compromisopago.puede_cambiar_estado():
                            # Consulto el estado DOCUMENTOS CARGADOS
                            estado = obtener_estado_solicitud(2, 3)
                            compromisopago.estado = estado
                            compromisopago.observacion = ''
                            compromisopago.save(request)

                            # Creo el recorrido del compromiso
                            recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                        fecha=datetime.now().date(),
                                                                        observacion='DOCUMENTOS CARGADOS',
                                                                        estado=estado
                                                                        )
                            recorrido.save(request)

                            # Si el compromiso de pago es por refinanciamieno
                            if compromisopago.tipo == 2:
                                # Actualizo el estado en la solicitud
                                solicitud = compromisopago.solicitudrefinanciamiento
                                solicitud.estado = estado
                                solicitud.observacion = ''
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='DOCUMENTOS CARGADOS',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)

                            # enviar_correo_notificacion(persona, estado)


                    aData = {


                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'subircomprobantepago':
                try:
                    if not 'fileDocumentoComprobante' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte.")

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")

                    if not 'id_matri' in eRequest:
                        raise NameError(u"No se encuentra el código de la matricula.")

                    nfileDocumento = None
                    if 'fileDocumentoComprobante' in eFiles:
                        nfileDocumento = eFiles['fileDocumentoComprobante']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)


                    id = int(encrypt(eRequest['id']))
                    idmatricula = int(encrypt(eRequest['id_matri']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    solicitud = compromisopago.solicitudrefinanciamiento
                    solicitud.comprobantepago = nfileDocumento
                    solicitud.save(request)

                    compromisopago.archivocomprobante = nfileDocumento
                    compromisopago.observacioncomprobante = ""
                    compromisopago.estadocomprobante = 1
                    compromisopago.save(request)

                    if compromisopago.puede_cambiar_estado():
                        # Consulto el estado DOCUMENTOS CARGADOS
                        estado = obtener_estado_solicitud(2, 3)
                        compromisopago.estado = estado
                        compromisopago.observacion = ''
                        compromisopago.save(request)

                        # Creo el recorrido del compromiso
                        recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                    fecha=datetime.now().date(),
                                                                    observacion='DOCUMENTOS CARGADOS',
                                                                    estado=estado
                                                                    )
                        recorrido.save(request)

                        # Si el compromiso de pago es por refinanciamieno
                        if compromisopago.tipo == 2:
                            # Actualizo el estado en la solicitud
                            solicitud = compromisopago.solicitudrefinanciamiento
                            solicitud.estado = estado
                            solicitud.observacion = ''
                            solicitud.save(request)

                            # Creo el recorrido de la solicitud
                            recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                   fecha=datetime.now().date(),
                                                                                   observacion='DOCUMENTOS CARGADOS',
                                                                                   estado=estado
                                                                                   )
                            recorrido.save(request)
                        # enviar_correo_notificacion(compromisopago.matricula.inscripcion.persona, estado)
                    log(u'Cargó documento comprobante de pago %s' % (compromisopago.matricula.inscripcion.persona), request, "add")
                    aData = {


                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


            if action == 'datosconyugue':
                try:

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")
                    id = int(encrypt(eRequest['id']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    conyuge = compromisopago.datos_conyuge()
                    serializer_datos_conyugue = CompromisoPagoPosgradoGaranteFinanzaSerializer(conyuge)
                    aData = {
                        'datos_conyugue': serializer_datos_conyugue.data if conyuge else None,

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'datosconyuguegarante':
                try:

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")
                    id = int(encrypt(eRequest['id']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    conyuge = compromisopago.datos_conyuge_garante()
                    serializer_datos_conyugue = CompromisoPagoPosgradoGaranteFinanzaSerializer(conyuge)
                    aData = {
                        'datos_conyugue_garante': serializer_datos_conyugue.data if conyuge else None,

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'datosgarante':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")
                    id = int(encrypt(eRequest['id']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    garante = compromisopago.datos_garante()
                    serializer_datos_garante = CompromisoPagoPosgradoGaranteFinanzaSerializer(garante)
                    persona_juridica = garante.personajuridica
                    if persona_juridica == 1:
                        juridica_valor = True
                    else:
                        juridica_valor = False
                    relacion_dependencia = garante.relaciondependencia

                    aData = {
                        'datos_garante': serializer_datos_garante.data if garante else None,
                        'persona_juridica': juridica_valor,
                        'relacion_dependencia': relacion_dependencia

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'subirdocumentopagare':
                try:
                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")
                    id = int(encrypt(eRequest['id']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    if compromisopago.estado.valor == 2:
                        raise NameError(u"No se puede cargar los documentos debido a que ya se asignó estado LEGALIZADO al compromiso de pago.")

                    if compromisopago.tipo == 1:
                        if not 'eFileContratoM' in eFiles:
                            raise NameError(u"Favor subir el archivo contrato de Maestria.")


                    if not 'eFileTablaAmortizacion' in eFiles:
                        raise NameError(u"Favor subir el archivo tabla de amortización.")

                    if not 'eFilePagare' in eFiles:
                        raise NameError(u"Favor subir el archivo pagaré.")

                    if compromisopago.tipo == 1:
                        nfileContratoM = None
                        if 'eFileContratoM' in eFiles:
                            nfileContratoM = eFiles['eFileContratoM']
                            extensionContratoM = nfileContratoM._name.split('.')
                            tamContratoM = len(extensionContratoM)
                            exteContratoM = extensionContratoM[tamContratoM - 1]
                            if nfileContratoM.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteContratoM.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileContratoM._name = generar_nombre("dp_contrato_maestria", nfileContratoM._name)

                    nfileTablaA = None
                    if 'eFileTablaAmortizacion' in eFiles:
                        nfileTablaA = eFiles['eFileTablaAmortizacion']
                        extensionTablaM = nfileTablaA._name.split('.')
                        tamTablaM = len(extensionTablaM)
                        exteTablaM = extensionTablaM[tamTablaM - 1]
                        if nfileTablaA.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteTablaM.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileTablaA._name = generar_nombre("dp_contrato_maestria", nfileTablaA._name)

                    nfilePagare = None
                    if 'eFilePagare' in eFiles:
                        nfilePagare = eFiles['eFilePagare']
                        extensionPagare = nfilePagare._name.split('.')
                        tamPagare = len(extensionPagare)
                        extePagare = extensionPagare[tamPagare - 1]
                        if nfilePagare.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not extePagare.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")


                    nfilePagare._name = generar_nombre("dp_contrato_maestria", nfilePagare._name)

                    if 'eFileTablaAmortizacion' in eFiles:
                        compromisopago.archivocompromiso = nfileTablaA
                        compromisopago.observacioncompromiso = ''
                        compromisopago.estadocompromiso = 1

                    if 'eFileContratoM' in eFiles:
                        compromisopago.archivocontrato = nfileContratoM
                        compromisopago.observacioncontrato = ''
                        compromisopago.estadocontrato = 1

                    if 'eFileContratoM' in eFiles:
                        compromisopago.archivopagare = nfilePagare
                        compromisopago.observacionpagare = ''
                        compromisopago.estadopagare = 1

                    compromisopago.save(request)

                    if compromisopago.puede_cambiar_estado():
                        # Consulto el estado DOCUMENTOS CARGADOS
                        estado = obtener_estado_solicitud(2, 3)
                        estadosolicitud = obtener_estado_solicitud(1, 21)

                        compromisopago.estado = estado
                        compromisopago.observacion = ''
                        compromisopago.save(request)

                        # Creo el recorrido del compromiso
                        recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                    fecha=datetime.now().date(),
                                                                    observacion='DOCUMENTOS CARGADOS',
                                                                    estado=estado
                                                                    )
                        recorrido.save(request)

                        # Si el compromiso de pago es por refinanciamiento
                        if compromisopago.tipo == 2:
                            # Actualizo el estado en la solicitud
                            solicitud = compromisopago.solicitudrefinanciamiento
                            solicitud.estado = estadosolicitud
                            solicitud.observacion = ''
                            solicitud.save(request)

                            # Creo el recorrido de la solicitud
                            recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                   fecha=datetime.now().date(),
                                                                                   observacion='DOCUMENTOS CARGADOS',
                                                                                   estado=estadosolicitud
                                                                                   )
                            recorrido.save(request)

                        # enviar_correo_notificacion(compromisopago.matricula.inscripcion.persona, estado)

                    log(u'Cargó documentos para su compromiso de pago %s - %s' % (compromisopago.matricula.inscripcion.persona, compromisopago), request, "add")

                    aData = {
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'guardardatosconyuge':
                try:
                    if not 'fileDocumentoConyugue' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte.")

                    if not 'eFileDocumentoVotacionConyugue' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de votación.")

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")

                    if not 'id_matri' in eRequest:
                        raise NameError(u"No se encuentra el código de la matricula.")

                    if not 'cedulaconyugue' in eRequest:
                        raise NameError(u"No se encuentra la cedula conyugue.")

                    if not 'nombresconyugue' in eRequest:
                        raise NameError(u"No se encuentra el nombre conyugue.")

                    if not 'apellido1conyugue' in eRequest:
                        raise NameError(u"No se encuentra el nombre apellido 1.")

                    if not 'apellido2conyugue' in eRequest:
                        raise NameError(u"No se encuentra el nombre apellido 2.")

                    if not 'direcionconyugue' in eRequest:
                        raise NameError(u"No se encuentra la dirección del conyugue.")

                    if not 'conyugue_estadocivil' in eRequest:
                        raise NameError(u"No se encuentra el estado civil del conyugue.")

                    if not 'sexo_id_conyugue' in eRequest:
                        raise NameError(u"No se encuentra el genero del conyugue.")

                    cedulaconyugue = eRequest.get("cedulaconyugue")
                    nombresconyugue = eRequest.get("nombresconyugue")
                    apellido1conyugue = eRequest.get("apellido1conyugue")
                    apellido2conyugue = eRequest.get("apellido2conyugue")
                    direcionconyugue = eRequest.get("direcionconyugue")
                    conyugue_estadocivil = int(eRequest.get("conyugue_estadocivil"))
                    sexo_id_conyugue = int(eRequest.get("sexo_id_conyugue"))

                    nfileDocumento = None
                    if 'fileDocumentoConyugue' in eFiles:
                        nfileDocumento = eFiles['fileDocumentoConyugue']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("dp_documento_conyugue", nfileDocumento._name)

                    nfileDocumentoVotacion = None
                    if 'eFileDocumentoVotacionConyugue' in eFiles:
                        nfileDocumentoVotacion = eFiles['eFileDocumentoVotacionConyugue']
                        extensionDocumentoVotacion = nfileDocumentoVotacion._name.split('.')
                        tamDocumentoVotacion = len(extensionDocumentoVotacion)
                        exteDocumentoVota = extensionDocumentoVotacion[tamDocumentoVotacion - 1]
                        if nfileDocumentoVotacion.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumentoVota.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumentoVotacion._name = generar_nombre("dp_documento_votacion_conyugue", nfileDocumentoVotacion._name)

                    id = int(encrypt(eRequest['id']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    conyuge = compromisopago.datos_conyuge()
                    sexo_id = Sexo.objects.get(pk=sexo_id_conyugue)
                    estado_civil = PersonaEstadoCivil.objects.get(pk=conyugue_estadocivil)
                    # Si no existen datos del conyuge se crea
                    if not conyuge:
                        conyuge = CompromisoPagoPosgradoGarante(compromisopago=compromisopago,
                                                                tipo=1,
                                                                cedula=cedulaconyugue,
                                                                nombres=nombresconyugue,
                                                                apellido1=apellido1conyugue,
                                                                apellido2=apellido2conyugue,
                                                                genero=sexo_id,
                                                                estadocivil=estado_civil,
                                                                direccion=direcionconyugue
                                                                )
                        conyuge.save(request)
                        # Tipo de archivo cedula del conyuge
                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 1)
                        # Guardo archivo de la cedula
                        archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyuge,
                                                                              tipoarchivo=tipoarchivo,
                                                                              archivo=nfileDocumento,
                                                                              estado=1)
                        archivoconyuge.save(request)

                        # Tipo de archivo papeleta de votacion del conyuge
                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 2)
                        # Guardo archivo de la papeleta de votación
                        archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyuge,
                                                                              tipoarchivo=tipoarchivo,
                                                                              archivo=nfileDocumentoVotacion,
                                                                              estado=1)
                        archivoconyuge.save(request)

                        log(u'Agregó datos del conyuge %s' % (compromisopago.matricula.inscripcion.persona), request, "add")
                    else:
                        conyuge.cedula = cedulaconyugue
                        conyuge.nombres = nombresconyugue
                        conyuge.apellido1 = apellido1conyugue
                        conyuge.apellido2 = apellido2conyugue
                        conyuge.genero = sexo_id
                        conyuge.estadocivil = estado_civil
                        conyuge.direccion = direcionconyugue
                        conyuge.save(request)

                        if nfileDocumento:
                            archivocedula = conyuge.archivocedulaconyuge()
                            archivocedula.archivo = nfileDocumento
                            archivocedula.estado = 1
                            archivocedula.observacion = ''
                            archivocedula.save(request)
                        if nfileDocumentoVotacion:
                            archivovotacion = conyuge.archivovotacionconyuge()
                            archivovotacion.archivo = nfileDocumentoVotacion
                            archivovotacion.estado = 1
                            archivovotacion.observacion = ''
                            archivovotacion.save(request)

                        if compromisopago.puede_cambiar_estado():
                            # Consulto el estado DOCUMENTOS CARGADOS
                            estado = obtener_estado_solicitud(2, 3)
                            compromisopago.estado = estado
                            compromisopago.observacion = ''
                            compromisopago.save(request)

                            # Creo el recorrido del compromiso
                            recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                        fecha=datetime.now().date(),
                                                                        observacion='DOCUMENTOS CARGADOS',
                                                                        estado=estado
                                                                        )
                            recorrido.save(request)

                            # Si el compromiso de pago es por refinanciamieno
                            if compromisopago.tipo == 2:
                                # Actualizo el estado en la solicitud
                                solicitud = compromisopago.solicitudrefinanciamiento
                                solicitud.estado = estado
                                solicitud.observacion = ''
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='DOCUMENTOS CARGADOS',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)

                            # enviar_correo_notificacion(compromisopago.matricula.inscripcion.persona, estado)

                        log(u'Actualizó datos del conyuge %s' % (compromisopago.matricula.inscripcion.persona), request, "edit")


                    aData = {


                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'guardardatosconyuge':
                try:
                    if not 'fileDocumentoConyugue' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte.")

                    if not 'eFileDocumentoVotacionConyugue' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de votación.")

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")

                    if not 'id_matri' in eRequest:
                        raise NameError(u"No se encuentra el código de la matricula.")

                    if not 'cedulaconyugue' in eRequest:
                        raise NameError(u"No se encuentra la cedula conyugue.")

                    if not 'nombresconyugue' in eRequest:
                        raise NameError(u"No se encuentra el nombre conyugue.")

                    if not 'apellido1conyugue' in eRequest:
                        raise NameError(u"No se encuentra el nombre apellido 1.")

                    if not 'apellido2conyugue' in eRequest:
                        raise NameError(u"No se encuentra el nombre apellido 2.")

                    if not 'direcionconyugue' in eRequest:
                        raise NameError(u"No se encuentra la dirección del conyugue.")

                    if not 'conyugue_estadocivil' in eRequest:
                        raise NameError(u"No se encuentra el estado civil del conyugue.")

                    if not 'sexo_id_conyugue' in eRequest:
                        raise NameError(u"No se encuentra el genero del conyugue.")

                    cedulaconyugue = eRequest.get("cedulaconyugue")
                    nombresconyugue = eRequest.get("nombresconyugue")
                    apellido1conyugue = eRequest.get("apellido1conyugue")
                    apellido2conyugue = eRequest.get("apellido2conyugue")
                    direcionconyugue = eRequest.get("direcionconyugue")
                    conyugue_estadocivil = int(eRequest.get("conyugue_estadocivil"))
                    sexo_id_conyugue = int(eRequest.get("sexo_id_conyugue"))

                    nfileDocumento = None
                    if 'fileDocumentoConyugue' in eFiles:
                        nfileDocumento = eFiles['fileDocumentoConyugue']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("dp_documento_conyugue", nfileDocumento._name)

                    nfileDocumentoVotacion = None
                    if 'eFileDocumentoVotacionConyugue' in eFiles:
                        nfileDocumentoVotacion = eFiles['eFileDocumentoVotacionConyugue']
                        extensionDocumentoVotacion = nfileDocumentoVotacion._name.split('.')
                        tamDocumentoVotacion = len(extensionDocumentoVotacion)
                        exteDocumentoVota = extensionDocumentoVotacion[tamDocumentoVotacion - 1]
                        if nfileDocumentoVotacion.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumentoVota.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumentoVotacion._name = generar_nombre("dp_documento_votacion_conyugue", nfileDocumentoVotacion._name)

                    id = int(encrypt(eRequest['id']))
                    idmatricula = int(encrypt(eRequest['id_matri']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    conyuge = compromisopago.datos_conyuge()
                    sexo_id = Sexo.objects.get(pk=sexo_id_conyugue)
                    estado_civil = PersonaEstadoCivil.objects.get(pk=conyugue_estadocivil)
                    # Si no existen datos del conyuge se crea
                    if not conyuge:
                        conyuge = CompromisoPagoPosgradoGarante(compromisopago=compromisopago,
                                                                tipo=1,
                                                                cedula=cedulaconyugue,
                                                                nombres=nombresconyugue,
                                                                apellido1=apellido1conyugue,
                                                                apellido2=apellido2conyugue,
                                                                genero=sexo_id,
                                                                estadocivil=estado_civil,
                                                                direccion=direcionconyugue
                                                                )
                        conyuge.save(request)
                        # Tipo de archivo cedula del conyuge
                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 1)
                        # Guardo archivo de la cedula
                        archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyuge,
                                                                              tipoarchivo=tipoarchivo,
                                                                              archivo=nfileDocumento,
                                                                              estado=1)
                        archivoconyuge.save(request)

                        # Tipo de archivo papeleta de votacion del conyuge
                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 2)
                        # Guardo archivo de la papeleta de votación
                        archivoconyuge = CompromisoPagoPosgradoGaranteArchivo(garante=conyuge,
                                                                              tipoarchivo=tipoarchivo,
                                                                              archivo=nfileDocumentoVotacion,
                                                                              estado=1)
                        archivoconyuge.save(request)

                        log(u'Agregó datos del conyuge %s' % (compromisopago.matricula.inscripcion.persona), request, "add")
                    else:
                        conyuge.cedula = cedulaconyugue
                        conyuge.nombres = nombresconyugue
                        conyuge.apellido1 = apellido1conyugue
                        conyuge.apellido2 = apellido2conyugue
                        conyuge.genero = sexo_id
                        conyuge.estadocivil = estado_civil
                        conyuge.direccion = direcionconyugue
                        conyuge.save(request)

                        if nfileDocumento:
                            archivocedula = conyuge.archivocedulaconyuge()
                            archivocedula.archivo = nfileDocumento
                            archivocedula.estado = 1
                            archivocedula.observacion = ''
                            archivocedula.save(request)
                        if nfileDocumentoVotacion:
                            archivovotacion = conyuge.archivovotacionconyuge()
                            archivovotacion.archivo = nfileDocumentoVotacion
                            archivovotacion.estado = 1
                            archivovotacion.observacion = ''
                            archivovotacion.save(request)

                        if compromisopago.puede_cambiar_estado():
                            # Consulto el estado DOCUMENTOS CARGADOS
                            estado = obtener_estado_solicitud(2, 3)
                            compromisopago.estado = estado
                            compromisopago.observacion = ''
                            compromisopago.save(request)

                            # Creo el recorrido del compromiso
                            recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                        fecha=datetime.now().date(),
                                                                        observacion='DOCUMENTOS CARGADOS',
                                                                        estado=estado
                                                                        )
                            recorrido.save(request)

                            # Si el compromiso de pago es por refinanciamieno
                            if compromisopago.tipo == 2:
                                # Actualizo el estado en la solicitud
                                solicitud = compromisopago.solicitudrefinanciamiento
                                solicitud.estado = estado
                                solicitud.observacion = ''
                                solicitud.save(request)

                                # Creo el recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='DOCUMENTOS CARGADOS',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)

                            # enviar_correo_notificacion(compromisopago.matricula.inscripcion.persona, estado)

                        log(u'Actualizó datos del conyuge %s' % (compromisopago.matricula.inscripcion.persona), request, "edit")


                    aData = {


                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'guardardatosgarante':
                try:
                    if not 'fileDocumentoGarante' in eFiles:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte.")

                    if not 'fileDocumentoVotacionGarante' in eFiles:
                        raise NameError(u"Favor subir el archivo de pasaporte.")

                    if not 'id' in eRequest:
                        raise NameError(u"No se encuentra el código.")

                    if not 'id_matri' in eRequest:
                        raise NameError(u"No se encuentra el código de la matricula.")

                    if not 'cedulagarante' in eRequest:
                        raise NameError(u"No se encuentra la cedula conyugue.")

                    if not 'nombresgarante' in eRequest:
                        raise NameError(u"No se encuentra el nombre conyugue.")

                    if not 'apellido1garante' in eRequest:
                        raise NameError(u"No se encuentra el nombre apellido 1.")

                    if not 'apellido2garante' in eRequest:
                        raise NameError(u"No se encuentra el nombre apellido 2.")

                    if not 'direciongarante' in eRequest:
                        raise NameError(u"No se encuentra la dirección del conyugue.")

                    if not 'estado_civil_garante' in eRequest:
                        raise NameError(u"No se encuentra el estado civil del conyugue.")

                    if not 'sexo_id_garante' in eRequest:
                        raise NameError(u"No se encuentra el genero del conyugue.")

                    if not 'trabajador_relacion_dependencia' in eRequest:
                        raise NameError(u"No se encuentra el trabajador_relacion_dependencia.")

                    if not 'persona_juridica' in eRequest:
                        raise NameError(u"No se encuentra el persona_juridica.")

                    cedulagarante = eRequest.get("cedulagarante")
                    nombresgarante = eRequest.get("nombresgarante")
                    apellido1garante = eRequest.get("apellido1garante")
                    apellido2garante = eRequest.get("apellido2garante")
                    direciongarante = eRequest.get("direciongarante")
                    estado_civil_garante = int(eRequest.get("estado_civil_garante"))
                    sexo_id_garante = int(eRequest.get("sexo_id_garante"))

                    persona_juridica = eRequest.get("persona_juridica")
                    if persona_juridica == 'false':
                        persona_juridica = False
                    else:
                        persona_juridica = True

                    trabajador_relacion_dependencia = int(eRequest.get("trabajador_relacion_dependencia"))

                    nfileDocumento = None
                    if 'fileDocumentoGarante' in eFiles:
                        nfileDocumento = eFiles['fileDocumentoGarante']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumento._name = generar_nombre("dp_documento_garante", nfileDocumento._name)

                    nfileDocumentoVotacion = None
                    if 'fileDocumentoVotacionGarante' in eFiles:
                        nfileDocumentoVotacion = eFiles['fileDocumentoVotacionGarante']
                        extensionDocumentoVotacion = nfileDocumentoVotacion._name.split('.')
                        tamDocumentoVotacion = len(extensionDocumentoVotacion)
                        exteDocumentoVota = extensionDocumentoVotacion[tamDocumentoVotacion - 1]
                        if nfileDocumentoVotacion.size > 1500000:
                            raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                        if not exteDocumentoVota.lower() == 'pdf':
                            raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                    nfileDocumentoVotacion._name = generar_nombre("dp_documento_votacion_garante", nfileDocumentoVotacion._name)

                    if persona_juridica:
                        nfileCopiaConstitucion = None
                        if 'fileDocumentoCopiaConstitucion' in eFiles:
                            nfileCopiaConstitucion = eFiles['fileDocumentoCopiaConstitucion']
                            extensionCopiaConstitucion = nfileCopiaConstitucion._name.split('.')
                            tamCopiaConstitucion = len(extensionCopiaConstitucion)
                            exteCopiaConstitucion = extensionCopiaConstitucion[tamCopiaConstitucion - 1]
                            if nfileCopiaConstitucion.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteCopiaConstitucion.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileCopiaConstitucion._name = generar_nombre("dp_documento_constitucion_garante", nfileCopiaConstitucion._name)

                        nfileCertificacionLegal = None
                        if 'fileCertificacionLegal' in eFiles:
                            nfileCertificacionLegal = eFiles['fileCertificacionLegal']
                            extensionCertificacionLegal = nfileCertificacionLegal._name.split('.')
                            tamCertificacionLegal = len(extensionCertificacionLegal)
                            exteCertificacionLegal = extensionCertificacionLegal[tamCertificacionLegal - 1]
                            if nfileCertificacionLegal.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteCertificacionLegal.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileCertificacionLegal._name = generar_nombre("dp_documento_certi_legal_garante", nfileCertificacionLegal._name)

                        nfileDeclaracionRental = None
                        if 'fileDeclaracionRenta' in eFiles:
                            nfileDeclaracionRental = eFiles['fileDeclaracionRenta']
                            extensionDeclaracionRental = nfileDeclaracionRental._name.split('.')
                            tamDeclaracionRental = len(extensionDeclaracionRental)
                            exteDeclaracionRental  = extensionDeclaracionRental[tamDeclaracionRental - 1]
                            if nfileDeclaracionRental.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDeclaracionRental.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileDeclaracionRental._name = generar_nombre("dp_documento_declaracion_renta_garante", nfileDeclaracionRental._name)

                        nfileNombramientoRepresentante = None
                        if 'fileNombramientoRepresentante' in eFiles:
                            nfileNombramientoRepresentante = eFiles['fileNombramientoRepresentante']
                            extensionNombramientoRepresentante = nfileNombramientoRepresentante._name.split('.')
                            tamNombramientoRepresentante = len(extensionNombramientoRepresentante)
                            exteNombramientoRepresentante = extensionNombramientoRepresentante[tamNombramientoRepresentante - 1]
                            if nfileNombramientoRepresentante.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteNombramientoRepresentante.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileNombramientoRepresentante._name = generar_nombre("dp_nombramiento_repre_garante", nfileNombramientoRepresentante._name)

                        nfileActaJunta = None
                        if 'fileActaJunta' in eFiles:
                            nfileActaJunta = eFiles['fileActaJunta']
                            extensionActaJunta = nfileActaJunta._name.split('.')
                            tamActaJunta = len(extensionActaJunta)
                            exteActaJunta = extensionActaJunta[tamActaJunta - 1]
                            if nfileActaJunta.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteActaJunta.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileActaJunta._name = generar_nombre("dp_acta_junta_garante", nfileActaJunta._name)

                        nfileRUC = None
                        if 'fileRUC' in eFiles:
                            nfileRUC= eFiles['fileRUC']
                            extensionRUC = nfileRUC._name.split('.')
                            tamRUC = len(extensionRUC)
                            exteRUC = extensionRUC[tamRUC - 1]
                            if nfileRUC.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteRUC.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileRUC._name = generar_nombre("dp_RUC_garante", nfileRUC._name)

                    if not persona_juridica and trabajador_relacion_dependencia == 1:
                        nfileRolPago = None
                        if 'fileRolPago' in eFiles:
                            nfileRolPago = eFiles['fileRolPago']
                            extensionRolPago = nfileRolPago._name.split('.')
                            tamRolPago = len(extensionRolPago)
                            exteRolPago = extensionRolPago[tamRolPago - 1]
                            if nfileRolPago.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteRolPago.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileRolPago._name = generar_nombre("dp_rol_pago_garante", nfileRolPago._name)

                    if not persona_juridica and trabajador_relacion_dependencia == 2:
                        nfileImpuestoPrediales = None
                        if 'fileImpuestoPrediales' in eFiles:
                            nfileImpuestoPrediales = eFiles['fileImpuestoPrediales']
                            extensionImpuestoPrediales = nfileImpuestoPrediales._name.split('.')
                            tamImpuestoPrediales = len(extensionImpuestoPrediales)
                            exteImpuestoPrediales = extensionImpuestoPrediales[tamImpuestoPrediales - 1]
                            if nfileImpuestoPrediales.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteImpuestoPrediales.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileImpuestoPrediales._name = generar_nombre("dp_impuesto_prediales_garante", nfileImpuestoPrediales._name)

                        nfileServicioBasico = None
                        if 'fileServicioBasico' in eFiles:
                            nfileServicioBasico = eFiles['fileServicioBasico']
                            extensionServicioBasico = nfileServicioBasico._name.split('.')
                            tamServicioBasico = len(extensionServicioBasico)
                            exteServicioBasico = extensionServicioBasico[tamServicioBasico - 1]
                            if nfileServicioBasico.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteServicioBasico.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileServicioBasico._name = generar_nombre("dp_servicio_basico_garante", nfileServicioBasico._name)

                        nfileRISEoRUC = None
                        if 'fileRISEoRUC' in eFiles:
                            nfileRISEoRUC = eFiles['fileRISEoRUC']
                            extensionRISEoRUC = nfileRISEoRUC._name.split('.')
                            tamRISEoRUC = len(extensionRISEoRUC)
                            exteServicioBasico = extensionRISEoRUC[tamRISEoRUC - 1]
                            if nfileRISEoRUC.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteServicioBasico.lower() == 'pdf':
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                        nfileRISEoRUC._name = generar_nombre("dp_rise_ruc_garante", nfileRISEoRUC._name)

                    id = int(encrypt(eRequest['id']))
                    idmatricula = int(encrypt(eRequest['id_matri']))
                    compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                    garante = compromisopago.datos_garante()
                    sexo_id = Sexo.objects.get(pk=sexo_id_garante)
                    estado_civil = PersonaEstadoCivil.objects.get(pk=estado_civil_garante)
                    if persona_juridica:
                        juridica_numero = 1
                    else:
                        juridica_numero = 2
                    # Si no existen datos del garante se crea
                    if not garante:
                        garante = CompromisoPagoPosgradoGarante(compromisopago=compromisopago,
                                                                tipo=2,
                                                                cedula=cedulagarante,
                                                                nombres=nombresgarante,
                                                                apellido1=apellido1garante,
                                                                apellido2=apellido2garante,
                                                                genero=sexo_id,
                                                                estadocivil=estado_civil,
                                                                direccion=direciongarante,
                                                                personajuridica= juridica_numero,
                                                                relaciondependencia= trabajador_relacion_dependencia
                                                                )
                        garante.save(request)
                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 3)

                        archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                              tipoarchivo=tipoarchivo,
                                                                              archivo=nfileDocumento,
                                                                              estado=1)
                        archivogarante.save(request)

                        # Tipo de archivo papeleta de votacion del garante
                        tipoarchivo = obtener_tipoarchivo_solicitud(2, 4)

                        archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                              tipoarchivo=tipoarchivo,
                                                                              archivo=nfileDocumentoVotacion,
                                                                              estado=1)
                        archivogarante.save(request)
                        if juridica_numero == 2:
                            # si trabaja bajo relacion de dependencia
                            if trabajador_relacion_dependencia  == 1:
                                # Tipo de archivo rol de pago
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 5)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=nfileRolPago,
                                                                                      estado=1)
                                archivogarante.save(request)
                            else:
                                # Tipo de archivo pago impuestos prediales
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 6)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=nfileImpuestoPrediales,
                                                                                      estado=1)
                                archivogarante.save(request)

                                if nfileServicioBasico:
                                    # Tipo de archivo factura de servicio básico
                                    tipoarchivo = obtener_tipoarchivo_solicitud(2, 7)

                                    archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                          tipoarchivo=tipoarchivo,
                                                                                          archivo=nfileServicioBasico,
                                                                                          estado=1)
                                    archivogarante.save(request)

                                # Tipo de archivo RISE o RUC
                                tipoarchivo = obtener_tipoarchivo_solicitud(2, 8)

                                archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                      tipoarchivo=tipoarchivo,
                                                                                      archivo=nfileRISEoRUC,
                                                                                      estado=1)
                                archivogarante.save(request)
                        else:
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 9)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=nfileCopiaConstitucion,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Tipo de archivo certificado existencia legal
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 10)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=nfileCertificacionLegal,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Tipo de archivo impuesto a la renta
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 11)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=nfileDeclaracionRental,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Tipo de archivo nombramiento de reprsentante
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 12)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=nfileNombramientoRepresentante,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Tipo de archivo acta junta de accionistas
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 13)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=nfileActaJunta,
                                                                                  estado=1)
                            archivogarante.save(request)

                            # Tipo de archivo copia del ruc
                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 14)

                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                  tipoarchivo=tipoarchivo,
                                                                                  archivo=nfileRUC,
                                                                                  estado=1)
                            archivogarante.save(request)

                        # log(u'Agregó datos del garante %s' % (persona), request, "add")
                    else:
                            garante.cedula = cedulagarante
                            garante.nombres = nombresgarante
                            garante.apellido1 = apellido1garante
                            garante.apellido2 = apellido2garante
                            if sexo_id_garante:
                                garante.genero = sexo_id

                            if estado_civil_garante:
                                garante.estadocivil = estado_civil

                            garante.direccion = direciongarante
                            garante.save(request)

                            if nfileDocumento:
                                archivogarante = garante.archivocedulagarante()
                                archivogarante.archivo = nfileDocumento
                                archivogarante.observacion = ''
                                archivogarante.estado = 1
                                archivogarante.save(request)

                            if nfileDocumentoVotacion:
                                archivogarante = garante.archivovotaciongarante()
                                archivogarante.archivo = nfileDocumentoVotacion
                                archivogarante.estado = 1
                                archivogarante.observacion = ''
                                archivogarante.save(request)

                            # si no es persona juridica
                            if garante.personajuridica == 2:
                                # si trabaja bajo relacion de dependencia
                                relaciondependencia = trabajador_relacion_dependencia if trabajador_relacion_dependencia else garante.relaciondependencia
                                if relaciondependencia == 1:
                                    if nfileRolPago:
                                        archivogarante = garante.archivorolpagos()
                                        if archivogarante:
                                            archivogarante.archivo = nfileRolPago
                                            archivogarante.observacion = ''
                                            archivogarante.estado = 1
                                            archivogarante.save(request)

                                            garante.relaciondependencia = relaciondependencia
                                            garante.save(request)
                                        else:
                                            # Tipo de archivo rol de pago
                                            tipoarchivo = obtener_tipoarchivo_solicitud(2, 5)

                                            archivogarante = CompromisoPagoPosgradoGaranteArchivo(garante=garante,
                                                                                                  tipoarchivo=tipoarchivo,
                                                                                                  archivo=nfileRolPago,
                                                                                                  estado=1)
                                            archivogarante.save(request)

                                            garante.relaciondependencia = relaciondependencia
                                            garante.save(request)
                                else:
                                    if nfileImpuestoPrediales:
                                        archivogarante = garante.archivoimpuestopredial()
                                        archivogarante.archivo = nfileImpuestoPrediales
                                        archivogarante.observacion = ''
                                        archivogarante.estado = 1
                                        archivogarante.save(request)

                                    if nfileServicioBasico:
                                        archivogarante = garante.archivofacturaserviciobasico()
                                        archivogarante.archivo = nfileServicioBasico
                                        archivogarante.observacion = ''
                                        archivogarante.estado = 1
                                        archivogarante.save(request)

                                    if nfileRISEoRUC:
                                        archivogarante = garante.archivoriseruc()
                                        archivogarante.archivo = nfileRISEoRUC
                                        archivogarante.observacion = ''
                                        archivogarante.estado = 1
                                        archivogarante.save(request)
                            else:
                                if nfileCopiaConstitucion:
                                    archivogarante = garante.archivoconstitucion()
                                    archivogarante.archivo = nfileCopiaConstitucion
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if nfileCertificacionLegal:
                                    archivogarante = garante.archivoexistencialegal()
                                    archivogarante.archivo = nfileCertificacionLegal
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if nfileDeclaracionRental:
                                    archivogarante = garante.archivoimpuestorenta()
                                    archivogarante.archivo = nfileDeclaracionRental
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if nfileNombramientoRepresentante:
                                    archivogarante = garante.archivonombramientorepresentante()
                                    archivogarante.archivo = nfileNombramientoRepresentante
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if nfileActaJunta:
                                    archivogarante = garante.archivojuntaaccionistas()
                                    archivogarante.archivo = nfileActaJunta
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                                if nfileRUC:
                                    archivogarante = garante.archivoruc()
                                    archivogarante.archivo = nfileRUC
                                    archivogarante.observacion = ''
                                    archivogarante.estado = 1
                                    archivogarante.save(request)

                            if compromisopago.puede_cambiar_estado():
                                # Consulto el estado DOCUMENTOS CARGADOS
                                estado = obtener_estado_solicitud(2, 3)
                                compromisopago.estado = estado
                                compromisopago.observacion = ''
                                compromisopago.save(request)

                                # Creo el recorrido del compromiso
                                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                            fecha=datetime.now().date(),
                                                                            observacion='DOCUMENTOS CARGADOS',
                                                                            estado=estado
                                                                            )
                                recorrido.save(request)

                                # Si el compromiso de pago es por refinanciamieno
                                if compromisopago.tipo == 2:
                                    # Actualizo el estado en la solicitud
                                    solicitud = compromisopago.solicitudrefinanciamiento
                                    solicitud.estado = estado
                                    solicitud.observacion = ''
                                    solicitud.save(request)

                                    # Creo el recorrido de la solicitud
                                    recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                           fecha=datetime.now().date(),
                                                                                           observacion='DOCUMENTOS CARGADOS',
                                                                                           estado=estado
                                                                                           )
                                    recorrido.save(request)

                                # enviar_correo_notificacion(compromisopago.matricula.inscripcion.persona, estado)

                            log(u'Actualizó datos del garante %s' % (compromisopago.matricula.inscripcion.persona), request, "edit")


                    aData = {


                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


            elif action == 'to_differ':
                with transaction.atomic():
                    try:
                        id = encrypt(request.data['id'])
                        eMatricula = Matricula.objects.get(pk=id)
                        if not eMatricula.puede_diferir_rubro_arancel():
                            raise NameError(u"No se permite diferir arancel")
                        ePersona = eMatricula.inscripcion.persona
                        ePeriodoMatricula = None
                        if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=eMatricula.nivel.periodo).exists():
                            ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=eMatricula.nivel.periodo)
                        if not ePeriodoMatricula:
                            raise NameError(u"No se permite diferir arancel")
                        if ePeriodoMatricula.valida_cuotas_rubro and ePeriodoMatricula.num_cuotas_rubro <= 0:
                            raise NameError(u"Periodo acádemico no permite diferir arancel")
                        if not ePeriodoMatricula.tiene_fecha_cuotas_rubro():
                            raise NameError(u"Periodo acádemico no permite diferir arancel")
                        if ePeriodoMatricula.monto_rubro_cuotas == 0:
                            raise NameError(u"Periodo acádemico no permite diferir arancel")
                        if eMatricula.aranceldiferido == 1:
                            raise NameError(u"El rubro arancel ya ha sido diferido.")
                        if not Rubro.objects.values('id').filter(matricula=eMatricula, tipo_id=RUBRO_ARANCEL, status=True).exists():
                            raise NameError(u"No se puede procesar el registro.")
                        arancel = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_ARANCEL, status=True).first()
                        nombrearancel = arancel.nombre
                        valorarancel = Decimal(arancel.valortotal).quantize(Decimal('.01'))
                        if valorarancel < ePeriodoMatricula.monto_rubro_cuotas:
                            raise NameError(f"Periodo acádemico no permite diferir arancel manor a ${ePeriodoMatricula.monto_rubro_cuotas}")
                        num_cuotas = ePeriodoMatricula.num_cuotas_rubro
                        try:
                            valor_cuota_mensual = (valorarancel / num_cuotas).quantize(Decimal('.01'))
                        except ZeroDivisionError:
                            valor_cuota_mensual = 0
                        if valor_cuota_mensual == 0:
                            raise NameError(u"No se puede procesar el registro.")
                        eRubroMatricula = Rubro.objects.filter(matricula=eMatricula, tipo_id=RUBRO_MATRICULA)[0]
                        eRubroMatricula.relacionados = None
                        eRubroMatricula.save(request)
                        lista = []
                        c = 0
                        for r in ePeriodoMatricula.fecha_cuotas_rubro().values('fecha').distinct():
                            c += 1
                            lista.append([c, valor_cuota_mensual, r['fecha']])
                        for item in lista:
                            rubro = Rubro(tipo_id=RUBRO_ARANCEL,
                                          persona=Persona.objects.get(pk=ePersona.id),
                                          relacionados=eRubroMatricula,
                                          matricula=eMatricula,
                                          nombre=nombrearancel,
                                          cuota=item[0],
                                          fecha=datetime.now().date(),
                                          fechavence=item[2],
                                          valor=item[1],
                                          iva_id=1,
                                          valoriva=0,
                                          valortotal=item[1],
                                          saldo=item[1],
                                          cancelado=False)
                            rubro.save(request)
                        arancel.delete()
                        # Matricula.objects.filter(pk=eMatricula.id).update(aranceldiferido=1)
                        url_acta_compromiso = ""
                        if ePeriodoMatricula.valida_rubro_acta_compromiso:
                            isResult, message = eMatricula.generar_actacompromiso_matricula_pregrado(request)
                            if not isResult:
                                raise NameError(message)
                            url_acta_compromiso = message
                            eMatricula.aranceldiferido = 1
                            eMatricula.actacompromiso = url_acta_compromiso
                            eMatricula.save(request)
                        return Helper_Response(isSuccess=True, data={'acta_compromiso': url_acta_compromiso}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'cuentasbancarias':
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
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                    eCuentaBanco = CuentaBanco.objects.filter(status=True,banco_id=19,pk=5).order_by('banco__nombre')
                    cuentas_serializer = CuentaBancoSerializer(eCuentaBanco,many=True)
                    eRubro = Rubro.objects.filter(status=True,persona = ePersona, cancelado =False)#matricula__isnull=Falsematricula__isnull=False
                    celular = ePersona.telefono
                    correo = ePersona.email
                    comprobante = None
                    rubros = None
                    id_rubros = []
                    rubros_seri = None
                    if 'id' in eRequest:
                        id = encrypt(eRequest['id'])
                        comprobante = ComprobanteAlumno.objects.get(id = int(id))
                        rubros = comprobante.comprobantealumnorubros_set.filter(status=True).values_list('rubro__id',flat=True)
                        rubros_seri = Rubro.objects.filter(status=True,persona=ePersona, id__in = rubros).values_list('id',flat=True)
                        comprobante_serializer = ComprobanteAlumnoSerializer(comprobante)
                    if rubros_seri:
                        for ii in rubros_seri:
                            id_rubros.append(encrypt(ii))
                    if ComprobanteAlumnoRubros.objects.filter(status=True,comprobantealumno__persona=ePersona,rubro__in=eRubro.values('id')).exclude(comprobantealumno__estados__in=[3,4]).exists():
                        exclrubro = ComprobanteAlumnoRubros.objects.filter(status=True,comprobantealumno__persona=ePersona,rubro__in=eRubro.values('id')).values_list('rubro__id',flat=True).exclude(comprobantealumno__estados__in=[3])
                        if not comprobante:
                            eRubro = eRubro.exclude(id__in=exclrubro)
                    rubros_serializer = RubroSerializer(eRubro, many = True)
                    aData = {
                        'eCuentasBancaria': cuentas_serializer.data if eCuentaBanco else {},
                        'eCelular':celular,
                        'eCorreo':correo,
                        'eTipoComrpobante':TIPO_COMPROBANTE,
                        'eComprobante': comprobante_serializer.data if comprobante else [],
                        'eRubrosId': id_rubros if rubros else {},
                        'eRubros': rubros_serializer.data if eRubro.exists() else {}
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == "addcomprobantepago":
                with transaction.atomic():
                    try:
                        if eRequest['id_comprobante'] == "0":
                            if not 'eFileComrpobantePagoF' in eFiles:
                                raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte.")

                        if not 'id_matri' in eRequest:
                            raise NameError(u"No se encuentra el código de la matricula.")

                        nfileDocumento = None
                        if 'eFileComrpobantePagoF' in eFiles:
                            nfileDocumento = eFiles['eFileComrpobantePagoF']
                            extensionDocumento = nfileDocumento._name.split('.')
                            tamDocumento = len(extensionDocumento)
                            exteDocumento = extensionDocumento[tamDocumento - 1]
                            if nfileDocumento.size > 1500000:
                                raise NameError(u"Error al cargar, el archivo es mayor a 15 Mb.")
                            if not exteDocumento.lower() in ['pdf']:
                                raise NameError(u"Error al cargar, solo se permiten archivos .pdf")
                            nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)
                        idmatricula = int(encrypt(eRequest['id_matri']))

                        matricula = Matricula.objects.get(pk=idmatricula)
                        persona = Persona.objects.get(pk=matricula.inscripcion.persona.id)
                        if eRequest['id_comprobante'] != "0":
                            id_comprobante = encrypt(eRequest['id_comprobante'])
                            comprobante = ComprobanteAlumno.objects.get(id = int(id_comprobante))
                            comprobante.persona = persona
                            comprobante.matricula = matricula
                            comprobante.telefono = eRequest['eCelularCom']
                            comprobante.email = eRequest['eCorreoPersonal']
                            comprobante.observacion = eRequest['eObservacionComprobante']
                            if int(eRequest['eTipoCuentaBancoComrp']) == 1:
                                comprobante.referenciapapeleta = eRequest['eReferenciaPapeleta']
                            comprobante.valor = float(eRequest['eValorComprobante'])
                            #comprobante.cuentabancaria_id = int(encrypt(eRequest['eCuentaBancoComrp']))
                            comprobante.tipocomprobante = int(eRequest['eTipoCuentaBancoComrp'])
                            comprobante.fechapago = datetime.strptime(eRequest['eFechaPago'], "%Y-%m-%d").date()
                            if nfileDocumento:
                                comprobante.comprobantes = nfileDocumento
                            comprobante.save(request)
                            log(u"Editó cormprobante alumno: %s" % comprobante, request, "edit")
                            comprubros = ComprobanteAlumnoRubros.objects.filter(status=True,comprobantealumno=comprobante)
                            id_rubros = []
                            for ru_id in json.loads(eRequest['rubros_id[]']):
                                id = encrypt(ru_id.replace('"',''))
                                id_rubros.append(int(id))
                                if not comprubros.filter(rubro_id = id).exists():
                                    rubcompalu = ComprobanteAlumnoRubros(
                                        comprobantealumno = comprobante,
                                        rubro_id = id
                                    )
                                    rubcompalu.save(request)
                                    log(u"Agregó rubros al comprobante de pago %s"% rubcompalu, request,'add')
                            for ruex_id in comprubros.exclude(rubro_id__in = id_rubros):
                                ruex_id.status = False
                                ruex_id.save(request)
                                log(u"Eliminó rubros al comprobante de pago %s"% ruex_id,request,'del')
                        else:
                            comprobante = ComprobanteAlumno(
                                persona = persona,
                                matricula = matricula,
                                telefono = eRequest['eCelularCom'],
                                email = eRequest['eCorreoPersonal'],
                                observacion = eRequest['eObservacionComprobante'],

                                valor = float(eRequest['eValorComprobante']),
                                #cuentabancaria_id = int(encrypt(eRequest['eCuentaBancoComrp'])),
                                tipocomprobante = int(eRequest['eTipoCuentaBancoComrp']),
                                fechapago = datetime.strptime(eRequest['eFechaPago'],"%Y-%m-%d").date(),
                                comprobantes = nfileDocumento
                            )
                            if int(eRequest['eTipoCuentaBancoComrp']) == 1:
                                comprobante.referenciapapeleta = eRequest['eReferenciaPapeleta']
                            comprobante.save(request)
                            log(u"Agregó cormprobante alumno: %s"%comprobante, request,"add")
                            for ru_id in json.loads(eRequest['rubros_id[]']):
                                id = encrypt(ru_id.replace('"', ''))
                                rubcompalu = ComprobanteAlumnoRubros(
                                    comprobantealumno=comprobante,
                                    rubro_id=id
                                )
                                rubcompalu.save(request)
                                log(u"Agregó rubros al comprobante de pago %s" % rubcompalu, request, 'add')
                        historial = HistorialGestionComprobanteAlumno(
                            comprobante = comprobante,
                            persona = persona,
                            estado = comprobante.estados,
                            fecha = datetime.today(),
                            observacion = comprobante.observacion
                        )
                        historial.save(request)
                        log(u"Agregó historial del comprobante alumno: %s"%historial,request,"add")
                        return Helper_Response(isSuccess=True,  data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'historialcomprobantes':
                try:
                    if not 'id' in request.data:
                        raise NameError(u'No se encontro parametro de hostorial asignada.')
                    id = encrypt(request.data['id'])
                    historial = HistorialGestionComprobanteAlumno.objects.filter(comprobante_id=int(id))
                    histo = HistorialComprobanteAlumnoSerializer(historial, many=True)
                    aData = {
                        'eHistorialComp': histo.data if historial.exists() else {},
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'comprobantespagos':
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
                    # if eInscripcion.coordinacion.id != 7:
                    #     if not eInscripcion.tiene_ficha_socioeconomica_confirmada():
                    #         return Helper_Response(isSuccess=False, redirect="alu_socioecon", module_access=False, token=True, status=status.HTTP_200_OK)
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                    comprobantes = ComprobanteAlumno.objects.filter(status=True,persona=ePersona)
                    comprobantes_serializer = ComprobanteAlumnoSerializer(comprobantes, many=True)
                    persona_serializer = ComprobantePersonaSerializer(ePersona)
                    matri_serial = MatriculaSerializer(eMatricula)
                    fecha_hoy = date.today()
                    aData = {
                        'eComprobantesLista': comprobantes_serializer.data if comprobantes.exists() else {},
                        'ePersona': persona_serializer.data,
                        'eMatricula': matri_serial.data

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error : {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'deleteComprobantePago':
                with transaction.atomic():
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
                        # if eInscripcion.coordinacion.id != 7:
                        #     if not eInscripcion.tiene_ficha_socioeconomica_confirmada():
                        #         return Helper_Response(isSuccess=False, redirect="alu_socioecon", module_access=False, token=True, status=status.HTTP_200_OK)
                        if 'id' in payload['matricula'] and payload['matricula']['id']:
                            eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                            ePeriodo = eMatricula.nivel.periodo
                        if not 'id' in eRequest:
                            raise NameError(u'No se encuentra el comprobante de pago.')
                        id = encrypt(eRequest['id'])
                        if not ComprobanteAlumno.objects.filter(id=int(id),status=True).exists():
                            raise NameError(u'No se encuentra el comprobante de pago. Recarge la pagina')
                        comprobante = ComprobanteAlumno.objects.get(id=int(id))
                        comprobante.status = False
                        comprobante.save(request)
                        for comprubro in comprobante.comprobantealumnorubros_set.filter(status=True):
                            comprubro.status = False
                            comprubro.save(request)
                        log(u'Elimino comprobante de pago: %s' % comprobante, request, "del")
                        return Helper_Response(isSuccess=True, data={}, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            if action == 'consultarvalores':
                try:
                    id = json.loads(eRequest['id'])
                    filter = []
                    for i in id:
                        filter.append(int(encrypt(i)))

                    eValores = Rubro.objects.filter(id__in= filter).aggregate(Sum('saldo'))
                    aData = {
                        'eValores':eValores['saldo__sum']
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        urlepunemi = 'https://sagest.epunemi.gob.ec/'

        try:
            action = ''
            if 'action' in request.query_params:
                action = request.query_params['action']

            if action == 'listacomprobantes':
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
                    habilitaPagoTarjeta = False
                    if eInscripcion.coordinacion.id == 7:
                    #     if not eInscripcion.tiene_ficha_socioeconomica_confirmada():
                    #         return Helper_Response(isSuccess=False, redirect="alu_socioecon", module_access=False, token=True, status=status.HTTP_200_OK)
                    # else:
                        habilitaPagoTarjeta = True
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                    comprobantes = eMatricula.comprobantealumno_set.filter(status=True)
                    comprobantes_serializer = ComprobanteAlumnoSerializer(comprobantes, many = True)
                    persona_serializer = ComprobantePersonaSerializer(ePersona)
                    fecha_hoy = date.today()
                    url = urlepunemi + "api?a=apicuentas&clavesecreta=unemiepunemi2022"
                    r = requests.get(url)
                    listadocuentas = []
                    for lista in r.json():
                        listadocuentas.append([lista['id'], lista['nombre'], lista['numerocuenta'], lista['tipo']])
                    aData = {
                        'eListadoComprobante': comprobantes_serializer.data if comprobantes.exists() else {},
                        'ePersona': persona_serializer.data,
                        'listadocuentas': listadocuentas,
                        'fecha_hoy': fecha_hoy,
                        'id_matricula': int(eMatricula.id),
                        'habilitaPagoTarjeta': habilitaPagoTarjeta

                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al diferir: {ex.__str__()}', status=status.HTTP_200_OK)
            else:
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
                    # if eInscripcion.coordinacion.id != 7:
                    #     if not eInscripcion.tiene_ficha_socioeconomica_confirmada():
                    #         return Helper_Response(isSuccess=False, redirect="alu_socioecon", module_access=False, token=True, status=status.HTTP_200_OK)
                    if 'id' in payload['matricula'] and payload['matricula']['id']:
                        eMatricula = Matricula.objects.get(pk=encrypt(payload['matricula']['id']))
                        ePeriodo = eMatricula.nivel.periodo
                        if PeriodoMatricula.objects.values('id').filter(status=True, activo=True, periodo=ePeriodo).exists():
                            ePeriodoMatricula = PeriodoMatricula.objects.get(status=True, activo=True, periodo=ePeriodo)

                        # automatricula de pregrado
                        confirmar_automatricula_pregrado = eInscripcion.tiene_automatriculapregrado_por_confirmar(ePeriodo)
                        if confirmar_automatricula_pregrado:
                            if eMatricula.nivel.fechainicioagregacion > datetime.now().date():
                                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} estudiante, se informa que el proceso de aceptación de matrícula empieza {eMatricula.nivel.fechainicioagregacion.__str__()}",
                                                       status=status.HTTP_200_OK)
                            if eMatricula.nivel.fechafinagregacion < datetime.now().date():
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
                            if eMatricula.nivel.fechainicioagregacion > datetime.now().date():
                                return Helper_Response(isSuccess=False, redirect="/", module_access=False,
                                                       message=f"Estimad{'a' if ePersona.es_mujer() else 'o'} aspirante, se informa que el proceso de aceptación de matrícula empieza {eMatricula.nivel.fechainicioagregacion.__str__()}",
                                                       status=status.HTTP_200_OK)
                            if eMatricula.nivel.fechafinagregacion < datetime.now().date():
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
                    tipo = eMatricula.nivel.periodo.tipo.id if eMatricula else 0
                    eRubros = Rubro.objects.filter(persona=ePersona, status=True)
                    eRubrosMatriculas_No_Valida = eRubros.filter(Q(matricula__automatriculapregrado=True,
                                                           matricula__fechaautomatriculapregrado__isnull=False) |
                                                         Q(matricula__automatriculaadmision=True,
                                                           matricula__fechaautomatriculaadmision__isnull=False),
                                                         matricula__termino=False,
                                                         matricula__fechatermino__isnull=True)
                    if eRubrosMatriculas_No_Valida.values("id").exists():
                        eRubros = eRubros.exclude(pk__in=eRubrosMatriculas_No_Valida.values_list("id", flat=True))
                    eRubros_1 = eRubros.filter(cancelado=False, status=True).order_by('cancelado', 'fechavence')
                    eRubros_2 = eRubros.filter(cancelado=True, status=True).order_by('cancelado', '-fechavence')
                    eRubross = eRubros_1 | eRubros_2
                    eRubros_serializer = RubroSerializer(eRubross, many=True)
                    eMatricula_data = None
                    ePeriodoMatricula_data = None
                    canlespago = ''
                    if eMatricula.inscripcion.coordinacion.id == 9:
                        canlespago= './alumno/finanzas/finanzas_canalespago_admision.png'
                    else:
                        if eMatricula.inscripcion.coordinacion.id < 6:
                            canlespago = './alumno/finanzas/finanzas_canalespago.png'

                    if eMatricula:
                        eMatricula_data = MatriculaSerializer(eMatricula).data
                    if ePeriodoMatricula:
                        ePeriodoMatricula_data = PeriodoMatriculaSerializer(ePeriodoMatricula).data

                    eReportes = Reporte.objects.filter(nombre__in=['listado_deuda_xinscripcion', 'recibo_cobro', 'factura_reporte', 'tabla_amortizacion_posgrado'])
                    compromisopago = None
                    imprimircompromiso = False
                    if eMatricula:
                        fecharige = datetime.strptime('2021-03-25', '%Y-%m-%d').date()
                        if ePeriodo.inicio >= fecharige and ePeriodo.tipo.id == 3 and en_fecha_disponible():
                            imprimircompromiso = True
                            if not CompromisoPagoPosgrado.objects.filter(matricula=eMatricula, status=True, vigente=True, tipo=1).exists():
                                # Consulto el estado Compromiso Generado
                                estado = obtener_estado_solicitud(2, 1)
                                compromisopago = CompromisoPagoPosgrado(matricula=eMatricula,
                                                                        fecha=datetime.now().date(),
                                                                        tipo=1,
                                                                        vigente=True,
                                                                        estado=estado)
                                compromisopago.save(request)
                                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                            fecha=datetime.now().date(),
                                                                            observacion='COMPROMISO DE PAGO GENERADO',
                                                                            estado=estado
                                                                            )
                                recorrido.save(request)
                            compromiso = eMatricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=1)[0]
                            compromisopago = compromiso
                            if compromiso.estado.id == 14:
                                # Compromiso de pago por refinanciamiento
                                if eMatricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2).exists():
                                    compromisopago = eMatricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2)[0]
                            if compromisopago:
                                Compromiso_serializer = CompromisoPagoPosgradoRecorridoSerializer(compromisopago)

                        elif en_fecha_disponible() and ePeriodo.tipo.id == 3 and eMatricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2).exists():
                            imprimircompromiso = True
                            compromisopago = eMatricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2)[0]
                            if compromisopago:
                                Compromiso_serializer = CompromisoPagoPosgradoRecorridoSerializer(compromisopago)
                        else:
                            imprimircompromiso = False

                    estado_civil = PersonaEstadoCivil.objects.all()
                    estado_civil_seria = PersonaEstadoCivilFinanzaSerializer(estado_civil, many = True)

                    aData = {'eRubros': eRubros_serializer.data if eRubross.values("id").exists() else [],
                             'ePersona': FinanzaPersonaSerializer(ePersona).data,
                             'eReportes': ReporteSerializer(eReportes, many=True).data if eReportes.values("id").exists() else [],
                             'eMatricula': eMatricula_data,
                             'ePeriodoMatricula': ePeriodoMatricula_data,
                             'tipoperiodo': tipo,
                             'canlespago': canlespago,
                             'compromisopago': Compromiso_serializer.data if compromisopago else None,
                             'estado_civil': estado_civil_seria.data,
                             'imprimircompromiso': imprimircompromiso

                             }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)



def en_fecha_disponible():
    fechadisponible = datetime.strptime('2021-06-01', '%Y-%m-%d').date()
    fechaactual = datetime.now().date()
    return fechaactual.__ge__(fechadisponible)

def enviar_correo_notificacion(persona, estado):
    listacuentascorreo = [18]  # posgrado@unemi.edu.ec

    fechaenvio = datetime.now().date()
    horaenvio = datetime.now().time()
    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)
    tituloemail = "Carga de Documentos - Contrato de Programas de Posgrado"

    send_html_mail(tituloemail,
                   "emails/notificacion_estado_compromisopago.html",
                   {'sistema': u'Posgrado UNEMI',
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'saludo': 'Estimada' if persona.sexo.id == 1 else 'Estimado',
                    'estudiante': persona.nombre_completo_inverso(),
                    'estado': estado.valor,
                    'observaciones': '',
                    'destinatario': 'ALUMNO',
                    't': miinstitucion()
                    },
                   persona.lista_emails_envio(),
                   # ['isaltosm@unemi.edu.ec'],
                   [],
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )

    # Temporizador para evitar que se bloquee el servicio de gmail
    pausaparaemail.sleep(1)

    # Envío de e-mail de notificación a Posgrado
    lista_email_posgrado = []

    lista_email_posgrado.append('dmaciasv@unemi.edu.ec')
    lista_email_posgrado.append('smendietac@unemi.edu.ec')

    # lista_email_posgrado.append('ivan_saltos_medina@hotmail.com')
    # lista_email_posgrado.append('ivan.saltos.medina@gmail.com')

    cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

    send_html_mail(tituloemail,
                   "emails/notificacion_estado_compromisopago.html",
                   {'sistema': u'Posgrado UNEMI',
                    'fecha': fechaenvio,
                    'hora': horaenvio,
                    'saludo': 'Estimados',
                    'estudiante': persona.nombre_completo_inverso(),
                    'estado': estado.valor,
                    'genero': 'la' if persona.sexo.id == 1 else 'él',
                    'destinatario': 'POSGRADO',
                    't': miinstitucion()
                    },
                   lista_email_posgrado,
                   [],
                   cuenta=CUENTAS_CORREOS[cuenta][1]
                   )
    # Temporizador para evitar que se bloquee el servicio de gmail
    pausaparaemail.sleep(1)