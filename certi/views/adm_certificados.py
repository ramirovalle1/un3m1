# -*- coding: UTF-8 -*-
import json
from django.contrib.auth.decorators import login_required
from django.db import connection
from django.db import transaction
from django.db.models import Count, PROTECT, Sum, Avg, Min, Max
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import xlwt
from django.template.loader import get_template
from django.template import Context
from openpyxl import load_workbook
from xlwt import *
import random
import time as pausaparaemail

# from datetime import datetime
from datetime import datetime, time
from decimal import Decimal

from django.contrib import messages
from django.db.models import Max
import xlrd as xlrd
from decorators import secure_module, last_access
from sagest.commonviews import secuencia_convenio_devengacion
from sagest.models import DistributivoPersona
from secretaria.models import Servicio
from settings import ARCHIVO_TIPO_GENERAL, DEBUG
from sga.commonviews import adduserdata, secuencia_contrato_beca, secuencia_solicitud_pago_beca
from sga.forms import BecaTipoForm, BecaUtilizacionForm, BecaRequisitosForm, BecaAprobarArchivoForm, \
    BecaAprobarArchivoUtilizacionForm, BecaPeriodoForm, BecaAsignacionForm, ImportarBecaForm, BecaAsignacionManualForm, \
    BecaSolicitudAnulacionForm, BecaAsignacion2Form, BecaSolicitudRechazaOnLineForm, BecaValidarCedulaForm, \
    BecaSolicitudSubirCedulaForm, BecaAsignacionSubirEvidenciaForm, RepresentanteSolidarioForm, \
    ImportarArchivoPagoBecaXLSForm, BecaComprobanteVentaEditForm, BecaComprobanteVentaValidaForm, \
    BecaComprobanteEliminarForm, BecaTipoConfiguracionForm
from sga.funciones import MiPaginador, log, variable_valor, convertir_fecha, null_to_numeric, convertir_hora, \
    generar_nombre, convertir_fecha_invertida, convertir_fecha_invertida_hora, convertir_fecha_hora, \
    convertir_fecha_hora_invertida, fechaformatostr, fechaletra_corta, validarcedula, cuenta_email_disponible, \
    puede_realizar_accion
from certi.models import Certificado, CertificadoUnidadCertificadora, CertificadoAsistenteCertificadora, \
    DESTINO_CERTIFICADO
from certi.forms import CertificadoForm, CertificadoUnidadCertificadoraForm, CertificadoAsistenteCertificadoraForm, \
    ResponsableCertificadoUnidadCertificadoraForm, AsistenteCertificadoAsistenteCertificadoraForm
from sga.models import Coordinacion, Carrera
from sagest.models import Departamento
from sga.tasks import send_html_mail, conectar_cuenta
from dateutil.relativedelta import relativedelta
from django.db.models.functions import ExtractYear
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'saveCertificado':
            try:
                puede_realizar_accion(request, 'certi.puede_modificar_certificados')
                id = None
                type = 'new'
                f = CertificadoForm(request.POST, request.FILES)
                new_file = None
                if 'imagen_tarjeta' in request.FILES:
                    new_file = request.FILES['imagen_tarjeta']
                    if new_file:
                        newfilesd = new_file._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        if not ext in ['.jpg', '.png', '.jpeg']:
                            raise NameError('Formato de imagen incorrecta. Tipo de archivo valido .jpg, .png, .jpeg')
                        if new_file.size > 20480000:
                            raise NameError(u"Archivo erroneo, solo se permiten menor a 20 Mb.")
                if 'id' in request.POST and int(request.POST['id']):
                    id = int(request.POST['id'])
                    type = 'edit'
                if not f.is_valid():
                    print(f.errors)
                    raise NameError(u"Formulario incorrecto.")
                certificado = None
                if type == 'new':
                    certificado = Certificado(codigo=f.cleaned_data['codigo'],
                                              clasificacion=f.cleaned_data['clasificacion'],
                                              certificacion=f.cleaned_data['certificacion'],
                                              tipo_certificacion=int(f.cleaned_data['tipo_certificacion']),
                                              tipo_origen=int(f.cleaned_data['tipo_origen']),
                                              tipo_validacion=int(f.cleaned_data['tipo_validacion']),
                                              version=f.cleaned_data['version'],
                                              primera_emision=f.cleaned_data['primera_emision'],
                                              ultima_modificacion=f.cleaned_data['ultima_modificacion'],
                                              reporte=f.cleaned_data['reporte'],
                                              vigencia=f.cleaned_data['vigencia'],
                                              tipo_vigencia=int(f.cleaned_data['tipo_vigencia']),
                                              destino=int(f.cleaned_data['destino']),
                                              visible=f.cleaned_data['visible'],
                                              adjuntararchivo=f.cleaned_data['adjuntararchivo'],
                                              funcionadjuntar=f.cleaned_data['funcionadjuntar'],
                                              servicio=f.cleaned_data['servicio'],
                                              costo=f.cleaned_data['costo'],
                                              tiempo_cobro=f.cleaned_data['tiempo_cobro']
                                              )
                    certificado.save(request)
                    log(u'Adiciono certificado: %s' % certificado, request, "add")
                    if new_file:
                        new_file._name = generar_nombre(f"{certificado.pk}", new_file._name)
                        certificado.imagen_tarjeta = new_file
                        certificado.save(request)
                else:
                    if not Certificado.objects.filter(pk=id).exists():
                        raise NameError(u"Datos incorrectos.")

                    certificado = Certificado.objects.get(pk=id)
                    certificado.codigo = f.cleaned_data['codigo']
                    certificado.clasificacion = f.cleaned_data['clasificacion']
                    certificado.certificacion = f.cleaned_data['certificacion']
                    certificado.tipo_certificacion = int(f.cleaned_data['tipo_certificacion'])
                    certificado.tipo_origen = int(f.cleaned_data['tipo_origen'])
                    certificado.tipo_validacion = int(f.cleaned_data['tipo_validacion'])
                    certificado.version = f.cleaned_data['version']
                    certificado.primera_emision = f.cleaned_data['primera_emision']
                    certificado.ultima_modificacion = f.cleaned_data['ultima_modificacion']
                    certificado.reporte = f.cleaned_data['reporte']
                    certificado.vigencia = f.cleaned_data['vigencia']
                    certificado.tipo_vigencia = int(f.cleaned_data['tipo_vigencia'])
                    certificado.visible = f.cleaned_data['visible']
                    certificado.destino = f.cleaned_data['destino']
                    certificado.adjuntararchivo = f.cleaned_data['adjuntararchivo']
                    certificado.funcionadjuntar = f.cleaned_data['funcionadjuntar']
                    certificado.servicio = f.cleaned_data['servicio']
                    certificado.costo = f.cleaned_data['costo']
                    certificado.tiempo_cobro = f.cleaned_data['tiempo_cobro']
                    certificado.save(request)
                    log(u'Edito certificado: %s' % certificado, request, "edit")
                if new_file:
                    new_file._name = generar_nombre(f"{certificado.pk}", new_file._name)
                    certificado.imagen_tarjeta = new_file
                    certificado.save(request)
                if certificado.tipo_validacion == 1:
                    #certificado.coordinacion = f.cleaned_data['coordinacion']
                    certificado.coordinacion.clear()
                    for obj in f.cleaned_data['coordinacion']:
                        certificado.coordinacion.add(obj)
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al guardar los datos. %s" % ex})

        elif action == 'deleteCertificado':
            try:
                certificado = Certificado.objects.get(pk=request.POST['id'])
                puede_realizar_accion(request, 'certi.puede_eliminar_certificados')
                if certificado.tiene_unidades_certificadoras():
                    raise NameError(u"Existen unidades certificadoras registradas.")
                log(u'Elimino certificado: %s' % certificado, request, "del")
                certificado.delete()
                messages.add_message(request, messages.WARNING, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. %s" % ex})

        elif action == 'saveUnidadCertificadora':
            try:
                puede_realizar_accion(request, 'certi.puede_modificar_unidades_certificadoras')
                if 'idc' not in request.POST:
                    raise NameError(u"No se encontro datos del certificado.")
                idc = request.POST['idc']
                if not Certificado.objects.filter(pk=idc).exists():
                    raise NameError(u"No se encontro datos del certificado.")
                certificado = Certificado.objects.get(pk=idc)
                id = None
                type = 'new'
                f = CertificadoUnidadCertificadoraForm(request.POST)
                f.tipo_validacion(certificado)
                if 'id' in request.POST and int(request.POST['id']):
                    id = int(request.POST['id'])
                    type = 'edit'
                if not f.is_valid():
                    # print(f.errors)
                    raise NameError(u"Formulario incorrecto.")
                unidadcertificadora = None
                if type == 'new':
                    if certificado.tipo_validacion == 1:
                        if CertificadoUnidadCertificadora.objects.filter(departamento=f.cleaned_data['departamento'], certificado=certificado).exists():
                            raise NameError(u"Unidad certificadora ya se encuentra registrada.")
                    elif certificado.tipo_validacion == 2:
                        if CertificadoUnidadCertificadora.objects.filter(coordinacion=f.cleaned_data['coordinacion'], certificado=certificado).exists():
                            raise NameError(u"Unidad certificadora ya se encuentra registrada.")

                    unidadcertificadora = CertificadoUnidadCertificadora(certificado=certificado,
                                                                         departamento=f.cleaned_data['departamento'],
                                                                         coordinacion=f.cleaned_data['coordinacion'] if certificado.tipo_validacion == 2 else None,
                                                                         alias=f.cleaned_data['alias'],
                                                                         responsable=f.cleaned_data['responsable'],
                                                                         responsable_titulo=f.cleaned_data['responsable_titulo'],
                                                                         responsable_denominacion=f.cleaned_data['responsable_denominacion'],
                                                                         compartir_responsabilidad=f.cleaned_data.get('compartir_responsabilidad', False)
                                                                         )
                    unidadcertificadora.save(request)
                    log(u'Adiciono unidad certificadora: %s' % unidadcertificadora, request, "add")
                else:
                    if not CertificadoUnidadCertificadora.objects.filter(pk=id).exists():
                        raise NameError(u"Datos incorrectos.")
                    if certificado.tipo_validacion == 1:
                        if CertificadoUnidadCertificadora.objects.filter(departamento=f.cleaned_data['departamento'], certificado=certificado).exclude(pk=id).exists():
                            raise NameError(u"Unidad certificadora ya se encuentra registrada.")
                    elif certificado.tipo_validacion == 2:
                        if CertificadoUnidadCertificadora.objects.filter(coordinacion=f.cleaned_data['coordinacion'], certificado=certificado).exclude(pk=id).exists():
                            raise NameError(u"Unidad certificadora ya se encuentra registrada.")

                    unidadcertificadora = CertificadoUnidadCertificadora.objects.get(pk=id)
                    unidadcertificadora.certificado = certificado
                    unidadcertificadora.departamento = f.cleaned_data['departamento']
                    if certificado.tipo_validacion == 2:
                        unidadcertificadora.coordinacion = f.cleaned_data['coordinacion']
                    unidadcertificadora.compartir_responsabilidad = f.cleaned_data.get('compartir_responsabilidad', False)
                    unidadcertificadora.alias = f.cleaned_data['alias']
                    unidadcertificadora.responsable = f.cleaned_data['responsable']
                    unidadcertificadora.responsable_titulo = f.cleaned_data['responsable_titulo']
                    unidadcertificadora.responsable_denominacion = f.cleaned_data['responsable_denominacion']
                    unidadcertificadora.save(request)
                    log(u'Edito unidad certificadora: %s' % unidadcertificadora, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al guardar los datos. %s" % ex})

        elif action == 'deleteUnidadCertificadora':
            try:
                puede_realizar_accion(request, 'certi.puede_eliminar_unidades_certificadoras')
                unidadcertificadora = CertificadoUnidadCertificadora.objects.get(pk=request.POST['id'])
                if unidadcertificadora.tiene_asistentes_certificadoras():
                    raise NameError(u"Existen asistentes certificadoras registradas.")
                log(u'Elimino unidad certificadora: %s' % unidadcertificadora, request, "del")
                unidadcertificadora.delete()
                messages.add_message(request, messages.WARNING, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. %s" % ex})

        elif action == 'saveAsistenteCertificadora':
            try:
                puede_realizar_accion(request, 'certi.puede_modificar_asistentes_certificadoras')
                if 'idu' not in request.POST:
                    raise NameError(u"No se encontro datos de la unidad certificadora.")
                idu = request.POST['idu']
                if not CertificadoUnidadCertificadora.objects.filter(pk=idu).exists():
                    raise NameError(u"No se encontro datos de la unidad certificadora.")
                unidad = CertificadoUnidadCertificadora.objects.get(pk=idu)
                id = None
                type = 'new'
                f = CertificadoAsistenteCertificadoraForm(request.POST)
                if 'id' in request.POST and int(request.POST['id']):
                    id = int(request.POST['id'])
                    type = 'edit'
                if not f.is_valid():
                    # print(f.errors)
                    raise NameError(u"Formulario incorrecto.")
                if unidad.certificado.tipo_validacion == 2 and not f.cleaned_data['carrera']:
                    raise NameError(u"Debe seleccionar al menos una carrera")
                asistentecertificadora = None
                if type == 'new':
                    if unidad.compartir_responsabilidad and unidad.certificado.tipo_validacion == 1:
                        if CertificadoAsistenteCertificadora.objects.filter(unidad_certificadora=unidad, asistente=f.cleaned_data['asistente'],
                                                                                unidad_certificadora__departamento=unidad.departamento, coordinacion_compartida=f.cleaned_data['coordinacion_compartida']
                                                                                ).exists():
                            raise NameError(u"Asistente certificadora ya se encuentra registrada.")
                    else:
                        if CertificadoAsistenteCertificadora.objects.filter(unidad_certificadora=unidad, asistente=f.cleaned_data['asistente']).exists():
                            raise NameError(u"Asistente certificadora ya se encuentra registrada.")
                    asistentecertificadora = CertificadoAsistenteCertificadora(unidad_certificadora=unidad,
                                                                               asistente=f.cleaned_data['asistente'],
                                                                               asistente_titulo=f.cleaned_data['asistente_titulo'],
                                                                               asistente_denominacion=f.cleaned_data['asistente_denominacion'],
                                                                               coordinacion_compartida=f.cleaned_data.get('coordinacion_compartida')
                                                                               )
                    asistentecertificadora.save(request)
                    if f.cleaned_data['carrera']:
                        #asistentecertificadora.carrera = f.cleaned_data['carrera']
                        for obj  in f.cleaned_data['carrera']:
                            asistentecertificadora.carrera.add(obj)
                    log(u'Adiciono asistente certificadora: %s' % asistentecertificadora, request, "add")
                else:
                    if not CertificadoAsistenteCertificadora.objects.filter(pk=id).exists():
                        raise NameError(u"Datos incorrectos.")

                    if unidad.compartir_responsabilidad and unidad.certificado.tipo_validacion == 1:
                        if CertificadoAsistenteCertificadora.objects.filter(unidad_certificadora=unidad, asistente=f.cleaned_data['asistente'],
                                                                            unidad_certificadora__departamento=unidad.departamento, coordinacion_compartida=f.cleaned_data['coordinacion_compartida']
                                                                                ).exclude(pk=id).exists():
                            raise NameError(u"Asistente certificadora ya se encuentra registrada.")
                    else:
                        if CertificadoAsistenteCertificadora.objects.filter(unidad_certificadora=unidad, asistente=f.cleaned_data['asistente']).exclude(pk=id).exists():
                            raise NameError(u"Asistente certificadora ya se encuentra registrada.")

                    asistentecertificadora = CertificadoAsistenteCertificadora.objects.get(pk=id)
                    asistentecertificadora.unidad_certificadora = unidad
                    asistentecertificadora.asistente = f.cleaned_data['asistente']
                    asistentecertificadora.asistente_titulo = f.cleaned_data['asistente_titulo']
                    asistentecertificadora.asistente_denominacion = f.cleaned_data['asistente_denominacion']
                    asistentecertificadora.coordinacion_compartida = f.cleaned_data.get('coordinacion_compartida')
                    asistentecertificadora.carrera.clear()
                    # asistentecertificadora.save(request)
                    # asistentecertificadora.carrera = f.cleaned_data['carrera']
                    for carr in f.cleaned_data['carrera']:
                        asistentecertificadora.carrera.add(carr)
                    asistentecertificadora.save(request)
                    log(u'Edito asistente certificadora: %s' % asistentecertificadora, request, "edit")
                messages.add_message(request, messages.SUCCESS, f'Se guardo correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error al guardar los datos. %s" % ex})

        elif action == 'deleteAsistenteCertificadora':
            try:
                puede_realizar_accion(request, 'certi.puede_eliminar_asistentes_certificadoras')
                asistentecertificadora = CertificadoAsistenteCertificadora.objects.get(pk=request.POST['id'])
                # if asistentecertificadora.tiene_asistentes_certificadoras():
                #     return JsonResponse({"result": "bad", "mensaje": u"Existen asistentes certificadoras registradas."})
                log(u'Elimino asistente certificadora: %s' % asistentecertificadora, request, "del")
                asistentecertificadora.delete()
                messages.add_message(request, messages.WARNING, f'Se elimino correctamente el registro')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos. %s" % ex})

        elif action == 'deleteCarrera':
            try:
                puede_realizar_accion(request, 'certi.puede_eliminar_asistentes_certificadoras')
                asistentecertificadora = CertificadoAsistenteCertificadora.objects.get(pk=request.POST['id'])
                carrera = Carrera.objects.get(pk=request.POST['idc'])
                asistentecertificadora.carrera.remove(carrera)
                log(u'Elimino carrera de asistente certificadora: %s' % carrera, request, "del")
                messages.add_message(request, messages.WARNING, f'Se quito carrera correctamente')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al quitar la carrera. %s" % ex})

        elif action == 'loadClone':
            try:
                data['certificados'] = certificados = Certificado.objects.filter(tipo_origen=request.POST['to'], tipo_validacion=request.POST['tv']).exclude(pk=request.POST['idc'])
                data['certificado'] = certificado = Certificado.objects.get(pk=request.POST['idc'])
                template = get_template("adm_certificados/loadClone.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex})

        elif action == 'loadCertifyingEntities':
            try:
                data['certificado'] = certificado = Certificado.objects.get(pk=request.POST['id'])
                template = get_template("adm_certificados/loadCertifyingEntities.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos. %s" % ex})

        elif action == 'cloneEntities':
            try:
                if not 'id_to' in request.POST or not 'id_from' in request.POST:
                    raise NameError(u"Falta parametros")
                if not Certificado.objects.filter(pk=request.POST['id_to']).exists() or not Certificado.objects.filter(pk=request.POST['id_from']).exists():
                    raise NameError(u"No se encontro la unidad certificadora a copiar")
                certificado_to = Certificado.objects.get(pk=request.POST['id_to'])
                certificado_from = Certificado.objects.get(pk=request.POST['id_from'])
                for uc_from in certificado_from.unidades_certificadoras():
                    acs_from = uc_from.asistentes_certificadoras()
                    uc_to = uc_from
                    uc_to.pk = None
                    uc_to.certificado = certificado_to
                    uc_to.save(request)
                    log(u'Adiciono unidad certificadora: %s' % uc_to, request, "add")
                    for ac_from in acs_from:
                        ac_to = ac_from
                        c_to = ac_from.carreras()
                        ac_to.pk = None
                        ac_to.unidad_certificadora = uc_to
                        ac_to.save(request)
                        ac_to.carrera.set(c_to)
                        log(u'Adiciono asistente certificadora: %s' % ac_to, request, "add")
                messages.add_message(request, messages.SUCCESS, f'Se copio correctamente las unidades certificadoras')
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al copiar los datos. %s" % ex})

        elif action == 'editresponasablesunidadescertificadoras':
            try:
                # puede_realizar_accion(request, 'certi.puede_eliminar_asistentes_certificadoras')
                form = ResponsableCertificadoUnidadCertificadoraForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError("%s: %s" %(k, v[0]))

                responsable_id = request.POST['responsable_id']
                tipo_origen = request.POST['tipo_origen']
                unidades_certificadoras = CertificadoUnidadCertificadora.objects.filter(status=True, responsable_id=responsable_id, certificado__tipo_origen=tipo_origen)
                if 'certificado_id' in request.POST:
                    unidades_certificadoras = unidades_certificadoras.filter(certificado_id=request.POST['certificado_id'])

                for unidad in unidades_certificadoras:
                    unidad.responsable = form.cleaned_data['responsable']
                    unidad.responsable_titulo = form.cleaned_data['responsable_titulo']
                    unidad.responsable_denominacion = form.cleaned_data['responsable_denominacion']
                    unidad.save(request)
                    log(u'Actulizo responsable unidad certificado: %s' % unidad, request, "edit")
                return JsonResponse({"result": True, "mensaje": u"Se actualizo correctamente las unidades certificadoras.", "btipo_origen": tipo_origen})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"%s" % ex.__str__()})

        elif action == 'editasistentescertificadoras':
            try:
                # puede_realizar_accion(request, 'certi.puede_eliminar_asistentes_certificadoras')
                form = AsistenteCertificadoAsistenteCertificadoraForm(request.POST)
                if not form.is_valid():
                    for k, v in form.errors.items():
                        raise NameError("%s: %s" %(k, v[0]))

                asistente_id = request.POST['asistente_id']
                tipo_origen = request.POST['tipo_origen']
                asistentes = CertificadoAsistenteCertificadora.objects.filter(status=True, asistente_id=asistente_id, unidad_certificadora__certificado__tipo_origen=tipo_origen)
                if 'certificado_id' in request.POST:
                    asistentes = asistentes.filter(unidad_certificadora__certificado_id=request.POST['certificado_id'])

                for asistentecer in asistentes:
                    asistentecer.asistente = form.cleaned_data['asistente']
                    asistentecer.asistente_titulo = form.cleaned_data['asistente_titulo']
                    asistentecer.asistente_denominacion = form.cleaned_data['asistente_denominacion']
                    asistentecer.save(request)
                    log(u'Actulizo responsable unidad certificado: %s' % asistentecer, request, "edit")
                return JsonResponse({"result": True, "mensaje": u"Se actualizo correctamente las unidades certificadoras.", "btipo_origen": tipo_origen})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": False, "mensaje": u"%s" % ex.__str__()})

        if action == 'searchServicio':
            try:
                id = request.POST['id']
                eServicio = Servicio.objects.get(pk=id)
                data = {"result": "ok", "costo": eServicio.costo}
                return JsonResponse(data)
            except Exception as ex:
                data = {"result": "ok", "costo": 0.0}
                return JsonResponse(data)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Agregar certificado'
                    f = CertificadoForm()
                    data['form'] = f
                    return render(request, "adm_certificados/addcertificado.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'edit':
                try:
                    data['title'] = u'Editar certificado'
                    if 'id' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    id = request.GET['id']
                    if not Certificado.objects.filter(pk=id).exists():
                        raise NameError(u"No se encontro datos.")
                    data['certificado'] = certificado = Certificado.objects.get(pk=id)
                    f = CertificadoForm(initial=model_to_dict(certificado))
                    f.editar(certificado)
                    # f.set_coordinacion(certificado.get_coordinaciones())
                    data['form'] = f
                    return render(request, "adm_certificados/editcertificado.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'deletecertificado':
                try:
                    puede_realizar_accion(request, 'certi.puede_eliminar_certificados')
                    data['title'] = u'Eliminar de certificación'
                    data['certificado'] = certificado = Certificado.objects.get(pk=request.GET['id'])
                    return render(request, "adm_certificados/deletecertificado.html", data)
                except Exception as ex:
                    pass

            elif action == 'unidadescertificadoras':
                try:
                    data['title'] = u'Unidades certificadoras'
                    search = None
                    ids = None
                    departamentos = None
                    facultades = None
                    if 'idc' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    idc = request.GET['idc']
                    if not Certificado.objects.filter(pk=idc).exists():
                        raise NameError(u"No se encontro datos.")
                    certificado = Certificado.objects.get(pk=idc)
                    departamentos = Departamento.objects.filter(status=True, integrantes__isnull=False).distinct()
                    facultades = Coordinacion.objects.filter(status=True, carrera__isnull=False).distinct()
                    unidades = CertificadoUnidadCertificadora.objects.filter(certificado=certificado)
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        unidades = unidades.filter(pk=ids)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            unidades = unidades.filter(Q(responsable__nombres__icontains=search) |
                                                       Q(responsable__apellido1__icontains=search) |
                                                       Q(responsable__apellido2__icontains=search) |
                                                       Q(responsable_titulo__icontains=search))
                        else:
                            unidades = unidades.filter(Q(responsable__apellido1__icontains=ss[0]) |
                                                       Q(responsable__apellido2__icontains=ss[1]) |
                                                       Q(responsable_titulo__icontains=search))
                    iddd = 0
                    idcc = 0
                    if 'iddd' in request.GET and int(request.GET['iddd']) > 0 and certificado.tipo_validacion == 1:
                        iddd = int(request.GET['iddd'])
                        unidades = unidades.filter(departamento_id=iddd)
                    if 'idcc' in request.GET and int(request.GET['idcc']) > 0 and certificado.tipo_validacion == 2:
                        idcc = int(request.GET['idcc'])
                        unidades = unidades.filter(coordinacion_id=idcc)
                    paging = MiPaginador(unidades, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['unidades'] = page.object_list
                    data['departamentos'] = departamentos
                    data['facultades'] = facultades
                    data['certificado'] = certificado
                    data['iddd'] = iddd
                    data['idcc'] = idcc
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""

                    return render(request, "adm_certificados/unidadescertificadoras.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'addunidadcertificadora':
                try:
                    data['title'] = u'Agregar unidad certificadora'
                    if 'idc' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    idc = request.GET['idc']
                    if not Certificado.objects.filter(pk=idc).exists():
                        raise NameError(u"No se encontro datos.")
                    data['certificado'] = certificado = Certificado.objects.get(pk=idc)
                    f = CertificadoUnidadCertificadoraForm()
                    f.tipo_validacion(certificado)
                    data['form'] = f
                    return render(request, "adm_certificados/addunidadcertificadora.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'editunidadcertificadora':
                try:
                    data['title'] = u'Editar unidad certificadora'
                    if 'id' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    id = request.GET['id']
                    if not CertificadoUnidadCertificadora.objects.filter(pk=id).exists():
                        raise NameError(u"No se encontro datos.")
                    data['unidad'] = unidad = CertificadoUnidadCertificadora.objects.get(pk=id)
                    f = CertificadoUnidadCertificadoraForm(initial=model_to_dict(unidad))
                    f.tipo_validacion(unidad.certificado)
                    data['form'] = f
                    return render(request, "adm_certificados/editunidadcertificadora.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'deleteunidadcertificadora':
                try:
                    puede_realizar_accion(request, 'certi.puede_eliminar_unidades_certificadoras')
                    data['title'] = u'Eliminar de unidad certificadora'
                    data['unidad'] = unidad = CertificadoUnidadCertificadora.objects.get(pk=request.GET['id'])
                    return render(request, "adm_certificados/deleteunidadcertificadora.html", data)
                except Exception as ex:
                    pass

            elif action == 'asistentescertificadoras':
                try:
                    data['title'] = u'Asistentes certificadoras'
                    search = None
                    ids = None
                    departamentos = None
                    facultades = None
                    if 'idu' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    idu = request.GET['idu']
                    if not CertificadoUnidadCertificadora.objects.filter(pk=idu).exists():
                        raise NameError(u"No se encontro datos.")
                    unidad = CertificadoUnidadCertificadora.objects.get(pk=idu)
                    asistentes = CertificadoAsistenteCertificadora.objects.filter(unidad_certificadora=unidad)
                    if 'id' in request.GET:
                        ids = request.GET['id']
                        asistentes = asistentes.filter(pk=ids)
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            asistentes = asistentes.filter(Q(asistente__nombres__icontains=search) |
                                                           Q(asistente__apellido1__icontains=search) |
                                                           Q(asistente__apellido2__icontains=search) |
                                                           Q(asistente_titulo__icontains=search))
                        else:
                            asistentes = asistentes.filter(Q(responsable__apellido1__icontains=ss[0]) |
                                                           Q(responsable__apellido2__icontains=ss[1]) |
                                                           Q(asistente_titulo__icontains=search))

                    paging = MiPaginador(asistentes, 20)
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
                    data['page'] = page
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['asistentes'] = page.object_list
                    data['unidad'] = unidad
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""

                    return render(request, "adm_certificados/asistentescertificadoras.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'deletecarrera':
                try:
                    puede_realizar_accion(request, 'certi.puede_eliminar_asistentes_certificadoras')
                    data['title'] = u'Eliminar carrera'
                    data['asistente'] = CertificadoAsistenteCertificadora.objects.get(pk=request.GET['id'])
                    data['carrera'] = Carrera.objects.get(pk=request.GET['idc'])
                    return render(request, "adm_certificados/deletecarrera.html", data)
                except Exception as ex:
                    pass

            elif action == 'addasistentecertificadora':
                try:
                    data['title'] = u'Agregar asistente certificadora'
                    if 'idu' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    idu = request.GET['idu']
                    if not CertificadoUnidadCertificadora.objects.filter(pk=idu).exists():
                        raise NameError(u"No se encontro datos.")
                    data['unidad'] = unidad = CertificadoUnidadCertificadora.objects.get(pk=idu)
                    f = CertificadoAsistenteCertificadoraForm()
                    f.set_departamento(unidad)
                    data['form'] = f
                    return render(request, "adm_certificados/addasistentecertificadora.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'editasistentecertificadora':
                try:
                    data['title'] = u'Editar asistente certificadora'
                    if 'id' not in request.GET:
                        raise NameError(u"No se encontro datos.")
                    id = request.GET['id']
                    if not CertificadoAsistenteCertificadora.objects.filter(pk=id).exists():
                        raise NameError(u"No se encontro datos.")
                    data['asistente'] = asistente = CertificadoAsistenteCertificadora.objects.get(pk=id)
                    f = CertificadoAsistenteCertificadoraForm(initial=model_to_dict(asistente))
                    f.set_departamento(asistente.unidad_certificadora)
                    data['form'] = f
                    return render(request, "adm_certificados/editasistentecertificadora.html", data)
                except Exception as ex:
                    return HttpResponseRedirect('/adm_certificados?info=%s' % ex)

            elif action == 'deleteasistentecertificadora':
                try:
                    puede_realizar_accion(request, 'certi.puede_eliminar_asistentes_certificadoras')
                    data['title'] = u'Eliminar de asistente certificadora'
                    destination = 'asistentescertificadoras'
                    if 'destination' in request.GET:
                        if request.GET['destination'] == 'unidad':
                            destination = 'unidadescertificadoras'
                    data['destination'] = destination
                    data['asistente'] = asistente = CertificadoAsistenteCertificadora.objects.get(pk=request.GET['id'])
                    return render(request, "adm_certificados/deleteasistentecertificadora.html", data)
                except Exception as ex:
                    pass

            elif action == 'showresponasablesunidadescertificadoras':
                try:
                    unidades_certificadoras = CertificadoUnidadCertificadora.objects.filter(status=True)
                    data['responsablesunidad_internos'] =unidades_internos = unidades_certificadoras.filter(certificado__tipo_origen=1).order_by("responsable_id", "responsable_titulo", "responsable_denominacion").distinct("responsable_id", "responsable_titulo", "responsable_denominacion")
                    data['responsablesunidad_externos'] = unidades_externos = unidades_certificadoras.filter(certificado__tipo_origen=2).order_by("responsable_id", "responsable_titulo", "responsable_denominacion").distinct("responsable_id", "responsable_titulo", "responsable_denominacion")
                    data['title'] = u'Cambiar Responsables de Unidades  Certificadoras'
                    data['action'] = action
                    data['btipo_origen'] = request.GET['btipo_origen']
                    template = get_template("adm_certificados/modal/showresponasablesunidadescertificadoras.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al mostrar datos."})

            elif action == 'editresponasablesunidadescertificadoras':
                try:
                    data['responsable_id'] = responsable_id = request.GET['responsable_id']
                    data['tipo_origen'] = tipo_origen = request.GET['tipo_origen']
                    unidades_certificadoras = CertificadoUnidadCertificadora.objects.filter(status=True, responsable_id=responsable_id, certificado__tipo_origen=tipo_origen)
                    data['title'] = u'Editar Masivamente Responsable de Unidades  Certificadoras'
                    if 'certificado_id' in request.GET:
                        data['certificado_id'] = certificado_id = request.GET['certificado_id']
                        unidades_certificadoras = unidades_certificadoras.filter(certificado_id=certificado_id)
                        data['title'] = u'Editar Responsable de Unidades  Certificadoras'

                    data['action'] = action
                    data['form'] = form = ResponsableCertificadoUnidadCertificadoraForm(initial=model_to_dict(unidades_certificadoras.first()))
                    template = get_template("adm_certificados/modal/modaleditresponasablesunidadescertificadoras.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al mostrar datos."})

            elif action == 'showasistentescertificadoras':
                try:
                    asistentes_certificadoras = CertificadoAsistenteCertificadora.objects.filter(status=True)
                    data['asistentes_internos'] = asistentes_internos = asistentes_certificadoras.filter(unidad_certificadora__certificado__tipo_origen=1).order_by("asistente_id", "asistente_titulo", "asistente_denominacion").distinct("asistente_id")
                    data['asistentes_externos'] = asistentes_externos = asistentes_certificadoras.filter(unidad_certificadora__certificado__tipo_origen=2).order_by("asistente_id", "asistente_titulo", "asistente_denominacion").distinct("asistente_id")
                    data['title'] = u'Cambiar Asistente de Unidades  Certificadoras'
                    data['action'] = action
                    data['btipo_origen'] = request.GET['btipo_origen']
                    template = get_template("adm_certificados/modal/showasistentescertificadoras.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al mostrar datos."})

            elif action == 'editasistentescertificadoras':
                try:
                    data['asistente_id'] = asistente_id = request.GET['asistente_id']
                    data['tipo_origen'] = tipo_origen = request.GET['tipo_origen']
                    asistente_certificadoras = CertificadoAsistenteCertificadora.objects.filter(status=True, asistente_id=asistente_id, unidad_certificadora__certificado__tipo_origen=tipo_origen)
                    data['title'] = u'Editar Masivamente Asistente Certificadoras'
                    if 'certificado_id' in request.GET:
                        data['certificado_id'] = certificado_id = request.GET['certificado_id']
                        asistente_certificadoras = asistente_certificadoras.filter(unidad_certificadora__certificado_id=certificado_id)
                        data['title'] = u'Editar Asistentes  Certificadoras'

                    data['action'] = action
                    data['form'] = form = AsistenteCertificadoAsistenteCertificadoraForm(initial=model_to_dict(asistente_certificadoras.first()))
                    template = get_template("adm_certificados/modal/modaleditasistentescertificadoras.html")
                    return JsonResponse({"result": True, 'data': template.render(data), 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": u"Error al mostrar datos."})

            return HttpResponseRedirect('/')
        else:
            try:
                data['title'] = u"Certificados"
                search = None
                ids = None
                certificados = Certificado.objects.filter(status=True).order_by('codigo', 'tipo_origen', '-version')
                unidades_cer = CertificadoUnidadCertificadora.objects.filter(certificado__in=certificados.values_list('id', flat=True))
                coordinaciones = Coordinacion.objects.filter(id__in=unidades_cer.values_list('coordinacion_id', flat=True).distinct())
                departamentos = Departamento.objects.filter(id__in=unidades_cer.values_list('departamento_id', flat=True).distinct())
                data['total_internos'] = total_internos = certificados.filter(tipo_origen=1).count()
                data['total_internos_facultad'] = total_internos_facultad = certificados.filter(tipo_origen=1, tipo_validacion=2).count()
                data['total_internos_departamento'] = total_internos_departamento = certificados.filter(tipo_origen=1, tipo_validacion=1).count()
                data['total_externos'] = total_externos = certificados.filter(tipo_origen=2).count()
                if 'id' in request.GET:
                    ids = request.GET['id']
                    certificados = certificados.filter(pk=ids)
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    certificados = certificados.filter(Q(certificacion__icontains=search) |
                                                       Q(reporte__nombre__icontains=search) |
                                                       Q(reporte__descripcion__icontains=search)|
                                                       Q(codigo__icontains=search))

                visible = 0
                if 'v' in request.GET and int(request.GET['v']) > 0:
                    visible = int(request.GET['v'])
                    certificados = certificados.filter(visible=int(request.GET['v']) == 1)

                origen = 0
                if 'o' in request.GET and int(request.GET['o']) > 0:
                    origen = int(request.GET['o'])
                    certificados = certificados.filter(tipo_origen=int(request.GET['o']))

                destino = 0
                if 'd' in request.GET and int(request.GET['d']) > 0:
                    destino = int(request.GET['d'])
                    certificados = certificados.filter(destino=int(request.GET['d']))

                tipo_validacion = 0
                if 'tv' in request.GET and int(request.GET['tv']) > 0:
                    tipo_validacion = int(request.GET['tv'])
                    certificados = certificados.filter(tipo_validacion=int(request.GET['tv']))



                departamento = 0
                if 'dep' in request.GET and int(request.GET['dep']) > 0:
                    departamento = int(request.GET['dep'])
                    certificados = certificados.filter(pk__in=unidades_cer.filter(departamento__id=departamento).values("certificado_id").distinct())
                   # certificados = certificados.filter(certificadounidadcertificadora__departamento__id=departamento)

                coordinacion = 0
                if 'co' in request.GET and int(request.GET['co']) > 0:
                    coordinacion = int(request.GET['co'])
                    certificados = certificados.filter(pk__in=unidades_cer.filter(coordinacion__id=coordinacion).values("certificado_id").distinct())
                   # certificados = certificados.filter(certificadounidadcertificadora__departamento__id=departamento)
                paging = MiPaginador(certificados, 25)
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
                data['page'] = page
                data['rangospaging'] = paging.rangos_paginado(p)
                data['certificados'] = page.object_list
                data['visible'] = visible
                data['origen'] = origen
                data['tipo_validacion'] = tipo_validacion
                data['destinos'] = DESTINO_CERTIFICADO
                data['destino'] = destino
                data['departamentoselect'] = departamento
                data['departamentos'] = departamentos
                data['coordinacionselect'] = coordinacion
                data['coordinaciones'] = coordinaciones
                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                return render(request, "adm_certificados/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect('/info=%s' % ex)
