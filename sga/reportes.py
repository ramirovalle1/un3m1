# coding=utf-8
import json

from googletrans import Translator
import threading
import unicodedata
import subprocess
import io as StringIO

from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
import pyqrcode
from xhtml2pdf import pisa

# OJO no borrar se lo usa en las vistas guardadas en bases
from django.template import engines
from django.db import transaction
from decorators import secure_module, last_access
from settings import JR_JAVA_COMMAND, DATABASES, JR_USEROUTPUT_FOLDER, JR_RUN, MEDIA_URL, SUBREPOTRS_FOLDER, \
    MEDIA_ROOT, SITE_ROOT, DEBUG, EMAIL_DOMAIN
from sga.commonviews import adduserdata
from sga.funciones import ok_json, bad_json, generar_codigo
from sga.models import *
from sagest.models import *
from bib.models import *
from certi.models import *
from matricula.models import *
from bd.models import *
from soap.models import *
from inno.models import *
from sga.tasks import send_html_mail

unicode = str


def tipoparametro(tipo):
    if tipo == 1:
        return "string"
    elif tipo == 2:
        return "integer"
    elif tipo == 3:
        return "double"
    elif tipo == 4:
        return "boolean"
    elif tipo == 5:
        return "integer"
    elif tipo == 6:
        return "string"
    elif tipo == 7:
        return "integer"
    return "string"


def fixparametro(tipo, valor):
    if tipo == 6:
        # FECHA
        fm = valor.index("-")
        sm = valor.index("-", fm + 1)
        d = valor[:fm]
        m = valor[fm + 1:sm]
        y = valor[sm + 1:]
        return y + "-" + m + "-" + d
    return valor


def transform(parametro, request):
    return "%s=%s:%s" % (parametro.nombre, tipoparametro(parametro.tipo), fixparametro(parametro.tipo, request.GET[parametro.nombre]))


def transform_jasperstarter(parametro, request, method=None):
    if parametro.tipo == 1 or parametro.tipo == 6:
        if method and method == 'POST':
            return '%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, request.POST[parametro.nombre]))
        elif method and method == 'GET':
            return '%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, request.GET[parametro.nombre]))
        else:
            return '%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, request.GET[parametro.nombre]))
    else:
        if method and method == 'POST':
            return '%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, request.POST[parametro.nombre]))
        elif method and method == 'GET':
            return '%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, request.GET[parametro.nombre]))
        else:
            return '%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, request.GET[parametro.nombre]))


def transform_jasperstarter_kwargs(parametro, **kwargs):
    if parametro.tipo == 1 or parametro.tipo == 6:
        for key, value in kwargs.items():
            if parametro.nombre == key:
                return '%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, value))
    else:
        for key, value in kwargs.items():
            if parametro.nombre == key:
                return '%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, value))


def transform_jasperstarter_new(parametro, arrPar):
    if parametro.tipo == 1 or parametro.tipo == 6:
        return '%s="%s"' % (parametro.nombre, fixparametro(parametro.tipo, arrPar[parametro.nombre]))
    else:
        return '%s=%s' % (parametro.nombre, fixparametro(parametro.tipo, arrPar[parametro.nombre]))


def elimina_tildes(cadena):
    s = ''.join((c for c in unicodedata.normalize('NFD', unicode(cadena)) if unicodedata.category(c) != 'Mn'))
    # return s.decode()
    return s


def fetch_resources(uri, rel):
    return os.path.join(MEDIA_ROOT, uri.replace(MEDIA_URL, ""))


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if 'action' in request.GET:
        action = request.GET['action']

        if action == 'data':
            try:
                m = request.GET['model']
                if 'q' in request.GET:
                    q = request.GET['q'].upper().strip()
                    if ':' in m:
                        sp = m.split(':')
                        model = eval(sp[0])
                        if len(sp) > 1:
                            query = model.flexbox_query(q, extra=sp[1])
                        else:
                            query = model.flexbox_query(q)
                    else:
                        model = eval(request.GET['model'])
                        query = model.flexbox_query(q)
                else:
                    m = request.GET['model']
                    if ':' in m:
                        sp = m.split(':')
                        model = eval(sp[0])
                        resultquery = model.flexbox_query('')
                        try:
                            query = eval('resultquery.filter(%s, status=True).distinct()' % (sp[1]))
                        except Exception as ex:
                            query = resultquery
                    else:
                        model = eval(request.GET['model'])
                        query = model.flexbox_query('')
                data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), 'alias': x.flexbox_alias() if hasattr(x, 'flexbox_alias') else []} for x in query]}
                return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'data_estudiante':
            try:
                m = request.GET['model']
                if 'q' in request.GET:
                    q = request.GET['q'].upper().strip()
                    if ':' in m:
                        sp = m.split(':')
                        model = eval(sp[0])
                        if len(sp) > 1:
                            query = model.flexbox_query(q, extra=sp[1])
                        else:
                            query = model.flexbox_query(q)
                    else:
                        model = eval(request.GET['model'])
                        query = model.flexbox_query_solo_estudiantes(q)
                else:
                    m = request.GET['model']
                    if ':' in m:
                        sp = m.split(':')
                        model = eval(sp[0])
                        resultquery = model.flexbox_query('')
                        try:
                            query = eval('resultquery.filter(%s, status=True).distinct()' % (sp[1]))
                        except Exception as ex:
                            query = resultquery
                    else:
                        model = eval(request.GET['model'])
                        query = model.flexbox_query('')
                data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), 'alias': x.flexbox_alias() if hasattr(x, 'flexbox_alias') else []} for x in query]}
                return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'dataexclude':
            try:
                m = request.GET['model']
                peri = request.GET['periodoid']
                if 'q' in request.GET:
                    q = request.GET['q'].upper().strip()
                    if ':' in m:
                        sp = m.split(':')
                        model = eval(sp[0])
                        if len(sp) > 1:
                            query = model.flexbox_querydistributivo(q, extra=sp[1])
                        else:
                            query = model.flexbox_querydistributivo(q,peri)
                    else:
                        model = eval(request.GET['model'])
                        query = model.flexbox_querydistributivo(q,peri)
                else:
                    m = request.GET['model']
                    if ':' in m:
                        sp = m.split(':')
                        model = eval(sp[0])
                        resultquery = model.flexbox_querydistributivo('')
                        try:
                            query = eval('resultquery.filter(%s, status=True).distinct()' % (sp[1]))
                        except Exception as ex:
                            query = resultquery
                    else:
                        model = eval(request.GET['model'])
                        query = model.flexbox_querydistributivo('')
                data = {"result": "ok", "results": [{"id": x.id, "name": x.flexbox_repr(), 'alias': x.flexbox_alias() if hasattr(x, 'flexbox_alias') else []} for x in query]}
                return JsonResponse(data)
            except Exception as ex:
                return JsonResponse({"result": "bad", 'mensaje': u'Error al obtener los datos.'})

        elif action == 'run':
            try:
                if 'n' in request.GET:
                    reporte = Reporte.objects.get(nombre=request.GET['n'])
                else:
                    reporte = Reporte.objects.get(pk=request.GET['rid'])
                cambiaruta = 0
                isQR = False
                codigo = None
                certificado = None
                base_url = request.META['HTTP_HOST']
                if reporte.archivo:
                    tipo = request.GET['rt']
                    output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
                    try:
                        os.makedirs(output_folder)
                    except Exception as ex:
                        print(ex)
                    d = datetime.now()
                    pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
                    if reporte.version == 2:
                        """SE REALIZA AJUSTES PARA NUEVAS VERSIONES"""
                        content_type = None
                        object_id = None
                        vqr = None
                        if 'vqr' in request.GET:
                            isQR = True
                            vqr = request.GET['vqr']
                            # pdfname = reporte.nombre + vqr
                            parametros_reporte = reporte.parametroreporte_set.get(nombre='vqr')
                            if not Certificado.objects.filter(reporte=reporte, visible=True).exists():
                                raise NameError(u"No se encontro certificado activo" if request.user.is_superuser else u"Código: ADM_001")
                            if Certificado.objects.filter(reporte=reporte, visible=True).count() > 1:
                                raise NameError(u"Mas de un certificado activo" if request.user.is_superuser else u"Código: ADM_002")
                            certificado = Certificado.objects.get(reporte=reporte, visible=True)

                            if parametros_reporte.extra:
                                try:
                                    content_type = ContentType.objects.get_for_model(eval(parametros_reporte.extra))
                                    object_id = vqr
                                except Exception as ex:
                                    content_type = ContentType.objects.get_for_model(request.user)
                                    object_id = request.user.id
                            else:
                                try:
                                    if Persona.objects.filter(usuario_id=request.user.id).exists():
                                        persona = Persona.objects.filter(usuario_id=request.user.id).first()
                                        content_type = ContentType.objects.get_for_model(persona)
                                        object_id = persona.id
                                    else:
                                        content_type = ContentType.objects.get_for_model(request.user)
                                        object_id = request.user.id
                                except Exception as ex:
                                    content_type = ContentType.objects.get_for_model(request.user)
                                    object_id = request.user.id
                        else:
                            try:
                                if Persona.objects.filter(usuario_id=request.user.id).exists():
                                    persona = Persona.objects.filter(usuario_id=request.user.id).first()
                                    content_type = ContentType.objects.get_for_model(persona)
                                    object_id = persona.id
                                else:
                                    content_type = ContentType.objects.get_for_model(request.user)
                                    object_id = request.user.id
                            except Exception as ex:
                                content_type = ContentType.objects.get_for_model(request.user)
                                object_id = request.user.id

                        if isQR:
                            SUFFIX = None
                            if (parametros_reporte.extra).upper() == "MATRICULA":
                                matricula = Matricula.objects.get(pk=vqr)
                                carrera = matricula.inscripcion.carrera
                                coordinacion = matricula.inscripcion.coordinacion
                                #Validación  de que estudiantes esten matriculado
                                if not matricula.status:
                                    raise NameError('El estudiante actualmente no se encuentra matriculado en el periodo actual')
                                if matricula.retiradomatricula:
                                    raise NameError(f'El estudiante actualmente se encuentra retirado de la carrera {matricula.inscripcion.carrera} en el período actual')
                            else:
                                inscripcion = Inscripcion.objects.get(pk=vqr)
                                carrera = inscripcion.carrera
                                coordinacion = inscripcion.coordinacion
                            if not certificado:
                                raise NameError(u"No se encontro certificado." if request.user.is_superuser else u"Código: ADM_003")
                            uc = None
                            ac = None
                            if not certificado.tiene_unidades_certificadoras():
                                raise NameError(u"Certificado no tiene configurado Unidad certificadora" if request.user.is_superuser else u"Código: ADM_004")
                            if certificado.tipo_origen == 1 and certificado.tipo_validacion == 2:
                                if not CertificadoAsistenteCertificadora.objects.filter(status=True, carrera=carrera, unidad_certificadora__certificado=certificado, unidad_certificadora__coordinacion=coordinacion).exists():
                                    raise NameError(u"Certificado no tiene configurado Asistente certificadora" if request.user.is_superuser else u"Código: ADM_005")
                                ac = CertificadoAsistenteCertificadora.objects.get(status=True, carrera=carrera, unidad_certificadora__certificado=certificado, unidad_certificadora__coordinacion=coordinacion)
                                uc = ac.unidad_certificadora
                            else:
                                if not certificado.unidades_certificadoras().count() > 0:
                                    raise NameError(u"Certificado tiene configurado mas de una Unidad certificadora" if request.user.is_superuser else u"Código: ADM_006")
                                uc = CertificadoUnidadCertificadora.objects.get(certificado=certificado)
                            if not uc or not uc.alias:
                                raise NameError(u"Certificado no tiene configurado Unidad certificadora" if request.user.is_superuser else u"Código: ADM_007")
                            SUFFIX = uc.alias
                            secuencia = 1
                            try:
                                #fechahora__gte=datetime.now().date(),
                                if not LogReporteDescarga.objects.filter(fechahora__year=datetime.now().year, suffix=SUFFIX, secuencia__gt=0).exists():
                                    secuencia = 1
                                else:
                                    eLogReporteDescarga = LogReporteDescarga.objects.filter(fechahora__year=datetime.now().year, secuencia__gt=0, suffix=SUFFIX).order_by("-secuencia")[0].secuencia
                                    if eLogReporteDescarga:
                                        secuencia = int(eLogReporteDescarga) + 1
                            except:
                                pass
                            codigo = generar_codigo(secuencia, 'UNEMI', SUFFIX, 7)

                        url = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])
                        logreporte = LogReporteDescarga(reporte=reporte,
                                                        content_type=content_type,
                                                        object_id=object_id,
                                                        url=url,
                                                        fechahora=datetime.now())
                        logreporte.save(request)
                        if isQR:
                            logreporte.secuencia = secuencia
                            logreporte.codigo = codigo
                            logreporte.prefix = 'UNEMI'
                            logreporte.suffix = SUFFIX
                            logreporte.save(request)
                        data['logreporte'] = logreporte

                    else:
                        """SE MANTIENE PARA VERSIONES ANTERIORES"""
                        if 'variableqr' in request.GET:
                            variable = request.GET['variableqr']
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
                                        return bad_json(mensaje=u"Estimado aspirante, el período de confirmación de la automatrícula ha culminado, usted no se encuentra matriculado")

                                #Validación  de que estudiantes esten matriculado
                                if not matricula.status:
                                    raise NameError('El estudiante actualmente no se encuentra matriculado en el periodo actual')
                                if matricula.retiradomatricula:
                                    raise NameError(f'El estudiante se encuentra retirado de la carrera {matricula.inscripcion.carrera} en el período actual')
                            else:
                                inscripcion_id = variable

                            itemdescarga = ReporteDescarga(reporte=reporte, matricula_id=matricula_id, inscripcion_id=inscripcion_id)
                            # itemdescarga.save()
                            itemdescarga.save(request)
                            cambiaruta = 1
                    folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'documentos', 'userreports', elimina_tildes(request.user.username), ''))
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

                    print(runjrcommand)
                    parametros = reporte.parametros()
                    paramlist = [transform_jasperstarter(p, request) for p in parametros]
                    if paramlist:
                        runjrcommand.append('-P')
                        for parm in paramlist:
                            if 'qr=' in parm and 'true' in parm:
                                if reporte.version == 2:
                                    url = pyqrcode.create(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo]))
                                    url.png(os.path.join(os.path.join(SITE_STORAGE, 'media', 'qrcode', pdfname + '.png', 10, '#000000')))
                                else:
                                    url = pyqrcode.create("http://sga.unemi.edu.ec" + "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo]))
                                    url.png('/var/lib/django/sistemagestion/media/qrcode/' + pdfname + '.png', 10, '#000000')
                                runjrcommand.append(u'qr=' + pdfname + '.png')
                            else:
                                runjrcommand.append(parm)
                    else:
                        runjrcommand.append('-P')
                    # if cambiaruta == 1:
                    #     # rutaimagen = os.path.join(SITE_ROOT, 'media', 'firmasdigitales', '')
                    #     rutaimagen = os.path.join(os.path.join(SITE_STORAGE, 'media', 'firmasdigitales', ''))
                    #     runjrcommand.append(u'IMAGE_DIR=' + unicode(rutaimagen))

                    runjrcommand.append(u'userweb=' + unicode(request.user.username))
                    if reporte.version == 2:
                        runjrcommand.append(u'MEDIA_DIR=' + unicode("/".join([MEDIA_ROOT, ''])))
                        runjrcommand.append(u'IMAGE_DIR=' + unicode(SUBREPOTRS_FOLDER))
                        runjrcommand.append(u'SUBREPORT_DIR=' + reporte.ruta_subreport())
                        if isQR:
                            runjrcommand.append(u'URL_QR=' + unicode(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])))
                            runjrcommand.append(u'CODIGO_QR=' + unicode(codigo))
                            runjrcommand.append(u'CERTIFICADO_ID=' + unicode(certificado.id))
                    else:
                        runjrcommand.append(u'SUBREPORT_DIR=' + unicode(SUBREPOTRS_FOLDER))
                    mens = ''
                    mensaje = ''
                    for m in runjrcommand:
                        mens += ' ' + m
                    reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])
                    if reporte.es_background:
                        lista_correos = []
                        if 'dirigidos' in request.GET:
                            dirigidos = []
                            try:
                                dirigidos = json.loads(request.GET['dirigidos'])
                            except:
                                _dirigidos = request.GET.get('dirigidos', None)
                                if _dirigidos:
                                    dirigidos = [int(x) for x in _dirigidos.split(',')]
                            if isinstance(dirigidos,(list, tuple, set)):
                               personas = Persona.objects.filter(pk__in=dirigidos)
                            else:
                                personas = Persona.objects.filter(pk=dirigidos)
                            for persona in personas:
                                lista_correos.extend(persona.lista_emails())
                        if 'persona' in request.session:
                            persona = request.session['persona']
                            lista_correos.extend(persona.lista_emails())
                        ReportBackground(request=request, data=data, reporte=reporte, mensaje=mens, reportfile=reportfile, certificado=certificado).start()

                        mensaje = 'El reporte se está realizando. Verifique los correos: %s después de unos minutos.' % (", ".join(lista_correos))
                    else:
                        urlbase = ""#"http://127.0.0.1:8000"
                        print(mens)
                        if DEBUG:

                            runjr = subprocess.run(mens, shell=True, check=True)
                            # print('runjr:', runjr.returncode)
                        else:


                            runjr = subprocess.call(mens.encode("latin1"), shell=True)
                            app = request.session['tiposistema']


                            # urlbase = f"https://{app}.unemi.edu.ec"
                        # reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])
                        print(runjr)
                        if certificado:
                            if certificado.funcionadjuntar:
                                if certificado.funcionadjuntar.get_nombrefuncion_display() == 'adjuntar_malla_curricular':
                                    result, mensaje, reportfile_aux = certificado.funcionadjuntar.adjuntar_malla_curricular(logreporte)
                                    if not result:
                                        raise NameError(mensaje)
                                    reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), reportfile_aux])

                        #reportfile = f"{urlbase}{reportfile}"
                        if reporte.enviar_email:
                            ids_personas = []
                            if 'dirigidos' in request.GET:
                                dirigidos = []
                                try:
                                    dirigidos = json.loads(request.GET['dirigidos'])
                                except:
                                    _dirigidos = request.GET.get('dirigidos', None)
                                    if _dirigidos:
                                        dirigidos = [int(x) for x in _dirigidos.split(',')]
                                personas = Persona.objects.filter(pk__in=dirigidos)
                                for persona in personas:
                                    ids_personas.append(persona.id)
                            if not 'no_persona_session' in request.GET:
                                if 'persona' in request.session:
                                    persona = request.session['persona']
                                    ids_personas.append(persona.id)
                            # if DEBUG:
                            #     urlbase = "http://127.0.0.1:8000"
                            # else:
                            #     app = request.session['tiposistema']
                            #     urlbase = f"https://{app}.unemi.edu.ec"
                            # reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])
                            # reportfile = f"{urlbase}{reportfile}"
                            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                                send_html_mail(reporte.descripcion,
                                               "reportes/emails/reporte_generacion.html",
                                               {'sistema': u'SGA - UNEMI',
                                                'persona': persona,
                                                'reporte': reporte,
                                                'reportfile': reportfile,
                                                't': miinstitucion()},
                                               persona.lista_emails(),
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )

                    sp = os.path.split(reporte.archivo.file.name)
                    # return ok_json({'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])})
                    if cambiaruta == 0:
                        return ok_json({"r": mensaje, 'es_background': reporte.es_background, 'reportfile': reportfile})
                    if cambiaruta == 1:
                        return ok_json({"r": mensaje, 'es_background': reporte.es_background, 'reportfile': reportfile})

                else:
                    tipo = request.GET['rt']
                    d = datetime.now()
                    output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
                    try:
                        os.makedirs(output_folder)
                    except Exception as ex:
                        pass
                    mensaje = ''

                    if tipo == 'pdf':
                        nombre = reporte.nombre + d.strftime('%Y%m%d_%H%M%S') + ".pdf"
                        paramlist = {}
                        for p in reporte.parametros():
                            paramlist.update({p.nombre: fixparametro(p.tipo, request.GET[p.nombre])})
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
                            paramlist.update({p.nombre: fixparametro(p.tipo, request.GET[p.nombre])})
                        d = locals()
                        exec(reporte.vista, globals(), d)
                        book = d['vistareporte'](reporte, parametros=paramlist)
                        output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
                        filename = os.path.join(output_folder, nombre)
                        book.save(filename)
                    return ok_json({"r": mensaje, 'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), nombre])})
            except Exception as ex:
                transaction.set_rollback(True)
                # print(ex)
                # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                eror_line = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                msg = str(ex)
                msg += f' {eror_line}'
                return bad_json(mensaje="Error, al generar el reporte. %s" % msg)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Reportes'
        search = None
        categorias = []
        tiposistema = request.session['tiposistema']
        if 's' in request.GET:
            search = request.GET['s']
            try:
                ids = int(search)
            except Exception as ex:
                pass
                ids = 0
            reportes = Reporte.objects.filter(Q(descripcion__icontains=search) | Q(id=int(ids), grupos__in=data['grupos_usuarios']), interface=False).distinct().order_by('descripcion')
        else:
            reportes = Reporte.objects.filter(grupos__in=data['grupos_usuarios'], interface=False).distinct().order_by('descripcion')
        if tiposistema == 'sga':
            reportes = reportes.filter(sga=True)
        if tiposistema == 'sagest':
            reportes = reportes.filter(sagest=True)
        if tiposistema == 'posgrado':
            reportes = reportes.filter(posgrado=True)
        for categoria in CategoriaReporte.objects.all():
            reportes_categoria = reportes.filter(categoria=categoria, grupos__in=data['grupos_usuarios'], interface=False).distinct().order_by('descripcion')
            if reportes_categoria.values('id').count() > 0:
                categorias.append({'nombre': categoria.nombre, 'reportes': reportes_categoria})
        data['categorias'] = categorias
        data['search'] = search if search else ""
        return render(request, "reportes/view.html", data)


def qweb(request):
    try:
        data = {}
        return render(request, "reportes/qweb/demo.html", data)
    except Exception as ex:
        return HttpResponseRedirect("/")


def run_report_v1(reporte=None, tipo='pdf', paRequest={}, request=None):
    try:
        if not reporte:
            raise NameError(u"Reporte no encontrado")
        if not request:
            raise NameError(u"Datos de sesión no encontrado")
        if not tipo in ['pdf', 'xlsx']:
            raise NameError(u"Tipo de reporte no encontrado")

        output_folder = os.path.join(JR_USEROUTPUT_FOLDER, elimina_tildes(request.user.username))
        try:
            os.makedirs(output_folder)
        except Exception as ex:
            pass
        d = datetime.now()
        pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
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
        paramlist = [transform_jasperstarter_new(p, paRequest) for p in parametros]
        if paramlist:
            runjrcommand.append('-P')
            for parm in paramlist:
                runjrcommand.append(parm)
        else:
            runjrcommand.append('-P')
        runjrcommand.append(u'userweb=' + unicode(request.user.username))
        # runjrcommand.append(u'SUBREPORT_DIR=' + unicode("/".join([SUBREPOTRS_FOLDER, ''])))
        if reporte.version == 2:
            runjrcommand.append(u'MEDIA_DIR=' + unicode("/".join([MEDIA_ROOT, ''])))
            runjrcommand.append(u'IMAGE_DIR=' + unicode(SUBREPOTRS_FOLDER))
            runjrcommand.append(u'SUBREPORT_DIR=' + reporte.ruta_subreport())
        else:
            runjrcommand.append(u'SUBREPORT_DIR=' + unicode(SUBREPOTRS_FOLDER))
        mens = ''
        mensaje = ''
        for m in runjrcommand:
            mens += ' ' + m
        print(mens)
        if DEBUG:
            runjr = subprocess.run(mens, shell=True, check=True)
        else:
            runjr = subprocess.call(mens.encode("latin1"), shell=True)
        return {"isSuccess": True, 'mensaje': None, 'data': {'reportfile': "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo])}}
    except Exception as ex:
        # transaction.set_rollback(True)
        return {"isSuccess": False, 'mensaje': "Error, al generar el reporte. %s" % ex.__str__(), 'data': None}


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
            if DEBUG:
                urlbase = "http://127.0.0.1:8000"
            else:
                app = request.session['tiposistema']
                urlbase = f"https://{app}.unemi.edu.ec"
            ids_personas = []
            if 'dirigidos' in request.GET:
                dirigidos = []
                try:
                    dirigidos = json.loads(request.GET['dirigidos'])
                except:
                    _dirigidos = request.GET.get('dirigidos', None)
                    if _dirigidos:
                        dirigidos = [int(x) for x in _dirigidos.split(',')]
                if isinstance(dirigidos, (list, tuple, set)):
                    personas = Persona.objects.filter(pk__in=dirigidos)
                else:
                    personas = Persona.objects.filter(pk=dirigidos)
                for persona in personas:
                    ids_personas.append(persona.id)
            if not 'no_persona_session' in request.GET:
                if 'persona' in request.session:
                    persona = request.session['persona']
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
                            reportfile = "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), reportfile_aux])
            reportfile = f"{urlbase}{reportfile}"

            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                send_html_mail(reporte.descripcion,
                               "reportes/emails/reporte_generacion.html",
                               {'sistema': u'SGA - UNEMI',
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
                                            app_label=request.session['tiposistema'],
                                            fecha_hora_visible=datetime.now() + timedelta(days=2)
                                            )
                notificacion.save(request)

        except Exception as ex:
            # print(ex)
            # print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
            for persona in Persona.objects.filter(pk__in=ids_personas).distinct():
                send_html_mail(reporte.descripcion,
                               "reportes/emails/reporte_generacion_error.html",
                               {'sistema': u'SGA - UNEMI',
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
                                            app_label=request.session['tiposistema'],
                                            fecha_hora_visible=datetime.now() + timedelta(days=2)
                                            )
                notificacion.save(request)
