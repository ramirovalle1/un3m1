# -*- coding: UTF-8 -*-
import csv
import io
import os
import sys
import fitz

from django.db.models import Q
from django.forms import model_to_dict
from django.template import Context
from django.template.loader import get_template
from googletrans import Translator
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from certi.models import CertificadoAsistenteCertificadora, Certificado
from core.firmar_documentos import obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc
from decorators import secure_module, last_access, inhouse_check, get_client_ip
from settings import DATOS_ESTRICTO, PAGO_ESTRICTO, USA_EVALUACION_INTEGRAL, \
    ARCHIVO_TIPO_NOTAS, SITE_ROOT, VALIDATE_IPS, SERVER_RESPONSE, MEDIA_URL
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_docente
from sga.forms import ImportarArchivoCSVForm, AsignacionResponsableForm, SubirActaForm, ValidarActaForm
from sga.funciones import log, generar_nombre, variable_valor, null_to_decimal, ok_json, bad_json, MiPaginador, \
    notificacion, remover_caracteres_especiales_unicode
from sga.models import Materia, MateriaAsignada, miinstitucion, LeccionGrupo, Archivo, PlanificacionMateria, \
    ProfesorReemplazo, CUENTAS_CORREOS, DetalleModeloEvaluativo, Reporte, DocumentosFirmadosEvaluaciones, \
    ConfiguracionDocumentoEvaluaciones, Persona, HistorialDocumentoEvaluacion, Coordinacion, ESTADO_SEGUIMIENTO, \
    Carrera, Malla
from sga.reportes import elimina_tildes, run_report_v1
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
from settings import SITE_STORAGE, PUESTO_ACTIVO_ID, SITE_POPPLER, DEBUG
from django.contrib import messages
from django.core.files import File as DjangoFile


unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
# @last_access
@transaction.atomic()
def view(request):
    data = {}
    hoy=datetime.now()
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    mi_cargo=persona.mi_cargo_administrativo()
    if not mi_cargo and not request.user.is_superuser:
        return HttpResponseRedirect("/?info=Módulo disponible solo a funcionarios con cargo asignado.")

    # if mi_cargo and not mi_cargo.id in [16, 30] and not request.user.is_superuser:
    #     return HttpResponseRedirect("/?info=Solo asistentes de facultad pueden ingresar al módulo.")
    profesor = perfilprincipal.profesor
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'subiractafirmada':
                try:
                    with transaction.atomic():
                        form = SubirActaForm(request.POST, request.FILES)
                        id = int(encrypt(request.POST['id']))
                        if form.is_valid():
                            conf = ConfiguracionDocumentoEvaluaciones.objects.get(id=id)
                            if 'archivo_final' in request.FILES:
                                newfile = request.FILES['archivo_final']
                                newfile._name = 'acta_{}'.format(generar_nombre(conf.nombre_input(), newfile._name))
                                conf.archivo_final = newfile
                                conf.save(request)

                            responsable = DocumentosFirmadosEvaluaciones.objects.get(persona=persona, status=True, configuraciondoc=conf)
                            responsable.subido = True
                            responsable.fecha = hoy
                            if 'archivo_final' in request.FILES:
                                newfile = request.FILES['archivo_final']
                                newfile._name = 'acta_responsable_{}'.format(generar_nombre(conf.nombre_input(), newfile._name))
                                responsable.archivo = newfile
                            responsable.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                    log(u'Subir acta firmada: %s' % conf, request, "subiractafirmada")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, 'mensaje': str(ex)}, safe=False)

            if action == 'validaracta':
                try:
                    id = int(encrypt(request.POST['id']))
                    form = ValidarActaForm(request.POST)
                    if form.is_valid():
                        documento = DocumentosFirmadosEvaluaciones.objects.get(id=id)
                        documento.fecha_revision=hoy
                        documento.save(request)

                        configuracion=documento.configuraciondoc
                        configuracion.estado=form.cleaned_data['estado']
                        configuracion.observacion=form.cleaned_data['observacion']
                        configuracion.save(request)
                        log(u'Validacion de acta: %s [%s]' % (documento, documento.id), request, "validaracta")

                        historial=HistorialDocumentoEvaluacion(configuraciondoc=configuracion,
                                                               persona=documento.persona,
                                                               responsable=persona,
                                                               estado=configuracion.estado,
                                                               observacion=configuracion.observacion,
                                                               fecha=documento.fecha,
                                                               fecha_revision=hoy)
                        historial.save(request)

                        if int(configuracion.estado) == 2:
                            notificacion('Acta de calificaciones rechazada','Acta de {} fue rechazada'.format(configuracion.materia.nombre_completo()),
                                                      documento.persona, None, '/pro_evaluaciones',
                                                      documento.pk, 1, 'sga', DocumentosFirmadosEvaluaciones, request)
                        log(u'Agrego historial de validacion: %s [%s]' % (historial, historial.id), request, "validaracta")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                             "mensaje": "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': True, "mensaje": 'Error: {}'.format(ex)}, safe=False)

            if action == 'firmarmasivo':
                try:
                    import json
                    informesselect = request.POST['ids'].split(',')
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    razon = request.POST['razon'] if 'razon' in request.POST else ''
                    bytes_certificado = firma.read()
                    if not txtFirmas:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"No se ha podido seleccionar la ubicación de la firma"})
                    for idinforme in informesselect:
                        try:
                            archivo = DocumentosFirmadosEvaluaciones.objects.get(pk=idinforme)
                            historial = ConfiguracionDocumentoEvaluaciones.objects.get(id=archivo.configuraciondoc.id)

                            if historial.estado == 0:
                                pdf = historial.archivo_final
                                pdfname = SITE_STORAGE + '/media/' + str(historial.archivo_final)


                            palabras = f'{persona.nombre_completo_inverso()}'
                            documento = fitz.open(pdfname)
                            numpaginafirma = int(documento.page_count) - 1
                            with fitz.open(pdfname) as document:
                                words_dict = {}
                                for page_number, page in enumerate(document):
                                    if page_number == numpaginafirma:
                                        words = page.get_text("blocks")
                                        words_dict[0] = words
                            valor = None
                            for cadena in words_dict[0]:
                                if palabras in cadena[4]:
                                    valor = cadena

                            if valor:
                                posicinony = 5000 - int(valor[3]) - 4090
                            else:
                                messages.warning(request,
                                                 "Alerta: El nombre en la firma no es el correcto. Se ha rechazado y enviado a comercialización.")
                                return JsonResponse({"result": "errornombre"})
                            x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)

                            if x and y:
                                x = x + 320  ## ajustado para lado derecho de infome
                                y = posicinony

                                extension_certificado = os.path.splitext(firma.name)[1][1:]

                                datau = JavaFirmaEc(
                                    archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                                    extension_certificado=extension_certificado,
                                    password_certificado=passfirma,
                                    page=int(numpaginafirma), reason=razon, lx=x, ly=y
                                ).sign_and_get_content_bytes()
                                if datau:
                                    generar_archivo_firmado = io.BytesIO()
                                    generar_archivo_firmado.write(datau)
                                    generar_archivo_firmado.seek(0)
                                    extension = pdf.name.split('.')
                                    tam = len(extension)
                                    if not archivo.archivo:
                                        _name = 'actafirmada' + str(historial.usuario_creacion)
                                    else:
                                        _name = 'actafirmada' + str(historial.usuario_creacion) + '_firma' + str(
                                            archivo.orden)
                                    file_obj = DjangoFile(generar_archivo_firmado,
                                                          name=f"{remover_caracteres_especiales_unicode(_name)}.pdf")

                                    archivoexiste = SITE_STORAGE + '/media/firmas_pro_evaluaciones/' + _name + '.pdf'
                                    if os.path.isfile(archivoexiste):
                                        os.remove(archivoexiste)

                                    historial.archivo_final = file_obj
                                    historial.fechamodificacion = datetime.now().date()
                                    historial.save(request)

                                    archivo.archivo = file_obj
                                    archivo.fechamodificacion = datetime.now().date()
                                    archivo.save(request)
                        except Exception as ex:
                            pass
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    eline = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__())
                    return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % eline})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action']= action = request.GET['action']
            if action == 'subiractafirmada':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['configuracion'] = ConfiguracionDocumentoEvaluaciones.objects.get(id=id)
                    info=request.GET.get('ext','')
                    if not info:
                        form = SubirActaForm()
                        data['form'] = form
                    else:
                        data['info'] =info
                    template = get_template("pro_evaluaciones/modal/formfirma.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            if action == 'validaracta':
                try:
                    id = int(encrypt(request.GET['id']))
                    data['documento'] = documento =DocumentosFirmadosEvaluaciones.objects.get(id=id)
                    form = ValidarActaForm(initial=model_to_dict(documento.configuraciondoc))
                    data['form'] = form
                    template = get_template("pro_evaluaciones/modal/formvalidaracta.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            if action == 'firmaracta':
                try:
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect
                    data['accionfirma'] = request.GET['accionfirma']
                    template = get_template("adm_criteriosactividadesdocente/firmarinformesmasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Actas de calificaciones'
                lista=[]

                if persona.es_coordinadorcarrera(periodo):
                    data['coordinador'] = persona.es_coordinadorcarrera(periodo)
                    miscarreras = Carrera.objects.filter(status=True,coordinadorcarrera__in=persona.gruposcarrera(periodo),pk__in=persona.mis_carreras()).values_list("id", flat=True).distinct()
                    malla = Malla.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla_id', flat=True).filter(status=True, asignaturamalla__malla__carrera__in=miscarreras,nivel__periodo=periodo).distinct()).distinct()
                    for mall in malla:
                        lista.append(mall.carrera.id)
                else:
                    certificado=Certificado.objects.filter(status=True).first()
                    asistentes = CertificadoAsistenteCertificadora.objects.filter(status=True, asistente=persona, unidad_certificadora__certificado=certificado)
                    for asistente in asistentes:
                        carreras=asistente.unidad_certificadora.coordinacion.carrera.all()
                        for carrera in carreras:
                            lista.append(carrera.id)
                estado, search, filtro, url_vars = request.GET.get('estado', ''), request.GET.get('s', ''), Q(status=True, configuraciondoc__materia__asignaturamalla__malla__carrera_id__in=lista), ''

                if estado:
                    data['est'] = int(estado)
                    filtro = filtro & (Q(configuraciondoc__estado=estado))
                    url_vars += '&est=' + estado

                if search:
                    data['s'] = search
                    s = search.split(' ')
                    if len(s) == 1:
                        filtro = filtro & (Q(persona__nombres__unaccent__icontains=search) |
                                           Q(persona__cedula__unaccent__icontains=search) |
                                           Q(configuraciondoc__materia__asignatura__nombre__unaccent__icontains=search))
                    if len(s) >= 2:
                        filtro = filtro & (Q(persona__nombres__unaccent__icontains=search)|
                                           (Q(persona__apellido1__unaccent__icontains=s[0]) & Q(persona__apellido2__unaccent__icontains=s[1]))|
                                           Q(configuraciondoc__materia__asignatura__nombre__unaccent__icontains=search))
                    url_vars += '&s=' + search

                listado = DocumentosFirmadosEvaluaciones.objects.filter(filtro,configuraciondoc__materia__nivel__periodo=periodo).order_by('-id')
                # for list in listado:
                #     if list.configuraciondoc.materia.coordinacion_materia()== coordinacion:
                #         lista.append(list)
                paging = MiPaginador(listado, 20)
                p = 1
                try:
                    paginasesion = 1
                    if 'paginador' in request.session:
                        paginasesion = int(request.session['paginador'])
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    else:
                        p = paginasesion
                    try:
                        page = paging.page(p)
                    except:
                        p = 1
                    page = paging.page(p)
                except:
                    page = paging.page(p)
                request.session['paginador'] = p
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['estados']=ESTADO_SEGUIMIENTO
                data["url_vars"] = url_vars
                data['listado'] = page.object_list
                data['listcount'] = len(listado)
                return render(request, 'pro_evaluaciones/actas.html', data)
            except Exception as ex:
                pass