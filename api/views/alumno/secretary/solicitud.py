# coding=utf-8
import json
from datetime import datetime, timedelta
from decimal import Decimal
from collections import OrderedDict, namedtuple
from django.db import transaction, connections
from operator import itemgetter
from django.contrib.contenttypes.fields import ContentType, GenericForeignKey
from django.db.models import Q
from rest_framework.pagination import PageNumberPagination, LimitOffsetPagination
from django.core.paginator import Paginator
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status, serializers
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.secretary import ServicioSerializer, CategoriaServicioSerializer, \
    SolicitudSerializer, HistorialSolicitudSerializer, RubroSerializer, PagoSerializer
from certi.models import Certificado
from sagest.models import Rubro, Partida, Pago, CuentaContable, TipoOtroRubro
from secretaria.funciones import generar_codigo_solicitud
from secretaria.models import Servicio, CategoriaServicio, Solicitud, HistorialSolicitud, SolicitudAsignatura
from sga.funciones import generar_codigo, log, generar_nombre, notificacion3, variable_valor, notificacion2
from sga.models import PerfilUsuario, Notificacion, Matricula, AsignaturaMalla, Reporte, Persona
from sga.templatetags.sga_extras import encrypt, traducir_mes
from django.core.cache import cache
from posgrado.models import ProductoSecretaria, InscripcionCohorte
from sga.reportes import run_report_v1
import os
import shutil
from settings import SITE_STORAGE
from api.helpers.functions_helper import get_variable
from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
import io
from django.core.files.base import ContentFile

class SolicitudAPIView(APIView, LimitOffsetPagination):
    permission_classes = (IsAuthenticated,)
    # pagination_class = PageNumberPagination
    default_limit = 25
    api_key_module = 'ALUMNO_SECRETARY'

    @api_security
    def post(self, request):
        if 'multipart/form-data' in request.content_type:
            eRequest = request._request.POST
            eFiles = request._request.FILES
        else:
            eRequest = request.data
        TIEMPO_ENCACHE = 60 * 15
        try:
            payload = request.auth.payload
            if cache.has_key(f"perfilprincipal_id_{payload['perfilprincipal']['id']}"):
                ePerfilUsuario = cache.get(f"perfilprincipal_id_{payload['perfilprincipal']['id']}")
            else:
                ePerfilUsuario = PerfilUsuario.objects.db_manager("sga_select").get(pk=encrypt(payload['perfilprincipal']['id']))
                cache.set(f"perfilprincipal_id_{payload['perfilprincipal']['id']}", ePerfilUsuario, TIEMPO_ENCACHE)
            if not 'action' in eRequest:
                raise NameError(u'Acción no permitida')
            action = eRequest.get('action', None)
            if not action:
                raise NameError(u'Acción no permitida')

            if action == 'addRequest':
                try:
                    if not 'product' in eRequest:
                        raise NameError(u'Producto no encontrado')
                    product = eRequest.get('product', None)
                    if product is None:
                        raise NameError(u'Producto no encontrado')
                    if not 'aData' in eRequest:
                        raise NameError(u'Parametro no encontrado')
                    aData = eRequest.get('aData', None)
                    if aData is None:
                        raise NameError(u'Producto no encontrado')
                    if product == 'certificado':
                        aData = json.loads(aData)
                        idc = encrypt(aData.get('id', encrypt(0)))
                        eCertificado = Certificado.objects.get(pk=idc)
                        eServicio = eCertificado.servicio

                        if eServicio.proceso == 8:
                            if eServicio.categoria.roles == '3':
                                obs = None
                                if 'observacion' in eRequest:
                                    obs = eRequest.get('observacion', None)
                                if not 'fileDocumento' in eFiles:
                                    raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte")
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
                                result = process_certificate(request, ePerfilUsuario, aData, nfileDocumento, obs)
                            else:
                                tipodoc = None
                                if not 'opciones' in eRequest:
                                    raise NameError(u"Por favor, seleccione una de las opciones ya sea Documento Físico o Documento con firma electrónica")
                                else:
                                    tipodoc = eRequest.get('opciones', None)

                                obs = None
                                if 'observacion' in eRequest:
                                    obs = eRequest.get('observacion', None)
                                result = process_certificate(request, ePerfilUsuario, aData, None, obs, tipodoc)
                        else:
                            result = process_certificate(request, ePerfilUsuario, aData)

                        success = result.get('success', False)
                        eSolicitud = result.get('eSolicitud', None)
                        error = result.get('error', '')
                        if not success:
                            if error == '':
                                raise NameError(u"Solicitud no se pudo procesar")
                            raise NameError(error)
                        if eSolicitud is None:
                            raise NameError(u"Solicitud no se pudo procesar")
                        return Helper_Response(isSuccess=True, data={"ids": eSolicitud.pk}, message='Se guardo correctamente solicitud', status=status.HTTP_200_OK)

                    elif product == 'titulacion':
                        aData = json.loads(aData)
                        idc = encrypt(aData.get('id', encrypt(0)))
                        result = process_titulate(request, ePerfilUsuario, aData)
                        success = result.get('success', False)
                        eSolicitud = result.get('eSolicitud', None)
                        error = result.get('error', '')
                        if not success:
                            if error == '':
                                raise NameError(u"Solicitud no se pudo procesar")
                            raise NameError(error)
                        if eSolicitud is None:
                            raise NameError(u"Solicitud no se pudo procesar")
                        return Helper_Response(isSuccess=True, data={"ids": eSolicitud.pk}, message='Se guardo correctamente solicitud', status=status.HTTP_200_OK)

                    return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'historial':
                try:
                    eSolicitud = Solicitud.objects.get(id=int(encrypt(request.data['id'])))
                    eHistorial = HistorialSolicitud.objects.filter(solicitud= eSolicitud)

                    historial_serializer = HistorialSolicitudSerializer(eHistorial, many=True)

                    aData = {
                        'eHistorial': historial_serializer.data,
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'rubrosgenerados':
                try:
                    eSolicitud = Solicitud.objects.get(id=int(request.data['id']))

                    eRubroli = []
                    eRubros = Rubro.objects.filter(status=True, solicitud=eSolicitud).order_by('-id')

                    for eRubro in eRubros:
                        eRubroli.append({
                            "id": eRubro.id,
                            "nombre": eRubro.nombre,
                            "fechavence": eRubro.fechavence,
                            "valortotal": eRubro.valortotal,
                            "total_pagado": eRubro.total_pagado(),
                            "total_adeudado": eRubro.total_adeudado(),
                            "vencido": "SI" if datetime.now().date() > eRubro.fechavence else "NO",
                            "cancelado": "SI" if eRubro.cancelado else "NO"
                        })

                    aData = {
                        'eRubros': eRubroli if len(eRubroli) > 0 else []
                    }

                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)
                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'descargacertificado':
                try:
                    eSolicitud = Solicitud.objects.get(id=int(encrypt(request.data['id'])))
                    eSolicitud.generar_certificado()

                    aData = {
                        'mensaje': 'Certificado generado correctamente, por favor descargue'
                    }


                    return Helper_Response(isSuccess=True, data=aData, message='Se generó cerfificado',status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


            elif action == 'verpagos':
                try:
                    # eSolicitud = Solicitud.objects.get(id=int(encrypt(request.data['id'])))
                    # eHistorial = HistorialSolicitud.objects.filter(id=int(encrypt(request.data['id'])))
                    #
                    # eSolicitud = eHistorial.solicitud
                    # eRubro = Rubro.objects.get(solicitud=eSolicitud)
                    # ePagos=  eRubro.pago_set.filter(status=True)
                    eHistorial = HistorialSolicitud.objects.get(id= int(encrypt(request.data['id'])))

                    content_type = ContentType.objects.get_for_model(Pago)
                    my_objects = HistorialSolicitud.objects.filter(destino_content_type=content_type)
                    historial_serializer = HistorialSolicitudSerializer(my_objects, many=True)
                    #pago_serializer = PagoSerializer(my_objects, many=True)
                    aData = {
                        #'ePagos': pago_serializer.data,
                        'eHistorial': historial_serializer.data,
                    }
                    return Helper_Response(isSuccess=True, data=aData, status=status.HTTP_200_OK)

                except Exception as ex:
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'delete':
                with transaction.atomic():
                    try:
                        if not 'id' in eRequest:
                            raise NameError(u'Solicitud no encontrado')
                        id = int(encrypt(eRequest.get('id', f"{encrypt(0)}")))
                        if not id:
                            raise NameError(u"Solicitud no encontrado")
                        eSolicitud = delete = Solicitud.objects.get(pk=id)
                        if not eSolicitud.puede_eliminar():
                            raise NameError(u"Solicitud se esta utilizando")
                        eRubros = Rubro.objects.filter(solicitud=eSolicitud, status=True)
                        historial = False
                        if eRubros.values("id").exists():
                            eRubro = eRubros.first()
                            if not eRubro.tiene_pagos():
                                #eSolicitud.anular_solicitud()
                                if eRubro.idrubroepunemi != 0:
                                    cursor = connections['epunemi'].cursor()
                                    sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (eRubro.idrubroepunemi)
                                    cursor.execute(sql)
                                    tienerubropagos = cursor.fetchone()

                                    if tienerubropagos is None:
                                        sql = """DELETE FROM sagest_rubro WHERE sagest_rubro.id=%s AND sagest_rubro.idrubrounemi=%s; """ % (eRubro.idrubroepunemi, eRubro.id)
                                        cursor.execute(sql)
                                        cursor.close()
                                eRubro.status = False
                                eRubro.save()
                                eSolicitud.estado = 8
                                eSolicitud.save()
                                historial = True
                                # eSolicitud.delete()
                                log(u'Eliminó solicitud de secretaría: %s' % delete, request, "del")
                            else:
                                raise NameError(u"La solicitud posee pagos en curso")
                                historial = True

                        if historial:
                            if eSolicitud.estado == 9:
                                observacion = u'Eliminó solicitud vencida'
                            else:
                                observacion = u'Eliminó solicitud'
                            eSolicitud.estado = 8
                            eSolicitud.en_proceso = False
                            eSolicitud.save(request)
                            log(u'Eliminó solicitud de secretaría: %s' % delete, request, "del")
                            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                     observacion=observacion,
                                                                     fecha=datetime.now().date(),
                                                                     hora=datetime.now().time(),
                                                                     estado=eSolicitud.estado,
                                                                     responsable=eSolicitud.perfil.persona,
                                                                     )
                            eHistorialSolicitud.save(request)
                        if eSolicitud.origen_object_id in [58, 59]:
                            eSolicitud.estado = 8
                            eSolicitud.en_proceso = False
                            eSolicitud.save(request)
                            observacion = u'Eliminó solicitud'

                            log(u'Eliminó solicitud de secretaría: %s' % delete, request, "del")
                            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                     observacion=observacion,
                                                                     fecha=datetime.now().date(),
                                                                     hora=datetime.now().time(),
                                                                     estado=eSolicitud.estado,
                                                                     responsable=eSolicitud.perfil.persona,
                                                                     )
                            eHistorialSolicitud.save(request)
                        eSolicitudes = Solicitud.objects.filter(status=True, perfil=ePerfilUsuario).order_by('-codigo').values("id")
                        return Helper_Response(isSuccess=True, data={"total": eSolicitudes.count()}, message='Solicitud eliminada correctamente', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al eliminar: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'generarrubro2modulos':
                with transaction.atomic():
                    try:
                        if not 'id' in eRequest:
                            raise NameError(u'Solicitud no encontrado')
                        id = int(encrypt(eRequest.get('id', f"{encrypt(0)}")))
                        if not id:
                            raise NameError(u"Solicitud no encontrado")
                        eSolicitud = Solicitud.objects.get(pk=id)
                        eProducto = ProductoSecretaria.objects.get(status=True, pk=eSolicitud.origen_object_id)
                        eTipoOtroRubro = TipoOtroRubro.objects.get(status=True, pk=3442)
                        eValor = costo_tit_ex(eSolicitud.perfil.inscripcion)
                        codigo = eSolicitud.codigo
                        descripcion = eTipoOtroRubro.nombre
                        fecha_vence = datetime.now().date() + timedelta(days=30)

                        eMatricula = Matricula.objects.filter(status=True, inscripcion=eSolicitud.perfil.inscripcion).order_by('id').first()

                        eSolicitud.estado = 14
                        eSolicitud.save(request)

                        eRubro = Rubro(tipo=eTipoOtroRubro,
                                       persona_id=eSolicitud.perfil.inscripcion.persona.pk,
                                       nombre=f'({codigo}) - {eProducto.codigo} - {descripcion}'[:299],
                                       cuota=1,
                                       tipocuota=3,
                                       fecha=datetime.now().date(),
                                       fechavence=fecha_vence,
                                       valor=eValor,
                                       iva_id=1,
                                       valoriva=0,
                                       valortotal=eValor,
                                       saldo=eValor,
                                       cancelado=False,
                                       solicitud=eSolicitud,
                                       matricula_id=eMatricula.pk)
                        eRubro.save(request)

                        # -------CREAR PERSONA EPUNEMI-------
                        cursor = connections['epunemi'].cursor()
                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                        cursor.execute(sql)
                        idalumno = cursor.fetchone()

                        if idalumno is None:
                            sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                        nacimiento, tipopersona, sector, direccion,  direccion2,
                                        num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                        anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                        regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                        tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                        acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                        idunemi)
                                                VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                FALSE, FALSE, 0); """ % (
                                eRubro.persona.nombres, eRubro.persona.apellido1,
                                eRubro.persona.apellido2, eRubro.persona.cedula,
                                eRubro.persona.ruc if eRubro.persona.ruc else '',
                                eRubro.persona.pasaporte if eRubro.persona.pasaporte else '',
                                eRubro.persona.nacimiento,
                                eRubro.persona.tipopersona if eRubro.persona.tipopersona else 1,
                                eRubro.persona.sector if eRubro.persona.sector else '',
                                eRubro.persona.direccion if eRubro.persona.direccion else '',
                                eRubro.persona.direccion2 if eRubro.persona.direccion2 else '',
                                eRubro.persona.num_direccion if eRubro.persona.num_direccion else '',
                                eRubro.persona.telefono if eRubro.persona.telefono else '',
                                eRubro.persona.telefono_conv if eRubro.persona.telefono_conv else '',
                                eRubro.persona.email if eRubro.persona.email else '')
                            cursor.execute(sql)

                            if eRubro.persona.sexo:
                                sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (eRubro.persona.sexo.id)
                                cursor.execute(sql)
                                sexo = cursor.fetchone()

                                if sexo is not None:
                                    sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.pais:
                                sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (eRubro.persona.pais.id)
                                cursor.execute(sql)
                                pais = cursor.fetchone()

                                if pais is not None:
                                    sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.parroquia:
                                sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (eRubro.persona.parroquia.id)
                                cursor.execute(sql)
                                parroquia = cursor.fetchone()

                                if parroquia is not None:
                                    sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.canton:
                                sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (eRubro.persona.canton.id)
                                cursor.execute(sql)
                                canton = cursor.fetchone()

                                if canton is not None:
                                    sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.provincia:
                                sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (eRubro.persona.provincia.id)
                                cursor.execute(sql)
                                provincia = cursor.fetchone()

                                if provincia is not None:
                                    sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], eRubro.persona.cedula)
                                    cursor.execute(sql)
                            # ID DE PERSONA EN EPUNEMI
                            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                            cursor.execute(sql)
                            idalumno = cursor.fetchone()
                            alumnoepu = idalumno[0]
                        else:
                            alumnoepu = idalumno[0]

                        # Consulto el tipo otro rubro en epunemi
                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()

                        # Si existe
                        if registro is not None:
                            tipootrorubro = registro[0]
                        else:
                            # Debo crear ese tipo de rubro
                            # Consulto centro de costo
                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (eRubro.tipo.tiporubro)
                            cursor.execute(sql)
                            centrocosto = cursor.fetchone()
                            idcentrocosto = centrocosto[0]

                            # Consulto la cuenta contable
                            cuentacontable = CuentaContable.objects.get(partida=eRubro.tipo.partida, status=True)

                            # Creo el tipo de rubro en epunemi
                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                eRubro.tipo.nombre, cuentacontable.partida.id, eRubro.tipo.valor,
                                eRubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                eRubro.tipo.id)
                            cursor.execute(sql)

                            print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                            # Obtengo el id recién creado del tipo de rubro
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            tipootrorubro = registro[0]

                        # pregunto si no existe rubro con ese id de unemi
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (eRubro.id)
                        cursor.execute(sql)
                        registrorubro = cursor.fetchone()

                        if registrorubro is None:
                            # Creo nuevo rubro en epunemi
                            sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                        valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                        idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                        valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                        titularcambiado, coactiva) 
                                      VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                  % (alumnoepu, eRubro.nombre, eRubro.cuota, eRubro.tipocuota, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                     eRubro.valoriva, eRubro.valor,
                                     eRubro.valortotal, eRubro.cancelado, eRubro.observacion, eRubro.id, tipootrorubro,
                                     eRubro.compromisopago if eRubro.compromisopago else 0,
                                     eRubro.refinanciado, eRubro.bloqueado, eRubro.coactiva)
                            cursor.execute(sql)

                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (eRubro.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            rubroepunemi = registro[0]

                            eRubro.idrubroepunemi = rubroepunemi
                            eRubro.epunemi = True
                            eRubro.save()

                            print(".:: Rubro creado en EPUNEMI ::.")
                        else:
                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (eRubro.id)
                            cursor.execute(sql)
                            rubronoc = cursor.fetchone()

                            if rubronoc is not None:
                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                cursor.execute(sql)
                                tienerubropagos = cursor.fetchone()

                                if tienerubropagos is not None:
                                    pass
                                else:
                                    sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                       valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                       valortotal = %s, observacion = '%s', tipo_id = %s
                                       WHERE id=%s; """ % (eRubro.nombre, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                                           eRubro.valoriva, eRubro.valor, eRubro.valortotal, eRubro.observacion, tipootrorubro,
                                                           registrorubro[0])
                                    cursor.execute(sql)
                                eRubro.idrubroepunemi = registrorubro[0]
                                eRubro.save()

                        eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                 observacion='Generó rubro por concepto de costo de dos módulos de titulación extraordinaria posgrado',
                                                                 fecha=datetime.now().date(),
                                                                 hora=datetime.now().time(),
                                                                 estado=eSolicitud.estado,
                                                                 responsable=eSolicitud.perfil.persona,
                                                                 )
                        eHistorialSolicitud.save(request)

                        return Helper_Response(isSuccess=True, data={}, message='Rubro generado correctamente', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al generar el rubro: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'generarsolicitudhomologacion':
                try:
                    idas = eRequest.get('idas', None)
                    idnasi = eRequest.get('idnasi', None)
                    payload = request.auth.payload
                    ePerfilUsuario = PerfilUsuario.objects.get(id=int(encrypt(payload['perfilprincipal']['id'])))
                    eInscripcion = ePerfilUsuario.inscripcion
                    hoy = datetime.now()

                    postulante = InscripcionCohorte.objects.get(status=True, inscripcion=eInscripcion)
                    eProducto = ProductoSecretaria.objects.get(pk=2)

                    eServicio = eProducto.servicio
                    valor = Decimal(eProducto.costo).quantize(Decimal('.01'))
                    eContentTypeProducto = ContentType.objects.get_for_model(eProducto)

                    result = generar_codigo_solicitud(eServicio)
                    success = result.get('success', False)
                    codigo = result.get('codigo', None)
                    secuencia = result.get('secuencia', 0)
                    suffix = result.get('suffix', None)
                    prefix = result.get('prefix', None)
                    if not success:
                        raise NameError(u"Código de solicitud no se pudo generar")
                    if codigo is None:
                        raise NameError(u"Código de solicitud no se pudo generar")
                    if secuencia == 0:
                        raise NameError(u"Secuenia del código de solicitud no se pudo generar")
                    if suffix is None:
                        raise NameError(u"Sufijo del código de solicitud no se pudo generar")
                    if prefix is None:
                        raise NameError(u"Prefijo del código de solicitud no se pudo generar")

                    eSolicitudes = Solicitud.objects.filter(status=True,
                                                            perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                                                            origen_content_type_id=eContentTypeProducto.pk,
                                                            inscripcioncohorte=postulante,
                                                            origen_object_id=eProducto.id)
                    if not eSolicitudes.values("id").exists():
                        parametros = {
                            'vqr': eInscripcion.id
                        }
                        eSolicitud = Solicitud(codigo=codigo,
                                               secuencia=secuencia,
                                               prefix=prefix,
                                               suffix=suffix,
                                               perfil_id=ePerfilUsuario.pk,
                                               servicio_id=eServicio.pk,
                                               origen_content_type=eContentTypeProducto,
                                               origen_object_id=eProducto.pk,
                                               descripcion=f'Solicitud ({codigo}) de Homologación de asignaturas Posgrado con código {eProducto.codigo} - {eProducto.descripcion}',
                                               fecha=datetime.now().date(),
                                               hora=datetime.now().time(),
                                               estado=23,
                                               cantidad=1,
                                               valor_unitario=valor,
                                               subtotal=valor,
                                               iva=0,
                                               descuento=0,
                                               en_proceso=False,
                                               parametros=parametros,
                                               tiempo_cobro=eProducto.tiempo_cobro,
                                               inscripcioncohorte=postulante)
                        eSolicitud.save(request)
                        log(u'Adicionó solicitud de homologación: %s del aspirante %s' % (eSolicitud, postulante), request, "add")

                        if len(idas) > 0:
                            for id in idas:
                                asignaturamalla = AsignaturaMalla.objects.get(status=True, pk=id)
                                if not SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, asignaturamalla=asignaturamalla).exists():
                                    eSolicitudAsig = SolicitudAsignatura(
                                        solicitud=eSolicitud,
                                        asignaturamalla=asignaturamalla,
                                        estado=1
                                    )
                                    eSolicitudAsig.save()
                                    log(u'Adicionó asignaturas de homologación: %s del aspirante %s' % (eSolicitudAsig, postulante), request, "add")

                    else:
                        eSolicitud = Solicitud.objects.filter(status=True,
                                                              perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk,
                                                              origen_content_type_id=eContentTypeProducto.pk,
                                                              inscripcioncohorte=postulante,
                                                              origen_object_id=eProducto.id).first()

                        if len(idas) > 0:
                            for id in idas:
                                asignaturamalla = AsignaturaMalla.objects.get(status=True, pk=id)
                                if not SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, asignaturamalla=asignaturamalla).exists():
                                    eSolicitudAsig = SolicitudAsignatura(
                                        solicitud=eSolicitud,
                                        asignaturamalla=asignaturamalla,
                                        estado=1
                                    )
                                    eSolicitudAsig.save()
                                    log(u'Adicionó asignaturas de homologación: %s del aspirante %s' % (eSolicitudAsig, postulante), request, "add")

                        if len(idnasi) > 0:
                            for id in idnasi:
                                asignaturamalla = AsignaturaMalla.objects.get(status=True, pk=id)
                                if SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, asignaturamalla=asignaturamalla).exists():
                                    eSolicitudAsig = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud, asignaturamalla=asignaturamalla).first()
                                    eSolicitudAsig.status = False
                                    eSolicitudAsig.save()

                    tipo = 'pdf'
                    paRequest = {
                        'idins': eSolicitud.id,
                    }

                    reporte = Reporte.objects.get(id=668)

                    d = run_report_v1(reporte=reporte, tipo=tipo, paRequest=paRequest, request=request)

                    if not d['isSuccess']:
                        raise NameError('Ocurrió un error en la generación de la solicitud.')
                    else:
                        url_archivo = (SITE_STORAGE + d['data']['reportfile']).replace('\\', '/')
                        url_archivo = (url_archivo).replace('//', '/')
                        _name = generar_nombre(f'soli_hp_{request.user.username}_{eSolicitud.id}_', 'descargado')
                        folder = os.path.join(SITE_STORAGE, 'media', 'archivohomologaciondescargado', '')

                        if not os.path.exists(folder):
                            os.makedirs(folder)
                        folder_save = os.path.join('archivohomologaciondescargado', '').replace('\\', '/')
                        url_file_generado = f'{folder_save}{_name}.pdf'
                        ruta_creacion = SITE_STORAGE
                        ruta_creacion = ruta_creacion.replace('\\', '/')
                        shutil.copy(url_archivo, ruta_creacion + '/media/' + url_file_generado)

                        eSolicitud.archivo_solicitud = url_file_generado
                        if eSolicitud.archivo_respuesta:
                            eSolicitud.archivo_respuesta = ''
                        eSolicitud.estado = 23
                        eSolicitud.save(request)

                        obs = f'Archivo de solicitud generado - Asignaturas seleccionadas: {eSolicitud.lista_asignaturas_nombres()}'
                        if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud):
                            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                     observacion=obs,
                                                                     fecha=hoy.date(),
                                                                     hora=hoy.time(),
                                                                     estado=eSolicitud.estado,
                                                                     responsable=eSolicitud.inscripcioncohorte.inscripcionaspirante.persona,
                                                                     archivo=eSolicitud.archivo_solicitud)
                            eHistorialSolicitud.save(request)
                        else:
                            histo = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud).first()
                            histo.fecha = hoy.date()
                            histo.hora = hoy.time()
                            histo.observacion = obs
                            histo.archivo = eSolicitud.archivo_solicitud
                            histo.save(request)

                        mensaje = 'Su archivo de solicitud de homologación ha sido realizada correctamente.'

                        urlbase = get_variable('SITE_URL_SGA')
                        reportfile = f"{urlbase}{eSolicitud.archivo_solicitud.url}"
                        aData = {'reportfile': reportfile}
                        return Helper_Response(isSuccess=True, data=aData, message=mensaje, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al generar la solicitud: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'firmarsolicitudhomologacion':
                try:
                    id_soli = eRequest.get('id_soli', None)
                    hoy = datetime.now()
                    ida = int(variable_valor('ID_USER_A'))
                    certificado = eFiles['eFileSolicitudForm']
                    contrasenaCertificado = eRequest.get('ePassword', None)
                    extension_certificado = os.path.splitext(certificado.name)[1][1:]
                    bytes_certificado = certificado.read()

                    eSolicitud = Solicitud.objects.get(status=True, pk=id_soli)
                    name_file = f'soliciud_hi_firmada{id_soli}.pdf'

                    texto = 'C.I.'
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(eSolicitud.archivo_solicitud.url, texto)
                    datau = JavaFirmaEc(
                        archivo_a_firmar=eSolicitud.archivo_solicitud, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(numpaginafirma), reason='', lx=x + 5, ly=y + 10
                    )

                    if datau.datos_del_certificado['cedula'] == eSolicitud.perfil.inscripcion.persona.cedula or ida == 38472:
                        documento_a_firmar = io.BytesIO()
                        documento_a_firmar.write(datau.sign_and_get_content_bytes())
                        documento_a_firmar.seek(0)
                        eSolicitud.archivo_respuesta.save(f'{name_file.replace(".pdf", "")}_firmado.pdf',
                                                      ContentFile(documento_a_firmar.read()))

                        eSolicitud.estado = 1
                        eSolicitud.fecha = hoy.date()
                        eSolicitud.hora = hoy.time()
                        eSolicitud.firmadoec = True
                        eSolicitud.save(request)

                        if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=1):
                            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                     observacion='Su archivo de solicitud de homologación interna ha sido firmado correctamente.',
                                                                     fecha=hoy.date(),
                                                                     hora=hoy.time(),
                                                                     estado=eSolicitud.estado,
                                                                     responsable=eSolicitud.perfil.inscripcion.persona,
                                                                     archivo=eSolicitud.archivo_respuesta)
                            eHistorialSolicitud.save(request)
                        else:
                            eHistorialSolicitud = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=1).first()
                            eHistorialSolicitud.fecha = hoy.date()
                            eHistorialSolicitud.hora = hoy.time()
                            eHistorialSolicitud.archivo = eSolicitud.archivo_respuesta
                            eHistorialSolicitud.save(request)

                        titulo = "SOLICITUD DE HOMOLOGACIÓN INTERNA VALIDADA"

                        cuerpo = f"Se informa al coordinador del programa de {eSolicitud.inscripcioncohorte.cohortes.maestriaadmision.carrera} que el solicitante {eSolicitud.perfil.persona} ha firmado correctamente su archivo de solicitud de homologación interna de Posgrado. Por favor, realizar el proceso respectivo (Informe, Ficha de homologación)."

                        notificacion2(titulo, cuerpo, eSolicitud.inscripcioncohorte.cohortes.coordinador, None,
                                      '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo), eSolicitud.inscripcioncohorte.cohortes.coordinador.pk, 1, 'sga',
                                      eSolicitud.inscripcioncohorte.cohortes.coordinador)

                        mensaje = 'Su archivo de solicitud de homologación interna ha sido firmado correctamente.'
                        urlbase = get_variable('SITE_URL_SGA')
                        reportfile = f"{urlbase}{eSolicitud.archivo_respuesta.url}"
                        aData = {'reportfile': reportfile}
                        return Helper_Response(isSuccess=True, data=aData, message=mensaje, status=status.HTTP_200_OK)
                    else:
                        mensaje = f'La firma utilizada para firmar el archivo de <b>solicitud de homologación interna</b> no corresponde al inscrito <b>{eSolicitud.perfil.inscripcion.persona.__str__()}</b>. El archivo debe ser firmado exclusivamente con la firma electrónica del inscrito, y no con la de terceros.'
                        # urlbase = get_variable('SITE_URL_SGA')
                        # reportfile = f"{urlbase}{eSolicitud.archivo_respuesta.url}"
                        aData = {}
                        return Helper_Response(isSuccess=False, data=aData, message=mensaje, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={},
                                           message=f'Ocurrio un error al generar la solicitud: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'subirsolicitudhomologacion':
                try:
                    id_soli = eRequest.get('id_soli', None)
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

                    nfileDocumento._name = generar_nombre("soliciud_hi_firmada_s", nfileDocumento._name)

                    eSolicitud = Solicitud.objects.get(status=True, pk=id_soli)
                    eSolicitud.archivo_respuesta = nfileDocumento
                    eSolicitud.estado = 1
                    eSolicitud.fecha = hoy.date()
                    eSolicitud.hora = hoy.time()
                    eSolicitud.save(request)

                    if not HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=1):
                        eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                 observacion='Su archivo de solicitud de homologación interna ha sido subido correctamente. Se verificará la validez del documento firmado.',
                                                                 fecha=hoy.date(),
                                                                 hora=hoy.time(),
                                                                 estado=eSolicitud.estado,
                                                                 responsable=eSolicitud.perfil.inscripcion.persona,
                                                                 archivo=eSolicitud.archivo_respuesta)
                        eHistorialSolicitud.save(request)
                    else:
                        eHistorialSolicitud = HistorialSolicitud.objects.filter(status=True, solicitud=eSolicitud, estado=1).first()
                        eHistorialSolicitud.fecha = hoy.date()
                        eHistorialSolicitud.hora = hoy.time()
                        eHistorialSolicitud.save(request)

                    titulo = "ARCHIVO DE HOMOLOGACIÓN INTERNA SUBIDO"
                    secretaria = Persona.objects.get(id=variable_valor('ENCARGADA_ADMISION'), status=True)

                    cuerpo3 = f"Se informa a la encargada de admisión que el solicitante {eSolicitud.perfil.persona} ha subido el archivo de solicitud de homologación interna posgrado firmado. Por favor, validar que el archivo este correctamente firmado."

                    notificacion2(titulo, cuerpo3, secretaria, None, '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo), secretaria.pk, 1, 'sga', secretaria)

                    mensaje = 'Su archivo de solicitud de homologación interna ha sido subido correctamente. En caso de que la firma no pertenezca al inscrito, tendrá que volver a subir el archivo o firmarlo, de lo contrario no podrá avanzar en el proceso.'
                    urlbase = get_variable('SITE_URL_SGA')
                    reportfile = f"{urlbase}{eSolicitud.archivo_respuesta.url}"
                    aData = {'reportfile': reportfile}
                    return Helper_Response(isSuccess=True, data=aData, message=mensaje, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={},
                                           message=f'Ocurrio un error al generar la solicitud: {ex.__str__()}',
                                           status=status.HTTP_200_OK)

            elif action == 'deletesolicitud':
                try:
                    eSolicitud = Solicitud.objects.get(status=True, pk=int(eRequest.get('id', None)))

                    if Rubro.objects.filter(status=True, solicitud=eSolicitud).exists():
                        eRubros = Rubro.objects.filter(status=True, solicitud=eSolicitud)
                        for eRubro in eRubros:
                            cursor = connections['epunemi'].cursor()
                            sql1 = """SELECT deta.id FROM crm_detallepedidoonline deta 
                                        INNER JOIN crm_pedidoonline pedi ON deta.pedido_id = pedi.id
                                        WHERE deta.rubro_id = %s AND deta."status" AND pedi."status"
                                        AND pedi.estado IN (1, 2);""" % (eRubro.idrubroepunemi)
                            cursor.execute(sql1)
                            idpedi = cursor.fetchone()

                            if idpedi is None:
                                sql = "UPDATE sagest_rubro SET status=FALSE WHERE sagest_rubro.status= true and sagest_rubro.id= %s" % (eRubro.idrubroepunemi)
                                cursor.execute(sql)
                                cursor.close()

                                eRubro.status = False
                                eRubro.save(request)
                            else:
                                return Helper_Response(isSuccess=False, data={}, message=f'No puede eliminar su solicitud porque ha realizado un pago', status=status.HTTP_200_OK)

                    if SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud).exists():
                        eSolicitudAsignatura = SolicitudAsignatura.objects.filter(status=True, solicitud=eSolicitud)
                        for eSolicitudAsi in eSolicitudAsignatura:
                            eSolicitudAsi.status = False
                            eSolicitudAsi.save()

                    observacion = u'Eliminó solicitud'

                    log(u'Eliminó solicitud de secretaría: %s' % eSolicitud, request, "del")
                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=observacion,
                                                             fecha=datetime.now().date(),
                                                             hora=datetime.now().time(),
                                                             estado=8,
                                                             responsable=eSolicitud.perfil.persona,
                                                             )
                    eHistorialSolicitud.save(request)

                    eSolicitud.estado = 8
                    eSolicitud.status = False
                    eSolicitud.save(request)

                    mensaje = 'Solicitud eliminada correctamente'
                    aData = {}
                    return Helper_Response(isSuccess=True, data=aData, message=mensaje, status=status.HTTP_200_OK)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al eliminar: {ex.__str__()}', status=status.HTTP_200_OK)

            elif action == 'generarrubrohomologacion':
                with transaction.atomic():
                    try:
                        if not 'id' in eRequest:
                            raise NameError(u'Solicitud no encontrado')
                        # id = int(encrypt(eRequest.get('id', f"{encrypt(0)}")))
                        # if not id:
                        #     raise NameError(u"Solicitud no encontrado")
                        eSolicitud = Solicitud.objects.get(pk=eRequest.get('id'))
                        eProducto = ProductoSecretaria.objects.get(status=True, pk=eSolicitud.origen_object_id)
                        eTipoOtroRubro = TipoOtroRubro.objects.get(status=True, pk=eSolicitud.servicio.tiporubro.id)
                        codigo = eSolicitud.codigo
                        descripcion = eTipoOtroRubro.nombre
                        fecha_vence = datetime.now().date() + timedelta(hours=eProducto.tiempo_cobro)
                        # fecha_vence = eSolicitud.fecha + timedelta(hours=eProducto.tiempo_cobro)

                        eMatricula = Matricula.objects.filter(status=True, inscripcion=eSolicitud.perfil.inscripcion).order_by('id').first()

                        eSolicitud.estado = 25
                        eSolicitud.save(request)

                        if not Rubro.objects.filter(status=True, tipo=eTipoOtroRubro, solicitud=eSolicitud, persona=eSolicitud.perfil.persona).exists():
                            eRubro = Rubro(tipo=eTipoOtroRubro,
                                           persona_id=eSolicitud.perfil.inscripcion.persona.pk,
                                           nombre=f'({codigo}) - {eProducto.codigo} - {descripcion}'[:299],
                                           cuota=1,
                                           tipocuota=3,
                                           fecha=datetime.now().date(),
                                           fechavence=fecha_vence,
                                           valor=eSolicitud.servicio.costo,
                                           iva_id=1,
                                           valoriva=0,
                                           valortotal=eSolicitud.servicio.costo,
                                           saldo=eSolicitud.servicio.costo,
                                           cancelado=False,
                                           solicitud=eSolicitud,
                                           matricula_id=eMatricula.pk if eMatricula else None)
                            eRubro.save(request)

                            # -------CREAR PERSONA EPUNEMI-------
                            cursor = connections['epunemi'].cursor()
                            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                            cursor.execute(sql)
                            idalumno = cursor.fetchone()

                            if idalumno is None:
                                sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                            nacimiento, tipopersona, sector, direccion,  direccion2,
                                            num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                            anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                            regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                            tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                            acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                            idunemi)
                                                    VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                    FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                    FALSE, FALSE, 0); """ % (
                                    eRubro.persona.nombres, eRubro.persona.apellido1,
                                    eRubro.persona.apellido2, eRubro.persona.cedula,
                                    eRubro.persona.ruc if eRubro.persona.ruc else '',
                                    eRubro.persona.pasaporte if eRubro.persona.pasaporte else '',
                                    eRubro.persona.nacimiento,
                                    eRubro.persona.tipopersona if eRubro.persona.tipopersona else 1,
                                    eRubro.persona.sector if eRubro.persona.sector else '',
                                    eRubro.persona.direccion if eRubro.persona.direccion else '',
                                    eRubro.persona.direccion2 if eRubro.persona.direccion2 else '',
                                    eRubro.persona.num_direccion if eRubro.persona.num_direccion else '',
                                    eRubro.persona.telefono if eRubro.persona.telefono else '',
                                    eRubro.persona.telefono_conv if eRubro.persona.telefono_conv else '',
                                    eRubro.persona.email if eRubro.persona.email else '')
                                cursor.execute(sql)

                                if eRubro.persona.sexo:
                                    sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (eRubro.persona.sexo.id)
                                    cursor.execute(sql)
                                    sexo = cursor.fetchone()

                                    if sexo is not None:
                                        sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], eRubro.persona.cedula)
                                        cursor.execute(sql)

                                if eRubro.persona.pais:
                                    sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (eRubro.persona.pais.id)
                                    cursor.execute(sql)
                                    pais = cursor.fetchone()

                                    if pais is not None:
                                        sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], eRubro.persona.cedula)
                                        cursor.execute(sql)

                                if eRubro.persona.parroquia:
                                    sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (eRubro.persona.parroquia.id)
                                    cursor.execute(sql)
                                    parroquia = cursor.fetchone()

                                    if parroquia is not None:
                                        sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], eRubro.persona.cedula)
                                        cursor.execute(sql)

                                if eRubro.persona.canton:
                                    sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (eRubro.persona.canton.id)
                                    cursor.execute(sql)
                                    canton = cursor.fetchone()

                                    if canton is not None:
                                        sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], eRubro.persona.cedula)
                                        cursor.execute(sql)

                                if eRubro.persona.provincia:
                                    sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (eRubro.persona.provincia.id)
                                    cursor.execute(sql)
                                    provincia = cursor.fetchone()

                                    if provincia is not None:
                                        sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], eRubro.persona.cedula)
                                        cursor.execute(sql)
                                # ID DE PERSONA EN EPUNEMI
                                sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                                cursor.execute(sql)
                                idalumno = cursor.fetchone()
                                alumnoepu = idalumno[0]
                            else:
                                alumnoepu = idalumno[0]

                            # Consulto el tipo otro rubro en epunemi
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()

                            # Si existe
                            if registro is not None:
                                tipootrorubro = registro[0]
                            else:
                                # Debo crear ese tipo de rubro
                                # Consulto centro de costo
                                sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (eRubro.tipo.tiporubro)
                                cursor.execute(sql)
                                centrocosto = cursor.fetchone()
                                idcentrocosto = centrocosto[0]

                                # Consulto la cuenta contable
                                cuentacontable = CuentaContable.objects.get(partida=eRubro.tipo.partida, status=True)

                                # Creo el tipo de rubro en epunemi
                                sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                    VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                    eRubro.tipo.nombre, cuentacontable.partida.id, eRubro.tipo.valor,
                                    eRubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                    eRubro.tipo.id)
                                cursor.execute(sql)

                                print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                                # Obtengo el id recién creado del tipo de rubro
                                sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                                cursor.execute(sql)
                                registro = cursor.fetchone()
                                tipootrorubro = registro[0]

                            # pregunto si no existe rubro con ese id de unemi
                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (eRubro.id)
                            cursor.execute(sql)
                            registrorubro = cursor.fetchone()

                            if registrorubro is None:
                                # Creo nuevo rubro en epunemi
                                sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                            valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                            idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                            valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                            titularcambiado, coactiva) 
                                          VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                      % (alumnoepu, eRubro.nombre, eRubro.cuota, eRubro.tipocuota, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                         eRubro.valoriva, eRubro.valor,
                                         eRubro.valortotal, eRubro.cancelado, eRubro.observacion, eRubro.id, tipootrorubro,
                                         eRubro.compromisopago if eRubro.compromisopago else 0,
                                         eRubro.refinanciado, eRubro.bloqueado, eRubro.coactiva)
                                cursor.execute(sql)

                                sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (eRubro.id)
                                cursor.execute(sql)
                                registro = cursor.fetchone()
                                rubroepunemi = registro[0]

                                eRubro.idrubroepunemi = rubroepunemi
                                eRubro.epunemi = True
                                eRubro.save()

                                print(".:: Rubro creado en EPUNEMI ::.")
                            else:
                                sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (eRubro.id)
                                cursor.execute(sql)
                                rubronoc = cursor.fetchone()

                                if rubronoc is not None:
                                    sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                    cursor.execute(sql)
                                    tienerubropagos = cursor.fetchone()

                                    if tienerubropagos is not None:
                                        pass
                                    else:
                                        sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                           valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                           valortotal = %s, observacion = '%s', tipo_id = %s
                                           WHERE id=%s; """ % (eRubro.nombre, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                                               eRubro.valoriva, eRubro.valor, eRubro.valortotal, eRubro.observacion, tipootrorubro,
                                                               registrorubro[0])
                                        cursor.execute(sql)
                                    eRubro.idrubroepunemi = registrorubro[0]
                                    eRubro.save()

                            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                                     observacion='Generó rubro por concepto de pago de asignaturas favorables de homologación interna de Posgrado.',
                                                                     fecha=datetime.now().date(),
                                                                     hora=datetime.now().time(),
                                                                     estado=eSolicitud.estado,
                                                                     responsable=eSolicitud.perfil.persona,
                                                                     )
                            eHistorialSolicitud.save(request)
                            return Helper_Response(isSuccess=True, data={}, message='Rubro generado correctamente', status=status.HTTP_200_OK)
                        else:
                            return Helper_Response(isSuccess=False, data={}, message='Usted ya ha generado el rubro', status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error al generar el rubro: {ex.__str__()}', status=status.HTTP_200_OK)

            return Helper_Response(isSuccess=False, data={}, message=f'Acciòn no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)

    @api_security
    def get(self, request):
        try:
            payload = request.auth.payload
            ePerfilUsuario = PerfilUsuario.objects.get(pk=encrypt(payload['perfilprincipal']['id']))
            eInscripcion = ePerfilUsuario.inscripcion
            habilitaPagoTarjeta = False
            if eInscripcion.coordinacion.id == 7:
                habilitaPagoTarjeta = True

            if not ePerfilUsuario.es_estudiante():
                raise NameError(u'Solo los perfiles de estudiantes pueden ingresar al modulo.')
            action = None
            if 'action' in request.query_params:
                action = request.query_params['action']
            if action == 'validateInitLoad':
                return Helper_Response(isSuccess=True, data={
                'habilitaPagoTarjeta': habilitaPagoTarjeta}, status=status.HTTP_200_OK)
            eSolicitudes = Solicitud.objects.filter(status=True, perfil=ePerfilUsuario).order_by('-id')
            if 'search' in request.query_params and request.query_params['search']:
                search = request.query_params['search']
                eSolicitudes = eSolicitudes.filter(Q(codigo__icontains=search) | Q(descripcion__icontains=search))
            results = self.paginate_queryset(eSolicitudes, request, view=self)
            serializer = SolicitudSerializer(results, many=True)
            data = {
                'count':  self.count,
                'next':  self.get_next_link(),
                'previous':  self.get_previous_link(),
                'eSolicitudes':  serializer.data if eSolicitudes.values("id").exists() else [],
            }
            return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)


def process_certificate(request, ePerfilUsuario, aData, ArchivoF=None, Obs=None, Tipodoc=None):
    from sga.models import Persona
    from sga.funciones import variable_valor, notificacion2
    with transaction.atomic():
        try:
            eInscripcion = ePerfilUsuario.inscripcion
            eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
            ePersona = ePerfilUsuario.persona
            idc = encrypt(aData.get('id', encrypt(0)))
            ids = encrypt(aData.get('ids', encrypt(0)))
            parametros = aData.get('parametros', {})
            eCertificado = Certificado.objects.get(pk=idc)
            eServicio = eCertificado.servicio
            valor = Decimal(eCertificado.costo).quantize(Decimal('.01'))
            # fecha_vence = datetime.now().date() + timedelta(days=30)
            eTipoOtroRubro = eServicio.tiporubro
            eContentTypeCertificado = ContentType.objects.get_for_model(eCertificado)
            eSolicitudes = Solicitud.objects.filter(Q(en_proceso=True) | Q(estado__in=[1]), status=True, perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk, origen_content_type_id=eContentTypeCertificado.pk, origen_object_id=idc).exclude(servicio__proceso=8)
            if eSolicitudes.values("id").exists():
                raise NameError(u"Existe una solicitud en proceso.")
            result = generar_codigo_solicitud(eServicio)
            success = result.get('success', False)
            codigo = result.get('codigo', None)
            secuencia = result.get('secuencia', 0)
            suffix = result.get('suffix', None)
            prefix = result.get('prefix', None)
            if not success:
                raise NameError(u"Código de solicitud no se pudo generar")
            if codigo is None:
                raise NameError(u"Código de solicitud no se pudo generar")
            if secuencia == 0:
                raise NameError(u"Secuenia del código de solicitud no se pudo generar")
            if suffix is None:
                raise NameError(u"Sufijo del código de solicitud no se pudo generar")
            if prefix is None:
                raise NameError(u"Prefijo del código de solicitud no se pudo generar")
            eSolicitud = Solicitud(codigo=codigo,
                                   secuencia=secuencia,
                                   prefix=prefix,
                                   suffix=suffix,
                                   perfil_id=ePerfilUsuario.pk,
                                   servicio_id=eServicio.pk,
                                   origen_content_type=eContentTypeCertificado,
                                   origen_object_id=eCertificado.pk,
                                   descripcion=f'Solicitud ({codigo}) del Certificado académico con código {eCertificado.codigo} - {eCertificado.certificacion}',
                                   fecha=datetime.now().date(),
                                   hora=datetime.now().time(),
                                   estado=1,
                                   cantidad=1,
                                   valor_unitario=valor,
                                   subtotal=valor,
                                   iva=0,
                                   descuento=0,
                                   en_proceso=False,
                                   parametros=parametros,
                                   tiempo_cobro=eCertificado.tiempo_cobro)
            eSolicitud.save(request)
            fecha_vence = eSolicitud.fecha + timedelta(hours=eSolicitud.tiempo_cobro)

            if eSolicitud.servicio.categoria.id in [4, 5]:
                if eInscripcion.graduado() or eInscripcion.egresado() or eInscripcion.estado_gratuidad != 3:
                    financieros = Persona.objects.filter(id__in=variable_valor('NOTIFICAR_FINANCIERO'), status=True)
                    area = ''
                    if eSolicitud.servicio.categoria.id == 4:
                        area = 'PREGRADO'
                    if eSolicitud.servicio.categoria.id == 5:
                        area = 'NIVELACIÓN'

                    for financiero in financieros:
                        titulo = f'SOLICITUD DE CERTIFICADO DE {area}'
                        cuerpo = f'Se informa al departamento financiero que existe una solicitud de certificado del maestrante {eSolicitud.perfil.persona}'

                        notificacion2(titulo, cuerpo, financiero, None, '/rec_bancopacifico', financiero.pk, 1, 'sagest', financiero)

            if eServicio.proceso == 8 and ArchivoF:
                eSolicitud.archivo_solicitud_fisica = ArchivoF
                eSolicitud.save(request)

            if Tipodoc:
                if Tipodoc == 'opcion1':
                    eSolicitud.tipodocumento = 2
                    eSolicitud.save(request)
                elif Tipodoc == 'opcion2':
                    eSolicitud.tipodocumento = 3
                    eSolicitud.save(request)

            if eCertificado.costo > 0:
                if eCoordinacion.id != 7:
                    if not eInscripcion.graduado():
                        print('no graduado')
                        if not eInscripcion.egresado():
                            print('no egresado')
                            if ePerfilUsuario.inscripcion.estado_gratuidad != 3:
                                #eServicio.costo = 0
                                eSolicitud.valor_unitatio = 0
                                eSolicitud.subtotal = eSolicitud.valor_unitario
                                eSolicitud.save()
                                #eServicio.save()
                                #eCertificado.save()

                            else:
                                eRubro = Rubro(tipo=eTipoOtroRubro,
                                               persona_id=ePersona.pk,
                                               nombre=f'({codigo}) - Certificado académico - {eCertificado.codigo} - {eCertificado.certificacion}'[:299],
                                               cuota=1,
                                               tipocuota=3,
                                               fecha=datetime.now().date(),
                                               fechavence=fecha_vence,
                                               valor=valor,
                                               iva_id=1,
                                               valoriva=0,
                                               valortotal=valor,
                                               saldo=valor,
                                               cancelado=False,
                                               solicitud=eSolicitud)
                                eRubro.save(request)
                        else:
                            eRubro = Rubro(tipo=eTipoOtroRubro,
                                           persona_id=ePersona.pk,
                                           nombre=f'({codigo}) - Certificado académico - {eCertificado.codigo} - {eCertificado.certificacion}'[:299],
                                           cuota=1,
                                           tipocuota=3,
                                           fecha=datetime.now().date(),
                                           fechavence=fecha_vence,
                                           valor=valor,
                                           iva_id=1,
                                           valoriva=0,
                                           valortotal=valor,
                                           saldo=valor,
                                           cancelado=False,
                                           solicitud=eSolicitud)
                            eRubro.save(request)
                    else:
                        eRubro = Rubro(tipo=eTipoOtroRubro,
                                       persona_id=ePersona.pk,
                                       nombre=f'({codigo}) - Certificado académico - {eCertificado.codigo} - {eCertificado.certificacion}'[:299],
                                       cuota=1,
                                       tipocuota=3,
                                       fecha=datetime.now().date(),
                                       fechavence=fecha_vence,
                                       valor=valor,
                                       iva_id=1,
                                       valoriva=0,
                                       valortotal=valor,
                                       saldo=valor,
                                       cancelado=False,
                                       solicitud=eSolicitud)
                        eRubro.save(request)
                else:
                    eMatricula = Matricula.objects.filter(status=True, inscripcion=eSolicitud.perfil.inscripcion).order_by('id').first()

                    eRubro = Rubro(tipo=eTipoOtroRubro,
                                   persona_id=ePersona.pk,
                                   nombre=f'({codigo}) - Certificado académico - {eCertificado.codigo} - {eCertificado.certificacion}'[:299],
                                   cuota=1,
                                   tipocuota=3,
                                   fecha=datetime.now().date(),
                                   fechavence=fecha_vence,
                                   valor=valor,
                                   iva_id=1,
                                   valoriva=0,
                                   valortotal=valor,
                                   saldo=valor,
                                   cancelado=False,
                                   solicitud=eSolicitud,
                                   matricula_id=eMatricula.pk if eMatricula else None)
                    eRubro.save(request)

                    if eRubro.tipo.tiporubro == 1:
                        # -------CREAR PERSONA EPUNEMI-------
                        cursor = connections['epunemi'].cursor()
                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                        cursor.execute(sql)
                        idalumno = cursor.fetchone()

                        if idalumno is None:
                            sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                        nacimiento, tipopersona, sector, direccion,  direccion2,
                                        num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                        anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                        regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                        tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                        acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                        idunemi)
                                                VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                                FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                                FALSE, FALSE, 0); """ % (
                                eRubro.persona.nombres, eRubro.persona.apellido1,
                                eRubro.persona.apellido2, eRubro.persona.cedula,
                                eRubro.persona.ruc if eRubro.persona.ruc else '',
                                eRubro.persona.pasaporte if eRubro.persona.pasaporte else '',
                                eRubro.persona.nacimiento,
                                eRubro.persona.tipopersona if eRubro.persona.tipopersona else 1,
                                eRubro.persona.sector if eRubro.persona.sector else '',
                                eRubro.persona.direccion if eRubro.persona.direccion else '',
                                eRubro.persona.direccion2 if eRubro.persona.direccion2 else '',
                                eRubro.persona.num_direccion if eRubro.persona.num_direccion else '',
                                eRubro.persona.telefono if eRubro.persona.telefono else '',
                                eRubro.persona.telefono_conv if eRubro.persona.telefono_conv else '',
                                eRubro.persona.email if eRubro.persona.email else '')
                            cursor.execute(sql)

                            if eRubro.persona.sexo:
                                sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (eRubro.persona.sexo.id)
                                cursor.execute(sql)
                                sexo = cursor.fetchone()

                                if sexo is not None:
                                    sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.pais:
                                sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (eRubro.persona.pais.id)
                                cursor.execute(sql)
                                pais = cursor.fetchone()

                                if pais is not None:
                                    sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.parroquia:
                                sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (eRubro.persona.parroquia.id)
                                cursor.execute(sql)
                                parroquia = cursor.fetchone()

                                if parroquia is not None:
                                    sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.canton:
                                sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (eRubro.persona.canton.id)
                                cursor.execute(sql)
                                canton = cursor.fetchone()

                                if canton is not None:
                                    sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], eRubro.persona.cedula)
                                    cursor.execute(sql)

                            if eRubro.persona.provincia:
                                sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (eRubro.persona.provincia.id)
                                cursor.execute(sql)
                                provincia = cursor.fetchone()

                                if provincia is not None:
                                    sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], eRubro.persona.cedula)
                                    cursor.execute(sql)
                            # ID DE PERSONA EN EPUNEMI
                            sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                            cursor.execute(sql)
                            idalumno = cursor.fetchone()
                            alumnoepu = idalumno[0]
                        else:
                            alumnoepu = idalumno[0]

                        # Consulto el tipo otro rubro en epunemi
                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()

                        # Si existe
                        if registro is not None:
                            tipootrorubro = registro[0]
                        else:
                            # Debo crear ese tipo de rubro
                            # Consulto centro de costo
                            sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (eRubro.tipo.tiporubro)
                            cursor.execute(sql)
                            centrocosto = cursor.fetchone()
                            idcentrocosto = centrocosto[0]

                            # Consulto la cuenta contable
                            cuentacontable = CuentaContable.objects.get(partida=eRubro.tipo.partida, status=True)

                            # Creo el tipo de rubro en epunemi
                            sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                                VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                                eRubro.tipo.nombre, cuentacontable.partida.id, eRubro.tipo.valor,
                                eRubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                                eRubro.tipo.id)
                            cursor.execute(sql)

                            print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                            # Obtengo el id recién creado del tipo de rubro
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            tipootrorubro = registro[0]

                        # pregunto si no existe rubro con ese id de unemi
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (eRubro.id)
                        cursor.execute(sql)
                        registrorubro = cursor.fetchone()

                        if registrorubro is None:
                            # Creo nuevo rubro en epunemi
                            sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                        valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                        idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                        valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                        titularcambiado, coactiva) 
                                      VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                                  % (alumnoepu, eRubro.nombre, eRubro.cuota, eRubro.tipocuota, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                     eRubro.valoriva, eRubro.valor,
                                     eRubro.valortotal, eRubro.cancelado, eRubro.observacion, eRubro.id, tipootrorubro,
                                     eRubro.compromisopago if eRubro.compromisopago else 0,
                                     eRubro.refinanciado, eRubro.bloqueado, eRubro.coactiva)
                            cursor.execute(sql)

                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (eRubro.id)
                            cursor.execute(sql)
                            registro = cursor.fetchone()
                            rubroepunemi = registro[0]

                            eRubro.idrubroepunemi = rubroepunemi
                            eRubro.epunemi = True
                            eRubro.save()

                            print(".:: Rubro creado en EPUNEMI ::.")
                        else:
                            sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (eRubro.id)
                            cursor.execute(sql)
                            rubronoc = cursor.fetchone()

                            if rubronoc is not None:
                                sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                                cursor.execute(sql)
                                tienerubropagos = cursor.fetchone()

                                if tienerubropagos is not None:
                                    pass
                                else:
                                    sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                       valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                       valortotal = %s, observacion = '%s', tipo_id = %s
                                       WHERE id=%s; """ % (eRubro.nombre, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                                           eRubro.valoriva, eRubro.valor, eRubro.valortotal, eRubro.observacion, tipootrorubro,
                                                           registrorubro[0])
                                    cursor.execute(sql)
                                eRubro.idrubroepunemi = registrorubro[0]
                                eRubro.save()

            if eServicio.proceso == 8:
                observa = ''
                ti = 0
                if Obs == 'undefined':
                    observa = eSolicitud.descripcion
                else:
                    observa = Obs

                if Tipodoc:
                    if Tipodoc == 'opcion1':
                        ti = 2
                    elif Tipodoc == 'opcion2':
                        ti = 3

                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=observa,
                                                             fecha=eSolicitud.fecha,
                                                             hora=eSolicitud.hora,
                                                             estado=eSolicitud.estado,
                                                             responsable=eSolicitud.perfil.persona,
                                                             tipodocumento=ti)
                    eHistorialSolicitud.save(request)
                else:
                    eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                             observacion=observa,
                                                             fecha=eSolicitud.fecha,
                                                             hora=eSolicitud.hora,
                                                             estado=eSolicitud.estado,
                                                             responsable=eSolicitud.perfil.persona)
                    eHistorialSolicitud.save(request)

                if eSolicitud.origen_object_id == 55:
                    titulo = 'SOLICITUD DE CERTIFICADO PERSONALIZADO'
                    cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(eSolicitud.perfil.persona) + ' que su solicitud ha sido emitida correctamente. Por favor, cancelar el valor de $' + str((Decimal(eSolicitud.valor_unitario).quantize(Decimal('.01')))) + ' por la elaboración del certificado(personalizado) solicitado. Una vez PROCESADO el pago del valor generado, se le notificará la fecha, a partir de la cual podrá descargar su certificado desde el módulo Servicios de secretaría.'
                elif eSolicitud.origen_object_id in [58, 59]:
                    if eInscripcion.estado_gratuidad != 3 and not eInscripcion.graduado() and not eInscripcion.egresado():
                        titulo = 'SOLICITUD DE CERTIFICADO PERSONALIZADO'
                        cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(eSolicitud.perfil.persona) + ' que su solicitud ha sido emitida correctamente. Se le comunicará vía SGA y correo electrónico cuando su certificado este terminado y subido en el sistema.'
                    else:
                        titulo = 'SOLICITUD DE CERTIFICADO PERSONALIZADO'
                        cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(eSolicitud.perfil.persona) + ' que su solicitud ha sido emitida correctamente. Por favor, cancelar el valor de $' + str((Decimal(eSolicitud.valor_unitario).quantize(Decimal('.01')))) + ' por la elaboración del certificado(personalizado) solicitado. Se le comunicará vía SGA y correo electrónico cuando su certificado este terminado y subido en el sistema.'
                else:
                    titulo = 'SOLICITUD DE CERTIFICADO FÍSICO'
                    cuerpo = 'Saludos cordiales, se comunica al maestrante ' + str(eSolicitud.perfil.persona) + ' que su solicitud ha sido emitida correctamente. Por favor, cancelar el valor de $' + str((Decimal(eSolicitud.valor_unitario).quantize(Decimal('.01')))) +' por la elaboración del certificado(físico) solicitado. Una vez PROCESADO el pago del valor generado, se le notificará la fecha, hora y lugar entrega.'

                notificacion3(titulo,
                              cuerpo, eSolicitud.perfil.persona, None,
                              '/alu_secretaria/mis_pedidos',
                              eSolicitud.pk, 1, 'SIE', eSolicitud, eSolicitud.perfil, request)

                if eSolicitud.origen_object_id == 58:
                    if eInscripcion.estado_gratuidad != 3 and not eInscripcion.graduado() and not eInscripcion.egresado():
                        if eSolicitud.perfil.inscripcion.carrera.coordinacion_carrera().id == 1:
                            secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_FACS')

                            for secretaria in secretarias:
                                titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE PREGRADO"
                                cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' ha realizado el pago por la elaboración de un certificado personalizado. Por favor atender dicha solicitud.'

                                notificacion2(titulo,
                                              cuerpo, secretaria, None,
                                              '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo),
                                              secretaria.pk, 1, 'sga', secretaria)
                        if eSolicitud.perfil.inscripcion.carrera.coordinacion_carrera().id in [3, 2]:
                            if eSolicitud.perfil.inscripcion.carrera.id in [134, 138, 244, 7, 130, 160, 246, 89, 190, 161, 6, 162, 92, 141, 95, 225, 140, 61]:
                                secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_ASISTENTE_1')

                                for secretaria in secretarias:
                                    titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE PREGRADO"
                                    cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' ha realizado el pago por la elaboración de un certificado personalizado. Por favor atender dicha solicitud.'

                                    notificacion2(titulo,
                                                  cuerpo, secretaria, None,
                                                  '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo),
                                                  secretaria.pk, 1, 'sga', secretaria)

                            if eSolicitud.perfil.inscripcion.carrera.id in [188, 9, 145, 91, 164, 8, 43, 165, 11, 128, 158, 245, 248, 10, 88, 144, 16, 12, 126, 242, 163, 93]:
                                secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_ASISTENTE_2')

                                for secretaria in secretarias:
                                    titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE PREGRADO"
                                    cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' ha realizado el pago por la elaboración de un certificado personalizado. Por favor atender dicha solicitud.'

                                    notificacion2(titulo,
                                                  cuerpo, secretaria, None,
                                                  '/adm_secretaria?action=versolicitudes&id=' + str(
                                                      eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(
                                                      eSolicitud.codigo),
                                                  secretaria.pk, 1, 'sga', secretaria)
                            if eSolicitud.perfil.inscripcion.carrera.id in [132, 136, 243, 18, 137, 58, 152, 5, 159, 15, 131, 143, 247, 80]:
                                secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_ASISTENTE_3')

                                for secretaria in secretarias:
                                    titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE PREGRADO"
                                    cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' ha realizado el pago por la elaboración de un certificado personalizado. Por favor atender dicha solicitud.'

                                    notificacion2(titulo,
                                                  cuerpo, secretaria, None,
                                                  '/adm_secretaria?action=versolicitudes&id=' + str(
                                                      eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(
                                                      eSolicitud.codigo),
                                                  secretaria.pk, 1, 'sga', secretaria)


                        if eSolicitud.perfil.inscripcion.carrera.coordinacion_carrera().id == 4:
                            secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_FACI')

                            for secretaria in secretarias:
                                titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE PREGRADO"
                                cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' ha realizado el pago por la elaboración de un certificado personalizado. Por favor atender dicha solicitud.'

                                notificacion2(titulo,
                                              cuerpo, secretaria, None,
                                              '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo),
                                              secretaria.pk, 1, 'sga', secretaria)

                        if eSolicitud.perfil.inscripcion.carrera.coordinacion_carrera().id == 5:
                            secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_FACE')

                            for secretaria in secretarias:
                                titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE PREGRADO"
                                cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' ha realizado el pago por la elaboración de un certificado personalizado. Por favor atender dicha solicitud.'

                                notificacion2(titulo,
                                              cuerpo, secretaria, None,
                                              '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo),
                                              secretaria.pk, 1, 'sga', secretaria)

                if eSolicitud.origen_object_id == 59:
                    if eInscripcion.estado_gratuidad != 3 and not eInscripcion.graduado() and not eInscripcion.egresado():
                        secretarias = Persona.objects.filter(usuario__groups__name='SOLICITUDES_NIVELACION')

                        for secretaria in secretarias:
                            titulo = "ELABORACIÓN DE CERTIFICADO PERSONALIZADO DE NIVELACIÓN"
                            cuerpo = 'Se informa a ' + str(secretaria) + ' que el maestrante ' + str(eSolicitud.perfil.persona) + ' es un estudiante regular y ha solicitado un certificado personalizado. Por favor atender dicha solicitud.'

                            notificacion2(titulo,
                                          cuerpo, secretaria, None,
                                          '/adm_secretaria?action=versolicitudes&id=' + str(eSolicitud.servicio.categoria.id) + '&ids=0&s=' + str(eSolicitud.codigo),
                                          secretaria.pk, 1, 'sga', secretaria)

            else:
                eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                         observacion=eSolicitud.descripcion,
                                                         fecha=eSolicitud.fecha,
                                                         hora=eSolicitud.hora,
                                                         estado=eSolicitud.estado,
                                                         responsable=eSolicitud.perfil.persona,
                                                         )
                eHistorialSolicitud.save(request)
            return {"success": True, 'eSolicitud': eSolicitud, 'error': ''}
        except Exception as ex:
            transaction.set_rollback(True)
            return {"success": False, 'eSolicitud': None, 'error': ex.__str__()}

def process_titulate(request, ePerfilUsuario, aData):
    with transaction.atomic():
        try:
            eInscripcion = ePerfilUsuario.inscripcion
            eCoordinacion = eInscripcion.carrera.coordinacion_set.all()[0]
            ePersona = ePerfilUsuario.persona
            idt = encrypt(aData.get('id', encrypt(0)))
            ids = encrypt(aData.get('ids', encrypt(0)))
            parametros = aData.get('parametros', {})
            eProducto = ProductoSecretaria.objects.get(pk=idt)
            eServicio = eProducto.servicio
            valor = Decimal(eProducto.costo).quantize(Decimal('.01'))
            fecha_vence = datetime.now().date() + timedelta(days=30)
            eTipoOtroRubro = eServicio.tiporubro
            eContentTypeProducto = ContentType.objects.get_for_model(eProducto)
            eSolicitudes = Solicitud.objects.filter(Q(en_proceso=True) | Q(estado__in=[1]), status=True, perfil_id=ePerfilUsuario.pk, servicio_id=eServicio.pk, origen_content_type_id=eContentTypeProducto.pk, origen_object_id=idt).exclude(servicio__proceso=8)
            if eSolicitudes.values("id").exists():
                raise NameError(u"Existe una solicitud en proceso.")
            result = generar_codigo_solicitud(eServicio)
            success = result.get('success', False)
            codigo = result.get('codigo', None)
            secuencia = result.get('secuencia', 0)
            suffix = result.get('suffix', None)
            prefix = result.get('prefix', None)
            if not success:
                raise NameError(u"Código de solicitud no se pudo generar")
            if codigo is None:
                raise NameError(u"Código de solicitud no se pudo generar")
            if secuencia == 0:
                raise NameError(u"Secuencia del código de solicitud no se pudo generar")
            if suffix is None:
                raise NameError(u"Sufijo del código de solicitud no se pudo generar")
            if prefix is None:
                raise NameError(u"Prefijo del código de solicitud no se pudo generar")
            eSolicitud = Solicitud(codigo=codigo,
                                   secuencia=secuencia,
                                   prefix=prefix,
                                   suffix=suffix,
                                   perfil_id=ePerfilUsuario.pk,
                                   servicio_id=eServicio.pk,
                                   origen_content_type=eContentTypeProducto,
                                   origen_object_id=eProducto.pk,
                                   descripcion=f'Solicitud ({codigo}) de Titulación Extraordinaria con código {eProducto.codigo} - {eProducto.descripcion}',
                                   fecha=datetime.now().date(),
                                   hora=datetime.now().time(),
                                   estado=1,
                                   cantidad=1,
                                   valor_unitario=valor,
                                   subtotal=valor,
                                   iva=0,
                                   descuento=0,
                                   en_proceso=False,
                                   parametros=parametros,
                                   tiempo_cobro=eProducto.tiempo_cobro)
            eSolicitud.save(request)

            eMatricula = Matricula.objects.filter(status=True, inscripcion=eSolicitud.perfil.inscripcion).order_by('id').first()
            if eProducto.costo > 0:
                eRubro = Rubro(tipo=eTipoOtroRubro,
                               persona_id=ePersona.pk,
                               nombre=f'({codigo}) - {eProducto.codigo} - {eProducto.descripcion}'[:299],
                               cuota=1,
                               tipocuota=3,
                               fecha=datetime.now().date(),
                               fechavence=fecha_vence,
                               valor=valor,
                               iva_id=1,
                               valoriva=0,
                               valortotal=valor,
                               saldo=valor,
                               cancelado=False,
                               solicitud=eSolicitud,
                               matricula_id=eMatricula.pk)
                eRubro.save(request)

                if eRubro.tipo.tiporubro == 1:
                    # -------CREAR PERSONA EPUNEMI-------
                    cursor = connections['epunemi'].cursor()
                    sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                    cursor.execute(sql)
                    idalumno = cursor.fetchone()

                    if idalumno is None:
                        sql = """ INSERT INTO sga_persona (status, nombres, apellido1, apellido2, cedula, ruc, pasaporte,
                                    nacimiento, tipopersona, sector, direccion,  direccion2,
                                    num_direccion, telefono, telefono_conv, email, contribuyenteespecial,
                                    anioresidencia, nacionalidad, ciudad, referencia, emailinst, identificacioninstitucion,
                                    regitrocertificacion, libretamilitar, servidorcarrera, concursomeritos, telefonoextension,
                                    tipocelular, periodosabatico, real, lgtbi, datosactualizados, confirmarextensiontelefonia,
                                    acumuladecimo, acumulafondoreserva, representantelegal, inscripcioncurso, unemi,
                                    idunemi)
                                            VALUES(TRUE, '%s', '%s', '%s', '%s', '%s', '%s', '/%s/', %s, '%s', '%s', '%s', '%s', '%s', '%s', '%s', 
                                            FALSE, 0, '', '', '', '', '', '', '', FALSE, FALSE, '', 0, FALSE, TRUE, FALSE, 0, FALSE, TRUE, FALSE, FALSE, 
                                            FALSE, FALSE, 0); """ % (
                            eRubro.persona.nombres, eRubro.persona.apellido1,
                            eRubro.persona.apellido2, eRubro.persona.cedula,
                            eRubro.persona.ruc if eRubro.persona.ruc else '',
                            eRubro.persona.pasaporte if eRubro.persona.pasaporte else '',
                            eRubro.persona.nacimiento,
                            eRubro.persona.tipopersona if eRubro.persona.tipopersona else 1,
                            eRubro.persona.sector if eRubro.persona.sector else '',
                            eRubro.persona.direccion if eRubro.persona.direccion else '',
                            eRubro.persona.direccion2 if eRubro.persona.direccion2 else '',
                            eRubro.persona.num_direccion if eRubro.persona.num_direccion else '',
                            eRubro.persona.telefono if eRubro.persona.telefono else '',
                            eRubro.persona.telefono_conv if eRubro.persona.telefono_conv else '',
                            eRubro.persona.email if eRubro.persona.email else '')
                        cursor.execute(sql)

                        if eRubro.persona.sexo:
                            sql = """SELECT sexo.id FROM sga_sexo AS sexo WHERE sexo.id='%s'  AND sexo.status=TRUE;  """ % (eRubro.persona.sexo.id)
                            cursor.execute(sql)
                            sexo = cursor.fetchone()

                            if sexo is not None:
                                sql = """UPDATE sga_persona SET sexo_id='%s' WHERE cedula='%s'; """ % (sexo[0], eRubro.persona.cedula)
                                cursor.execute(sql)

                        if eRubro.persona.pais:
                            sql = """SELECT pai.id FROM sga_pais AS pai WHERE pai.id='%s'  AND pai.status=TRUE;  """ % (eRubro.persona.pais.id)
                            cursor.execute(sql)
                            pais = cursor.fetchone()

                            if pais is not None:
                                sql = """UPDATE sga_persona SET pais_id='%s' WHERE cedula='%s'; """ % (pais[0], eRubro.persona.cedula)
                                cursor.execute(sql)

                        if eRubro.persona.parroquia:
                            sql = """SELECT pa.id FROM sga_parroquia AS pa WHERE pa.id='%s'  AND pa.status=TRUE;  """ % (eRubro.persona.parroquia.id)
                            cursor.execute(sql)
                            parroquia = cursor.fetchone()

                            if parroquia is not None:
                                sql = """UPDATE sga_persona SET parroquia_id='%s' WHERE cedula='%s'; """ % (parroquia[0], eRubro.persona.cedula)
                                cursor.execute(sql)

                        if eRubro.persona.canton:
                            sql = """SELECT ca.id FROM sga_canton AS ca WHERE ca.id='%s'  AND ca.status=TRUE;  """ % (eRubro.persona.canton.id)
                            cursor.execute(sql)
                            canton = cursor.fetchone()

                            if canton is not None:
                                sql = """UPDATE sga_persona SET canton_id='%s' WHERE cedula='%s'; """ % (canton[0], eRubro.persona.cedula)
                                cursor.execute(sql)

                        if eRubro.persona.provincia:
                            sql = """SELECT pro.id FROM sga_provincia AS pro WHERE pro.id='%s'  AND pro.status=TRUE;  """ % (eRubro.persona.provincia.id)
                            cursor.execute(sql)
                            provincia = cursor.fetchone()

                            if provincia is not None:
                                sql = """UPDATE sga_persona SET provincia_id='%s' WHERE cedula='%s'; """ % (provincia[0], eRubro.persona.cedula)
                                cursor.execute(sql)
                        # ID DE PERSONA EN EPUNEMI
                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE (pe.cedula='%s' OR pe.pasaporte='%s' OR pe.ruc='%s') AND pe.status=TRUE;  """ % (eRubro.persona.cedula, eRubro.persona.cedula, eRubro.persona.cedula)
                        cursor.execute(sql)
                        idalumno = cursor.fetchone()
                        alumnoepu = idalumno[0]
                    else:
                        alumnoepu = idalumno[0]

                    # Consulto el tipo otro rubro en epunemi
                    sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                    cursor.execute(sql)
                    registro = cursor.fetchone()

                    # Si existe
                    if registro is not None:
                        tipootrorubro = registro[0]
                    else:
                        # Debo crear ese tipo de rubro
                        # Consulto centro de costo
                        sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (eRubro.tipo.tiporubro)
                        cursor.execute(sql)
                        centrocosto = cursor.fetchone()
                        idcentrocosto = centrocosto[0]

                        # Consulto la cuenta contable
                        cuentacontable = CuentaContable.objects.get(partida=eRubro.tipo.partida, status=True)

                        # Creo el tipo de rubro en epunemi
                        sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi, es_especie, es_convalidacionconocimiento)
                                            VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE, FALSE, FALSE); """ % (
                            eRubro.tipo.nombre, cuentacontable.partida.id, eRubro.tipo.valor,
                            eRubro.tipo.ivaaplicado.id, cuentacontable.id, idcentrocosto,
                            eRubro.tipo.id)
                        cursor.execute(sql)

                        print(".:: Tipo de Rubro creado en EPUNEMI ::.")

                        # Obtengo el id recién creado del tipo de rubro
                        sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (eRubro.tipo.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()
                        tipootrorubro = registro[0]

                    # pregunto si no existe rubro con ese id de unemi
                    sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE; """ % (eRubro.id)
                    cursor.execute(sql)
                    registrorubro = cursor.fetchone()

                    if registrorubro is None:
                        # Creo nuevo rubro en epunemi
                        sql = """ INSERT INTO sagest_rubro (status, persona_id, nombre, cuota, tipocuota, fecha, fechavence,
                                    valor, saldo, iva_id, valoriva, totalunemi, valortotal, cancelado, observacion, 
                                    idrubrounemi, tipo_id, fecha_creacion, usuario_creacion_id, tienenotacredito, valornotacredito, 
                                    valordescuento, anulado, compromisopago, refinanciado, bloqueado, bloqueadopornovedad, 
                                    titularcambiado, coactiva) 
                                  VALUES (TRUE, %s, '%s', %s, %s, '/%s/', '/%s/', %s, %s, %s, %s, %s, %s, %s, '%s', %s, %s, NOW(), 1, FALSE, 0, 0, FALSE, %s, %s, %s, FALSE, FALSE, %s); """ \
                              % (alumnoepu, eRubro.nombre, eRubro.cuota, eRubro.tipocuota, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                 eRubro.valoriva, eRubro.valor,
                                 eRubro.valortotal, eRubro.cancelado, eRubro.observacion, eRubro.id, tipootrorubro,
                                 eRubro.compromisopago if eRubro.compromisopago else 0,
                                 eRubro.refinanciado, eRubro.bloqueado, eRubro.coactiva)
                        cursor.execute(sql)

                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND anulado=FALSE; """ % (eRubro.id)
                        cursor.execute(sql)
                        registro = cursor.fetchone()
                        rubroepunemi = registro[0]

                        eRubro.idrubroepunemi = rubroepunemi
                        eRubro.epunemi = True
                        eRubro.save()

                        print(".:: Rubro creado en EPUNEMI ::.")
                    else:
                        sql = """SELECT id FROM sagest_rubro WHERE idrubrounemi=%s AND status=TRUE AND cancelado=FALSE; """ % (eRubro.id)
                        cursor.execute(sql)
                        rubronoc = cursor.fetchone()

                        if rubronoc is not None:
                            sql = """SELECT id FROM sagest_pago WHERE rubro_id=%s; """ % (registrorubro[0])
                            cursor.execute(sql)
                            tienerubropagos = cursor.fetchone()

                            if tienerubropagos is not None:
                                pass
                            else:
                                sql = """UPDATE sagest_rubro SET nombre = '%s', fecha = '/%s/', fechavence = '/%s/',
                                   valor = %s, saldo = %s, iva_id = %s, valoriva = %s, totalunemi = %s,
                                   valortotal = %s, observacion = '%s', tipo_id = %s
                                   WHERE id=%s; """ % (eRubro.nombre, eRubro.fecha, eRubro.fechavence, eRubro.saldo, eRubro.saldo, eRubro.iva_id,
                                                       eRubro.valoriva, eRubro.valor, eRubro.valortotal, eRubro.observacion, tipootrorubro,
                                                       registrorubro[0])
                                cursor.execute(sql)
                            eRubro.idrubroepunemi = registrorubro[0]
                            eRubro.save()

            eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                     observacion=eSolicitud.descripcion,
                                                     fecha=eSolicitud.fecha,
                                                     hora=eSolicitud.hora,
                                                     estado=eSolicitud.estado,
                                                     responsable=eSolicitud.perfil.persona,
                                                     )
            eHistorialSolicitud.save(request)
            return {"success": True, 'eSolicitud': eSolicitud, 'error': ''}
        except Exception as ex:
            transaction.set_rollback(True)
            return {"success": False, 'eSolicitud': None, 'error': ex.__str__()}

def costo_tit_ex(eInscripcion):
    from sga.models import Matricula, AsignaturaMalla, MateriaAsignada, InscripcionMalla, PeriodoCarreraCosto
    from posgrado.models import CohorteMaestria
    from django.db.models import Sum
    try:
        vp = 0
        idmo = 0
        insmalla = InscripcionMalla.objects.filter(status=True, inscripcion=eInscripcion).first()
        matriculas = Matricula.objects.filter(status=True, inscripcion=eInscripcion).order_by('id')
        for matricula in matriculas:
            if MateriaAsignada.objects.filter(status=True, matricula=matricula).exists():
                idmo = matricula.id
                break
        if idmo == 0 and Matricula.objects.filter(status=True, inscripcion=eInscripcion, inscripcion__coordinacion_id = 7).exists():
            mat = Matricula.objects.filter(status=True, inscripcion=eInscripcion, inscripcion__coordinacion_id = 7).first()
            costotal = mat.nivel.periodo.periodocarreracosto_set.filter(carrera=mat.inscripcion.carrera, status=True).aggregate(
                costo=Sum('costo'))['costo']
        else:
            mat = Matricula.objects.get(status=True, pk=idmo)
            # cohorte = CohorteMaestria.objects.filter(status=True, periodoacademico=mat.nivel.periodo).first()
            costotal = mat.nivel.periodo.periodocarreracosto_set.filter(carrera=mat.inscripcion.carrera, status=True).aggregate(costo=Sum('costo'))['costo']
        mallas = AsignaturaMalla.objects.filter(status=True, opcional=False, malla=insmalla.malla, asignatura__status=True, itinerario__in=[0, eInscripcion.itinerario]).count()

        vp = (costotal / mallas) * 2
        # if cohorte.valorprogramacertificado:
        #     vp = (cohorte.valorprogramacertificado / mallas) * 2
        # elif cohorte.valorprograma:
        #     vp = (cohorte.valorprograma / mallas) * 2

        return Decimal(vp).quantize(Decimal('.01'))
    except Exception as ex:
        pass




