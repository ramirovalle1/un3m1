# -*- coding: UTF-8 -*-
import json
from datetime import datetime, timedelta, date
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Max
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from decorators import secure_module
from sagest.commonviews import secuencia_convenio_devengacion
from sagest.forms import CapacitacionPersonaForm
from sagest.models import DistributivoPersona
from sga.commonviews import adduserdata
from sga.forms import PlanificarCapacitacionesForm, PlanificarCapacitacionesArchivoForm, \
    SubirEvidenciaEjecutadoCapacitacionesForm

from sga.funciones import log, generar_nombre, variable_valor, null_to_decimal, \
    fechaletra_corta
from sga.models import miinstitucion, MESES_CHOICES, \
    PlanificarCapacitaciones, \
    PlanificarCapacitacionesCriterios, CronogramaCapacitacionDocente, PlanificarCapacitacionesDetalleCriterios, \
    PlanificarCapacitacionesRecorrido, Capacitacion
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not persona.es_administrativo_perfilactivo():
        return HttpResponseRedirect("/?info=Solo los perfiles de Administrativos pueden ingresar al módulo.")
    periodo = request.session['periodo']
    administrativo = persona.administrativo()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'detallecapacitacion':
                try:
                    data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=request.POST['id'])
                    data['capacitaciondetallecriterio'] = capacitacion.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                    data['capacitacionrecorrido'] = capacitacion.planificarcapacitacionesrecorrido_set.filter(status=True).order_by('id')
                    data['tipoaccion'] = 'MOSTRARDATOS'

                    template = get_template("adm_capacitacion/detallecapacitacion.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'generanumeroconvenio':
                try:
                    capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                    if not capacitacion.numeroconvenio:
                        secuencia = secuencia_convenio_devengacion(2)

                        if PlanificarCapacitaciones.objects.filter(fechaconvenio__year=datetime.now().year, numeroconvenio=secuencia, tipo=2, status=True).exists():
                            return JsonResponse({"result": "bad", "mensaje": u"Error al generar el convenio, intente nuevamente"})

                        capacitacion.fechaconvenio = datetime.now()
                        capacitacion.numeroconvenio = secuencia
                        capacitacion.save(request)
                        log(u'Editó solicitud de capacitacion/actualización: %s' % capacitacion, request, "edit")

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar la secuencia del convenio."})

            elif action == 'conveniodevengacion_pdf':
                try:
                    data = {}

                    data['dth'] = dth = DistributivoPersona.objects.get(denominacionpuesto_id=83, status=True)

                    tit1 = tit2 = ""
                    tit1th = None
                    dir = dth.persona.titulacion_principal_senescyt_registro()
                    if dir != '':
                        tit1th = dth.persona.titulacion_set.filter(titulo__nivel_id=3).order_by('-fechaobtencion')[0]
                        tit1 = tit1th.titulo.abreviatura
                        tit1 = tit1 + "." if tit1.find(".") < 0 else tit1

                    tit2th = dth.persona.titulacion_principal_senescyt_registro()
                    if tit2th:
                        tit2 = tit2th.titulo.abreviatura if tit2th.titulo.nivel_id == 4 else ''
                        if tit2 != '':
                            tit2 = tit2 + "." if tit2.find(".") < 0 else tit2

                    if tit1 != "":
                        if tit2 != "":
                            tit2 = ", " + tit2
                    else:
                        if tit2 != "":
                            tit1 = tit2
                            tit2 = ""

                    data['titulo1dth'] = tit1
                    data['titulo2dth'] = tit2

                    data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=int(encrypt(request.POST['id'])))

                    tit1 = tit2 = ""
                    tit1doc = None
                    doc = capacitacion.administrativo.persona.titulacion_principal_senescyt_registro()
                    if doc != '':
                        tit1th = doc.persona.titulacion_set.filter(titulo__nivel_id=3).order_by('-fechaobtencion')[0]
                        tit1 = tit1th.titulo.abreviatura.strip()
                        if tit1 != '':
                            tit1 = tit1 + "." if tit1.find(".") < 0 else tit1

                    tit2doc = capacitacion.administrativo.persona.titulacion_principal_senescyt_registro()
                    if tit2doc:
                        tit2 = tit2doc.titulo.abreviatura.strip() if tit2doc.titulo.nivel_id == 4 else ''
                        if tit2 != '':
                            tit2 = tit2 + "." if tit2.find(".") < 0 else tit2

                    if tit1 != "":
                        if tit2 != "":
                            tit2 = ", " + tit2
                    else:
                        if tit2 != "":
                            tit1 = tit2
                            tit2 = ""

                    data['titulo1bene'] = tit1
                    data['titulo2bene'] = tit2

                    data['numeroconvenio'] = "N° " + str(capacitacion.numeroconvenio).zfill(3) + ".UATH.LOSEP." + str(capacitacion.fechaconvenio.year)
                    data['fechaconvenio'] = fechaletra_corta(capacitacion.fechaconvenio)
                    data['titulo1bene'] = tit1
                    data['titulo2bene'] = tit2
                    data['fechainiciocap'] = str(capacitacion.fechainicio.day) + " de " + MESES_CHOICES[capacitacion.fechainicio.month - 1][1].capitalize() + " del " + str(capacitacion.fechainicio.year)
                    data['fechafincap'] = str(capacitacion.fechafin.day) + " de " + MESES_CHOICES[capacitacion.fechafin.month - 1][1].capitalize() + " del " + str(capacitacion.fechafin.year)
                    return conviert_html_to_pdf(
                        'adm_capacitacion/conveniodevengacion_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    return HttpResponseRedirect("/adm_capacitacion?info=%s" % "Error al generar el reporte")

            elif action == 'addsolicitud':
                try:
                    form = PlanificarCapacitacionesForm(request.POST, request.FILES)
                    convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['convocatoria']))
                    fechainicio = str(convocatoria.iniciocapacitacion)
                    fechainicio = fechainicio[8:10] + '-' + fechainicio[5:7] + '-' + fechainicio[0:4]
                    fechafin = str(convocatoria.fincapacitacion)
                    fechafin = fechafin[8:10] + '-' + fechafin[5:7] + '-' + fechafin[0:4]
                    saldo = null_to_decimal(convocatoria.monto - convocatoria.totalmonto_administrativo(administrativo=administrativo, convocatoria=convocatoria))

                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]

                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if form.is_valid():
                        if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitacion:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainicio)})

                        if form.cleaned_data['fechafin'] > convocatoria.fincapacitacion:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafin)})

                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})

                        if form.cleaned_data['horas'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El número de horas debe ser mayor a 0"})

                        if form.cleaned_data['costo'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo debe ser mayor a $ 0.00"})

                        costo = Decimal(form.cleaned_data['costo']).quantize(Decimal('0.00'))
                        if costo > saldo:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo supera el monto disponible: $ %s" % saldo})

                        lista = json.loads(request.POST['lista_items1'])
                        for l in lista:
                            if l['obligatorio'] is True and l['valor'] is False:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u'El criterio "%s" es obligatorio de marcar' % l['criterio']})

                        planificarcapacitacion = PlanificarCapacitaciones(cronograma=convocatoria,
                                                                          administrativo=administrativo,
                                                                          tema=form.cleaned_data['tema'],
                                                                          justificacion=form.cleaned_data['justificacion'],
                                                                          institucion=form.cleaned_data['institucion'].upper(),
                                                                          link=form.cleaned_data['link'],
                                                                          fechainicio=form.cleaned_data['fechainicio'],
                                                                          fechafin=form.cleaned_data['fechafin'],
                                                                          pais=form.cleaned_data['pais'],
                                                                          modalidad=form.cleaned_data['modalidad'],
                                                                          costo=form.cleaned_data['costo'],
                                                                          devolucion=0.00,
                                                                          costoneto=form.cleaned_data['costo'],
                                                                          horas=form.cleaned_data['horas'],
                                                                          periodo=periodo,
                                                                          estado=1,
                                                                          tipo=2,
                                                                          infocompletacap=False)

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivocapacitacionadmtrab", newfile._name)
                            planificarcapacitacion.archivo=newfile

                        planificarcapacitacion.save(request)

                        if 'lista_items1' in request.POST:
                            lista = json.loads(request.POST['lista_items1'])
                            for l in lista:
                                detallecriterios = PlanificarCapacitacionesDetalleCriterios(capacitacion=planificarcapacitacion,
                                                                                            criterio_id=l['id'],
                                                                                            estadodocente=l['valor'],
                                                                                            estadodirector=False,
                                                                                            estadouath=False)
                                detallecriterios.save()

                        #micorreo = Persona.objects.get(cedula='0923704928')

                        send_html_mail("Registro de Solicitud de capacitación",
                                       "emails/solicitud_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'administrativo': administrativo.persona,
                                        'numero': planificarcapacitacion.id,
                                        't': miinstitucion()},
                                       administrativo.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        # Director del departamento - envio de e-mail
                        director = planificarcapacitacion.obtenerdatosautoridad('DIRDEPA', periodo)
                        if director:
                            send_html_mail("Registro de Solicitud de capacitación",
                                           "emails/notificacion_capadmtra.html",
                                           {'sistema': u'SAGEST - UNEMI',
                                            'fase': 'SOL',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': planificarcapacitacion.id,
                                            'administrativo': administrativo.persona,
                                            'autoridad1': director.responsable,
                                            'autoridad2': '',
                                            't': miinstitucion()
                                            },
                                           director.responsable.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                        log(u'Adicionó solicitud de capacitacion/actualización: %s' % planificarcapacitacion,request, "add")
                        return JsonResponse({"result": "ok" })
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editsolicitud':
                try:
                    form = PlanificarCapacitacionesForm(request.POST, request.FILES)
                    convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.POST['convocatoria']))

                    fechainicio = str(convocatoria.iniciocapacitacion)
                    fechainicio = fechainicio[8:10] + '-' + fechainicio[5:7] + '-' + fechainicio[0:4]
                    fechafin = str(convocatoria.fincapacitacion)
                    fechafin = fechafin[8:10] + '-' + fechafin[5:7] + '-' + fechafin[0:4]

                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))
                    costosolcap = solicitud.costo

                    saldo = null_to_decimal(convocatoria.monto - (convocatoria.totalmonto_administrativo(administrativo=administrativo, convocatoria=convocatoria) - costosolcap))

                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]

                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if form.is_valid():
                        if form.cleaned_data['fechainicio'] < convocatoria.iniciocapacitacion:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha de inicio debe ser mayor o igual a %s" % (fechainicio)})

                        if form.cleaned_data['fechafin'] > convocatoria.fincapacitacion:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha de fin debe ser menor o igual a %s" % (fechafin)})

                        if form.cleaned_data['fechainicio'] > form.cleaned_data['fechafin']:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha de inicio deber ser menor o igual a la fecha fin"})

                        if form.cleaned_data['horas'] <=0:
                            return JsonResponse({"result": "bad", "mensaje": u"El número de horas debe ser mayor a 0"})

                        if form.cleaned_data['costo'] <= 0:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo debe ser mayor a $ 0.00"})

                        costo = Decimal(form.cleaned_data['costo']).quantize(Decimal('0.00'))
                        if costo > saldo:
                            return JsonResponse({"result": "bad", "mensaje": u"El costo supera el monto disponible: $ %s" % saldo})

                        lista = json.loads(request.POST['lista_items1'])
                        for l in lista:
                            if l['obligatorio'] is True and l['valor'] is False:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u'El criterio "%s" es obligatorio de marcar' % l['criterio']})

                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                        solicitud.tema = form.cleaned_data['tema']
                        solicitud.justificacion = form.cleaned_data['justificacion']
                        solicitud.institucion = form.cleaned_data['institucion'].upper()
                        solicitud.link = form.cleaned_data['link']
                        solicitud.fechainicio = form.cleaned_data['fechainicio']
                        solicitud.fechafin = form.cleaned_data['fechafin']
                        solicitud.pais = form.cleaned_data['pais']
                        solicitud.modalidad = form.cleaned_data['modalidad']
                        solicitud.costo = form.cleaned_data['costo']
                        solicitud.costoneto = form.cleaned_data['costo']
                        solicitud.horas = form.cleaned_data['horas']

                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            newfile._name = generar_nombre("archivocapacitacionadmtrab", newfile._name)
                            solicitud.archivo = newfile

                        solicitud.save(request)

                        if 'lista_items1' in request.POST:
                            lista = json.loads(request.POST['lista_items1'])
                            for l in lista:
                                detallecriterios = PlanificarCapacitacionesDetalleCriterios.objects.get(pk=int(l['id']))
                                detallecriterios.estadodocente = l['valor']
                                detallecriterios.save()

                        log(u'Editó solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")
                        return JsonResponse({"result": "ok" })
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'addarchivoconvenio':
                try:
                    f = PlanificarCapacitacionesArchivoForm(request.FILES)
                    newfile = None

                    if 'archivoconvenio' in request.FILES:
                        arch = request.FILES['archivoconvenio']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam-1]
                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                    if f.is_valid():
                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.POST['id']))
                        newfile = request.FILES['archivoconvenio']
                        newfile._name = generar_nombre("conveniodevengaciondocente", newfile._name)
                        solicitud.archivoconvenio = newfile
                        solicitud.save(request)
                        log(u'Agregó archivo de convenio a la solicitud de capacitacion/actualización: %s' % solicitud, request, "edit")


                        email_autoridad2 = 'formacion_uath@unemi.edu.ec'
                        tituloemail = 'Registro de Convenio de Devengación - ' + str(persona)
                        autoridad2nombre = ''

                        send_html_mail(tituloemail,
                                       "emails/notificacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'fase': 'CDE',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'numero': solicitud.id,
                                        'administrativo': solicitud.administrativo.persona,
                                        'autoridad1': autoridad2nombre,
                                        't': miinstitucion()
                                        },
                                       [email_autoridad2],
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subirevidenciaejecutadocap':
                try:
                    f = SubirEvidenciaEjecutadoCapacitacionesForm(request.POST, request.FILES)
                    evidenciavalidar = request.POST['evidenciavalidar']
                    newfile = None

                    if evidenciavalidar == 'FAC':
                        if not 'factura' in request.FILES:
                            return JsonResponse({"result": "bad", "mensaje": u"Atención, debe subir el archivo de la factura."})
                    else:
                        if not 'informe' in request.FILES and not 'certificado' in request.FILES:
                            return JsonResponse({"result": "bad", "mensaje": u"Atención, debe subir mínimo un archivo de las evidencias."})

                    if 'factura' in request.FILES:
                        arch = request.FILES['factura']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if 'informe' in request.FILES:
                        arch = request.FILES['informe']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if 'certificado' in request.FILES:
                        arch = request.FILES['certificado']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 4194304:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        capacitacion = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                        if 'factura' in request.FILES:
                            newfile = request.FILES['factura']
                            newfile._name = generar_nombre("evidejecapfactura", newfile._name)
                            capacitacion.archivofactura = newfile

                        if 'informe' in request.FILES:
                            newfile = request.FILES['informe']
                            newfile._name = generar_nombre("evidejecapinforme", newfile._name)
                            capacitacion.archivoinforme = newfile

                        if 'certificado' in request.FILES:
                            newfile = request.FILES['certificado']
                            newfile._name = generar_nombre("evidejecapcertificado", newfile._name)
                            capacitacion.archivocertificado = newfile

                            newfile = request.FILES['certificado']
                            newfile._name = generar_nombre("capacitacion_", newfile._name)
                            if capacitacion.capacitacion is None:
                                capacitacionth = Capacitacion(persona=persona,
                                                            institucion=capacitacion.institucion,
                                                            nombre=capacitacion.tema,
                                                            anio=datetime.now().date().year,
                                                            pais=capacitacion.pais,
                                                            fechainicio=capacitacion.fechainicio,
                                                            fechafin=capacitacion.fechafin,
                                                            horas=capacitacion.horas,
                                                            modalidad=capacitacion.modalidad,
                                                            archivo=newfile)
                                capacitacionth.save(request)
                                log(u'Adiciono capacitacion: %s' % persona, request, "add")

                                capacitacion.capacitacion = capacitacionth
                            else:
                                capacitacionth = Capacitacion.objects.get(pk=capacitacion.capacitacion.id)
                                capacitacionth.archivo = newfile


                        capacitacion.estado = 14
                        capacitacion.save(request)

                        log(u'Agregó archivos de evidencia de ejecución a la solicitud de capacitacion/actualización: %s' % capacitacion, request, "edit")

                        recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=capacitacion,
                                                                         observacion='Agregó archivos de evidencia de capacitación ejecutada',
                                                                         estado=14,
                                                                         fecha=datetime.now().date(),
                                                                         persona=persona)
                        recorridocap.save(request)
                        log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                        # Direccion de talento humano - envio de e-mail
                        correouath = 'formacion_uath@unemi.edu.ec'
                        if evidenciavalidar == 'FAC':
                            tituloemail = "Registro de evidencia - Factura de pago realizado por evento de capacitación"
                        else:
                            if 'informe' in request.FILES and 'certificado' in request.FILES:
                                tituloemail = "Registro de evidencias - Informe de comisión y Certificado por evento de capacitación"
                            elif 'informe' in request.FILES:
                                tituloemail = "Registro de evidencia - Informe de comisión por evento de capacitación"
                            else:
                                tituloemail = "Registro de evidencia - Certificado por evento de capacitación"

                        send_html_mail(tituloemail,
                                       "emails/notificacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'fase': 'EVI',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'numero': capacitacion.id,
                                        'administrativo': administrativo.persona,
                                        'autoridad1': '',
                                        'autoridad2': '',
                                        't': miinstitucion()
                                        },
                                       [correouath],
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'editcapacitacionth':
                try:
                    persona = request.session['persona']
                    capacitacion = Capacitacion.objects.get(pk=int(request.POST['id']))

                    f = CapacitacionPersonaForm(request.POST, request.FILES)
                    if f.is_valid():
                        capacitacion.institucion = f.cleaned_data['institucion']
                        capacitacion.nombre = f.cleaned_data['nombre']
                        capacitacion.descripcion = f.cleaned_data['descripcion']
                        capacitacion.tipocurso = f.cleaned_data['tipocurso']
                        capacitacion.tipocapacitacion = f.cleaned_data['tipocapacitacion']
                        capacitacion.tipocertificacion = f.cleaned_data['tipocertificacion']
                        capacitacion.tipoparticipacion = f.cleaned_data['tipoparticipacion']
                        capacitacion.auspiciante = f.cleaned_data['auspiciante']
                        capacitacion.areaconocimiento = f.cleaned_data['areaconocimiento']
                        capacitacion.subareaconocimiento = f.cleaned_data['subareaconocimiento']
                        capacitacion.subareaespecificaconocimiento = f.cleaned_data['subareaespecificaconocimiento']
                        capacitacion.pais = f.cleaned_data['pais']
                        capacitacion.contextocapacitacion = f.cleaned_data['contexto']
                        capacitacion.detallecontextocapacitacion = f.cleaned_data['detallecontexto']
                        capacitacion.provincia = f.cleaned_data['provincia']
                        capacitacion.canton = f.cleaned_data['canton']
                        capacitacion.parroquia = f.cleaned_data['parroquia']
                        capacitacion.fechainicio = f.cleaned_data['fechainicio']
                        capacitacion.fechafin = f.cleaned_data['fechafin']
                        capacitacion.horas = f.cleaned_data['horas']
                        capacitacion.expositor = f.cleaned_data['expositor']
                        capacitacion.modalidad = f.cleaned_data['modalidad']
                        capacitacion.otramodalidad = f.cleaned_data['otramodalidad']
                        capacitacion.save(request)

                        solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['idsolicitud'])))
                        solicitud.infocompletacap = True
                        solicitud.save(request)

                        log(u'Modifico capacitacion: %s' % persona, request, "edit")

                        # Enviar correo a Lic. Patricia Ortiz - UATH
                        revisor = solicitud.obtenerdatosautoridad('RHVTH', 0)
                        if revisor:
                            send_html_mail("Registro de Certificado de capacitación - " + str(administrativo.persona),
                                           "emails/notificacion_capadmtra.html",
                                           {'sistema': u'SAGEST - UNEMI',
                                            'fase': 'CER',
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': solicitud.id,
                                            'administrativo': administrativo.persona,
                                            'autoridad1': revisor.persona,
                                            'autoridad2': '',
                                            't': miinstitucion()
                                            },
                                           revisor.persona.lista_emails_envio(),
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, al guardar los datos."})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

            elif action == 'delsolicitud':
                try:
                    planificarcapacitaciones = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                    if planificarcapacitaciones.estado != 1 and planificarcapacitaciones.estado != 7:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"No se puede eliminar el Registro porque tiene estado %s" % planificarcapacitaciones.get_estado_display()})

                    log(u'Elimino planificación de capacitacion del docente:[%s]' % planificarcapacitaciones, request, "del")
                    planificarcapacitaciones.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:

        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'solicitarcapacitacion':
                try:
                    data['title'] = u'Solicitudes para capacitaciones/actualizaciones'
                    convocatoria = CronogramaCapacitacionDocente.objects.get(pk=int(request.GET['convocatoria']))

                    hoy = datetime.now().date()

                    if convocatoria.inicio.date() <= hoy <= convocatoria.fin.date():
                        data['puede_solicitar'] = True
                    else:
                        data['puede_solicitar'] = False

                    data['convocatoria'] = convocatoria.id
                    data['tipopersonal'] = convocatoria.tipo
                    data['modeloinforme'] = convocatoria.modeloinforme.url if convocatoria.modeloinforme else None
                    capacitaciones = PlanificarCapacitaciones.objects.filter(administrativo=administrativo, cronograma=convocatoria).order_by('-fecha_creacion')
                    data['saldo']= null_to_decimal(convocatoria.monto - convocatoria.totalmonto_administrativo(administrativo=administrativo, convocatoria=convocatoria))
                    paging = Paginator(capacitaciones, 30)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['capacitaciones'] = page.object_list
                    data['form2'] = PlanificarCapacitacionesArchivoForm()
                    return render(request, "adm_capacitacion/solicitudes.html", data)
                except Exception as ex:
                    pass

            elif action == 'cronogramacapacitaciones':
                try:
                    data['title'] = u'Cronograma y bases para capacitaciones'
                    capacitaciones = CronogramaCapacitacionDocente.objects.filter(status=True, tipo=2).order_by('-inicio')
                    paging = Paginator(capacitaciones, 50)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['page'] = page
                    data['capacitaciones'] = page.object_list
                    data['tipopersonal'] = 2
                    return render(request, "pro_cronograma/cronogramacapacitaciones.html", data)
                except Exception as ex:
                    pass

            elif action == 'addsolicitud':
                try:
                    data['title'] = u'Solicitud de capacitación'
                    form = PlanificarCapacitacionesForm()
                    data['form'] = form
                    data['convocatoria'] = convocatoria = request.GET['convocatoria']
                    data['criterios'] = PlanificarCapacitacionesCriterios.objects.filter(status=True, tipo=2).order_by('id')
                    return render(request, "adm_capacitacion/addsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editsolicitud':
                try:
                    data['title'] = u'Editar solicitud de capacitación'
                    data['convocatoria'] = convocatoria = request.GET['convocatoria']
                    data['solicitud'] = solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = PlanificarCapacitacionesForm(initial={'tema': solicitud.tema,
                                                                 'institucion': solicitud.institucion,
                                                                 'pais': solicitud.pais,
                                                                 'justificacion': solicitud.justificacion,
                                                                 'modalidad': solicitud.modalidad,
                                                                 'fechainicio': solicitud.fechainicio,
                                                                 'fechafin': solicitud.fechafin,
                                                                 'costo': solicitud.costo,
                                                                 'horas': solicitud.horas,
                                                                 'link': solicitud.link})

                    data['form'] = form
                    data['criterios'] = solicitud.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                    return render(request, "adm_capacitacion/editsolicitud.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcapacitacionth':
                try:
                    data['title'] = u'Editar capacitación - Hoja de vida'
                    data['convocatoria'] = request.GET['convocatoria']
                    data['idsolicitud'] = request.GET['id']
                    data['capacitacion'] = capacitacion = Capacitacion.objects.get(pk=int(request.GET['idcth']))
                    data['modalidad1'] = capacitacion.modalidad
                    form = CapacitacionPersonaForm(initial={'institucion': capacitacion.institucion,
                                                            'nombre': capacitacion.nombre,
                                                            'descripcion': capacitacion.descripcion,
                                                            'tipocurso': capacitacion.tipocurso,
                                                            'tipocertificacion': capacitacion.tipocertificacion,
                                                            'tipocapacitacion': capacitacion.tipocapacitacion,
                                                            'tipoparticipacion': capacitacion.tipoparticipacion,
                                                            'auspiciante': capacitacion.auspiciante,
                                                            'expositor': capacitacion.expositor,
                                                            'anio': capacitacion.anio,
                                                            'contexto': capacitacion.contextocapacitacion,
                                                            'detallecontexto': capacitacion.detallecontextocapacitacion,
                                                            'areaconocimiento': capacitacion.areaconocimiento,
                                                            'subareaconocimiento': capacitacion.subareaconocimiento,
                                                            'subareaespecificaconocimiento': capacitacion.subareaespecificaconocimiento,
                                                            'pais': capacitacion.pais,
                                                            'provincia': capacitacion.provincia,
                                                            'canton': capacitacion.canton,
                                                            'parroquia': capacitacion.parroquia,
                                                            'fechainicio': capacitacion.fechainicio,
                                                            'fechafin': capacitacion.fechafin,
                                                            'horas': capacitacion.horas,
                                                            'modalidad': capacitacion.modalidad,
                                                            'otramodalidad': capacitacion.otramodalidad})
                    form.editar(capacitacion)
                    form.quitar_campo_archivo()
                    data['form'] = form
                    return render(request, "adm_capacitacion/editcapacitacionth.html", data)
                except Exception as ex:
                    pass

            elif action == 'subirevidenciaejecutadocap':
                try:
                    data['title'] = u'Subir Evidencias de capacitación Ejecutada'
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    form = SubirEvidenciaEjecutadoCapacitacionesForm()
                    if datetime.now().date() < solicitud.fechafin:
                        form.quitarcamposevidencia('OTR')
                        data['evidenciavalidar'] = 'FAC'
                    else:
                        form.quitarcamposevidencia('FAC')
                        data['evidenciavalidar'] = 'OTR'

                    data['form'] = form
                    data['tema'] = solicitud.tema
                    data['factura'] = solicitud.archivofactura
                    data['informe'] = solicitud.archivoinforme
                    data['certificado'] = solicitud.archivocertificado

                    data['id'] = request.GET['id']
                    data['convocatoria'] = request.GET['convocatoria']

                    return render(request, "adm_capacitacion/subirevidenciaejecutado.html", data)
                except Exception as ex:
                    pass

            elif action == 'delsolicitud':
                try:
                    data['title'] = u'Eliminar solicitud de capacitación'
                    data['solicitud'] = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_capacitacion/delsolicitud.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Cronograma y bases para capacitaciones'
                capacitaciones = CronogramaCapacitacionDocente.objects.filter(status=True, tipo=2).order_by('-inicio')
                paging = Paginator(capacitaciones, 50)
                p = 1
                try:
                    if 'page' in request.GET:
                        p = int(request.GET['page'])
                    page = paging.page(p)
                except Exception as ex:
                    page = paging.page(1)
                data['paging'] = paging
                data['page'] = page
                data['capacitaciones'] = page.object_list
                data['tipopersonal'] = 2
                return render(request, "pro_cronograma/cronogramacapacitaciones.html", data)
            except Exception as ex:
                pass
