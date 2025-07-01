# coding=utf-8
import json
import os
import sys
import threading
import pyqrcode
import subprocess
import io as StringIO
from datetime import datetime, timedelta

from django.contrib.auth.models import User
from django.db.models import Q
from django.db import transaction
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework import status
from django.contrib.contenttypes.models import ContentType
from django.template import engines
from xhtml2pdf import pisa

from api.helpers.functions_helper import get_variable, remove_accents, transform_jasperstarter, fixparametro, \
    fetch_resources
from api.helpers.response_herlper import Helper_Response
from api.serializers.alumno.certificado import CertificadoSerializer, CertificadoMatriculaSerializer
from certi.models import CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora, Certificado
from settings import JR_JAVA_COMMAND, DATABASES, JR_USEROUTPUT_FOLDER, JR_RUN, MEDIA_URL, SUBREPOTRS_FOLDER, \
    MEDIA_ROOT, SITE_ROOT, DEBUG, EMAIL_DOMAIN, SITE_STORAGE
from sga.funciones import generar_codigo, variable_valor
from sga.models import Noticia, Inscripcion, PerfilUsuario, Matricula, Reporte, Persona, LogReporteDescarga, \
    ReporteDescarga, Notificacion, miinstitucion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


class RunAPIView(APIView):
    permission_classes = (IsAuthenticated,)

    def post(self, request):
        with transaction.atomic():
            try:
                data = {}
                hoy = datetime.now()
                payload = request.auth.payload
                ePersona = Persona.objects.get(pk=encrypt(payload['persona']['id']))
                data['ePersona'] = ePersona
                if 'n' in request.data:
                    reporte = Reporte.objects.get(nombre=request.data['n'])
                else:
                    reporte = Reporte.objects.get(pk=encrypt(request.data['rid']))
                cambiaruta = 0
                isQR = False
                codigo = None
                certificado = None
                base_url = get_variable('SITE_URL_SGA')
                eUser = request.user
                if reporte.archivo:
                    tipo = request.data['rt']
                    output_folder = os.path.join(JR_USEROUTPUT_FOLDER, remove_accents(eUser.username))
                    try:
                        os.makedirs(output_folder)
                    except Exception as ex:
                        pass
                    d = datetime.now()
                    pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
                    if reporte.version == 2:
                        """SE REALIZA AJUSTES PARA NUEVAS VERSIONES"""
                        content_type = None
                        object_id = None
                        vqr = None
                        if 'vqr' in request.data:
                            isQR = True
                            vqr = request.data['vqr']
                            # pdfname = reporte.nombre + vqr
                            parametros_reporte = reporte.parametroreporte_set.get(nombre='vqr')
                            if not Certificado.objects.filter(reporte=reporte, visible=True).exists():
                                raise NameError(u"No se encontro certificado activo" if eUser.is_superuser else u"Código: ADM_001")
                            if Certificado.objects.filter(reporte=reporte, visible=True).count() > 1:
                                raise NameError(u"Mas de un certificado activo" if eUser.is_superuser else u"Código: ADM_002")
                            certificado = Certificado.objects.get(reporte=reporte, visible=True)

                            if parametros_reporte.extra:
                                try:
                                    content_type = ContentType.objects.get_for_model(eval(parametros_reporte.extra))
                                    object_id = vqr
                                except Exception as ex:
                                    content_type = ContentType.objects.get_for_model(eUser)
                                    object_id = eUser.id
                            else:
                                try:
                                    if Persona.objects.filter(usuario_id=eUser.id).exists():
                                        persona = Persona.objects.filter(usuario_id=eUser.id).first()
                                        content_type = ContentType.objects.get_for_model(persona)
                                        object_id = persona.id
                                    else:
                                        content_type = ContentType.objects.get_for_model(eUser)
                                        object_id = eUser.id
                                except Exception as ex:
                                    content_type = ContentType.objects.get_for_model(eUser)
                                    object_id = eUser.id
                        else:
                            try:
                                if Persona.objects.filter(usuario_id=eUser.id).exists():
                                    persona = Persona.objects.filter(usuario_id=eUser.id).first()
                                    content_type = ContentType.objects.get_for_model(persona)
                                    object_id = persona.id
                                else:
                                    content_type = ContentType.objects.get_for_model(eUser)
                                    object_id = eUser.id
                            except Exception as ex:
                                content_type = ContentType.objects.get_for_model(eUser)
                                object_id = eUser.id

                        if isQR:
                            SUFFIX = None
                            if (parametros_reporte.extra).upper() == "MATRICULA":
                                # print(vqr, encrypt(vqr))
                                matricula = Matricula.objects.get(pk=encrypt(vqr))
                                carrera = matricula.inscripcion.carrera
                                coordinacion = matricula.inscripcion.coordinacion
                                #Validación  de que estudiantes esten matriculado
                                if not matricula.status:
                                    raise NameError('Usted actualmente no se encuentra matriculado en el periodo actual')
                                if matricula.retiradomatricula:
                                    raise NameError(f'Usted actualmente se encuentra retirado de la carrera {matricula.inscripcion.carrera} en el período actual')
                            else:
                                inscripcion = Inscripcion.objects.get(pk=encrypt(vqr))
                                carrera = inscripcion.carrera
                                coordinacion = inscripcion.coordinacion
                            if not certificado:
                                raise NameError(u"No se encontro certificado." if eUser.is_superuser else u"Código: ADM_003")
                            uc = None
                            ac = None
                            if not certificado.tiene_unidades_certificadoras():
                                raise NameError(u"Certificado no tiene configurado Unidad certificadora" if eUser.is_superuser else u"Código: ADM_004")
                            if certificado.tipo_origen == 1 and certificado.tipo_validacion == 2:
                                if not CertificadoAsistenteCertificadora.objects.filter(status=True, carrera=carrera, unidad_certificadora__certificado=certificado, unidad_certificadora__coordinacion=coordinacion).exists():
                                    raise NameError(u"Certificado no tiene configurado Asistente certificadora" if eUser.is_superuser else u"Código: ADM_005")
                                ac = CertificadoAsistenteCertificadora.objects.get(status=True, carrera=carrera, unidad_certificadora__certificado=certificado, unidad_certificadora__coordinacion=coordinacion)
                                uc = ac.unidad_certificadora
                            else:
                                if not certificado.unidades_certificadoras().count() > 0:
                                    raise NameError(u"Certificado tiene configurado mas de una Unidad certificadora" if eUser.is_superuser else u"Código: ADM_006")
                                uc = CertificadoUnidadCertificadora.objects.get(certificado=certificado)
                            if not uc or not uc.alias:
                                raise NameError(u"Certificado no tiene configurado Unidad certificadora" if eUser.is_superuser else u"Código: ADM_007")
                            if 'valido' not in request.data or ('valido' in request.data and request.data['valido'] == "0"):
                                SUFFIX = uc.alias
                                secuencia = 1
                                try:
                                    if not LogReporteDescarga.objects.filter(fechahora__year=datetime.now().year, suffix=SUFFIX, secuencia__gt=0).exists():
                                        secuencia = 1
                                    else:
                                        if LogReporteDescarga.objects.filter(secuencia__gt=0, suffix=SUFFIX).order_by("-secuencia").exists():
                                            sec = LogReporteDescarga.objects.filter(secuencia__gt=0, suffix=SUFFIX).order_by("-secuencia")[0].secuencia
                                            if sec:
                                                secuencia = int(sec) + 1
                                except:
                                    pass
                                codigo = generar_codigo(secuencia, 'UNEMI', SUFFIX, 7)

                        url = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])
                        logreporte = LogReporteDescarga(reporte=reporte,
                                                        content_type=content_type,
                                                        object_id=encrypt(object_id),
                                                        url=url,
                                                        fechahora=datetime.now())
                        logreporte.save(request)
                        if isQR:
                            if 'valido' not in request.data or ('valido' in request.data and request.data['valido'] == "0"):
                                logreporte.secuencia = secuencia
                                logreporte.codigo = codigo
                                logreporte.prefix = 'UNEMI'
                                logreporte.suffix = SUFFIX
                                logreporte.save(request)

                    else:
                        """SE MANTIENE PARA VERSIONES ANTERIORES"""
                        if 'variableqr' in request.data:
                            variable = request.data['variableqr']
                            pdfname = reporte.nombre + variable
                            matricula_id = None
                            inscripcion_id = None
                            parametros_reporte = reporte.parametroreporte_set.get(nombre='variableqr')
                            if (parametros_reporte.extra).upper() == "MATRICULA":
                                matricula_id = variable
                                matricula = Matricula.objects.get(pk=matricula_id)
                                inscripcion = matricula.inscripcion
                                periodo = matricula.nivel.periodo
                                confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
                                if confirmar_automatricula_admision and periodo.limite_agregacion < datetime.now().date():
                                    cordinacionid = inscripcion.carrera.coordinacion_carrera().id
                                    if cordinacionid in [9]:
                                        return Helper_Response(isSuccess=False, data={}, message=u"Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado",  status=status.HTTP_200_OK)

                                #Validación  de que estudiantes esten matriculado
                                if not matricula.status:
                                    raise NameError('Usted actualmente no se encuentra matriculado en el periodo actual')
                                if matricula.retiradomatricula:
                                    raise NameError(f'Usted actualmente se encuentra retirado de la carrera {matricula.inscripcion.carrera} en el período actual')
                            else:
                                inscripcion_id = variable

                            itemdescarga = ReporteDescarga(reporte=reporte, matricula_id=matricula_id, inscripcion_id=encrypt(inscripcion_id))
                            # itemdescarga.save()
                            itemdescarga.save(request)
                            cambiaruta = 1
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'documentos', 'userreports', remove_accents(eUser.username), ''))
                    # folder = '/mnt/nfs/home/storage/media/qrcode/evaluaciondocente/'
                    rutapdf = folder + pdfname + '.pdf'
                    if os.path.isfile(rutapdf):
                        os.remove(rutapdf)

                    runjrcommand = [JR_JAVA_COMMAND, '-jar',
                                    os.path.join(JR_RUN, 'jasperstarter.jar'),
                                    'pr', reporte.archivo.file.name,
                                    '--jdbc-dir', JR_RUN,
                                    '-f', tipo,
                                    '-t', 'postgres',
                                    '-H', DATABASES['sga_select']['HOST'],
                                    '-n', DATABASES['sga_select']['NAME'],
                                    '-u', DATABASES['sga_select']['USER'],
                                    '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                                    '--db-port', DATABASES['sga_select']['PORT'],
                                    '-o', output_folder + os.sep + pdfname]
                    parametros = reporte.parametros()
                    paramlist = [transform_jasperstarter(p, request) for p in parametros]
                    if paramlist:
                        runjrcommand.append('-P')
                        for parm in paramlist:
                            if 'qr=' in parm and 'true' in parm:
                                if reporte.version == 2:
                                    url = pyqrcode.create(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo]))
                                    url.png(os.path.join(
                                        os.path.join(SITE_STORAGE, 'media', 'qrcode', pdfname + '.png', 10, '#000000')))
                                else:
                                    url = pyqrcode.create("http://sga.unemi.edu.ec" + "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo]))
                                    url.png('/var/lib/django/sistemagestion/media/qrcode/' + pdfname + '.png', 10, '#000000')
                                runjrcommand.append(u'qr=' + pdfname + '.png')
                            else:
                                runjrcommand.append(parm)
                    else:
                        runjrcommand.append('-P')

                    runjrcommand.append(u'userweb=' + str(eUser.username))
                    if 'valido' in request.data:
                        runjrcommand.append(u'valido=' + str(request.data['valido']))
                    if reporte.version == 2:
                        runjrcommand.append(u'MEDIA_DIR=' + str("/".join([MEDIA_ROOT, ''])))
                        runjrcommand.append(u'IMAGE_DIR=' + str(SUBREPOTRS_FOLDER))
                        runjrcommand.append(u'SUBREPORT_DIR=' + reporte.ruta_subreport())
                        if isQR:
                            runjrcommand.append(u'URL_QR=' + str(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])))
                            if 'valido' not in request.data or ('valido' in request.data and request.data['valido'] == "0"):
                                runjrcommand.append(u'CODIGO_QR=' + str(codigo))
                            else:
                                runjrcommand.append(u'CODIGO_QR=DEMO_PREVISUALIZACIÓN')
                            runjrcommand.append(u'CERTIFICADO_ID=' + str(certificado.id))
                    else:
                        runjrcommand.append(u'SUBREPORT_DIR=' + str(SUBREPOTRS_FOLDER))
                    mens = ''
                    mensaje = ''
                    for m in runjrcommand:
                        mens += ' ' + m
                    urlbase = get_variable('SITE_URL_SGA')
                    reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])
                    # reportfile = f"{urlbase}{reportfile}"
                    if reporte.es_background:
                        data['logreporte'] = logreporte
                        ReportBackground(request=request, data=data, reporte=reporte, mensaje=mens, reportfile=reportfile, certificado=certificado).start()
                        lista_correos = []
                        if 'dirigidos' in request.data:
                            dirigidos = json.loads(request.data['dirigidos'])
                            personas = Persona.objects.filter(pk__in=dirigidos)
                            for persona in personas:
                                lista_correos.extend(persona.lista_emails())
                        if not 'no_persona_session' in request.data:
                            if ePersona:
                                lista_correos.extend(ePersona.lista_emails())
                        mensaje = 'El reporte se está realizando. Verifique los correos: %s después de unos minutos.' % (", ".join(lista_correos))
                    else:
                        if DEBUG:
                            runjr = subprocess.run(mens, shell=True, check=True)
                            # print('runjr:', runjr.returncode)
                        else:
                            runjr = subprocess.call(mens.encode("latin1"), shell=True)
                        #reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(request.user.username), pdfname + "." + tipo])
                        if certificado:
                            if certificado.funcionadjuntar:
                                if certificado.funcionadjuntar.get_nombrefuncion_display() == 'adjuntar_malla_curricular':
                                    result, mensaje, reportfile_aux = certificado.funcionadjuntar.adjuntar_malla_curricular(logreporte)
                                    if not result:
                                        raise NameError(mensaje)
                                    reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), reportfile_aux])

                        reportfile = f"{urlbase}{reportfile}"
                        if reporte.enviar_email:
                            ids_personas = []
                            if 'dirigidos' in request.data:
                                dirigidos = json.loads(request.data['dirigidos'])
                                personas = Persona.objects.filter(pk__in=dirigidos)
                                for persona in personas:
                                    ids_personas.append(persona.id)
                                if not 'no_persona_session' in request.data:
                                    if ePersona:
                                        ids_personas.append(ePersona.id)
                            # reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])
                            # reportfile = f"{urlbase}{reportfile}"
                            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                                send_html_mail(reporte.descripcion,
                                               "reportes/emails/reporte_generacion.html",
                                               {'sistema': u'SIE - UNEMI',
                                                'persona': persona,
                                                'reporte': reporte,
                                                'reportfile': reportfile,
                                                't': miinstitucion()},
                                               persona.lista_emails(),
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )

                    sp = os.path.split(reporte.archivo.file.name)
                    # return ok_json({'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])})
                    aData = {'es_background': reporte.es_background,
                             'reportfile': reportfile
                             }
                    return Helper_Response(isSuccess=True, data=aData, message=mensaje, status=status.HTTP_200_OK)
                else:
                    tipo = request.data['rt']
                    d = datetime.now()
                    output_folder = os.path.join(JR_USEROUTPUT_FOLDER, remove_accents(eUser.username))
                    try:
                        os.makedirs(output_folder)
                    except Exception as ex:
                        pass
                    mensaje = ''

                    if tipo == 'pdf':
                        nombre = reporte.nombre + d.strftime('%Y%m%d_%H%M%S') + ".pdf"
                        paramlist = {}
                        for p in reporte.parametros():
                            paramlist.update({p.nombre: fixparametro(p.tipo, request.data[p.nombre])})
                        global django_engine
                        django_engine = engines['django']
                        d = locals()
                        exec(reporte.vista, globals(), d)
                        reportefinal = d['vistareporte'](reporte, parametros=paramlist)
                        filepdf = open(output_folder + os.sep + nombre, "w+b")
                        pdf = pisa.pisaDocument(StringIO.BytesIO(reportefinal), dest=filepdf, link_callback=fetch_resources)
                        filepdf.close()
                    else:
                        nombre = reporte.nombre + d.strftime('%Y%m%d_%H%M%S') + ".xls"
                        paramlist = {}
                        for p in reporte.parametros():
                            paramlist.update({p.nombre: fixparametro(p.tipo, request.data[p.nombre])})
                        d = locals()
                        exec(reporte.vista, globals(), d)
                        book = d['vistareporte'](reporte, parametros=paramlist)
                        output_folder = os.path.join(JR_USEROUTPUT_FOLDER, remove_accents(eUser.username))
                        filename = os.path.join(output_folder, nombre)
                        book.save(filename)
                    reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), nombre])
                    urlbase = get_variable('SITE_URL_SGA')
                    reportfile = f"{urlbase}{reportfile}"
                    aData = {'es_background': reporte.es_background,
                             'reportfile': reportfile
                             }
                return Helper_Response(isSuccess=True, data=aData, message=mensaje, status=status.HTTP_200_OK)
            except Exception as ex:
                print(ex)
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                transaction.set_rollback(True)
                return Helper_Response(isSuccess=False, data={}, message=f'{ex.__str__()}', status=status.HTTP_200_OK)


class ReportBackground(threading.Thread):
    def __init__(self, request, data, reporte, mensaje, reportfile, certificado):
        self.request = request
        self.data = data
        self.reporte = reporte
        self.mensaje = mensaje
        self.reportfile = reportfile
        self.certificado = certificado
        threading.Thread.__init__(self)

    def run(self):
        request, data, reporte, mensaje, reportfile, certificado = self.request, self.data, self.reporte, self.mensaje, self.reportfile, self.certificado
        try:
            urlbase = get_variable('SITE_URL_SGA')
            ids_personas = []
            if 'dirigidos' in request.data:
                dirigidos = json.loads(request.data['dirigidos'])
                personas = Persona.objects.filter(pk__in=dirigidos)
                for persona in personas:
                    ids_personas.append(persona.id)
            if not 'no_persona_session' in request.data:
                if 'ePersona' in data:
                    persona = data['ePersona']
                    ids_personas.append(persona.id)
            if DEBUG:
                runjr = subprocess.run(mensaje, shell=True, check=True)
                # print('runjr:', runjr.returncode)
            else:
                runjr = subprocess.call(mensaje.encode("latin1"), shell=True)

            if certificado:
                if certificado.funcionadjuntar:
                    if certificado.funcionadjuntar.get_nombrefuncion_display() == 'adjuntar_malla_curricular':
                        if 'logreporte' in data:
                            logreporte = data['logreporte']
                            result, mens, reportfile_aux = certificado.funcionadjuntar.adjuntar_malla_curricular(logreporte)
                            if not result:
                                raise NameError(mens)
                            reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(request.user.username), reportfile_aux])
            reportfile = f"{urlbase}{reportfile}"

            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                send_html_mail(reporte.descripcion,
                               "reportes/emails/reporte_generacion.html",
                               {'sistema': u'SGAESTUDIANTE - UNEMI',
                                'persona': persona,
                                'reporte': reporte,
                                'reportfile': reportfile,
                                't': miinstitucion()},
                               persona.lista_emails(),
                               [],
                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                               )
                notificacion = Notificacion(titulo=f"{reporte.descripcion}",
                                            cuerpo=f"Se genero correctamente el reporte y/o certificado, para acceder al reporte y/o certificado ingresar al siguiente enlace {reportfile}",
                                            destinatario=persona,
                                            url=reportfile,
                                            content_type=ContentType.objects.get(app_label=reporte._meta.app_label, model=reporte._meta.model_name),
                                            object_id=reporte.id,
                                            prioridad=2,
                                            app_label='sie',#request.session['tiposistema'],
                                            fecha_hora_visible=datetime.now() + timedelta(days=2)
                                            )
                notificacion.save(request)

        except Exception as ex:
            print(ex)
            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                send_html_mail(reporte.descripcion,
                               "reportes/emails/reporte_generacion_error.html",
                               {'sistema': u'SGAESTUDIANTE - UNEMI',
                                'persona': persona,
                                'reporte': reporte,
                                'error': ex.__str__(),
                                't': miinstitucion()},
                               persona.lista_emails(),
                               [],
                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                               )
                notificacion = Notificacion(titulo=f"{reporte.descripcion}",
                                            cuerpo=f"Ocurrio un error al generarl reporte y/o certificado ingresar al siguiente enlace {reportfile}. {u'Error %s' % ex.__str__()  if persona.usuario.is_superuser else ''}",
                                            destinatario=persona,
                                            url=reportfile,
                                            content_type=ContentType.objects.get(app_label=reporte._meta.app_label, model=reporte._meta.model_name),
                                            object_id=reporte.id,
                                            prioridad=2,
                                            app_label='sie',#request.session['tiposistema'],
                                            fecha_hora_visible=datetime.now() + timedelta(days=2)
                                            )
                notificacion.save(request)
