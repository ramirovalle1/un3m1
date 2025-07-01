# -*- coding: UTF-8 -*-
import json
from googletrans import Translator
from datetime import datetime, date, timedelta, time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from xlwt import *
from decorators import secure_module
from sagest.forms import CapDocentePeriodoForm
from sagest.models import CapPeriodo, DistributivoPersona, Departamento
from settings import PUESTO_ACTIVO_ID
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PlanificarCapacitacionesAutorizarForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, convertir_fecha, convertir_fecha_invertida, \
    fechaformatostr
from sga.models import Administrativo, Persona, Pais, Provincia, Canton, Parroquia, DIAS_CHOICES, \
    CronogramaCapacitacionDocente, PlanificarCapacitaciones, PlanificarCapacitacionesRecorrido, \
    PlanificarCapacitacionesDetalleCriterios, miinstitucion, ProfesorDistributivoHoras, Titulacion, \
    ResponsableCoordinacion, CoordinadorCarrera, ESTADOS_PLANIFICAR_CAPACITACIONES
from django.template.context import Context
from django.db.models import Max, Q, Sum
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import conectar_cuenta, send_html_mail


@login_required(redirect_field_name='ret',login_url='/loginsga')
@secure_module
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    periodo = request.session['periodo']
    dosfases = False
    dosfasesth = False
    esjefe = False
    if persona.es_directordepartamental():
        esjefe = True
        departamento = persona.departamentodireccion()
        tipoautoridad = 3

        # if DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=114, estadopuesto_id=1, status=True):
        #     per = DistributivoPersona.objects.get(persona=persona, denominacionpuesto_id=114, estadopuesto_id=1,
        #                                           status=True)
        if persona.grupo_vicerrectoradoadministrativo():
            dosfases = True
        elif persona.grupo_talentohumano():
            dosfasesth = True
    elif persona.grupo_talentohumano():
        tipoautoridad = 1
    elif persona.distributivopersona_set.filter(denominacionpuesto_id__in =[70,51], estadopuesto_id=1,  status=True):
        # TESORERA GENERAL
        per = DistributivoPersona.objects.get(persona=persona, denominacionpuesto_id__in =[70,51], estadopuesto_id=1, status=True)
        tipoautoridad = 4
    else:
        return HttpResponseRedirect("/?info=Este módulo solo es para uso de los directores departamentales, unidad de talento humano y tesorero general.")


    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addcaprecorrido':
            try:
                hoy = datetime.now().date()
                capacitacion = PlanificarCapacitaciones.objects.get(pk=request.POST['id'])
                estado = int(request.POST['esta'])
                fase = request.POST['fase']
                textoadicional = ""

                if fase == 'VAL':
                    if capacitacion.estado == 1 or capacitacion.estado == 2 or capacitacion.estado == 7:
                        if capacitacion.fechainicio and capacitacion.fechafin:
                            esValido = True
                            entidadFase = u"el Director Departamental"
                        else:
                            if estado == 2:
                                esValido = False
                                mensaje = u"No se puede grabar debido a que los campos fecha de inicio y fecha fin están en blanco"
                            else:
                                esValido = True
                                entidadFase = u"el Director Departamental"
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())
                elif fase == 'APR':
                    if capacitacion.estado == 2 or capacitacion.estado == 3 or capacitacion.estado == 8:
                        esValido = True
                        entidadFase = u"la Dirección de Talento Humano"
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())
                elif fase == 'AUT':
                    if capacitacion.estado == 3 or capacitacion.estado == 4 or capacitacion.estado == 9:
                        esValido = True
                        entidadFase = u"el Vicerrectorado Administrativo"
                        textoadicional = u"Favor imprimir el convenio de devengación, recoger las firmas correspondientes y subirlo escaneado como archivo PDF al sistema."
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())
                else:
                    if capacitacion.estado == 5:
                        esValido = True
                        entidadFase = u"el Tesorero General"

                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())

                if esValido:
                    if capacitacion.estado != estado:
                        recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=capacitacion,
                                                                         observacion=request.POST['obse'],
                                                                         estado=int(request.POST['esta']),
                                                                         fecha=datetime.now().date(),
                                                                         persona=persona)
                        recorridocap.save(request)
                        capacitacion.estado = estado
                        capacitacion.save(request)

                        if fase == 'VAL' or fase == 'APR':
                            criterios = request.POST['criterios'].split('|')
                            for c in criterios:
                                fila = c.split(',')
                                detallecriterioscap = PlanificarCapacitacionesDetalleCriterios.objects.get(pk=int(fila[0]), status=True)
                                if fase == 'VAL':
                                    detallecriterioscap.estadodirector = True if fila[1] == 'true' else False
                                    detallecriterioscap.fecharevisiondirector = datetime.now().date()
                                else:
                                    detallecriterioscap.estadouath = True if fila[1] == 'true' else False
                                    detallecriterioscap.fecharevisionuath = datetime.now().date()

                                detallecriterioscap.save(request)

                        #micorreo = Persona.objects.get(cedula='0923704928')
                        if fase == 'VAL':
                            estadocorreo = "VALIDADA" if estado == 2 else "DENEGADA"
                        elif fase == 'APR':
                            estadocorreo = "APROBADA" if estado == 3 else "DENEGADA"
                        elif fase == 'AUT':
                            estadocorreo = "AUTORIZADA" if estado == 4 else "DENEGADA"

                        tituloemail = "Solicitud de Capacitación " + estadocorreo + " por " + entidadFase

                        send_html_mail(tituloemail,
                                       "emails/aprobacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'administrativo': capacitacion.administrativo.persona,
                                        'numero': capacitacion.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['obse'],
                                        'aprueba': entidadFase,
                                        'textoadicional': textoadicional,
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                        capacitacion.administrativo.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        # Para envío de correos a las autoridades
                        autoridad2nombre = ''
                        enviaremail = False
                        if fase == 'VAL' and estado == 2:
                            email_autoridad2 = 'formacion_uath@unemi.edu.ec'
                            enviaremail = True
                            tituloemail = 'Validación de Solicitud de capacitación - LOSEP y Código de Trabajo'

                        elif fase == 'APR' and estado == 3:
                            email_autoridad2 = 'vicerrectorado_administrativo@unemi.edu.ec'
                            enviaremail = True
                            tituloemail = 'Aprobación de Solicitud de capacitación - LOSEP y Código de Trabajo'

                        elif fase == 'AUT' and estado == 4:
                            email_autoridad2 = 'formacion_uath@unemi.edu.ec'
                            enviaremail = True
                            tituloemail = 'Autorización de Solicitud de capacitación - LOSEP y Código de Trabajo'

                        if enviaremail:
                            send_html_mail(tituloemail,
                                           "emails/notificacion_capadmtra.html",
                                           {'sistema': u'SAGEST - UNEMI',
                                            'fase': fase,
                                            'fecha': datetime.now().date(),
                                            'hora': datetime.now().time(),
                                            'numero': capacitacion.id,
                                            'administrativo': capacitacion.administrativo.persona,
                                            'autoridad1': persona,
                                            'autoridad2': autoridad2nombre,
                                            't': miinstitucion()
                                            },
                                           [email_autoridad2],
                                           [],
                                           cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                           )

                        log(u'Adiciono recorrido en solicitud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"El estado debe ser diferente a %s " % (capacitacion.get_estado_display())})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "%s" % (mensaje)})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar recorrido de solicitud"})

        elif action == 'autorizardesembolso':
            try:
                f = PlanificarCapacitacionesAutorizarForm(request.FILES)
                newfile = None

                estado = int(request.POST['estadodes'])
                observacion = request.POST['observaciondes'].upper()
                solicitud = PlanificarCapacitaciones.objects.get(pk=int(request.POST['id']))

                if estado == 6:
                    fecha = request.POST['fechadesembolso']
                    fechalegalizado = str(solicitud.ultimodetallelegalizadorecorrido().fecha)[:10]
                    fechalegalizado = fechaformatostr(fechalegalizado, "DMA")

                    if datetime.strptime(fecha, '%d-%m-%Y') < datetime.strptime(fechalegalizado, '%d-%m-%Y'):
                        return JsonResponse({"result": "bad","mensaje": u"Error, la fecha de desembolso debe ser mayor o igual a %s." % (fechalegalizado)})

                    if 'archivodesembolso' in request.FILES:
                        arch = request.FILES['archivodesembolso']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, debe subir un archivo."})

                if f.is_valid():
                    if estado == 6:
                        newfile = request.FILES['archivodesembolso']
                        newfile._name = generar_nombre("desembolso", newfile._name)
                        solicitud.archivodesembolso = newfile
                        solicitud.fechadesembolso = convertir_fecha(fecha)

                    solicitud.estado = estado
                    solicitud.save(request)
                    if estado == 6:
                        log(u'Agregó archivo de desembolso a la solicitud de capacitacion/actualización: %s' % solicitud,
                        request, "edit")

                    recorridocap = PlanificarCapacitacionesRecorrido(planificarcapacitaciones=solicitud,
                                                                     observacion=observacion,
                                                                     estado=estado,
                                                                     fecha=datetime.now().date(),
                                                                     persona=persona)
                    recorridocap.save(request)

                    log(u'Adiciono recorrido en solititud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")

                    # Enviar correo
                    #micorreo = Persona.objects.get(cedula='0923704928')

                    estadocorreo = "DESEMBOLSO AUTORIZADO" if estado == 6 else "DENEGADO"
                    tituloemail = "Solicitud de Capacitación " + estadocorreo + " por el Tesorero General"

                    if estado == 6:
                        send_html_mail(tituloemail,
                                       "emails/aprobacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'administrativo': solicitud.administrativo.persona,
                                        'numero': solicitud.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['observaciondes'],
                                        'aprueba': 'el Tesorero General',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                       solicitud.administrativo.persona.lista_emails_envio(),
                                       [],
                                       [solicitud.archivodesembolso],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )
                    else:
                        send_html_mail(tituloemail,
                                       "emails/aprobacion_capadmtra.html",
                                       {'sistema': u'SAGEST - UNEMI',
                                        'administrativo': solicitud.administrativo.persona,
                                        'numero': solicitud.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['observaciondes'],
                                        'aprueba': 'el Tesorero General',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                        solicitud.administrativo.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        elif action == 'detallecap':
            try:
                data['fase'] = fase = request.POST['fase']
                data['tipoaccion'] = 'MOSTRARDATOS' if request.POST['ta'] == 'VDA' else 'CAMBIOESTADO'
                data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=request.POST['id'])
                data['capacitaciondetallecriterio'] = capacitacion.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                data['capacitacionrecorrido'] = capacitacion.planificarcapacitacionesrecorrido_set.filter(status=True).order_by('id')

                if request.POST['ta'] == 'CES':
                    estado = capacitacion.estado
                    estados = ESTADOS_PLANIFICAR_CAPACITACIONES
                    if fase == 'VAL':
                        estados = ((0, 'Seleccione...'), estados[1], estados[6]) if estado == 1 else ((0, 'Seleccione...'), estados[6]) if estado == 2 else ((0, 'Seleccione...'), estados[1])
                    elif fase == 'APR':
                        estados = ((0,'Seleccione...'), estados[2], estados[7]) if estado == 2 else ((0,'Seleccione...'), estados[7]) if estado == 3 else ((0,'Seleccione...'), estados[2])
                    elif fase == 'AUT':
                        estados = ((0, 'Seleccione...'), estados[3], estados[8]) if estado == 3 else ((0, 'Seleccione...'), estados[8]) if estado == 4 else ((0, 'Seleccione...'), estados[3])

                    data['estados'] = estados

                template = get_template("adm_capacitacion/detallecapacitacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verificalistadosolicitud_pdf':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    estado = int(request.POST['estado'])

                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, fecha_creacion__range=(desde, hasta)).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                    codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                    participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                    if estado == 1 or estado == 7 or estado == 20:
                        if participantes.filter(estado=estado).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    elif estado == 2:
                        if participantes.filter(~Q(estado__in=[1, 7, 20])).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    else:
                        if participantes.filter(estado__in=[1, 7, 20]).exists() or participantes.filter(~Q(estado__in=[1, 7, 20])).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Formatos de fechas incorrectas."})

        elif action == 'verificalistadosolicitudaut_pdf':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    iddepartamento = int(request.POST['departamento'])
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    estado = int(request.POST['estado'])

                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, fecha_creacion__range=(desde, hasta)).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                    codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica_id=iddepartamento, status=True, estadopuesto_id=1)
                    participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                    if estado == 9 or estado == 3:
                        if participantes.filter(estado=estado).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    elif estado == 4:
                        if participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    else:
                        if participantes.filter(estado__in=[3, 9]).exists() or participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Formatos de fechas incorrectas."})

        elif action == 'listadosolicitud_pdf':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                estado = int(request.POST['estado'])

                participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, fecha_creacion__range=(desde, hasta))
                codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                if estado == 1 or estado == 7 or estado == 20:
                    participantes = participantes.filter(estado=estado)
                elif estado == 2:
                    participantes = participantes.filter(~Q(estado__in=[1, 7, 20]))
                else:
                    p1 = participantes.filter(estado__in=[1, 7, 20])
                    p2 = participantes.filter(~Q(estado__in=[1, 7, 20]))
                    participantes = p1 | p2

                participantes = participantes.order_by('-fecha_creacion', 'administrativo__persona__apellido1')

                calculo = participantes.filter(~Q(estado__in=[1, 7, 20])).aggregate(total=Sum('costo'))
                totsol = participantes.count()
                totanul = participantes.filter(estado=20).count()
                totval = participantes.filter(~Q(estado__in=[1, 7, 20])).count()
                totden = participantes.filter(estado=7).count()
                totpend = totsol - (totval + totden + totanul)

                cargo = DistributivoPersona.objects.filter(persona=persona, status=True).order_by('estadopuesto_id')[0]

                titulos = persona.titulo3y4nivel()

                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['titulo1jefe'] = titulos['tit1']
                data['titulo2jefe'] = titulos['tit2']
                data['departamento'] = departamento
                data['denominacionpuesto'] = cargo.denominacionpuesto.descripcion
                data['participantes'] = participantes
                data['costoacumulado'] = calculo['total'] if calculo['total'] is not None else 0.00
                data['estadoreporte'] = ' Validadas' if estado == 2 else ' Denegadas' if estado == 7 else 'Anuladas' if estado == 20 else ''
                data['estado'] = estado
                data['jefe'] = persona
                data['totsol'] = totsol
                data['totval'] = totval
                data['totden'] = totden
                data['totpend'] = totpend
                data['totanul'] = totanul

                return conviert_html_to_pdf(
                    'adm_capacitacion/listadosolicitudgen_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        elif action == 'listadosolicitudaut_pdf':
            try:
                data = {}

                iddepartamento = int(request.POST['departamento'])
                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                estado = int(request.POST['estado'])
                departamentosol = Departamento.objects.get(pk=iddepartamento)

                participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2, fecha_creacion__range=(desde, hasta))
                codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamentosol, status=True, estadopuesto_id=1)
                participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                if estado == 9 or estado == 3:
                    participantes = participantes.filter(estado=estado)
                elif estado == 4:
                    participantes = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                else:
                    p1 = participantes.filter(estado__in=[3, 9])
                    p2 = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                    participantes = p1 | p2

                participantes = participantes.order_by('-fecha_creacion', 'administrativo__persona__apellido1')

                calculo = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).aggregate(total=Sum('costo'))
                totsol = participantes.count()
                totaut = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).count()
                totden = participantes.filter(estado=9).count()
                totpend = totsol - (totaut + totden)

                #Vicerrector administrativo
                dpvice = DistributivoPersona.objects.filter(denominacionpuesto_id=114, estadopuesto_id=1, status=True).order_by('estadopuesto_id')[0]
                personavice = dpvice.persona
                titulos = personavice.titulo3y4nivel()

                data['titulo1vice'] = titulos['tit1']
                data['titulo2vice'] = titulos['tit2']
                data['denominacionpuestovice'] = dpvice.denominacionpuesto.descripcion
                data['vicerrector'] = personavice
                data['nombredptovice'] = dpvice.unidadorganica

                # Jefe departamento solicitante
                dpjefe = DistributivoPersona.objects.filter(persona=departamentosol.responsable, unidadorganica=departamentosol, estadopuesto_id=1, status=True).order_by('estadopuesto_id')[0]
                personajefe = dpjefe.persona
                titulos = personajefe.titulo3y4nivel()

                data['titulo1jefe'] = titulos['tit1']
                data['titulo2jefe'] = titulos['tit2']
                data['denominacionpuestojefe'] = dpjefe.denominacionpuesto.descripcion
                data['jefe'] = personajefe

                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['departamento'] = departamentosol
                data['participantes'] = participantes
                data['costoacumulado'] = calculo['total'] if calculo['total'] is not None else 0.00
                data['estadoreporte'] = ' Autorizadas' if estado == 4 else ' Denegadas' if estado == 9 else ''
                data['estado'] = estado
                data['totsol'] = totsol
                data['totaut'] = totaut
                data['totden'] = totden
                data['totpend'] = totpend

                return conviert_html_to_pdf(
                    'adm_capacitacion/listadosolicitudaut_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass


        return HttpResponseRedirect(request.path)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'participantes':
                try:
                    data['title'] = u'Solicitudes de capacitaciones'

                    departamentos = Departamento.objects.values_list('id', 'nombre').filter(status=True,
                                    pk__in=DistributivoPersona.objects.values_list('unidadorganica_id').filter(status=True, regimenlaboral__codigo__in=[1, 2],
                                        persona_id__in=Administrativo.objects.values_list('persona_id').filter(status=True,
                                            pk__in=PlanificarCapacitaciones.objects.values_list('administrativo_id').filter(tipo=2, status=True)
                                            )
                                        )
                                    )

                    if tipoautoridad == 1:
                        data['fase'] = 'APR'
                    elif tipoautoridad == 3:
                        data['fase'] = 'VAL'
                    elif tipoautoridad == 4:
                        data['fase'] = 'DES'
                    else:
                        data['fase'] = 'AUT'

                    data['estados'] = ESTADOS_PLANIFICAR_CAPACITACIONES
                    estadosol = int(request.GET['eSol']) if 'eSol' in request.GET else 0
                    fecharep = request.GET['fecharep'] if 'fecharep' in request.GET else ''
                    search = None

                    estadossol = [estadosol]

                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            participantes = PlanificarCapacitaciones.objects.filter(Q(administrativo__persona__apellido1__icontains=search) | Q(
                                                                                        administrativo__persona__apellido2__icontains=search) | Q(
                                                                                        administrativo__persona__nombres__icontains=search),status=True, cronograma__tipo=2).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                            if tipoautoridad == 3 and dosfases is False and dosfasesth is False:
                                codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                                participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)
                        else:
                            participantes = PlanificarCapacitaciones.objects.filter(Q(administrativo__persona__apellido1__icontains=ss[0]) & Q(
                                                                                    administrativo__persona__apellido2__icontains=ss[1]), status=True, cronograma__tipo=2).order_by('-fecha_creacion', 'administrativo__persona__apellido1')
                            if tipoautoridad == 3 and dosfases is False and dosfasesth is False:
                                codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                                participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)
                    else:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2).order_by('-fecha_creacion','administrativo__persona__apellido1')
                        if tipoautoridad == 3 and dosfases is False and dosfasesth is False:
                            codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                            participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)

                    if estadosol != 0:
                        if dosfases is False and dosfasesth is False:
                            participantes = participantes.filter(estado=estadosol)
                        else:
                            participantes = participantes.filter(estado__in=estadossol)


                    data['totalreg'] = participantes.count()

                    paging = MiPaginador(participantes, 15)
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
                    data['search'] = search if search else ""
                    data['participantes'] = page.object_list
                    data['estadosol'] = estadosol
                    data['fecharep'] = fecharep

                    form2 = PlanificarCapacitacionesAutorizarForm()
                    form2.estados_desembolso()
                    data['form2'] = form2
                    data['dosfases'] = dosfases
                    data['dosfasesth'] = dosfasesth
                    data['esjefe'] = esjefe
                    data['departamentos'] = departamentos
                    if tipoautoridad != 4:
                        data['dptoreporte'] = str(persona.departamentodireccion()).title()

                    return render(request, "adm_capacitacion/participantecapacitacion.html", data)
                except Exception as ex:
                    pass
        else:
            try:
                data['title'] = u'Solicitudes de capacitaciones'

                departamentos = Departamento.objects.values_list('id','nombre').filter(status=True,
                    pk__in=DistributivoPersona.objects.values_list('unidadorganica_id').filter(status=True, regimenlaboral__codigo__in=[1, 2],
                        persona_id__in=Administrativo.objects.values_list('persona_id').filter(status=True,
                            pk__in=PlanificarCapacitaciones.objects.values_list('administrativo_id').filter(tipo=2, status=True)
                        )
                    )
                )

                if tipoautoridad == 1:
                    data['fase'] = 'APR'
                elif tipoautoridad == 3:
                    data['fase'] = 'VAL'
                elif tipoautoridad == 4:
                    data['fase'] = 'DES'
                else:
                    data['fase'] = 'AUT'

                data['estados'] = ESTADOS_PLANIFICAR_CAPACITACIONES
                estadosol = int(request.GET['eSol']) if 'eSol' in request.GET else 0

                if dosfases:
                    estadossol = [1, 3]
                    estadosol = estadossol[0]
                elif dosfasesth:
                    estadossol = [1, 2]
                    estadosol = estadossol[0]
                else:
                    if tipoautoridad == 1 and estadosol == 0:
                        estadossol = [2]
                    elif tipoautoridad == 3 and estadosol == 0:
                        estadossol = [1]
                    elif tipoautoridad == 4 and estadosol == 0:
                        estadossol = [5]
                    elif tipoautoridad == 5 and estadosol == 0:
                        estadossol = [3]
                    estadosol = estadossol[0]

                search = None

                participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=2).order_by('-fecha_creacion', 'administrativo__persona__apellido1')

                if tipoautoridad == 3:
                    if persona.grupo_vicerrectoradoadministrativo():
                        if dosfases is False:
                            codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                            participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)
                        else:
                            codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                            participantes1 = participantes.filter(administrativo__persona__id__in=codigospersonas)
                            participantes2 = participantes.filter(estado=3)
                            participantes = participantes1 | participantes2
                    else:
                        if dosfasesth is False:
                            codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                            participantes = participantes.filter(administrativo__persona__id__in=codigospersonas)
                        else:
                            codigospersonas = DistributivoPersona.objects.values_list('persona__id', flat=True).filter(unidadorganica=departamento, status=True, estadopuesto_id=1)
                            participantes1 = participantes.filter(administrativo__persona__id__in=codigospersonas)
                            participantes2 = participantes.filter(estado=2)
                            participantes = participantes1 | participantes2

                if estadosol != 0:
                    participantes = participantes.filter(estado__in=estadossol)

                paging = MiPaginador(participantes, 15)
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
                data['search'] = search if search else ""
                data['participantes'] = page.object_list
                data['estadosol'] = estadosol
                data['fecharep'] = datetime.now().strftime('%d-%m-%Y')
                form2 = PlanificarCapacitacionesAutorizarForm()
                form2.estados_desembolso()
                data['form2'] = form2
                data['dosfases'] = dosfases
                data['dosfasesth'] = dosfasesth
                data['esjefe'] = esjefe
                data['departamentos'] = departamentos
                if esjefe:
                    if tipoautoridad != 4:
                        data['dptoreporte'] = str(persona.departamentodireccion()).title()

                return render(request, "adm_capacitacion/participantecapacitacion.html", data)
            except Exception as ex:
                pass
