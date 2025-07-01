# coding=utf-8
import json
import os
from datetime import datetime, timedelta
import  time
import pyqrcode
from django.db import transaction
from django.db.models import Q, Count, PROTECT, Sum, Avg, Min, Max, F
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from api.helpers.decorators import api_security
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.encuesta import AlumnoGrupoEncuestaSerializer, GrupoEncuestaSerializer
from api.serializers.alumno.insignias import InsigniaPersonaSerializer
from api.serializers.alumno.becas import BecaSolicitudSerializer
from settings import ALUMNOS_GROUP_ID
from sga.funciones import log, generar_nombre
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqr_generico
from sga.models import Noticia, Inscripcion, Persona, Periodo, InsigniaPersona, BecaSolicitud, BecaAsignacion, BecaDetalleUtilizacion, BecaPeriodo, PreInscripcionBeca, BecaSolicitudRecorrido, miinstitucion, Notificacion, CUENTAS_CORREOS
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from django.core.cache import cache
from settings import SITE_STORAGE, DEBUG


class BecaSolicitudView(APIView):
    permission_classes = (IsAuthenticated,)
    api_key_module = None

    @api_security
    def post(self, request):
        TIEMPO_ENCACHE = 60 * 60 * 60
        action = ''
        try:
            if 'action' in request.data:
                action = request.data.get('action')
            if action == 'aceptarrechazarbeca':
                with transaction.atomic():
                    try:
                        aData = {}
                        url_path = 'http://127.0.0.1:8000'
                        if not DEBUG:
                            url_path = 'https://sga.unemi.edu.ec'
                        idbeca = encrypt(request.data['id'])
                        acepto = request.data['acepto']
                        payload = request.auth.payload
                        eInscripcionEnCache = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
                        if eInscripcionEnCache:
                            eInscripcion = eInscripcionEnCache
                        else:
                            if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                                raise NameError(u"Inscripción no válida")
                            eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                            cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
                        ePersona = Persona.objects.get(pk=encrypt(payload['persona']['id']))
                        ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']))
                        output_folder = ''
                        aData['becasolicitud'] = becasolicitud = BecaSolicitud.objects.get(id=idbeca)
                        documentopersonal = ePersona.personadocumentopersonal_set.filter(status=True).first()
                        cuentabancaria = cuentabancaria = ePersona.cuentabancaria_becas()
                        perfil = ePersona.mi_perfil()
                        deportista = ePersona.deportistapersona_set.filter(status=True).first()
                        isPersonaExterior = ePersona.ecuatoriano_vive_exterior()
                        # if not becasolicitud.cumple_todos_documentos_requeridos():
                        #     raise NameError(f'Estimad {"a" if persona.sexo_id == 1 else "o" if persona.sexo_id == 2 else "o/a" } estudiante revisar su documentación desde el botón revisión de documentos')
                        aData['configuracionbecatipoperiodo'] = becatipoconfiguracion = becasolicitud.obtener_configuracionbecatipoperiodo()
                        aData['matricula'] = matricula = becasolicitud.obtener_matricula()
                        eInscripcion = becasolicitud.inscripcion
                        ePeriodo = becasolicitud.periodo
                        eUsuario = request.user
                        username = eUsuario.username
                        filename = f'acta_compromiso_{eInscripcion.id}_{ePeriodo.id}_{becasolicitud.id}'
                        filenametemp = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, filename + '.pdf'))
                        filenameqrtemp = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, 'qrcode', filename + '.png'))
                        url_actafirmada = None
                        mensaje = u"Usted rechazo la  beca"
                        if acepto == 1:
                            becaasignacion = BecaAsignacion.objects.filter(solicitud=becasolicitud, status=True).first()
                            if becaasignacion is not None:
                                raise NameError(u"El Registro de beca ya fue guardado.")
                            if becasolicitud.becatipo_id == 23:
                                beneficios = becasolicitud.becasolicitudnecesidad_set.all().first()
                                beneficio = beneficios.necesidad
                            if becatipoconfiguracion is None:
                                raise NameError(u"No se encontro configuración para el tipo de beca")
                            folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'actas_compromisos', username, ''))
                            folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'actas_compromisos', username, 'qrcode', ''))
                            aData['aceptobeca'] = True
                            aData['url_qr'] = rutaimg = folder2 + filename + '.png'
                            aData['rutapdf'] = rutapdf = folder + filename + '.pdf'
                            aData['url_pdf'] = url_pdf = f'{url_path}/media/becas/actas_compromisos/{username}/{filename}.pdf'
                            if os.path.isfile(rutapdf):
                                os.remove(rutapdf)
                            elif os.path.isfile(rutaimg):
                                os.remove(rutaimg)
                            os.makedirs(folder, exist_ok=True)
                            os.makedirs(folder2, exist_ok=True)
                            firma = f'ACEPTADO POR: {eInscripcion.persona.__str__()}\nUSUARIO:{username}\nFECHA: {datetime.utcnow()}\nACEPTO EN: sga.unemi.edu.ec\nDOCUMENTO:{url_pdf}'
                            url = pyqrcode.create(firma)
                            imageqr = url.png(rutaimg, 16, '#000000')
                            aData['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                            aData['image_qrcode'] = f'{url_path}/media/becas/actas_compromisos/{username}/qrcode/{filename}.png'
                            aData['fechaactual'] = datetime.now()
                            url_acta = f'becas/actas_compromisos/{username}/{filename}.pdf'
                            rutapdf = folder + filename + '.pdf'

                            valida, pdf, result = conviert_html_to_pdfsaveqr_generico(request, 'alu_becas/actav2.html', {
                                'pagesize': 'A4',
                                'data': aData,

                            }, folder, filename + '.pdf')
                            if not valida:
                                raise NameError('Error al generar el pdf de acta de compromiso')
                            becasolicitud.archivoactacompromiso = url_acta
                            becasolicitud.becaaceptada = 2
                            becasolicitud.becaasignada = 2
                            becasolicitud.save(request)
                            # AYUDAS ECONOMICAS COVID
                            if becasolicitud.becatipo.id == 23:
                                modalidad = becasolicitud.inscripcion.carrera.modalidad
                                montobeca = 270.36 if modalidad != 3 else 44.80
                                beca = BecaAsignacion(solicitud=becasolicitud,
                                                      montomensual=montobeca,
                                                      cantidadmeses=1,
                                                      montobeneficio=montobeca,
                                                      fecha=datetime.now().date(),
                                                      activo=True,
                                                      grupopago=None,
                                                      tipo=1,
                                                      notificar=True,
                                                      estadobeca=None,
                                                      infoactualizada=False,
                                                      cargadocumento=True)
                                beca.save(request)
                                detalleuso = BecaDetalleUtilizacion(asignacion=beca,
                                                                    utilizacion_id=8 if beneficio == 1 else 9,
                                                                    personaaprueba=ePersona,
                                                                    archivo=None,
                                                                    fechaaprueba=datetime.now(),
                                                                    fechaarchivo=None,
                                                                    estado=2,
                                                                    observacion='GENERADO AUTOMÁTICAMENTE')
                                detalleuso.save(request)
                                persona = becasolicitud.inscripcion.persona
                                if persona.documentos_personales():
                                    # SI TIENEN DOCUMENTACION VALIDADA
                                    if persona.cedula_solicitante_representante_validadas():
                                        beca.infoactualizada = True
                                        beca.cargadocumento = False
                                        beca.save(request)
                            else:
                                # OTROS TIPOS DE BECA
                                # if solicitud.becatipo_id == 16 or solicitud.becatipo_id == 17:
                                #     montobeca = 110.04
                                # else:
                                #     montobeca = 184.08
                                montobeca = becatipoconfiguracion.becamonto
                                meses = becatipoconfiguracion.becameses
                                montomensual = becatipoconfiguracion.monto_x_mes()
                                beca = BecaAsignacion(solicitud=becasolicitud,
                                                      montomensual=montomensual,
                                                      cantidadmeses=meses,
                                                      montobeneficio=montobeca,
                                                      fecha=datetime.now().date(),
                                                      activo=True,
                                                      grupopago=None,
                                                      tipo=becasolicitud.tiposolicitud,
                                                      notificar=True,
                                                      estadobeca=None,
                                                      infoactualizada=False,
                                                      cargadocumento=True)
                                beca.save(request)
                                # VERIFICAR SI TIENE DOCUMENTACION APROBADA DE UN PROCESO ANTERIOR
                                # persona = becasolicitud.inscripcion.persona
                                # if persona.documentos_personales():
                                #     # SI TIENEN DOCUMENTACION VALIDADA
                                #     if persona.cedula_solicitante_representante_validadas():
                                #         beca.infoactualizada = True
                                #         beca.cargadocumento = False
                                #         beca.save(request)

                                if becasolicitud.cumple_todos_documentos_requeridos():
                                    beca.infoactualizada = True
                                    beca.cargadocumento = False
                                    beca.save(request)
                            #url_actafirmada = becasolicitud.archivoactacompromiso.url
                            log(u'Aceptó la beca estudiantil: %s' % (ePersona), request, "edit")
                            mensaje = u"Acepto correctamente la beca"
                        if acepto == 0:
                            becasolicitud.becaaceptada = 3
                            becasolicitud.observacion = 'El estudiante rechazó la beca estudiantil'
                            becasolicitud.save(request)
                            #AL RECHAZAR EL ESTUDIANTE SU BECA SE SELEECIONARA DE LA PREDATA LOS SIGUIENTES BECARIOS CON NO FUERON SELECCIONADOS
                            cantidad_estudiantes_becados = BecaSolicitud.objects.values('id').filter(status=True, periodo_id=becasolicitud.periodo_id).exclude(becaaceptada=3).count()
                            cantidad_limite_becados = becatipoconfiguracion.becaperiodo.limitebecados
                            preinscripcion_rechazo = PreInscripcionBeca.objects.filter(inscripcion=becasolicitud.inscripcion, status=True, periodo=becasolicitud.periodo).first()

                            becados_rechazados = BecaSolicitud.objects.values('inscripcion_id').filter(periodo_id=becasolicitud.periodo_id, becaaceptada=3)
                            while cantidad_estudiantes_becados < cantidad_limite_becados:
                                preinscripcionbeca = PreInscripcionBeca.objects.filter(seleccionado=False, status=True, periodo_id=becasolicitud.periodo_id).exclude(inscripcion_id__in=becados_rechazados).order_by('orden').first()
                                if (preinscripcionbeca_p := PreInscripcionBeca.objects.filter(seleccionado=False, status=True, prioridad=True, periodo_id=becasolicitud.periodo_id).exclude(inscripcion_id__in=becados_rechazados).order_by('orden').first()) is not None:
                                    preinscripcionbeca = preinscripcionbeca_p
                                if preinscripcionbeca:
                                    becado = BecaSolicitud(inscripcion=preinscripcionbeca.inscripcion,
                                                           becatipo=preinscripcionbeca.becatipo,
                                                           periodo=becasolicitud.periodo,
                                                           periodocalifica=becasolicitud.periodocalifica,
                                                           estado=1,
                                                           tiposolicitud=preinscripcionbeca.tipo_renovacion_nueva(becasolicitud.periodocalifica),
                                                           observacion=f'SEMESTRE REGULAR {preinscripcionbeca.periodo.nombre}')
                                    becado.save(usuario_id=1)
                                    recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=1).first()
                                    preinscripcionbeca.seleccionado = True
                                    preinscripcionbeca.save(usuario_id=1)
                                    if recorrido is None:
                                        recorrido = BecaSolicitudRecorrido(solicitud=becado,
                                                                           observacion="SOLICITUD AUTOMÁTICA",
                                                                           estado=1)
                                        recorrido.save(usuario_id=1)
                                        recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=4).first()
                                        # REGISTRO EN ESTADO DE REVISION
                                        if recorrido is None:
                                            becado.estado = 4
                                            becado.save(usuario_id=1)
                                            recorrido = BecaSolicitudRecorrido(solicitud=becado,
                                                                               observacion="EN REVISION",
                                                                               estado=4)
                                            recorrido.save(usuario_id=1)
                                            # log(u'Agrego recorrido de beca: %s' % recorrido, request, "add")

                                        recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=2).first()
                                        if recorrido is None:
                                            becado.estado = 2
                                            becado.becaaceptada = 1
                                            becado.save(usuario_id=1)
                                            recorrido = BecaSolicitudRecorrido(solicitud=becado,
                                                                               observacion="PENDIENTE DE ACEPTACIÓN O RECHAZO",
                                                                               estado=2)
                                            recorrido.save(usuario_id=1)
                                            # log(u'Agrego recorrido de beca: %s' % recorrido, request, "add")
                                            notificacion = Notificacion(titulo=f"Solicitud de Beca en Revisión - {preinscripcionbeca.periodo.nombre}",
                                                                        cuerpo=f"Solicitud de aplicación a la beca por {becado.becatipo.nombre.upper()} para el periodo académico {becado.periodo.nombre} ha sido {'APROBADA' if becado.estado == 2 else 'RECHAZADA'}",
                                                                        destinatario=preinscripcionbeca.inscripcion.persona,
                                                                        url="/alu_becas",
                                                                        content_type=None,
                                                                        object_id=None,
                                                                        prioridad=2,
                                                                        perfil=preinscripcionbeca.inscripcion.perfil_usuario(),
                                                                        app_label='SIE',  # request.session['tiposistema'],
                                                                        fecha_hora_visible=datetime.now() + timedelta(days=2)
                                                                        )
                                            notificacion.save(usuario_id=1)
                                            preinscripcion_rechazo.seleccionado = False
                                            preinscripcion_rechazo.save(request)
                                            lista_envio_masivo = []
                                            tituloemail = "Beca estudiantil"
                                            data = {'sistema': u'SGA - UNEMI',
                                                    'fase': 'AR',
                                                    'tipobeca': preinscripcionbeca.becatipo.nombre.upper(),
                                                    'fecha': datetime.now().date(),
                                                    'hora': datetime.now().time(),
                                                    'saludo': 'Estimada' if becado.inscripcion.persona.sexo_id == 1 else 'Estimado',
                                                    'estado': 'APROBADA' if becado.estado == 2 else "RECHAZADA",
                                                    'estudiante': becado.inscripcion.persona.nombre_minus(),
                                                    'autoridad2': '',
                                                    'observaciones': '',
                                                    'periodo': becado.periodo.nombre,
                                                    't': miinstitucion()
                                                    }
                                            list_email = becado.inscripcion.persona.lista_emails_envio()
                                            plantilla = "emails/notificarestadosolicitudbeca.html"
                                            send_html_mail(tituloemail,
                                                           plantilla,
                                                           data,
                                                           list_email,
                                                           [],
                                                           cuenta=CUENTAS_CORREOS[0][1]
                                                           )
                                            time.sleep(3)
                                            cantidad_estudiantes_becados = BecaSolicitud.objects.values('id').filter(status=True, periodo_id=becasolicitud.periodo_id).exclude(becaaceptada=3).count()
                                else:
                                    break
                            log(u'Rechazó la beca estudiantil: %s' % ePersona, request, "edit")
                        request.session['periodo'] = becasolicitud.periodo
                        if os.path.isfile(filenameqrtemp):
                            os.remove(filenameqrtemp)
                        elif os.path.isfile(filenametemp):
                            os.remove(filenametemp)
                        return Helper_Response(isSuccess=True, status=status.HTTP_200_OK)
                    except Exception as ex:
                        transaction.set_rollback(True)
                        return Helper_Response(isSuccess=False, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)
            else:
                aDatapdf = {}
                hoy = datetime.now()
                url_path = 'http://127.0.0.1:8000'
                if not DEBUG:
                    url_path = 'https://sga.unemi.edu.ec'
                payload = request.auth.payload
                if cache.has_key(f"inscripcion_id_{payload['inscripcion']['id']}"):
                    eInscripcion = cache.get(f"inscripcion_id_{payload['inscripcion']['id']}")
                else:
                    if not Inscripcion.objects.db_manager("sga_select").values("id").filter(pk=encrypt(payload['inscripcion']['id'])).exists():
                        raise NameError(u"Inscripción no válida")
                    eInscripcion = Inscripcion.objects.db_manager("sga_select").get(pk=encrypt(payload['inscripcion']['id']))
                    cache.set(f"inscripcion_id_{payload['inscripcion']['id']}", eInscripcion, TIEMPO_ENCACHE)
                ePeriodo = None
                if 'id' in payload['periodo']:
                    if cache.has_key(f"periodo_id_{payload['periodo']['id']}"):
                        ePeriodo = cache.get(f"periodo_id_{payload['periodo']['id']}")
                    else:
                        if Periodo.objects.values("id").filter(pk=encrypt(payload['periodo']['id']), status=True).exists():
                            ePeriodo = Periodo.objects.get(pk=encrypt(payload['periodo']['id']), status=True)
                            cache.set(f"periodo_id_{payload['periodo']['id']}", ePeriodo, TIEMPO_ENCACHE)
                if ePeriodo is None:
                    raise NameError(u"No tiene acceso al módulo")
                ePersona = eInscripcion.persona
                fechaactual = datetime.now()
                if cache.has_key(f"becasolicitudpendiente_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}"):
                    eBecaSolicitudPendiente = cache.get(f"becasolicitudpendiente_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}")
                else:
                    eBecaSolicitudPendiente = eInscripcion.becasolicitud_set.filter(periodo__becaperiodo__periodo_id=F('periodo_id'),
                                                                                    periodo__becaperiodo__vigente=True,
                                                                                    periodo__becaperiodo__fechainiciosolicitud__lte=fechaactual,
                                                                                    periodo__becaperiodo__fechafinsolicitud__gte=fechaactual,
                                                                                    becaaceptada=1,
                                                                                    status=True,
                                                                                    estado=2).order_by('periodo__inicio').distinct().first()
                    if eBecaSolicitudPendiente is not None:
                        aDatapdf['becasolicitud'] = eBecaSolicitudPendiente
                        aDatapdf['configuracionbecatipoperiodo'] = becatipoconfiguracion = eBecaSolicitudPendiente.obtener_configuracionbecatipoperiodo()
                        aDatapdf['matricula'] = matricula = eBecaSolicitudPendiente.obtener_matricula()
                        username = ePersona.usuario.username
                        filename = f'acta_compromiso_{eInscripcion.id}_{ePeriodo.id}_{eBecaSolicitudPendiente.id}'
                        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, ''))
                        folder2 = os.path.join(os.path.join(SITE_STORAGE, 'media', 'becas', 'temp', 'actas_compromisos', username, 'qrcode', ''))
                        aDatapdf['url_qr'] = rutaimg = folder2 + filename + '.png'
                        aDatapdf['rutapdf'] = rutapdf = folder2 + filename + '.pdf'
                        if os.path.isfile(rutapdf):
                            os.remove(rutapdf)
                        elif os.path.isfile(rutaimg):
                            os.remove(rutaimg)
                        os.makedirs(folder, exist_ok=True)
                        os.makedirs(folder2, exist_ok=True)
                        aDatapdf['version'] = datetime.now().strftime('%Y%m%d_%H%M%S')
                        aDatapdf['image_qrcode'] = f'{url_path}/media/becas/temp/actas_compromisos/{username}/qrcode/{filename}.png'
                        aDatapdf['fechaactual'] = datetime.now()
                        url_acta = f'{url_path}/media/becas/temp/actas_compromisos/{username}/{filename}.pdf'
                        valida, pdf, result = conviert_html_to_pdfsaveqr_generico(request, 'alu_becas/actav2.html', {
                            'pagesize': 'A4',
                            'data': aDatapdf,

                        }, folder, filename + '.pdf')
                        eBecaSolicitudPendiente.__setattr__('url_acta', url_acta)
                        cache.set(f"becasolicitudpendiente_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}", eBecaSolicitudPendiente, TIEMPO_ENCACHE)
                    else:
                        cache.set(f"becasolicitudpendiente_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}", {}, TIEMPO_ENCACHE)
                eBecaSolicitudPendienteSerializer = BecaSolicitudSerializer(eBecaSolicitudPendiente).data if eBecaSolicitudPendiente else {}

                if cache.has_key(f"becasolicitudpendientedocumentacion_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}"):
                    eBecaSolicitudPendienteDocumentacion = cache.get(f"becasolicitudpendientedocumentacion_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}")
                else:
                    eBecaSolicitudPendienteDocumentacion = eInscripcion.becasolicitud_set.filter(periodo__becaperiodo__periodo_id=F('periodo_id'),
                                                                                                 periodo__becaperiodo__vigente=True,
                                                                                                 periodo__becaperiodo__fechainiciovalidaciondocumento__lte=fechaactual,
                                                                                                 periodo__becaperiodo__fechafinvalidaciondocumento__gte=fechaactual,
                                                                                                 becaaceptada=2,
                                                                                                 status=True,
                                                                                                 estado=2).order_by('periodo__inicio').distinct().first()
                    if eBecaSolicitudPendienteDocumentacion is not None:
                        tiene_documentacion_pendiente = eBecaSolicitudPendienteDocumentacion.tiene_pendiente_documentos_por_cargar()
                        eBecaSolicitudPendienteDocumentacion.__setattr__('tiene_documentacion_pendiente', tiene_documentacion_pendiente)
                        cache.set(f"becasolicitudpendientedocumentacion_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}", eBecaSolicitudPendienteDocumentacion, TIEMPO_ENCACHE)
                    else:
                        cache.set(f"becasolicitudpendientedocumentacion_inscripcion_id_{encrypt(eInscripcion.id)}__periodo_id_{encrypt(ePeriodo.id)}", [], TIEMPO_ENCACHE)

                eBecaSolicitudPendienteDocumentacionSerializer = BecaSolicitudSerializer(eBecaSolicitudPendienteDocumentacion).data if eBecaSolicitudPendienteDocumentacion else {}
                data = {
                    'eBecaSolicitudPendiente': eBecaSolicitudPendienteSerializer,
                    'eBecaSolicitudPendienteDocumentacion': eBecaSolicitudPendienteDocumentacionSerializer,
                }

                return Helper_Response(isSuccess=True, data=data, status=status.HTTP_200_OK)
            return Helper_Response(isSuccess=False, data={}, message=f'Acción no encontrada', status=status.HTTP_200_OK)
        except Exception as ex:
            return Helper_Response(isSuccess=False, data={}, message=f'Ocurrio un error: {ex.__str__()}', status=status.HTTP_200_OK)