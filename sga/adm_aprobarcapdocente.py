# -*- coding: UTF-8 -*-
import json
import os
import io

import sys
from django.core.files import File as DjangoFile

from googletrans import Translator
from datetime import datetime, date, timedelta, time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from xlwt import *
from decorators import secure_module, last_access
from sagest.forms import CapDocentePeriodoForm
from sagest.models import CapPeriodo, DistributivoPersona
from settings import PUESTO_ACTIVO_ID,SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import PlanificarCapacitacionesAutorizarForm
from sga.funciones import MiPaginador, log, variable_valor, generar_nombre, convertir_fecha, fechaformatostr, validar_archivo,\
    remover_caracteres_especiales_unicode,notificacion
from sga.models import Administrativo, Persona, Pais, Provincia, Canton, Parroquia, DIAS_CHOICES, \
    CronogramaCapacitacionDocente, PlanificarCapacitaciones, PlanificarCapacitacionesRecorrido, \
    PlanificarCapacitacionesDetalleCriterios, miinstitucion, ProfesorDistributivoHoras, Titulacion, \
    ResponsableCoordinacion, CoordinadorCarrera, ESTADOS_PLANIFICAR_CAPACITACIONES, Coordinacion, Periodo,Notificacion
from django.template.context import Context
from django.db.models import Max, Q, Sum, Exists, OuterRef
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import conectar_cuenta, send_html_mail
from sga.templatetags.sga_extras import encrypt,nombremes
from core.firmar_documentos import firmararchivogenerado, firmarmasivo, obtener_posicion_x_y_saltolinea
from core.firmar_documentos_ec import JavaFirmaEc


@login_required(redirect_field_name='ret',login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista = []
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    periodo = request.session['periodo']
    if persona.es_responsablecoordinacion(periodo):
        # DECANO DE FACULTAD
        responsablecoordinacion = persona.responsablecoordinacion(periodo)
        numerocoordinaciones = persona.numero_coordinaciones_asignadas(periodo)
        coordinacion = responsablecoordinacion.coordinacion
        coordinacion2 = None

        if numerocoordinaciones > 1:
            coordinacion2 = persona.coordinacion2(periodo)
            coordinacion2 = coordinacion2.coordinacion

        tipoautoridad = responsablecoordinacion.tipo
    elif persona.es_coordinadorcarrera(periodo):
        # DIRECTOR DE CARRERA
        responsablecarrera = persona.coordinadorcarreras(periodo)
        codigoscarrera = responsablecarrera.values_list('carrera__id', flat=True).filter(status=True)
        coordinacion = responsablecarrera[0].coordinacion()
        tipoautoridad = responsablecarrera[0].tipo
    elif persona.distributivopersona_set.filter(denominacionpuesto_id__in=[70, 51, 972], estadopuesto_id=1,  status=True):
        # TESORERA GENERAL
        # per = DistributivoPersona.objects.get(persona=persona, denominacionpuesto_id__in=[70, 51, 972], estadopuesto_id=1, status=True)
        tipoautoridad = 4
    elif DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=795, estadopuesto_id=1, status=True):
        # VICERRECTOR ACADEMICO
        # per = DistributivoPersona.objects.get(persona=persona, denominacionpuesto_id=795, estadopuesto_id=1, status=True)
        tipoautoridad = 5
    else:
        return HttpResponseRedirect("/?info=Este módulo solo es para uso de los responsables de carreras, de coordinación y tesorero general.")


    if request.method == 'POST':
        action = request.POST['action']
        #PERIODO
        if action == 'addcaprecorrido':
            try:
                browser = request.POST['navegador']
                ops = request.POST['os']
                cookies = request.POST['cookies']
                screensize = request.POST['screensize']
                hoy = datetime.now().date()
                capacitacion = PlanificarCapacitaciones.objects.get(pk=request.POST['id'])
                estado = int(request.POST['esta'])
                fase = request.POST['fase']
                textoadicional = ""

                if fase == 'VAL':
                    if capacitacion.estado == 1 or capacitacion.estado == 2 or capacitacion.estado == 7:
                        if capacitacion.fechainicio and capacitacion.fechafin:
                            esValido = True
                            entidadFase = u"la Dirección de carrera"
                        else:
                            if estado == 2:
                                esValido = False
                                mensaje = u"No se puede grabar debido a que los campos fecha de inicio y fecha fin están en blanco"
                            else:
                                esValido = True
                                entidadFase = u"la Dirección de carrera"
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())
                elif fase == 'APR':
                    es_solidirector = CoordinadorCarrera.objects.filter(periodo=periodo, tipo=3, status=True, persona_id=capacitacion.profesor.persona_id).exists()
                    if capacitacion.estado == 2 or capacitacion.estado == 3 or capacitacion.estado == 8 or es_solidirector:
                        esValido = True
                        entidadFase = u"el Decanato"
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())
                elif fase == 'AUT':
                    es_solidecano = ResponsableCoordinacion.objects.filter(periodo=periodo, tipo=1, status=True, persona_id=capacitacion.profesor.persona_id).exists()
                    es_solivicerrec = DistributivoPersona.objects.filter(denominacionpuesto_id__in=[796, 795, 797], estadopuesto_id=1, status=True, persona_id=capacitacion.profesor.persona_id).first()
                    if capacitacion.estado == 3 or capacitacion.estado == 4 or capacitacion.estado == 9 or es_solidecano or es_solivicerrec:
                        esValido = True
                        entidadFase = u"el Vicerrectorado de Investigación y Posgrado"
                        textoadicional = u"Favor descargar el convenio de devengación del sistema, firmarlo con firma electrónica y volverlo a subir."
                    else:
                        esValido = False
                        mensaje = u"No se puede grabar debido a que el Registro tiene estado %s" % (capacitacion.get_estado_display())
                else:
                    if capacitacion.estado == 5:
                        esValido = True
                        #entidadFase = u"el Rectorado"
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

                        # if fase == 'VAL':
                        #     criterios = request.POST['criterios'].split('|')
                        #     for c in criterios:
                        #         fila = c.split(',')
                        #         detallecriterioscap = PlanificarCapacitacionesDetalleCriterios.objects.get(pk=int(fila[0]), status=True)
                        #
                        #         if fila[1] == 'true':
                        #             detallecriterioscap.estadodirector = True
                        #         else:
                        #             detallecriterioscap.estadodirector = False
                        #
                        #         detallecriterioscap.save(request)

                        #micorreo = Persona.objects.get(cedula='0923704928')

                        send_html_mail("Cambio de Estado de solicitud de capacitación",
                                       "emails/aprobacion_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'docente': capacitacion.profesor.persona,
                                        'numero': capacitacion.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['obse'],
                                        'aprueba': entidadFase,
                                        'textoadicional': textoadicional,
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'bs': browser,
                                        'os': ops,
                                        'cookies': cookies,
                                        'screensize': screensize,
                                        't': miinstitucion()},
                                        capacitacion.profesor.persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        # Para envío de correos a las autoridades
                        enviaremail = False


                        if fase == 'VAL' and estado == 2:
                            autoridad2 = capacitacion.obtenerdatosautoridad('DEC', periodo)
                            if autoridad2:
                                enviaremail = True
                                data['tituloemail'] = tituloemail = 'Validación de Solicitud de capacitación'

                        elif fase == 'APR' and estado == 3:
                            autoridad2 = capacitacion.obtenerdatosautoridad('VICE', periodo)
                            enviaremail = True
                            data['tituloemail'] = tituloemail = 'Aprobación de Solicitud de capacitación'
                            emailenvio = "vr_investigacion_posgrado@unemi.edu.ec"

                        elif fase == 'AUT' and estado == 4:
                            autoridad2 = capacitacion.obtenerdatosautoridad('DTH', periodo)
                            enviaremail = True
                            data['tituloemail'] = tituloemail = 'Autorización de Solicitud de capacitación'
                            emailenvio = "formacion_uath@unemi.edu.ec"


                        if enviaremail:
                            if estado == 2:
                                send_html_mail(tituloemail,
                                               "emails/notificacion_capdocente.html",
                                               {'sistema': u'SGA - UNEMI',
                                                'fase': fase,
                                                'fecha': datetime.now().date(),
                                                'hora': datetime.now().time(),
                                                'numero': capacitacion.id,
                                                'docente': capacitacion.profesor.persona,
                                                'autoridad1': persona,
                                                'tituloemail': tituloemail,
                                                'autoridad2': autoridad2.persona,
                                                't': miinstitucion()
                                                },
                                               autoridad2.persona.lista_emails_envio(),
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )
                            else:
                                send_html_mail(tituloemail,
                                               "emails/notificacion_capdocente.html",
                                               {'sistema': u'SGA - UNEMI',
                                                'fase': fase,
                                                'fecha': datetime.now().date(),
                                                'hora': datetime.now().time(),
                                                'numero': capacitacion.id,
                                                'docente': capacitacion.profesor.persona,
                                                'tituloemail':tituloemail,
                                                'autoridad1': persona,
                                                'autoridad2': autoridad2.persona,
                                                't': miinstitucion()
                                                },
                                               [emailenvio],
                                               [],
                                               cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                               )

                        log(u'Adiciono recorrido en solititud de capacitaciones: %s - %s - Estado %s' % (recorridocap.planificarcapacitaciones, recorridocap.persona, recorridocap.estado), request, "add")
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
                    # IMPORTANTE: Se comento por que no se esta utilizando y daba error al traer el ultimorecorridolegalizado de la solicitud.
                    # fechalegalizado = str(solicitud.ultimodetallelegalizadorecorrido().fecha)[:10]
                    # fechalegalizado = fechaformatostr(fechalegalizado, "DMA")

                    # Se comento xq el departamento de perfeccionamiento no quiere que valide fecha en los desembolsos
                    # if datetime.strptime(fecha,'%d-%m-%Y') < datetime.strptime(fechalegalizado,'%d-%m-%Y'):
                    #     return JsonResponse({"result": "bad", "mensaje": u"Error, la fecha de desembolso debe ser mayor o igual a %s." % (fechalegalizado)})

                    if 'archivodesembolso' in request.FILES:
                        arch = request.FILES['archivodesembolso']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
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

                    if estado == 6:
                        send_html_mail("Cambio de Estado de solicitud de capacitación",
                                       "emails/aprobacion_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'docente': solicitud.profesor.persona,
                                        'numero': solicitud.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['observaciondes'],
                                        'aprueba': 'el Tesorero General',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                       solicitud.profesor.persona.lista_emails_envio(),
                                       [],
                                       [solicitud.archivodesembolso],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )
                    else:
                        send_html_mail("Cambio de Estado de solicitud de capacitación",
                                       "emails/aprobacion_capdocente.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'docente': solicitud.profesor.persona,
                                        'numero': solicitud.id,
                                        'estadoap': estado,
                                        'observacionap': request.POST['observaciondes'],
                                        'aprueba': 'el Tesorero General',
                                        'textoadicional': '',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        't': miinstitucion()},
                                        solicitud.profesor.persona.lista_emails_envio(),
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
                data['fase'] = request.POST['fase']
                data['capacitacion'] = capacitacion = PlanificarCapacitaciones.objects.get(id=request.POST['id'])
                data['capacitaciondetallecriterio'] = capacitacion.planificarcapacitacionesdetallecriterios_set.filter(status=True).order_by('criterio_id')
                data['capacitacionrecorrido'] = capacitacion.planificarcapacitacionesrecorrido_set.filter(status=True).order_by('id')
                data['es_solidirector'] = CoordinadorCarrera.objects.filter(periodo=periodo, tipo=3, status=True, persona_id=capacitacion.profesor.persona_id).exists()
                data['es_solidecano'] = ResponsableCoordinacion.objects.filter(periodo=periodo, tipo=1, status=True, persona_id=capacitacion.profesor.persona_id).exists()
                data['es_solivicerrec'] = DistributivoPersona.objects.filter(denominacionpuesto_id__in=[796, 795, 797], estadopuesto_id=1, status=True, persona_id=capacitacion.profesor.persona_id).exists()
                template = get_template("adm_capdocente/detallecapacitacion.html")

                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verificalistadosolicitud_pdf':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    periodosol = Periodo.objects.get(pk=int(request.POST['periodo']))
                    facultadsol = Coordinacion.objects.get(pk=int(request.POST['facultad']))
                    estado = int(request.POST['estado'])
                    codigosprofesores = facultadsol.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodosol, status=True)

                    # participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, fecha_creacion__range=(desde, hasta), periodo=periodosol, profesor_id__in=codigosprofesores)

                    if estado != 0:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol, profesor_id__in=codigosprofesores,
                                                                                planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                                planificarcapacitacionesrecorrido__estado=estado,
                                                                                planificarcapacitacionesrecorrido__status=True)

                        if estado == 3:
                            participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[4, 9])
                        # elif estado == 9:
                        #     participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[3, 4])
                    else:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol,
                                                                                profesor_id__in=codigosprofesores,
                                                                                planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                                planificarcapacitacionesrecorrido__estado__in=[3, 4, 9],
                                                                                planificarcapacitacionesrecorrido__status=True)

                    if participantes:
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse(
                            {"result": "bad", "mensaje": "No existen registros para generar el reporte"})


                    # if estado == 9 or estado == 3:
                    #     if participantes.filter(estado=estado).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    # elif estado == 4:
                    #     if participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    # else:
                    #     if participantes.filter(estado__in=[3, 9]).exists() or participantes.filter(
                    #             ~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Formatos de fechas incorrectas."})

        elif action == 'listadosolicitud_pdf':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                periodosol = Periodo.objects.get(pk=int(request.POST['periodo']))
                facultadsol = Coordinacion.objects.get(pk=int(request.POST['facultad']))
                estado = int(request.POST['estado'])

                codigosprofesores = facultadsol.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodosol, status=True, carrera_id__isnull=False)


                # participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, fecha_creacion__range=(desde, hasta), periodo=periodosol, profesor_id__in=codigosprofesores)
                if estado == 0:
                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol, profesor_id__in=codigosprofesores,
                                                                            planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                            planificarcapacitacionesrecorrido__status=True,
                                                                            planificarcapacitacionesrecorrido__estado__in=[3, 4, 9]).distinct()
                else:
                    participantes = PlanificarCapacitaciones.objects.filter(status=True, cronograma__tipo=1, periodo=periodosol, profesor_id__in=codigosprofesores,
                                                                            planificarcapacitacionesrecorrido__fecha__range=(desde, hasta),
                                                                            planificarcapacitacionesrecorrido__status=True,
                                                                            planificarcapacitacionesrecorrido__estado=estado).distinct()

                    if estado == 3:
                        participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[4, 9])
                    # elif estado == 9:
                    #     participantes = participantes.exclude(planificarcapacitacionesrecorrido__estado__in=[3, 4])


                # if estado == 9 or estado == 3:
                #     participantes = participantes.filter(estado=estado)
                # elif estado == 4:
                #     participantes = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                # else:
                #     p1 = participantes.filter(estado__in=[3, 9])
                #     p2 = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20]))
                #     participantes = p1 | p2



                participantes = participantes.order_by('-fecha_creacion', 'profesor__persona__apellido1')

                codigoscarreras = facultadsol.profesordistributivohoras_set.values_list('carrera__id', flat=True).filter(periodo=periodosol, status=True, carrera_id__isnull=False, profesor_id__in=participantes.values_list('profesor_id', flat=True).distinct()).distinct()

                calculo = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).aggregate(total=Sum('costo'))
                totsol = participantes.count()
                totaut = participantes.filter(~Q(estado__in=[1, 2, 3, 7, 8, 9, 20])).count()
                totden = participantes.filter(estado=9).count()
                totpend = totsol - (totaut + totden)

                # Vicerrector académico
                dpvice = DistributivoPersona.objects.filter(denominacionpuesto_id=795, estadopuesto_id=1, status=True).order_by('estadopuesto_id')[0]
                personavice = dpvice.persona
                titulos = personavice.titulo3y4nivel()
                tit1 = titulos['tit1']
                tit2 = titulos['tit2']

                data['titulo1vice'] = tit1
                data['titulo2vice'] = tit2
                data['denominacionpuestovice'] = dpvice.denominacionpuesto.descripcion
                data['vicerrector'] = personavice
                data['nombredptovice'] = dpvice.unidadorganica

                # Decano de facultad
                dpdeca = ResponsableCoordinacion.objects.filter(periodo=periodosol, coordinacion=facultadsol)[0]
                personadecano = dpdeca.persona
                titulos = personadecano.titulo3y4nivel()
                tit1 = titulos['tit1']
                tit2 = titulos['tit2']

                data['titulo1decano'] = tit1
                data['titulo2decano'] = tit2
                data['denominacionpuestodecano'] = "DECANA" if personadecano.sexo.id == 1 else "DECANO"
                data['decano'] = personadecano

                # Directores de carrera
                directores = CoordinadorCarrera.objects.values_list('persona__id', 'persona__apellido1','persona__apellido2','persona__nombres','carrera__nombre').filter(carrera_id__in=codigoscarreras, periodo=periodosol, status=True).order_by('carrera__nombre')
                dircar = []
                fila = []
                c = 1
                for dc in directores:
                    titulos = Persona.objects.get(pk=dc[0]).titulo3y4nivel()
                    dato = [dc[1] + ' ' + dc[2] + ' ' + dc[3], dc[4], titulos['tit1'], titulos['tit2']]
                    if c % 4 == 0:
                        aux = fila[:]
                        dircar.append(aux)
                        fila.clear()

                    fila.append(dato)
                    c += 1

                aux = fila[:]
                dircar.append(aux)

                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['facultad'] = facultadsol.nombre + " (" + facultadsol.alias+ ")"
                data['participantes'] = participantes
                data['costoacumulado'] = calculo['total'] if calculo['total'] is not None else 0.00
                data['estadoreporte'] = ' Autorizadas' if estado == 4 else ' Denegadas' if estado == 9 else ''
                data['estado'] = estado
                data['totsol'] = totsol
                data['totaut'] = totaut
                data['totden'] = totden
                data['totpend'] = totpend
                data['directores'] = dircar

                return conviert_html_to_pdf(
                    'adm_capdocente/listadosolicitudaut_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )


            except Exception as ex:
                pass

        elif action == 'actualizardesembolso':
            try:
                if 'id' not in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                archivo = request.FILES['archivodesembolso']
                descripcionarchivo = 'Archivo del Desembolso'

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": resp["mensaje"], "showSwal": "True", "swalType": "warning"})

                # Consulto la solciitud de capacitación
                solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.POST['id'])))

                archivo._name = generar_nombre("desembolso", archivo._name)

                solicitud.archivodesembolso = archivo
                solicitud.save(request)

                log(u'%s actualizó archivo del desembolso para la solicitud: %s' % (persona, solicitud), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        if action == 'firmarcapmasivo':
            try:
                import json
                informesselect = request.POST['ids'].split(',')
                certificado = request.FILES["firma"]
                contrasenaCertificado = request.POST['palabraclave']
                extension_certificado = os.path.splitext(certificado.name)[1][1:]
                bytes_certificado = certificado.read()
                for idcap in informesselect:
                    capacitacion = PlanificarCapacitaciones.objects.get(pk=idcap)
                    pdf = capacitacion.archivoconvenio
                    # obtener la posicion xy de la firma del doctor en el pdf
                    pdfname = SITE_STORAGE + '/media/' + str(capacitacion.archivoconvenio)
                    palabras = persona.nombre_completo_minus()
                    x, y, numpaginafirma = obtener_posicion_x_y_saltolinea(pdf.url, palabras)
                    x = x + 5
                    y = y + 20
                    datau = JavaFirmaEc(
                        archivo_a_firmar=pdf, archivo_certificado=bytes_certificado,
                        extension_certificado=extension_certificado,
                        password_certificado=contrasenaCertificado,
                        page=int(numpaginafirma), reason='', lx=x, ly=y
                    ).sign_and_get_content_bytes()
                    pdf = io.BytesIO()
                    pdf.write(datau)
                    pdf.seek(0)
                    _name = generar_nombre(
                        f'conveniodevengaciondocente_',
                        'firmada')
                    file_obj = DjangoFile(pdf, name=f"{remover_caracteres_especiales_unicode(_name)}.pdf")

                    capacitacion.archivoconveniofirmadovice = file_obj
                    capacitacion.estado = 5
                    capacitacion.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                eline = 'Error on line {} {}'.format(sys.exc_info()[-1].tb_lineno, ex.__str__())
                return JsonResponse({"result": "bad", "mensaje": u"Error: %s" % eline})

        return HttpResponseRedirect(request.path)
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'participantes':
                try:
                    data['title'] = u'Solicitudes de capacitaciones/actualizaciones'
                    periodos = Periodo.objects.values_list('id', 'nombre').filter(status=True, pk__in=PlanificarCapacitaciones.objects.values_list('periodo_id').filter(tipo=1,status=True).distinct()).order_by('-inicio')
                    facultades = Coordinacion.objects.values_list('id', 'nombre', 'alias').filter(excluir=False, status=True).exclude(pk__in=[10, 11]).order_by('id')
                    # 1 decano 3 coordinacion
                    listatipos = []
                    if persona.es_responsablecoordinacion(periodo) and persona.es_coordinadorcarrera(periodo):
                        listatipos.append(['APR', 'DECANO'])
                        listatipos.append(['VAL', 'DIRECTOR'])
                    else:
                        if tipoautoridad == 1:
                            data['fase'] = 'APR'
                            listatipos.append(['APR', 'DECANO'])
                        elif tipoautoridad == 3:
                            data['fase'] = 'VAL'
                            listatipos.append(['VAL', 'DIRECTOR'])
                        elif tipoautoridad == 4:
                            data['fase'] = 'DES'
                            listatipos.append(['DES', 'TESORERIA GENERAL'])
                        else:
                            data['fase'] = 'AUT'
                            listatipos.append(['AUT', 'VICERRECTORADO DE INVESTIGACIÓN Y POSGRADO'])

                    data['listatipos'] = listatipos
                    data['estados'] = ESTADOS_PLANIFICAR_CAPACITACIONES
                    estadosol = int(request.GET['eSol']) if 'eSol' in request.GET else 0
                    fecharep = request.GET['fecharep'] if 'fecharep' in request.GET else ''
                    search = None
                    participantes = PlanificarCapacitaciones.objects.filter(status=True).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                    if 's' in request.GET:
                        search = request.GET['s'].strip()
                        ss = search.split(' ')
                        if len(ss) == 1:
                            if tipoautoridad == 4 or tipoautoridad == 5:
                                if estadosol == 0:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=search) | Q(
                                            profesor__persona__apellido2__icontains=search) | Q(
                                            profesor__persona__nombres__icontains=search), status=True).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=search) | Q(
                                            profesor__persona__apellido2__icontains=search) | Q(
                                            profesor__persona__nombres__icontains=search), status=True, estado=estadosol).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                                    if estadosol == 4:
                                        participantes = participantes.filter(estado=estadosol).exclude(firmadocente=False)

                            elif tipoautoridad == 3:
                                codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id',
                                                                                                  flat=True).filter(
                                    carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                                if estadosol == 0:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=search) | Q(
                                            profesor__persona__apellido2__icontains=search) | Q(
                                            profesor__persona__nombres__icontains=search),
                                        profesor__id__in=codigosprofesores, status=True).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=search) | Q(
                                            profesor__persona__apellido2__icontains=search) | Q(
                                            profesor__persona__nombres__icontains=search),
                                        profesor__id__in=codigosprofesores, status=True, estado=estadosol).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')

                            elif tipoautoridad == 1:
                                codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list(
                                    'profesor__id', flat=True).filter(periodo=periodo, status=True)

                                codigosprofesores = codigosprofesores1

                                if coordinacion2:
                                    codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list(
                                        'profesor__id', flat=True).filter(periodo=periodo, status=True)
                                    codigosprofesores = codigosprofesores|codigosprofesores2


                                if estadosol == 0:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=search) | Q(
                                            profesor__persona__apellido2__icontains=search) | Q(
                                            profesor__persona__nombres__icontains=search),
                                        profesor__id__in=codigosprofesores, status=True).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=search) | Q(
                                            profesor__persona__apellido2__icontains=search) | Q(
                                            profesor__persona__nombres__icontains=search),
                                        profesor__id__in=codigosprofesores, status=True, estado=estadosol).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                        else:
                            if tipoautoridad == 4 or tipoautoridad == 5:
                                if estadosol == 0:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                            profesor__persona__apellido2__icontains=ss[1]), status=True).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                            profesor__persona__apellido2__icontains=ss[1]), status=True, estado=estadosol).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                            elif tipoautoridad == 3:
                                codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id',
                                                                                                  flat=True).filter(
                                    carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                                if estadosol == 0:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                            profesor__persona__apellido2__icontains=ss[1]),
                                        profesor__id__in=codigosprofesores, status=True).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                            profesor__persona__apellido2__icontains=ss[1]),
                                        profesor__id__in=codigosprofesores, status=True, estado=estadosol).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                            elif tipoautoridad == 1:
                                codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list(
                                    'profesor__id', flat=True).filter(periodo=periodo, status=True)

                                codigosprofesores = codigosprofesores1

                                if coordinacion2:
                                    codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list(
                                        'profesor__id', flat=True).filter(periodo=periodo, status=True)
                                    codigosprofesores = codigosprofesores | codigosprofesores2


                                if estadosol == 0:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                            profesor__persona__apellido2__icontains=ss[1]),
                                        profesor__id__in=codigosprofesores, status=True).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                                else:
                                    participantes = PlanificarCapacitaciones.objects.filter(
                                        Q(profesor__persona__apellido1__icontains=ss[0]) & Q(
                                            profesor__persona__apellido2__icontains=ss[1]),
                                        profesor__id__in=codigosprofesores, status=True, estado=estadosol).order_by(
                                        '-fecha_creacion', 'profesor__persona__apellido1')
                    else:
                        if tipoautoridad == 4 or tipoautoridad == 5:
                            if estadosol == 0:
                                participantes = PlanificarCapacitaciones.objects.filter(status=True).order_by(
                                    '-fecha_creacion', 'profesor__persona__apellido1')
                            else:
                                participantes = PlanificarCapacitaciones.objects.filter(status=True, estado=estadosol).order_by(
                                    '-fecha_creacion', 'profesor__persona__apellido1')
                        elif tipoautoridad == 3:
                            codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id',
                                                                                              flat=True).filter(
                                carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                            if estadosol == 0:
                                participantes = PlanificarCapacitaciones.objects.filter(profesor__id__in=codigosprofesores,
                                                                                    status=True).order_by(
                                    '-fecha_creacion', 'profesor__persona__apellido1')
                            else:
                                participantes = PlanificarCapacitaciones.objects.filter(
                                    profesor__id__in=codigosprofesores,
                                    status=True, estado=estadosol).order_by(
                                    '-fecha_creacion', 'profesor__persona__apellido1')
                        elif tipoautoridad == 1:
                            codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list('profesor__id',
                                                                                                       flat=True).filter(
                                periodo=periodo, status=True)
                            codigosprofesores = codigosprofesores1

                            if coordinacion2:
                                codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list(
                                    'profesor__id', flat=True).filter(periodo=periodo, status=True)
                                codigosprofesores = codigosprofesores | codigosprofesores2
                            if estadosol == 0:
                                participantes = PlanificarCapacitaciones.objects.filter(profesor__id__in=codigosprofesores,
                                                                                    status=True).order_by(
                                    '-fecha_creacion', 'profesor__persona__apellido1')
                            else:
                                participantes = PlanificarCapacitaciones.objects.filter(
                                    profesor__id__in=codigosprofesores,
                                    status=True, estado=estadosol).order_by(
                                    '-fecha_creacion', 'profesor__persona__apellido1')
                    participantes = participantes.annotate(soli_director=Exists(CoordinadorCarrera.objects.filter(periodo=periodo, tipo=3, status=True, persona_id=OuterRef('profesor__persona_id')))).annotate(
                        soli_decano=Exists(ResponsableCoordinacion.objects.filter(periodo=periodo, tipo=1, status=True, persona_id=OuterRef('profesor__persona_id')))).annotate(
                        soli_vicerrec=Exists(DistributivoPersona.objects.filter(denominacionpuesto_id__in=[795, 796, 797], estadopuesto_id=1, status=True, persona_id=OuterRef('profesor__persona_id'))))

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
                    data['periodos'] = periodos
                    data['departamentos'] = facultades
                    data['action'] = action

                    form2 = PlanificarCapacitacionesAutorizarForm()
                    form2.estados_desembolso()
                    data['form2'] = form2

                    return render(request, "adm_capdocente/participantecap.html", data)
                except Exception as ex:
                    pass

            elif action == 'actualizardesembolso':
                try:
                    data['title'] = u'Actualizar Archivo Desembolso'
                    solicitud = PlanificarCapacitaciones.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['solicitud'] = solicitud
                    template = get_template("adm_capdocente/actualizardesembolso.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    msg = ex.__str__()
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. [%s]" % (msg)})

            if action == 'firmarcapsmasivo':
                try:
                    ids = None
                    if 'ids' in request.GET:
                        ids = request.GET['ids']
                    leadsselect = ids
                    data['listadoseleccion'] = leadsselect
                    data['accionfirma'] = 'firmarcapmasivo'
                    template = get_template("adm_criteriosactividadesdocente/firmarinformesmasivo.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'html': json_content})
                except Exception as ex:
                    mensaje = 'Intentelo más tarde'
                    return JsonResponse({"result": False, "mensaje": mensaje})

        else:
            try:
                data['title'] = u'Solicitudes de capacitaciones/actualizaciones'

                periodos = Periodo.objects.values_list('id','nombre').filter(status=True, pk__in=PlanificarCapacitaciones.objects.values_list('periodo_id').filter(tipo=1, status=True).distinct()).order_by('-inicio')
                facultades = Coordinacion.objects.values_list('id','nombre','alias').filter(excluir=False, status=True).exclude(pk__in=[10, 11]).order_by('id')

                listatipos = []
                if persona.es_responsablecoordinacion(periodo) and persona.es_coordinadorcarrera(periodo):
                    listatipos.append(['APR', 'DECANO'])
                    listatipos.append(['VAL', 'DIRECTOR'])
                else:
                    if tipoautoridad == 1:
                        data['fase'] = 'APR'
                        listatipos.append(['APR', 'DECANO'])
                    elif tipoautoridad == 3:
                        data['fase'] = 'VAL'
                        listatipos.append(['VAL', 'DIRECTOR'])
                    elif tipoautoridad == 4:
                        data['fase'] = 'DES'
                        listatipos.append(['DES', 'TESORERIA GENERAL'])
                    else:
                        data['fase'] = 'AUT'
                        listatipos.append(['AUT', 'VICERECTOR ACADEMICO'])
                data['listatipos'] = listatipos
                data['estados'] = ESTADOS_PLANIFICAR_CAPACITACIONES
                estadosol = int(request.GET['eSol']) if 'eSol' in request.GET else 0

                if tipoautoridad == 4:
                    estadosol = 5

                search = None

                if tipoautoridad == 4 or tipoautoridad == 5:
                    if estadosol == 0:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, tipo=1).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                    else:
                        participantes = PlanificarCapacitaciones.objects.filter(status=True, tipo=1, estado=estadosol).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                elif tipoautoridad == 3:
                    codigosprofesores = ProfesorDistributivoHoras.objects.values_list('profesor__id', flat=True).filter(carrera__id__in=codigoscarrera, periodo=periodo, status=True)
                    if estadosol == 0:
                        participantes = PlanificarCapacitaciones.objects.filter(profesor__id__in=codigosprofesores, status=True, tipo=1).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                    else:
                        participantes = PlanificarCapacitaciones.objects.filter(profesor__id__in=codigosprofesores, status=True, tipo=1, estado=estadosol).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                elif tipoautoridad == 1:
                    codigosprofesores1 = coordinacion.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)
                    codigosprofesores = codigosprofesores1
                    if coordinacion2:
                        codigosprofesores2 = coordinacion2.profesordistributivohoras_set.values_list('profesor__id', flat=True).filter(periodo=periodo, status=True)
                        codigosprofesores = codigosprofesores | codigosprofesores2
                    if estadosol == 0:
                        participantes = PlanificarCapacitaciones.objects.filter(profesor__id__in=codigosprofesores,status=True, tipo=1).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                    else:
                        participantes = PlanificarCapacitaciones.objects.filter(profesor__id__in=codigosprofesores,status=True, tipo=1, estado=estadosol).order_by('-fecha_creacion', 'profesor__persona__apellido1')
                participantes = participantes.annotate(soli_director=Exists(CoordinadorCarrera.objects.filter(periodo=periodo, tipo=3, status=True, persona_id=OuterRef('profesor__persona_id')))).annotate(
                        soli_decano=Exists(ResponsableCoordinacion.objects.filter(periodo=periodo, tipo=1, status=True, persona_id=OuterRef('profesor__persona_id')))).annotate(
                        soli_vicerrec=Exists(DistributivoPersona.objects.filter(denominacionpuesto_id__in=[795, 796, 797], estadopuesto_id=1, status=True, persona_id=OuterRef('profesor__persona_id'))))
                # CoordinadorCarrera.objects.filter(carrera_id=carrera, periodo=periodo, tipo=3, status=True)
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        participantes = participantes.filter(Q(profesor__persona__apellido1__icontains=search) | Q(profesor__persona__apellido2__icontains=search) | Q(profesor__persona__nombres__icontains=search))
                    else:
                        participantes = participantes.filter(Q(profesor__persona__apellido1__icontains=ss[0]) & Q( profesor__persona__apellido2__icontains=ss[1]))
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
                data['fecharep'] = datetime.now().strftime('%d-%m-%Y')
                form2 = PlanificarCapacitacionesAutorizarForm()
                form2.estados_desembolso()
                data['form2'] = form2
                data['periodos'] = periodos
                data['departamentos'] = facultades
                data['persona'] = persona
                return render(request, "adm_capdocente/participantecap.html", data)
            except Exception as ex:
                pass