# -*- coding: UTF-8 -*-
import csv
import io
import os
import json
import urllib.request

import PyPDF2
import xlsxwriter
from django.db.models import Q
from django.template import Context
from django.template.loader import get_template
from googletrans import Translator
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.contrib import messages
from openpyxl import workbook as openxl
from pdf2image import convert_from_bytes
from xhtml2pdf import pisa
from django.core.files.storage import default_storage

from core.firmar_documentos import firmar, firmararchivogenerado
from decorators import secure_module, last_access, inhouse_check, get_client_ip
from settings import DATOS_ESTRICTO, PAGO_ESTRICTO, USA_EVALUACION_INTEGRAL, \
    ARCHIVO_TIPO_NOTAS, SITE_ROOT, VALIDATE_IPS, SERVER_RESPONSE, MEDIA_URL, SITE_STORAGE, SITE_POPPLER, DEBUG
from sga.commonviews import adduserdata, obtener_reporte, actualizar_nota_docente
from sga.forms import ImportarArchivoCSVForm, AsignacionResponsableForm, SubirActaForm
from sga.funciones import log, generar_nombre, variable_valor, null_to_decimal, ok_json, bad_json, notificacion, \
    remover_caracteres_tildes_unicode, remover_caracteres_especiales_unicode
from sga.funcionesxhtml2pdf import link_callback, convert_html_to_pdf
from sga.models import Materia, MateriaAsignada, miinstitucion, LeccionGrupo, Archivo, PlanificacionMateria, \
    ProfesorReemplazo, CUENTAS_CORREOS, DetalleModeloEvaluativo, Reporte, DocumentosFirmadosEvaluaciones, \
    ConfiguracionDocumentoEvaluaciones, Persona, CargoInstitucion, HistorialDocumentoEvaluacion, \
    ProfesorFirmaActaPeriodo, CoordinadorCarrera
from sga.reportes import elimina_tildes, run_report_v1
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt
unicode = str

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_profesor():
        return HttpResponseRedirect("/?info=Solo los perfiles de profesores pueden ingresar al modulo.")
    profesor = perfilprincipal.profesor
    data['periodo']= periodo = request.session['periodo']
    if periodo.ocultarnota and profesor.coordinacion.id == 9:
        return HttpResponseRedirect("/?info=Modulo temporalmente inactivo.")

    dominio_sistema = 'https://sga.unemi.edu.ec'
    if DEBUG:
        dominio_sistema = 'http://localhost:8000'
    data["DOMINIO_DEL_SISTEMA"] = dominio_sistema

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'cerrarmateriaasignada':
                try:
                    debe_cerrar_periodo = True
                    if periodo.periodo_academia():
                        if not periodo.periodo_academia().cierra_materia:
                            debe_cerrar_periodo = False
                            raise Exception('En este periodo no debe cerrarse las materias.')
                    if debe_cerrar_periodo:
                        materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt(request.POST['maid'])))
                        materiaasignada.cerrado = (request.POST['cerrado'] == 'false')
                        materiaasignada.fechacierre = datetime.now().date()
                        materiaasignada.save(request,actualiza=False)
                        d = locals()
                        exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                        d['calculo_modelo_evaluativo'](materiaasignada)

                        materiaasignada.actualiza_estado()
                        materiasabiertas = MateriaAsignada.objects.filter(materia=materiaasignada.materia, cerrado=False).count()
                        return JsonResponse({"result": "ok", 'cerrado': materiaasignada.cerrado, 'importadeuda': PAGO_ESTRICTO, 'tienedeuda': materiaasignada.matricula.inscripcion.persona.tiene_deuda(), 'materiasabiertas': materiasabiertas, "estadoid": materiaasignada.estado.id, "estado": materiaasignada.estado.nombre, "valida": materiaasignada.valida_pararecord(), "maid":materiaasignada.id })
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s"%ex})

            elif action == 'cerrarmateria':
                try:
                    debe_cerrar_periodo=True
                    if periodo.periodo_academia():
                        if not periodo.periodo_academia().cierra_materia:
                            debe_cerrar_periodo = False
                            raise Exception('En este periodo no debe cerrarse las materias.')
                    if debe_cerrar_periodo:
                        materia = Materia.objects.get(pk=int(encrypt(request.POST['mid'])))
                        materia.cerrado = True
                        materia.fechacierre = datetime.now().date()
                        materia.save(request)
                        for asig in materia.asignados_a_esta_materia():
                            asig.cerrado = True
                            asig.save(request,actualiza=False)
                            asig.actualiza_estado()
                        for asig in materia.asignados_a_esta_materia():
                            asig.cierre_materia_asignada()
                        for lg in LeccionGrupo.objects.filter(lecciones__clase__materia=materia, abierta=True):
                            lg.abierta = False
                            lg.horasalida = lg.turno.termina
                            lg.save(request)
                        # materia.materiaasignada_set.all()[0].cierre_materia_asignada_pre()
                        log(u'Cerro la materia: %s' % materia, request, "add")
                        send_html_mail("Cierre de materia", "emails/cierremateria.html", {'profesor': profesor, 'materia': materia, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"%s"%ex})

            elif action == 'abrirmateria':
                try:
                    materia = Materia.objects.get(pk=int(encrypt(request.POST['mid'])))
                    materia.cerrado = False
                    materia.save(request)
                    send_html_mail("Apertura de materia", "emails/aperturamateria.html", {'sistema': request.session['nombresistema'], 'profesor': profesor, 'materia': materia, 'apertura': datetime.now(), 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                    log(u'Abrio la materia: %s' % materia, request, "edit")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad"})

            elif action == 'nota':
                try:
                    result = actualizar_nota_docente(request)
                    return JsonResponse(result)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'envioclave':
                try:
                    clave = profesor.generar_clave_notas()
                    datos = profesor.datos_habilitacion()
                    datos.habilitado = False
                    datos.clavegenerada = clave
                    datos.fecha = datetime.now().date()
                    datos.save(request)
                    log(u'Nueva clave para ingreso de calificaciones: %s' % datos, request, "edit")
                    cuenta = 0
                    if SERVER_RESPONSE in ['207', '209', '211']:
                        cuenta = 6
                    elif SERVER_RESPONSE in ['212', '213']:
                        cuenta = 14
                    elif SERVER_RESPONSE in ['214', '215']:
                        cuenta = 15
                    send_html_mail("Nueva clave para ingreso de calificaciones", "emails/nuevaclavecalificaciones.html", {'sistema': request.session['nombresistema'], 'profesor': profesor, 'clave': datos.clavegenerada, 'fecha': datos.fecha, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[cuenta][1])
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'verificacionclave':
                try:
                    clave = request.POST['clave'].strip()
                    datos = profesor.datos_habilitacion()
                    if datos.clavegenerada == clave and datos.fecha == datetime.now().date():
                        datos.habilitado = True
                        datos.save(request)
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Clave incorrecta'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'actualizarestado':
                try:
                    materia = Materia.objects.get(pk=request.POST['mid'])
                    for materiaasignada in materia.asignados_a_esta_materia():
                        materiaasignada.actualiza_estado()
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'exportar':
                try:
                    materia = Materia.objects.get(pk=request.POST['id'])
                    output_folder = os.path.join(os.path.join(SITE_ROOT, 'media', 'notas'))
                    try:
                        os.makedirs(output_folder)
                    except Exception as ex:
                        pass
                    nombre = 'NOTAS_' + elimina_tildes(materia.identificacion).replace(' ', '') + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".csv"
                    filename = os.path.join(output_folder, nombre)
                    with open(filename, 'wb') as fichero:
                        cabecera = elimina_tildes(materia.nombre_completo()) + '\r\n\r\n'
                        fichero.write(cabecera)
                        cabecera = "COD;CEDULA;ESTUDIANTE;"
                        for campo in materia.modeloevaluativo.detallemodeloevaluativo_set.filter(dependiente=False).order_by('orden'):
                            cabecera += campo.nombre + ";"
                        cabecera += '\r\n'
                        fichero.write(cabecera)
                        for materiaasignada in materia.asignados_a_esta_materia():
                            persona = materiaasignada.matricula.inscripcion.persona
                            filanotas = str(materiaasignada.id) + ";" + persona.cedula + ";" + persona.nombre_completo_inverso().encode("ascii", "ignore") + ';'
                            for campo in materiaasignada.evaluacion().filter(detallemodeloevaluativo__dependiente=False).order_by('detallemodeloevaluativo__orden'):
                                filanotas += str(campo.valor) + ";"
                            filanotas += '\r\n'
                            fichero.write(filanotas)
                    fichero.close()
                    return JsonResponse({'result': 'ok', 'archivo': nombre})
                except Exception as ex:
                    transaction.set_rollback(True)
                    translator = Translator()
                    return JsonResponse({"result": "bad", "mensaje": translator.translate(ex.__str__(),'es').text})

            elif action == 'importar':
                try:
                    form = ImportarArchivoCSVForm(request.POST, request.FILES)
                    materia = Materia.objects.get(pk=request.POST['id'])
                    if form.is_valid():
                        nfile = request.FILES['archivo']
                        nfile._name = generar_nombre("importacionnotas_", nfile._name)
                        archivo = Archivo(nombre='IMPORTACION_NOTAS',
                                          fecha=datetime.now().date(),
                                          archivo=nfile,
                                          tipo_id=ARCHIVO_TIPO_NOTAS)
                        archivo.save(request)
                        datareader = csv.reader(open(archivo.archivo.file.name, "rU"), delimiter=';')
                        linea = 1
                        hoy = datetime.now().date()
                        for row in datareader:
                            if linea > 3:
                                if not materia.materiaasignada_set.filter(id=int(row[0])).exists():
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad", "mensaje": u"El codigo %s no existe como estudiante de esta materia." % row[0]})
                                materiaasignada = materia.materiaasignada_set.filter(id=int(row[0]))[0]
                                numero_campo = 3
                                for campo in materiaasignada.evaluacion().filter(detallemodeloevaluativo__dependiente=False):
                                    try:
                                        valor = float(row[numero_campo])
                                    except:
                                        valor = 0
                                    cronograma = materiaasignada.materia.cronogramacalificaciones()
                                    if cronograma:
                                        permite = campo.detallemodeloevaluativo.permite_ingreso_nota(materiaasignada, cronograma)
                                        if permite:
                                            result = actualizar_nota_docente(request, materiaasignada=materiaasignada, sel=campo.detallemodeloevaluativo.nombre, valor=valor)
                                    numero_campo += 1
                            linea += 1
                        return JsonResponse({"result": "ok"})
                    else:
                         raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'observaciones':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=request.POST['id'])
                    materiaasignada.observaciones = request.POST['observacion']
                    materiaasignada.save(request)
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'viewauditoria':
                try:
                    data['planificacion'] = MateriaAsignada.objects.get(pk=int(encrypt(request.POST['id'])))
                    template = get_template("pro_planificacion/viewauditorianota.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'listaauditoria':
                try:
                    materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt(request.POST['id'])))
                    campo = materiaasignada.campo(DetalleModeloEvaluativo.objects.get(pk=int(encrypt(request.POST['cid']))).nombre)
                    auditorias = campo.auditorianotas_set.filter(status=True)
                    return JsonResponse({"result": "ok", 'lista': [(null_to_decimal(auditoria.calificacion, 2), auditoria.usuario_creacion.__str__(), auditoria.fecha_creacion.strftime("%d/%m/%Y %H:%M:%S ").__str__(), auditoria.usuario_creacion_id) for auditoria in auditorias]})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al consultar los datos."})

            elif action == 'addresponsablefirma':
                try:
                    with transaction.atomic():
                        form = AsignacionResponsableForm(request.POST)
                        idmateria = int(encrypt(request.POST['idmateria']))
                        if form.is_valid():
                            if DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia_id=idmateria,orden=form.cleaned_data['orden'], status=True).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'result': True, "mensaje": 'Orden ingresado ya existe.'}, safe=False)
                            if DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia_id=idmateria,persona_id=form.cleaned_data['persona'], status=True).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'result': True, "mensaje": 'Orden ingresado ya existe.'}, safe=False)
                            if not ConfiguracionDocumentoEvaluaciones.objects.filter(materia_id=idmateria, status=True).exists():
                                configuracion = ConfiguracionDocumentoEvaluaciones(materia_id=idmateria)
                                configuracion.save(request)
                            else:
                                configuracion = ConfiguracionDocumentoEvaluaciones.objects.get(materia_id=idmateria)

                            instancia = DocumentosFirmadosEvaluaciones(configuraciondoc=configuracion,
                                                                       persona_id=form.cleaned_data['persona'],
                                                                       orden=form.cleaned_data['orden'])
                            instancia.save(request)
                            notificacion('Asignación de firma de acta',
                                         'Se le ha asignado una acta para ser firmada.',
                                         instancia.persona, None,'/pro_evaluaciones_firmas',
                                         instancia.pk, 1,'sga', DocumentosFirmadosEvaluaciones, request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],
                                                 "mensaje": "Error en el formulario"})
                        log(u'Adiciono configuracion de responsable firma: %s' % instancia, request,
                            "addresponsablefirma")
                        return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, 'mensaje': str(ex)}, safe=False)

            elif action == 'subiractafirmada':
                try:
                    with transaction.atomic():
                        form = SubirActaForm(request.POST, request.FILES)
                        idmateria = int(encrypt(request.POST['idmateria']))
                        responsables = request.POST.getlist('responsables[]')
                        if form.is_valid():
                            orden=1
                            if not DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia_id=idmateria, persona=persona, status=True).exists():
                                conf = ConfiguracionDocumentoEvaluaciones(materia_id=idmateria, estado=0)
                                conf.save(request)
                                documento = DocumentosFirmadosEvaluaciones(persona=persona,
                                                                           status=True,
                                                                           configuraciondoc=conf,
                                                                           fecha=datetime.now(),
                                                                           orden=orden, subido=True)
                                documento.save(request)
                                # cargo = CargoInstitucion.objects.filter(status=True, cargo='SECRETARIA GENERAL').first()
                                # responsables = [cargo.persona.id, ]
                                # for responsable in responsables:
                                #     orden += 1
                                #     asignacion = DocumentosFirmadosEvaluaciones(persona_id=responsable, status=True,
                                #                                                 configuraciondoc=conf, orden=orden,
                                #                                                 subido=False)
                                #     asignacion.save(request)
                                #     notificacion('Asignación de firma de acta',
                                #                  'Se le ha asignado una acta para ser firmada.',
                                #                  asignacion.persona, None, '/pro_evaluaciones_firmas',
                                #                  asignacion.pk, 1, 'sga', DocumentosFirmadosEvaluaciones, request)
                            else:
                                documento = DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia_id=idmateria, persona=persona, status=True).first()
                                documento.fecha = datetime.now()
                                documento.subido=True
                                documento.save(request)

                                conf = documento.configuraciondoc
                                conf.estado = 0
                                conf.save(request)
                                # for d in DocumentosFirmadosEvaluaciones.objects.get(configuraciondoc=conf).exclude(id=documento.id):
                                #     d.subido=False
                                #     d.save(request)

                            historial = HistorialDocumentoEvaluacion(configuraciondoc=conf,
                                                                     persona=persona,
                                                                     estado=0,
                                                                     fecha=documento.fecha,)
                            historial.save(request)
                            if 'archivo_final' in request.FILES:
                                newfile = request.FILES['archivo_final']
                                newfile._name = 'acta-{}'.format(generar_nombre(conf.nombre_input(), newfile._name))
                                conf.archivo_final = newfile
                                conf.save(request)

                                historial.archivo=newfile
                                historial.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],"mensaje": "Error en el formulario"})
                    log(u'Subir acta firmada: %s' % conf, request, "subiractafirmada")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, 'mensaje': str(ex)}, safe=False)

            elif action == 'addcabecera':
                try:
                    with transaction.atomic():
                        form = SubirActaForm(request.POST,request.FILES)
                        idmateria = int(request.POST['idmateria'])
                        if form.is_valid():
                            if ConfiguracionDocumentoEvaluaciones.objects.filter(materia_id=idmateria).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({'result': True, "mensaje": 'Ya existe una cabecera registrada.'},safe=False)
                            conf = ConfiguracionDocumentoEvaluaciones(materia_id=idmateria)
                            conf.save(request)
                            if 'archivo_final' in request.FILES:
                                newfile = request.FILES['archivo_final']
                                newfile._name = 'acta-{}'.format(generar_nombre(conf.nombre_input(), newfile._name))
                                conf.archivo_final = newfile
                                conf.save(request)
                        else:
                            transaction.set_rollback(True)
                            return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],"mensaje": "Error en el formulario"})
                    log(u'Subir acta base: %s' % conf, request, "subircabecera")
                    return JsonResponse({"result": False}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, 'mensaje': str(ex)}, safe=False)

            elif action == 'delresponsabledoc':
                try:
                    with transaction.atomic():
                        documento = DocumentosFirmadosEvaluaciones.objects.get(pk=int(request.POST['id']))
                        documento.status = False
                        documento.save(request)
                        log(u'Elimino responsable de subir documento firmado: %s - %s - %s', request,"delresponsabledoc")
                        res_json = {"error": False}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'firmardocumento':
                try:
                    #Parametros
                    txtFirmas = json.loads(request.POST['txtFirmas'])
                    if not txtFirmas:
                        raise NameError("Debe seleccionar ubicación de la firma")
                    x = txtFirmas[-1]
                    idmateria = int(encrypt(request.POST['id_objeto']))
                    responsables = request.POST.getlist('responsables[]')
                    firma = request.FILES["firma"]
                    passfirma = request.POST['palabraclave']
                    url_archivo = (SITE_STORAGE + request.POST["url_archivo"]).replace('\\','/')
                    _name = generar_nombre(f'actafirmada_{request.user.username}_{idmateria}_', 'firmada')
                    folder = os.path.join(SITE_STORAGE, 'media', 'firmas_pro_evaluaciones', '')

                    #Firmar y guardar archivo en folder definido.
                    firma = firmararchivogenerado(request, passfirma, firma, url_archivo, folder, _name, x["numPage"], x["x"], x["y"], x["width"], x["height"])
                    if firma != True:
                        raise NameError(firma)
                    log(u'Firmo Documento: {}'.format(_name), request, "add")

                    folder_save = os.path.join('firmas_pro_evaluaciones', '').replace('\\','/')
                    url_file_generado = f'{folder_save}{_name}.pdf'
                    if not DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia_id=idmateria,
                                                                         persona=persona, status=True).exists():
                        conf = ConfiguracionDocumentoEvaluaciones(materia_id=idmateria, estado=0)
                        conf.save(request)
                        documento = DocumentosFirmadosEvaluaciones(persona=persona,
                                                                   status=True,
                                                                   configuraciondoc=conf,
                                                                   fecha=datetime.now(), subido=True)
                        documento.save(request)
                    else:
                        documento = DocumentosFirmadosEvaluaciones.objects.filter(
                            configuraciondoc__materia_id=idmateria, persona=persona, status=True).first()
                        documento.fecha = datetime.now()
                        documento.subido = True
                        documento.save(request)

                        conf = documento.configuraciondoc
                        conf.estado = 0
                        conf.save(request)

                    historial = HistorialDocumentoEvaluacion(configuraciondoc=conf,
                                                             persona=persona,
                                                             estado=0,
                                                             fecha=documento.fecha, )
                    historial.save(request)

                    conf.archivo_final =url_file_generado
                    conf.save(request)

                    historial.archivo = url_file_generado
                    historial.save(request)
                    log(u'Guardo archivo firmado: {}'.format(conf), request, "add")
                    return JsonResponse({"result": False, "mensaje": "Guardado con exito",}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": u"Error al guardar. %s" % ex.__str__()},  safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'segmento':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['cronograma'] = materia.cronogramacalificaciones()
                    data['usacronograma'] = materia.usaperiodocalificaciones
                    data['usa_evaluacion_integral'] = USA_EVALUACION_INTEGRAL
                    data['validardeuda'] = PAGO_ESTRICTO
                    data['incluyedatos'] = DATOS_ESTRICTO
                    data['dentro_fechas'] = materia.fin >= datetime.now().date()
                    data['auditor'] = False
                    if materia.asignaturamalla.malla.carrera.coordinacion_carrera().id == 9:
                        data['reporte_0'] = obtener_reporte('acta_calificaciones_admision')#obtener_reporte('acta_notas_admision')
                    elif materia.asignaturamalla.malla.carrera.coordinacion_carrera().id == 7:
                        data['reporte_0'] = obtener_reporte('acta_calificaciones_posgrado')
                    else:
                        if periodo.inicio >= datetime(2022, 5, 30).date():
                            data['reporte_0'] = obtener_reporte('acta_notas')
                        else:
                            data['reporte_0'] = obtener_reporte('acta_notas_old')
                        data['reporte_0'] = obtener_reporte('acta_notas')
                    data['reporte_1'] = obtener_reporte('lista_control_calificaciones')
                    data['reporte_2'] = obtener_reporte('acta_notas_parcial')
                    bandera = False
                    if PlanificacionMateria.objects.filter(materia=materia, paraevaluacion=True).exists():
                        bandera = True
                    data['bandera'] = bandera
                    # 1, 3, 11, 12, 14, 6, 9, 16
                    TIPOS_DOCENTES_IMPORTA_NOTAS = variable_valor('TIPOS_DOCENTES_IMPORTA_NOTAS')
                    profesormateria_ = profesor.profesormateria_set.filter(materia=materia).filter(tipoprofesor_id__in=TIPOS_DOCENTES_IMPORTA_NOTAS).first()
                    data['alertatipoprofesor'] = not profesormateria_
                    data['asignado']=DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia=materia, status=True, persona=persona).first()
                    return render(request, "pro_evaluaciones/segmento.html", data)
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar notas'
                    data['form'] = ImportarArchivoCSVForm()
                    data['materia'] = Materia.objects.get(pk=request.GET['id'])
                    return render(request, "pro_evaluaciones/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'cierretodasma':
                try:
                    debe_cerrar_periodo = True
                    if periodo.periodo_academia():
                        if not periodo.periodo_academia().cierra_materia:
                            debe_cerrar_periodo = False
                            raise Exception('En este periodo no debe cerrarse las materias.')
                    if debe_cerrar_periodo:
                        data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['materiaid'])))
                        for materiaasignada in materia.materiaasignada_set.filter(status=True):
                            materiaasignada.cerrado = not materiaasignada.cerrado
                            materiaasignada.fechacierre = datetime.now().date()
                            materiaasignada.save(request,actualiza=False)
                            d = locals()
                            exec(materiaasignada.materia.modeloevaluativo.logicamodelo, globals(), d)
                            d['calculo_modelo_evaluativo'](materiaasignada)
                            materiaasignada.actualiza_estado()
                        return HttpResponseRedirect("/pro_evaluaciones?materiaid=%s" % request.GET['materiaid'])
                except Exception as ex:
                    transaction.set_rollback(True)
                    return HttpResponseRedirect("/pro_evaluaciones?materiaid=%s&info=%s" % (request.GET['materiaid'],ex))

            if action == 'reporte_acta_calificaciones':
                try:
                    if 'id' in request.GET:
                        materia_id = int(request.GET['id'])
                    else:
                        materia_id = int(request.GET['materia'])
                    reporte_id = request.GET['reporte']
                    reporte = Reporte.objects.get(pk=reporte_id)
                    base_url = request.META['HTTP_HOST']
                    d = datetime.now()
                    pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
                    tipo = 'pdf'
                    paRequest = {
                                    'materia': materia_id,
                                    'imp_logo':True,
                                    'imp_encabezado':True,
                                    'imp_fecha':True,
                                    'imp_membretada':False,
                                    'profesor': profesor.pk,
                                    'url_qr':unicode(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo]))
                                }
                    d = run_report_v1(reporte=reporte, tipo=tipo, paRequest=paRequest, request=request)
                    if not d['isSuccess']:
                        raise NameError(d['mensaje'])
                    else:
                        materia=Materia.objects.get(id=materia_id)
                        if materia.cerrado:
                            data['archivo'] = archivo = d['data']['reportfile']
                            data['url_archivo'] = '{}{}'.format(dominio_sistema, archivo)
                            data['id_objeto'] = materia_id
                            data['action_firma'] = 'firmardocumento'
                            template = get_template("formfirmaelectronica.html")
                            return JsonResponse({"result": True, 'data': template.render(data)})
                        else:
                            return ok_json({"r": d['mensaje'], 'reportfile': d['data']['reportfile']})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return bad_json(mensaje="Error, al generar el reporte. %s" % ex.__str__())

            # if action == 'reporte_acta_calificaciones':
            #     try:
            #         materia_id = request.GET['materia']
            #         reporte_id = request.GET['reporte']
            #         reporte = Reporte.objects.get(pk=reporte_id)
            #         base_url = request.META['HTTP_HOST']
            #         d = datetime.now()
            #         pdfname = reporte.nombre + d.strftime('%Y%m%d_%H%M%S')
            #         tipo = 'pdf'
            #         paRequest = {
            #                         'materia': materia_id,
            #                         'imp_logo':True,
            #                         'imp_encabezado':True,
            #                         'imp_fecha':True,
            #                         'imp_membretada':False,
            #                         'url_qr':unicode(base_url + "/".join([MEDIA_URL, 'documentos', 'userreports', elimina_tildes(request.user.username), pdfname + "." + tipo]))
            #                     }
            #         d = run_report_v1(reporte=reporte,tipo=tipo , paRequest=paRequest, request=request)
            #         if not d['isSuccess']:
            #             raise NameError(d['mensaje'])
            #         else:
            #             return ok_json({"r": d['mensaje'], 'reportfile':d['data']['reportfile']})
            #     except Exception as ex:
            #         transaction.set_rollback(True)
            #         return bad_json(mensaje="Error, al generar el reporte. %s" % ex.__str__())

            if action == 'responsablesfirma':
                try:
                    data['title'] = 'Configurar Responsables'
                    data['materia'] = materia = Materia.objects.get(id=int(encrypt(request.GET['id'])))
                    data['cabecera'] = ConfiguracionDocumentoEvaluaciones.objects.filter(materia=materia).first()
                    data['responsables'] = DocumentosFirmadosEvaluaciones.objects.filter(status=True,configuraciondoc__materia_id=materia.id).order_by('orden')
                    return render(request, "pro_evaluaciones/responsablesfirma.html", data)
                except Exception as es:
                    pass

            if action == 'configuracionordenfirmas':
                try:
                    data['action'] = action
                    data['idmateria'] = id = int(encrypt(request.GET['id']))
                    data['materia'] = Materia.objects.get(id=id)
                    data['configuracion'] = ConfiguracionDocumentoEvaluaciones.objects.get(materia_id=id)
                    form = AsignacionResponsableForm()
                    data['form'] = form
                    template = get_template("pro_evaluaciones/modal/configuracionfirmas.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            if action == 'buscapersona':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Persona.objects.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                            apellido2__icontains=q) | Q(cedula__contains=q))).distinct()[:15]
                    elif len(s) == 2:
                        per = Persona.objects.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) | (
                                Q(nombres__icontains=s[0]) & Q(
                            nombres__icontains=s[1])) | (
                                                             Q(nombres__icontains=s[0]) & Q(
                                                         apellido1__contains=s[1]))).distinct()[:15]
                    else:
                        per = Persona.objects.filter((Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(
                            apellido2__contains=s[2])) | (Q(nombres__contains=s[0]) & Q(
                            nombres__contains=s[1]) & Q(apellido1__contains=s[2]))).distinct()[:15]

                    data = {"result": "ok",
                            "results": [{"id": x.id, "name": str(x.nombre_completo())}
                                        for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            if action == 'subiractafirmada':
                try:
                    data['action'] = action
                    data['idmateria'] = id = int(encrypt(request.GET['id']))
                    data['materia'] = Materia.objects.get(id=id)
                    data['configuracion'] = configuracion=ConfiguracionDocumentoEvaluaciones.objects.filter(materia_id=id).first()
                    data['responsables']=DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc=configuracion, status=True).order_by('orden')
                    data['documentofirma']=DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc=configuracion,persona=persona, status=True, subido=False).first()
                    form = SubirActaForm()
                    data['form'] = form
                    template = get_template("pro_evaluaciones/modal/formarchivobase.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            if action == 'revisarestadodoc':
                try:
                    data['action'] = action
                    data['idmateria'] = id = int(encrypt(request.GET['id']))
                    data['materia'] = Materia.objects.get(id=id)
                    data['responsable']=DocumentosFirmadosEvaluaciones.objects.filter(configuraciondoc__materia_id=id,persona=persona, status=True).first()
                    form = SubirActaForm()
                    data['form'] = form
                    template = get_template("pro_evaluaciones/modal/formactafirmada.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            if action == 'addcabecera':
                try:
                    data['action'] = action
                    data['idmateria'] = id = int(encrypt(request.GET['id']))
                    data['materia'] = Materia.objects.get(id=id)
                    data['configuracion'] = ConfiguracionDocumentoEvaluaciones.objects.filter(materia_id=id).first()
                    form = SubirActaForm()
                    data['form'] = form
                    template = get_template("pro_evaluaciones/modal/formarchivobase.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as e:
                    print(e)
                    pass

            if action == 'configuracioninforme':
                try:
                    data['title'] = 'Configuración de informe de cumplimiento del sílabo'
                    data['materia'] = materia = Materia.objects.get(id=int(encrypt(request.GET['id'])))
                    return render(request, "pro_evaluaciones/configuracioninforme.html", data)
                except Exception as ex:
                    pass

            if action == 'generar_informe_cumplimiento_materia':
                try:
                    materia = Materia.objects.get(pk=request.GET['pk'])
                    now = datetime.now()

                    filename = f"/XXX.pdf"
                    filepath = u"informecumplimientosilabo/%s" % now.year
                    folder_pdf = os.path.join(SITE_STORAGE, 'media', 'informecumplimientosilabo', '')

                    os.makedirs(folder_pdf, exist_ok=True)
                    os.makedirs(os.path.join(folder_pdf, now.year.__str__(), ''), exist_ok=True)

                    if director := CoordinadorCarrera.objects.filter(carrera=materia.carrera(), periodo=periodo, sede_id=1, tipo=3, status=True).order_by('-id').first():
                        data['director_carrera'] = director


                    data['materia'] = materia
                    data['fecha_creacion'] = datetime.now()  # datetime(hoy.year, configuracion.mes, calendar.monthrange(hoy.year, configuracion.mes)[1])
                    if newfile := convert_html_to_pdf('../templates/pro_evaluaciones/informe_cumplimiento.html', data, filename, os.path.join(os.path.join(SITE_STORAGE, 'media', filepath, ''))):
                        return HttpResponseRedirect()

                except Exception as ex:
                    ...

            if action == 'reporteactuaciones':
                try:
                    if not 'id' in request.GET:
                        raise NameError('Materia no encontrada')
                    materia = Materia.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    if not materia:
                        raise NameError('Materia no encontrada')
                    __author__ = 'Unemi'
                    ahora = datetime.now()
                    time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                    name_file = f'Actuaciones_{materia.asignatura.nombre}_{time_codigo}.xlsx'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Listado')

                    fuentecabecera = workbook.add_format({
                        'align': 'center',
                        'bg_color': 'silver',
                        'border': 1,
                        'bold': 1
                    })

                    formatoceldacenter = workbook.add_format({
                        'border': 1,
                        'valign': 'vcenter',
                        'align': 'center'})
                    formatoceldaleft = workbook.add_format({
                        'valign': 'vleft',
                        'align': 'left'})

                    fuenteencabezado = workbook.add_format({
                        'align': 'center',
                        'bg_color': '#1C3247',
                        'font_color': 'white',
                        'border': 1,
                        'font_size': 24,
                        'bold': 1
                    })

                    columnas = [
                        (u"Cedula", 20),
                        (u"Nombres", 50),
                        (u"Actuaciones", 20),
                        (u"Puntaje total", 20),
                        (u"Promedio", 20)
                    ]
                    ws.merge_range(0, 0, 0, columnas.__len__() - 1, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
                    ws.merge_range(1, 0, 1, columnas.__len__() - 1, f'Actuaciones en clase', fuenteencabezado)
                    ws.merge_range(3, 0, 3, columnas.__len__() - 1,  'Asignatura: {}'.format(materia), formatoceldaleft)
                    row_num, numcolum = 5, 0
                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(numcolum, numcolum, col_name[1])
                        numcolum += 1
                    row_num += 1
                    for alumno in materia.asignados_a_esta_materia():
                        ws.write(row_num, 0, alumno.matricula.inscripcion.persona.cedula, formatoceldacenter)
                        ws.write(row_num, 1, alumno.matricula.inscripcion.persona.nombre_completo_minus(), formatoceldacenter)
                        ws.write(row_num, 2, alumno.cantidad_evaluaciones_clase(), formatoceldacenter)
                        ws.write(row_num, 3, alumno.total_evaluacion_clase(), formatoceldacenter)
                        ws.write(row_num, 4, alumno.promedio_evaluacion_clase(), formatoceldacenter)
                        row_num += 1
                    workbook.close()
                    output.seek(0)
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=mi_archivo_excel.xlsx'
                    return response
                except Exception as ex:
                    return HttpResponseRedirect("/pro_evaluaciones?info=Error al generar el reporte {}".format(ex))

            if action == 'reporteobservaciones':
                try:
                    from inno.models import AsistenciaLeccionObservacion

                    materia = Materia.objects.filter(pk=int(encrypt(request.GET['id']))).first()
                    __author__ = 'Unemi'
                    ahora = datetime.now()
                    time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
                    name_file = f'observaciones_{materia.asignatura.nombre}_{time_codigo}.xlsx'
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('Listado')
                    fuentecabecera = workbook.add_format({'align': 'center', 'bg_color': 'silver', 'border': 1, 'bold': 1})
                    formatoceldacenter = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center'})
                    formatoceldacenter_bold = workbook.add_format({'border': 1, 'valign': 'vcenter', 'align': 'center', 'bold': 1})
                    formatoceldaleft = workbook.add_format({'border': 1, 'valign': 'vleft', 'align': 'left'})
                    fuenteencabezado = workbook.add_format({'align': 'center','bg_color': '#1C3247','font_color': 'white','border': 1,'font_size': 24,'bold': 1})
                    columnas = [(u"#", 10), (u"Cedula", 20), (u"Nombres", 50), (u"Semana", 20), (u"Observación", 80)]
                    ws.merge_range(0, 0, 0, len(columnas) - 1, 'UNIVERSIDAD ESTATAL DE MILAGRO', fuenteencabezado)
                    ws.merge_range(1, 0, 1, len(columnas) - 1, f'Observaciones en clase', fuenteencabezado)
                    ws.merge_range(3, 0, 3, len(columnas) - 1,  'Asignatura: {}'.format(materia), formatoceldaleft)
                    row_num, numcolum = 5, 0
                    for col_name in columnas:
                        ws.write(row_num, numcolum, col_name[0], fuentecabecera)
                        ws.set_column(numcolum, numcolum, col_name[1])
                        numcolum += 1
                    row_num += 1
                    counter = 1
                    for alumno in materia.asignados_a_esta_materia():
                        for observacion in AsistenciaLeccionObservacion.objects.filter(asistencia__materiaasignada=alumno, asistencia__leccion__clase__materia=materia, asistencia__leccion__status=True, asistencia__leccion__clase__status=True, asistencia__leccion__clase__activo=True, status=True):
                            fecha = observacion.asistencia.leccion.fecha
                            silabosemanal = SilaboSemanal.objects.filter(silabo__materia=materia, fechainiciosemana__lte=fecha, fechafinciosemana__gte=fecha, status=True).first()
                            ws.write(row_num, 0, f"{counter}", formatoceldacenter)
                            ws.write(row_num, 1, f"{alumno.matricula.inscripcion.persona.cedula}", formatoceldacenter_bold)
                            ws.write(row_num, 2, f"{alumno.matricula.inscripcion.persona.nombre_completo_minus()}", formatoceldacenter)
                            ws.write(row_num, 3, f"{silabosemanal.numsemana}", formatoceldacenter)
                            ws.write(row_num, 4, f"{observacion.observacion}", formatoceldaleft)
                            row_num += 1
                            counter += 1
                    workbook.close()
                    output.seek(0)
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=mi_archivo_excel.xlsx'
                    return response
                except Exception as ex:
                    return HttpResponseRedirect("/pro_evaluaciones?info=Error al generar el reporte {}".format(ex))

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Calificaciones de Estudiantes'
            if persona.id not in (42552, 41508, 38029, 42551, 42553, 54, 3545,4379):
                if periodo.tipo.id != 3:
                    if str(persona.id) not in variable_valor('CALIFICAR_FUERA_UNEMI'):
                        # if not inhouse_check(request) and VALIDATE_IPS:
                        if not inhouse_check(request) and variable_valor('VALIDATE_IPS'):
                            log(u'Bloqueo de ip externa por ingreso de notas: %s' % get_client_ip(request), request, "add")
                            return HttpResponseRedirect("/?info=No puede ingresar las calificaciones fuera de la institucion.")

            hoy = datetime.now().date()
            materias = Materia.objects.filter(nivel__periodo__visible=True, profesormateria__profesor=profesor, profesormateria__principal=True, profesormateria__activo=True, nivel__periodo=periodo).distinct()
            otrasmaterias = []
            if profesor.reemplaza_set.filter(desde__lte=hoy, hasta__gte=hoy).exists():
                # solicita = profesor.reemplaza_set.filter(desde__lte=hoy, hasta__gte=hoy)[0].solicita
                solicita = ProfesorReemplazo.objects.values('solicita_id').filter(desde__lte=hoy, hasta__gte=hoy, reemplaza=profesor)
                otrasmaterias = Materia.objects.filter(nivel__periodo__visible=True, profesormateria__profesor__in=solicita, profesormateria__principal=True, profesormateria__activo=True, nivel__periodo=periodo)
            if otrasmaterias:
                if materias:
                    data['materias'] = materias | otrasmaterias
                else:
                    data['materias'] = materias = otrasmaterias
            else:
                data['materias'] = materias
                if not materias:
                    return HttpResponseRedirect("/?info=No tiene materias en el periodo seleccionado.")
            # if 'materiaid' not in request.GET:
            #     data['materiaid'] = materias[0].id
            # else:
            #     data['materiaid'] = int(request.GET['materiaid'])
            # data['materia'] = materia = Materia.objects.get(pk=data['materiaid'])

            todasmateria = data['materias']
            data['mensaje_bloqueo'] = None
            if ProfesorFirmaActaPeriodo.objects.filter(status=True, periodo=periodo, modalidad_id__in=materias.values_list('nivel__modalidad_id', flat=True)).exists():
                tipoprofesor = ProfesorFirmaActaPeriodo.objects.filter(status=True, periodo=periodo, modalidad_id__in=materias.values_list('nivel__modalidad_id', flat=True)).first().tipoprofesor.all().values_list('id', flat=True)
                data['materias'] = materias = materias.filter(profesormateria__tipoprofesor_id__in=tipoprofesor, profesormateria__profesor=profesor).distinct('id')
                if not materias:
                    return HttpResponseRedirect("/?info=No tiene materias en el periodo seleccionado.")
            if 'materiaid' not in request.GET:
                data['materiaid'] = materias[0].id
                materia = Materia.objects.get(pk=data['materiaid'])
            else:
                data['materiaid'] = int(encrypt(request.GET['materiaid']))
            #     verifica si es materia del docente
                materiano = Materia.objects.get(pk=data['materiaid'])
                if not todasmateria.filter(pk=data['materiaid']).exists():
                    data['materiaid'] = materias[0].id
                    data['mensaje_bloqueo'] = "Materia no Asignada"
                    log(u'Profesor %s intento ingresar notas en materias no asignadas %s' % (profesor, materiano), request, "add")
                materia = Materia.objects.get(pk=data['materiaid'])
            if periodo.ocultarmateria:
                materia = False
                materias = False
            data['materia'] = materia
            data['materias'] = materias

            data['utiliza_validacion_calificaciones'] = variable_valor('UTILIZA_VALIDACION_CALIFICACIONES')
            data['habilitado_ingreso_calificaciones'] = profesor.habilitado_ingreso_calificaciones()
            data['profesor'] = profesor
            data['idmateria']=request.GET.get('idmateria','')
            try:
                return render(request, "pro_evaluaciones/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f"/?info=No puede acceder al módulo")
