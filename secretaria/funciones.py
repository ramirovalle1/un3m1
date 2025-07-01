# coding=utf-8
from __future__ import division

import base64
import io
import sys
import json
import os
import subprocess
import threading
import uuid
import random
import string
from pathlib import Path

import PyPDF2
import requests
from hashlib import md5
import io as StringIO
import pyqrcode
from tempfile import NamedTemporaryFile
from django.core.files import File
from django.contrib.contenttypes.models import ContentType
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import JsonResponse
from xhtml2pdf import pisa
from api.helpers.functions_helper import get_variable
from api.helpers.functions_helper import get_variable, remove_accents, fixparametro, \
    fetch_resources
from bd.models import UserToken
from secrets import token_hex
from django.template import engines
from certi.models import Certificado, CertificadoAsistenteCertificadora, CertificadoUnidadCertificadora
from secretaria.models import Solicitud, HistorialSolicitud, solicitud_user_directory_path
from settings import EMAIL_DOMAIN, DEBUG, JR_USEROUTPUT_FOLDER, MEDIA_URL, SITE_STORAGE, JR_JAVA_COMMAND, JR_RUN, \
    DATABASES, MEDIA_ROOT, SUBREPOTRS_FOLDER
from sga.funciones import log, generar_codigo, variable_valor, generar_nombre
from sga.models import miinstitucion, CUENTAS_CORREOS, Persona, Matricula, Inscripcion, LogReporteDescarga, \
    ReporteDescarga, Notificacion
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt
from datetime import datetime, timedelta

unicode = str


def generar_codigo_solicitud(eServicio):
    SUFFIX = eServicio.alias
    PREFIX = 'UNEMI'
    codigo = ''
    contador = 0
    success = True
    while True:
        contador += 1
        secuencia = 0
        try:
            eSolicitudes = Solicitud.objects.filter(fecha__year=datetime.now().year, prefix=PREFIX, suffix=SUFFIX, secuencia__gt=0)
            if eSolicitudes.values("id").exists():
                secuencia = eSolicitudes.values("secuencia").order_by("-secuencia")[0].get("secuencia")
            secuencia += 1
        except:
            secuencia = 1
        codigo = generar_codigo(secuencia, PREFIX, SUFFIX, 7)
        if not Solicitud.objects.values("id").filter(codigo=codigo):
            break
        if contador >= 3:
            success = False
            break
    if not success:
        raise NameError(u"Código de solicitud no se pudo generar")
    data = {"success": success, "codigo": codigo, "secuencia": secuencia, "suffix": SUFFIX, "prefix": PREFIX}
    return data


def transform_jasperstarter(parametro, data):
    from sga.templatetags.sga_extras import encrypt
    if parametro.tipo == 1 or parametro.tipo == 6:
        return u'%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, data[parametro.nombre]))
    elif parametro.tipo == 2 or parametro.tipo == 5:
        return u'%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, data[parametro.nombre] if type(data[parametro.nombre]) is int else int(encrypt(data[parametro.nombre]))))
    else:
        return u'%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, data[parametro.nombre]))


def generar_certificado_digital(ePersona, eReporte, eUser, params, eSolicitud=None):
    data = {}
    cambiaruta = 0
    isQR = False
    codigo = None
    certificado = None
    base_url = get_variable('SITE_URL_SGA')
    app = 'sga'
    if 'app' in params:
        app = params['app']
    if eReporte.archivo:
        tipo = params['rt']
        output_folder = os.path.join(JR_USEROUTPUT_FOLDER, remove_accents(eUser.username))
        try:
            os.makedirs(output_folder)
        except Exception as ex:
            pass
        d = datetime.now()
        pdfname = eReporte.nombre + d.strftime('%Y%m%d_%H%M%S')
        if eReporte.version == 2:
            """SE REALIZA AJUSTES PARA NUEVAS VERSIONES"""
            content_type = None
            object_id = None
            vqr = None
            if 'vqr' in params:
                isQR = True
                vqr = params['vqr']
                # pdfname = reporte.nombre + vqr
                parametros_reporte = eReporte.parametroreporte_set.get(nombre='vqr')
                if not Certificado.objects.filter(reporte=eReporte, visible=True).exists():
                    raise NameError(u"No se encontro certificado activo" if eUser.is_superuser else u"Código: ADM_001")
                if Certificado.objects.filter(reporte=eReporte, visible=True).count() > 1:
                    raise NameError(u"Mas de un certificado activo" if eUser.is_superuser else u"Código: ADM_002")
                certificado = Certificado.objects.get(reporte=eReporte, visible=True)

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
            logreporte = LogReporteDescarga(reporte=eReporte,
                                            content_type=content_type,
                                            object_id=encrypt(object_id),
                                            url=url,
                                            fechahora=datetime.now())
            logreporte.save(usuario_id=eUser.id)
            if isQR:
                logreporte.secuencia = secuencia
                logreporte.codigo = codigo
                logreporte.prefix = 'UNEMI'
                logreporte.suffix = SUFFIX
                logreporte.save(usuario_id=eUser.id)

        else:
            """SE MANTIENE PARA VERSIONES ANTERIORES"""
            if 'variableqr' in params:
                variable = params['variableqr']
                pdfname = eReporte.nombre + variable
                matricula_id = None
                inscripcion_id = None
                parametros_reporte = eReporte.parametroreporte_set.get(nombre='variableqr')
                if (parametros_reporte.extra).upper() == "MATRICULA":
                    matricula_id = variable
                    matricula = Matricula.objects.get(pk=matricula_id)
                    inscripcion = matricula.inscripcion
                    periodo = matricula.nivel.periodo
                    confirmar_automatricula_admision = inscripcion.tiene_automatriculaadmision_por_confirmar(periodo)
                    if confirmar_automatricula_admision and periodo.limite_agregacion < datetime.now().date():
                        cordinacionid = inscripcion.carrera.coordinacion_carrera().id
                        if cordinacionid in [9]:
                            return False, u"Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado", {}
                else:
                    inscripcion_id = variable

                itemdescarga = ReporteDescarga(reporte=eReporte, matricula_id=matricula_id, inscripcion_id=encrypt(inscripcion_id))
                itemdescarga.save(usuario_id=eUser.id)
                cambiaruta = 1
        folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'documentos', 'userreports', remove_accents(eUser.username), ''))
        # folder = '/mnt/nfs/home/storage/media/qrcode/evaluaciondocente/'
        rutapdf = folder + pdfname + '.pdf'
        if os.path.isfile(rutapdf):
            os.remove(rutapdf)

        runjrcommand = [JR_JAVA_COMMAND, '-jar',
                        os.path.join(JR_RUN, 'jasperstarter.jar'),
                        'pr', eReporte.archivo.file.name,
                        '--jdbc-dir', JR_RUN,
                        '-f', tipo,
                        '-t', 'postgres',
                        '-H', DATABASES['sga_select']['HOST'],
                        '-n', DATABASES['sga_select']['NAME'],
                        '-u', DATABASES['sga_select']['USER'],
                        '-p', f"'{DATABASES['sga_select']['PASSWORD']}'",
                        '--db-port', DATABASES['sga_select']['PORT'],
                        '-o', output_folder + os.sep + pdfname]
        parametros = eReporte.parametros()
        paramlist = [transform_jasperstarter(p, params) for p in parametros]
        if paramlist:
            runjrcommand.append('-P')
            for parm in paramlist:
                if 'qr=' in parm and 'true' in parm:
                    if eReporte.version == 2:
                        url = pyqrcode.create(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo]))
                        url.png(os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', pdfname + '.png', 10, '#000000')))
                    else:
                        url = pyqrcode.create("http://sga.unemi.edu.ec" + "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo]))
                        url.png('/var/lib/django/sistemagestion/media/qrcode/' + pdfname + '.png', 10, '#000000')
                    runjrcommand.append(u'qr=' + pdfname + '.png')
                else:
                    runjrcommand.append(parm)
        else:
            runjrcommand.append('-P')

        runjrcommand.append(u'userweb=' + str(eUser.username))
        if eReporte.version == 2:
            runjrcommand.append(u'MEDIA_DIR=' + str("/".join([MEDIA_ROOT, ''])))
            if DEBUG:
                runjrcommand.append(u'IMAGE_DIR=' + str("/".join([SUBREPOTRS_FOLDER, ''])))
            else:
                runjrcommand.append(u'IMAGE_DIR=' + str(SUBREPOTRS_FOLDER))
            runjrcommand.append(u'SUBREPORT_DIR=' + eReporte.ruta_subreport())
            if isQR:
                runjrcommand.append(u'URL_QR=' + str(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])))
                runjrcommand.append(u'CODIGO_QR=' + str(codigo))
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
        if eReporte.es_background:
            data['logreporte'] = logreporte
            ReportBackground(params=params, data=data, reporte=eReporte, mensaje=mens, reportfile=reportfile, certificado=certificado, solicitud=eSolicitud).start()
            lista_correos = []
            if 'dirigidos' in params:
                dirigidos = json.loads(params['dirigidos'])
                personas = Persona.objects.filter(pk__in=dirigidos)
                for persona in personas:
                    lista_correos.extend(persona.lista_emails())
            if not 'no_persona_session' in params:
                if ePersona:
                    lista_correos.extend(ePersona.lista_emails())
            mensaje = 'El reporte se está realizando. Verifique los correos: %s después de unos minutos.' % (", ".join(lista_correos))
        else:
            if DEBUG:
                runjr = subprocess.run(mens, shell=True, check=True)
                # print('codigo:', mens)
            else:
                runjr = subprocess.call(mens.encode("latin1"), shell=True)
            if certificado:
                if certificado.funcionadjuntar:
                    if certificado.funcionadjuntar.get_nombrefuncion_display() == 'adjuntar_malla_curricular':
                        result, mensaje, reportfile_aux = certificado.funcionadjuntar.adjuntar_malla_curricular(logreporte)
                        if not result:
                            raise NameError(mensaje)
                        reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), reportfile_aux])
            reportfile = f"{urlbase}{reportfile}"
            if eReporte.enviar_email:
                ids_personas = []
                if 'dirigidos' in params:
                    dirigidos = json.loads(params['dirigidos'])
                    personas = Persona.objects.filter(pk__in=dirigidos)
                    for persona in personas:
                        ids_personas.append(persona.id)
                    if not 'no_persona_session' in params:
                        if ePersona:
                            ids_personas.append(ePersona.id)
                # reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])
                # reportfile = f"{urlbase}{reportfile}"
                for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                    send_html_mail(eReporte.descripcion,
                                   "reportes/emails/reporte_generacion.html",
                                   {'sistema': u'SGA+',
                                    'persona': persona,
                                    'reporte': eReporte,
                                    'reportfile': reportfile,
                                    't': miinstitucion()},
                                   persona.lista_emails(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )
            if eSolicitud:
                if os.path.isfile(rutapdf):
                    with open(rutapdf, 'rb') as f:
                        archivo = f.read()
                    buffer = io.BytesIO()
                    buffer.write(archivo)
                    pdf = buffer.getvalue()
                    buffer.seek(0)
                    buffer.close()
                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    nombre_archivo_resultado = f"resultado_{fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__()}_{hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()}.pdf"
                    eSolicitud.archivo_respuesta.save(nombre_archivo_resultado, ContentFile(pdf))
                eSolicitud.en_proceso = False

                if eSolicitud.perfil.inscripcion.carrera.coordinacion_carrera().id == 7 and eSolicitud.origen_object_id in [57, 39, 12]:
                    eSolicitud.estado = 22
                    eSolicitud.save()
                else:
                    eSolicitud.estado = 2
                    eSolicitud.save()
                observacion = f'Cambio de estado por proceso de entrega'
                #if ePersona.es_estudiante():
                #    observacion= f'Cambio de estado por generación'
                eHistorialSolicitud = HistorialSolicitud(solicitud=eSolicitud,
                                                         observacion=observacion,
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         estado=eSolicitud.estado,
                                                         responsable=ePersona,
                                                         #archivo=eSolicitud.archivo_respuesta,
                                                         )
                eHistorialSolicitud.save()
                titulo = f'Cambio de estado de la solicitud código {eSolicitud.codigo}'
                cuerpo = f'Solicitud código {eSolicitud.codigo} se encuentra en estado {eSolicitud.get_estado_display()}'
                eNotificacion = Notificacion(titulo=titulo,
                                             cuerpo=cuerpo,
                                             destinatario=eSolicitud.perfil.persona,
                                             perfil=eSolicitud.perfil,
                                             url='/alu_secretaria/mis_pedidos',
                                             prioridad=1,
                                             app_label='SIE',
                                             fecha_hora_visible=datetime.now() + timedelta(days=2),
                                             tipo=1,
                                             en_proceso=False,
                                             content_type=ContentType.objects.get_for_model(eSolicitud),
                                             object_id=eSolicitud.pk,
                                             )
                eNotificacion.save()

        # sp = os.path.split(eReporte.archivo.file.name)
        # return ok_json({'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), pdfname + "." + tipo])})
        aData = {'es_background': eReporte.es_background,
                 'reportfile': reportfile
                 }
        return True, aData, mensaje
    else:
        tipo = params['rt']
        d = datetime.now()
        output_folder = os.path.join(JR_USEROUTPUT_FOLDER, remove_accents(eUser.username))
        try:
            os.makedirs(output_folder)
        except Exception as ex:
            pass
        mensaje = ''

        if tipo == 'pdf':
            nombre = eReporte.nombre + d.strftime('%Y%m%d_%H%M%S') + ".pdf"
            paramlist = {}
            for p in eReporte.parametros():
                paramlist.update({p.nombre: fixparametro(p.tipo, params[p.nombre])})
            global django_engine
            django_engine = engines['django']
            d = locals()
            exec(eReporte.vista, globals(), d)
            reportefinal = d['vistareporte'](eReporte, parametros=paramlist)
            filepdf = open(output_folder + os.sep + nombre, "w+b")
            pdf = pisa.pisaDocument(StringIO.BytesIO(reportefinal), dest=filepdf, link_callback=fetch_resources)
            filepdf.close()
        else:
            nombre = eReporte.nombre + d.strftime('%Y%m%d_%H%M%S') + ".xls"
            paramlist = {}
            for p in eReporte.parametros():
                paramlist.update({p.nombre: fixparametro(p.tipo, params[p.nombre])})
            d = locals()
            exec(eReporte.vista, globals(), d)
            book = d['vistareporte'](eReporte, parametros=paramlist)
            output_folder = os.path.join(JR_USEROUTPUT_FOLDER, remove_accents(eUser.username))
            filename = os.path.join(output_folder, nombre)
            book.save(filename)
        reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(eUser.username), nombre])
        urlbase = get_variable('SITE_URL_SGA')
        reportfile = f"{urlbase}{reportfile}"
        aData = {'es_background': eReporte.es_background,
                 'reportfile': reportfile
                 }


class ReportBackground(threading.Thread):

    def __init__(self, params, data, reporte, mensaje, reportfile, certificado, user, solicitud, rutapdf):
        self.params = params
        self.data = data
        self.reporte = reporte
        self.mensaje = mensaje
        self.reportfile = reportfile
        self.certificado = certificado
        self.solicitud = solicitud
        self.user = user
        self.rutapdf = rutapdf
        threading.Thread.__init__(self)

    def run(self):
        params = data, reporte, mensaje, reportfile, certificado, user, solicitud, rutapdf = self.params, self.data, self.reporte, self.mensaje, self.reportfile, self.certificado, self.user, self.solicitud, self.rutapdf
        try:
            urlbase = get_variable('SITE_URL_SGA')
            ids_personas = []
            app = 'sga'
            temp_reportfile = reportfile
            if 'app' in params:
                app = params['app']
            if 'dirigidos' in params:
                dirigidos = json.loads(params['dirigidos'])
                personas = Persona.objects.filter(pk__in=dirigidos)
                for persona in personas:
                    ids_personas.append(persona.id)
            if not 'no_persona_session' in params:
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
                            reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', remove_accents(user.username), reportfile_aux])
            reportfile = f"{urlbase}{reportfile}"
            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                send_html_mail(reporte.descripcion,
                               "reportes/emails/reporte_generacion.html",
                               {'sistema': u'SGA+',
                                'persona': persona,
                                'reporte': reporte,
                                'reportfile': reportfile,
                                't': miinstitucion()},
                               persona.lista_emails(),
                               [],
                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                               )
                if not solicitud:
                    notificacion = Notificacion(titulo=f"{reporte.descripcion}",
                                                cuerpo=f"Se genero correctamente el reporte y/o certificado, para acceder ingresar al siguiente enlace {reportfile}",
                                                destinatario=persona,
                                                url=reportfile,
                                                content_type=ContentType.objects.get(app_label=reporte._meta.app_label, model=reporte._meta.model_name),
                                                object_id=reporte.id,
                                                prioridad=2,
                                                app_label=app,
                                                fecha_hora_visible=datetime.now() + timedelta(days=2)
                                                )
                    notificacion.save(usuario_id=user.id)
            if solicitud:
                if os.path.isfile(rutapdf):
                    with open(rutapdf, 'rb') as f:
                        archivo = f.read()
                    buffer = io.BytesIO()
                    buffer.write(archivo)
                    pdf = buffer.getvalue()
                    buffer.seek(0)
                    buffer.close()
                    fecha = datetime.now().date()
                    hora = datetime.now().time()
                    nombre_archivo_resultado = f"resultado_{fecha.year.__str__() + fecha.month.__str__() + fecha.day.__str__()}_{hora.hour.__str__() + hora.minute.__str__() + hora.second.__str__()}.pdf"
                    solicitud.archivo_respuesta.save(nombre_archivo_resultado, ContentFile(pdf))
                solicitud.en_proceso = False
                solicitud.estado = 2
                solicitud.save()
                eHistorialSolicitud = HistorialSolicitud(solicitud=solicitud,
                                                         observacion=f'Cambio de estado por proceso de entrega',
                                                         fecha=datetime.now().date(),
                                                         hora=datetime.now().time(),
                                                         estado=solicitud.estado,
                                                         responsable_id=1,
                                                         archivo=solicitud.archivo_respuesta,
                                                         )
                eHistorialSolicitud.save()
                titulo = f'Cambio de estado de la solicitud código {solicitud.codigo}'
                cuerpo = f'Solicitud código {solicitud.codigo} se encuentra en estado {solicitud.get_estado_display()}'
                eNotificacion = Notificacion(titulo=titulo,
                                             cuerpo=cuerpo,
                                             destinatario=solicitud.perfil.persona,
                                             perfil=solicitud.perfil,
                                             url='/alu_secretaria/mis_pedidos',
                                             prioridad=1,
                                             app_label='SIE',
                                             fecha_hora_visible=datetime.now() + timedelta(days=2),
                                             tipo=1,
                                             en_proceso=False,
                                             content_type=ContentType.objects.get_for_model(solicitud),
                                             object_id=solicitud.pk,
                                             )
                eNotificacion.save()

        except Exception as ex:
            # print(ex)
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
                                            app_label=app,
                                            fecha_hora_visible=datetime.now() + timedelta(days=2)
                                            )
                notificacion.save(usuario_id=user.id)

