# -*- coding: UTF-8 -*-
from datetime import time
import time as pausaparaemail
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction, connections
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module, last_access
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from sagest.models import datetime, Banco, Rubro, TipoOtroRubro, CompromisoPagoPosgrado, \
    CompromisoPagoPosgradoRecorrido, RubroRefinanciamiento, CuentaContable, CompromisoPagoPosgradoGaranteArchivo, \
    EstadoSolicitud
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, cuenta_email_disponible_para_envio
from sga.models import Persona, \
    BecaSolicitudRecorrido, BecaSolicitud, miinstitucion, SolicitudDevolucionDinero, SolicitudDevolucionDineroRecorrido, \
    CUENTAS_CORREOS, SolicitudRefinanciamientoPosgrado, SolicitudRefinanciamientoPosgradoRecorrido, \
    SolicitudRefinanciamientoPosgradoPropuesta, Matricula
from django.template import Context
from django.template.loader import get_template

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@last_access
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']

    es_gestor_refinanciamiento = persona.grupo_gestion_refinanciamiento_posgrado()
    es_consulta_epunemi = persona.grupo_consulta_refinanciamiento_posgrado()

    if not es_gestor_refinanciamiento and not es_consulta_epunemi:
        return HttpResponseRedirect("/?info=El Módulo está disponible para los Gestores de Refinanciamiento de deudas.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'anularsolicitud':
            conexion = connections['epunemi']
            cnepunemi = conexion.cursor()
            try:
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=request.POST['id'])

                # Consulto el estado a asignar
                estado = obtener_estado_solicitud(1, 24)

                # Rechazo la solicitud
                solicitud.estado = estado
                solicitud.observacion = 'ALUMNO DESISTIÓ DEL PROCESO'
                solicitud.save(request)

                # Creo el recorrido de la solicitud
                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='ANULADO - ALUMNO DESISITIÓ DEL PROCESO',
                                                                       estado=estado
                                                                       )
                recorrido.save(request)

                # Desbloquear los rubros en epunemi para que puedan cobrar
                for detalle in solicitud.solicitudrefinanciamientoposgradodetalle_set.filter(status=True):
                    sql = """UPDATE sagest_rubro SET bloqueado=FALSE WHERE idrubrounemi=%s AND status=true""" % (detalle.rubro.id)
                    cnepunemi.execute(sql)

                log(u'Anuló solicitud de refinanciamiento: %s' % (solicitud), request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'validarjustificativo':
            conexion = connections['epunemi']
            cnepunemi = conexion.cursor()
            try:
                id = int(encrypt(request.POST['id']))
                valorestado = int(request.POST['estadosolicitud'])
                # Obtengo estado a asignar
                estado = obtener_estado_solicitud(1, valorestado)

                # Consulto solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=id)

                # Actualizo solicitud
                solicitud.estado = estado
                solicitud.personarevisa = persona
                solicitud.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                solicitud.save(request)

                # Agrego recorrido de la solicitud
                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='SOLICITUD REVISADA' if valorestado == 2 else solicitud.observacion,
                                                                       estado=estado
                                                                       )
                recorrido.save(request)

                # En caso de haber sido rechazada se deben desbloquear los rubros en epunemi para pagos
                if estado.valor == 3:
                    # Desbloquear los rubros en epunemi para que puedan cobrar
                    for detalle in solicitud.solicitudrefinanciamientoposgradodetalle_set.filter(status=True):
                        sql = """UPDATE sagest_rubro SET bloqueado=FALSE WHERE idrubrounemi=%s AND status=true""" % (
                            detalle.rubro.id)
                        cnepunemi.execute(sql)

                conexion.commit()
                cnepunemi.close()

                # Envio de email de notificación al solicitante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec

                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estado.valor == 2:
                    tituloemail = "Solicitud de Refinanciamiento de Deuda de Programas de Posgrado - REVISADA"
                elif estado.valor == 3:
                    tituloemail = "Solicitud de Refinanciamiento de Deuda de Programas de Posgrado - RECHAZADA"
                else:
                    tituloemail = "Novedades en justificativos de su Solicitud de Refinanciamiento de Deuda de Programas de Posgrado"

                observaciones = solicitud.observacion

                send_html_mail(tituloemail,
                               "emails/notificacion_estado_refinanciamiento_posgrado.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimada' if solicitud.persona.sexo_id == 1 else 'Estimado',
                                'estudiante': solicitud.persona.nombre_completo_inverso(),
                                'numero': solicitud.id,
                                'estado': estado.valor,
                                'observaciones': observaciones,
                                't': miinstitucion()
                                },
                               solicitud.persona.lista_emails_envio(),
                               # ['isaltosm@unemi.edu.ec'],
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicio de gmail
                # pausaparaemail.sleep(2)

                log(u'Cambió estado de solicitud de refinanciamiento de deuda de posgrado: %s  - %s - %s' % (persona, solicitud, estado.descripcion), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'guardarpropuesta':
            try:
                if not 'idsolicitud' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto la solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.POST['idsolicitud'])))

                # Obtengo los valores de los arrays de fechas y cuotas del formulario
                fechas = request.POST.getlist('fechacuota[]')
                valorescuotas = request.POST.getlist('valorcuota[]')

                if not fechas or not valorescuotas:
                    return JsonResponse({"result": "bad", "mensaje": u"Ingrese el detalle de las cuotas"})

                # Obtengo valores del form (no array)
                valorpagar = request.POST['valorpagar']
                totalrefinanciar = request.POST['totalrefinanciar']

                # Consulto el estado PROPUESTA E.
                estado = obtener_estado_solicitud(1, 7)
                # Actualizo la solicitud
                solicitud.pagorequerido = valorpagar
                solicitud.montorefinanciar = totalrefinanciar
                solicitud.estado = estado
                solicitud.save(request)

                # Guardo el detalle de la propuesta de cuotas con sus fechas
                cuota = 1
                for fecha, valor in zip(fechas, valorescuotas):
                    detallepropuesta = SolicitudRefinanciamientoPosgradoPropuesta(solicitud=solicitud,
                                                                                  numerocuota=cuota,
                                                                                  fechacuota=fecha,
                                                                                  valorcuota=valor)
                    detallepropuesta.save(request)
                    cuota += 1

                # Agrego recorrido de la solicitud
                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='PROPUESTA DE REFINANCIAMIENTO ELABORADA',
                                                                       estado=estado
                                                                       )
                recorrido.save(request)


                # Envio de email de notificación al solicitante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec

                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                tituloemail = "Propuesta de Refinanciamiento de Deuda de Programas de Posgrado"

                send_html_mail(tituloemail,
                               "emails/notificacion_estado_refinanciamiento_posgrado.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimada' if solicitud.persona.sexo_id == 1 else 'Estimado',
                                'estudiante': solicitud.persona.nombre_completo_inverso(),
                                'numero': solicitud.id,
                                'estado': estado.valor,
                                'observaciones': '',
                                't': miinstitucion()
                                },
                               solicitud.persona.lista_emails_envio(),
                               # ['isaltosm@unemi.edu.ec'],
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicio de gmail
                # pausaparaemail.sleep(2)

                log(u'Registró propuesta de refinanciamiento de posgrado: %s' % (solicitud), request, "add")
                log(u'Cambió estado de solicitud de refinanciamiento de deuda de posgrado: %s  - %s - %s' % (persona, solicitud, estado.descripcion), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'editarcuotaspropuesta':
            try:
                if not 'idsolicitud' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                # Consulto la solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.POST['idsolicitud'])))

                # Obtengo los valores de los arrays de fechas y cuotas del formulario
                fechas = request.POST.getlist('fechacuota[]')
                valorescuotas = request.POST.getlist('valorcuota[]')

                if not fechas or not valorescuotas:
                    return JsonResponse({"result": "bad", "mensaje": u"Ingrese el detalle de las cuotas"})

                # Inactivo el detalle de cuotas de propuesta anterior
                detalles = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('id')
                for detalle in detalles:
                    detalle.observacion = 'ELIMINADO POR ACTUALIZACIÓN DE CUOTAS'
                    detalle.status = False
                    detalle.save(request)

                # Guardo el detalle de la propuesta de cuotas con sus fechas
                cuota = 1
                for fecha, valor in zip(fechas, valorescuotas):
                    detallepropuesta = SolicitudRefinanciamientoPosgradoPropuesta(solicitud=solicitud,
                                                                                  numerocuota=cuota,
                                                                                  fechacuota=fecha,
                                                                                  valorcuota=valor)
                    detallepropuesta.save(request)
                    cuota += 1


                log(u'Editó detalle de cuotas de la propuesta de refinanciamiento de posgrado: %s' % (solicitud), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'validarpago':
            # conexión a base de datos EPUNEMI
            conexion = connections['epunemi']
            cnepunemi = conexion.cursor()
            try:
                id = int(encrypt(request.POST['id']))
                valorestado = int(request.POST['estadopago'])
                # Obtengo estado a asignar
                estado = obtener_estado_solicitud(1, valorestado)

                # Consulto solicitud
                solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=id)

                # Actualizo solicitud
                solicitud.estado = estado
                solicitud.personarevisa = persona

                # Si pago fue validado
                if estado.valor == 11:
                    solicitud.montopagado = True
                solicitud.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                solicitud.save(request)

                # Agrego recorrido de la solicitud
                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='PAGO VALIDADO Y RUBROS POR REFINANCIAMIENTO GENERADOS' if valorestado == 11 else solicitud.observacion,
                                                                       estado=estado
                                                                       )
                recorrido.save(request)

                # Si el pago fue validado se deben crear los nuevos rubros
                if estado.valor == 11:
                    # Sino existe el compromiso de pago lo debo crear
                    if not CompromisoPagoPosgrado.objects.filter(matricula=solicitud.matricula, status=True, vigente=True, tipo=2).exists():
                        # conexión a base de datos EPUNEMI
                        # cnepunemi = connections['epunemi'].cursor()

                        # Consulto el estado Compromiso Generado
                        estado = obtener_estado_solicitud(2, 1)
                        compromisopago = CompromisoPagoPosgrado(matricula=solicitud.matricula,
                                                                fecha=datetime.now().date(),
                                                                tipo=2,
                                                                vigente=True,
                                                                estado=estado)
                        compromisopago.save(request)

                        # Creo el recorrido del compromiso de pago
                        recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                    fecha=datetime.now().date(),
                                                                    observacion='COMPROMISO DE PAGO GENERADO',
                                                                    estado=estado
                                                                    )
                        recorrido.save(request)

                        # Consulto los rubros de la tabla amortizacion original para guardarlos en el compromiso por refinanciamiento
                        rubros = Rubro.objects.filter(status=True, matricula=solicitud.matricula).order_by('fechavence')
                        for rubro in rubros:
                            fechapago = None
                            vencido = False

                            pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')

                            if pagosrubro:
                                fechapago = pagosrubro[0].fecha

                            if not rubro.cancelado:
                                vencido = datetime.now().date() > rubro.fechavence

                            rubrocompromiso = RubroRefinanciamiento(compromisopago=compromisopago,
                                                                    rubro=rubro,
                                                                    valor=rubro.valor,
                                                                    fechaemite=rubro.fecha,
                                                                    fechavence=rubro.fechavence,
                                                                    saldo=rubro.saldo,
                                                                    vencido=vencido,
                                                                    cancelado=rubro.cancelado)
                            rubrocompromiso.save(request)

                        # Los rubros no cancelados y que no tengan pagos se inactivan y se coloca estado refinanciado True
                        for rubro in rubros.filter(cancelado=False):
                            pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')
                            if not pagosrubro:
                                rubro.refinanciado = True
                                rubro.status = False
                                rubro.observacion = "REFINANCIADO POSGRADO"
                                rubro.save(request)

                                # Actualizar en base de epunemi
                                sql = """UPDATE sagest_rubro SET status=FALSE, refinanciado=TRUE, observacion = 'REFINANCIADO POSGRADO' WHERE idrubrounemi=%s AND status=true""" % (rubro.id)
                                cnepunemi.execute(sql)

                        # Consulto los rubros con saldo
                        rubrosconsaldo = Rubro.objects.filter(status=True, matricula=solicitud.matricula, saldo__gt=0).order_by('fechavence')
                        for rubrosaldo in rubrosconsaldo:
                            pagosrubro = rubrosaldo.pago_set.filter(status=True).order_by('-fecha')
                            # si tiene pagos actualizo el valor del rubro que seria valor original - saldo
                            if pagosrubro:
                                rubrosaldo.valor = rubrosaldo.valor - rubrosaldo.saldo
                                rubrosaldo.cancelado = True
                                rubrosaldo.refinanciado = True
                                rubrosaldo.observacion = "REFINANCIADO POSGRADO"
                                rubrosaldo.save(request)

                                # Hacer la misma actalizacion en EPUNEMI
                                sql = """UPDATE sagest_rubro SET valor=valor-saldo, cancelado=TRUE, refinanciado=TRUE, observacion = 'REFINANCIADO POSGRADO' WHERE idrubrounemi=%s AND status=true""" % (rubro.id)
                                cnepunemi.execute(sql)

                        # Consulto el tipo de rubro seleccionado
                        rubromaestria = TipoOtroRubro.objects.get(pk=int(request.POST['rubro']))

                        # Consulto la persona por cedula en base de epunemi
                        cedula = solicitud.matricula.inscripcion.persona.cedula

                        sql = """SELECT pe.id FROM sga_persona AS pe WHERE pe.cedula='%s' AND pe.status=TRUE;  """ % (cedula)
                        cnepunemi.execute(sql)
                        registro = cnepunemi.fetchone()
                        codigoalumno = registro[0]

                        #  Se crean los nuevos rubros según la propuesta aceptada
                        propuesta = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('id')
                        for cuota in propuesta:
                            nuevorubro = Rubro(fecha=datetime.now().date(),
                                               valor=cuota.valorcuota,
                                               valortotal=cuota.valorcuota,
                                               saldo=cuota.valorcuota,
                                               persona=solicitud.matricula.inscripcion.persona,
                                               matricula=solicitud.matricula,
                                               nombre=rubromaestria.nombre,
                                               tipo=rubromaestria,
                                               cancelado=False,
                                               observacion='',
                                               iva_id=1,
                                               epunemi=True,
                                               fechavence=cuota.fechacuota,
                                               compromisopago=compromisopago,
                                               bloqueado=True
                                               )
                            nuevorubro.save(request)

                            # Consulto el tipo otro rubro en epunemi
                            sql = """SELECT id FROM sagest_tipootrorubro WHERE idtipootrorubrounemi=%s; """ % (rubromaestria.id)
                            cnepunemi.execute(sql)
                            registro = cnepunemi.fetchone()

                            # Si existe
                            if registro is not None:
                                tipootrorubro = registro[0]
                            else:
                                # Debo crear ese tipo de rubro
                                # Consulto centro de costo
                                sql = """SELECT id FROM sagest_centrocosto WHERE status=True AND unemi=True AND tipo=%s;""" % (rubromaestria.tiporubro)
                                cnepunemi.execute(sql)
                                centrocosto = cnepunemi.fetchone()
                                idcentrocosto = centrocosto[0]

                                # Consulto la cuenta contable
                                cuentacontable = CuentaContable.objects.get(partida=rubromaestria.partida, status=True)

                                # Creo el tipo de rubro en epunemi
                                sql = """ Insert Into sagest_tipootrorubro (status, nombre, partida_id, valor, interface, activo, ivaaplicado_id, nofactura, exportabanco, cuentacontable_id, centrocosto_id, tiporubro, idtipootrorubrounemi, unemi)
VALUES(TRUE, '%s', %s, %s, FALSE, TRUE, %s, FALSE, TRUE, %s, %s, 1, %s, TRUE); """ % (rubromaestria.nombre, cuentacontable.partida.id, rubromaestria.valor, rubromaestria.ivaaplicado.id, cuentacontable.id,  idcentrocosto, rubromaestria.id)
                                cnepunemi.execute(sql)

                            # Insertar en base de datos epunemi
                            sql = """ INSERT INTO sagest_rubro (status, cuota, tipocuota, valoriva, tienenotacredito, valornotacredito, valordescuento, anulado, fecha, valor ,valortotal, saldo, persona_id, nombre, tipo_id, cancelado, observacion, iva_id, idrubrounemi, totalunemi, fechavence, compromisopago, bloqueado) 
                                      VALUES (TRUE, 0, 3, 0, FALSE, 0, 0, FALSE, NOW(),                   %s, %s,    %s, %s,     '%s', %s,   FALSE,    '',              1,   %s,        %s,     '/%s/',   %s, TRUE); """ \
                                                           % (cuota.valorcuota, cuota.valorcuota, cuota.valorcuota, codigoalumno, rubromaestria.nombre, tipootrorubro, nuevorubro.id, cuota.valorcuota, cuota.fechacuota, compromisopago.id)
                            cnepunemi.execute(sql)

                        # Notificar al alumno por email y luego viene la ertapa de legalizacion de la nueva tabla de amortizacion
                conexion.commit()
                cnepunemi.close()
                # Envio de email de notificación al solicitante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec

                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                if estado.valor == 2:
                    tituloemail = "Solicitud de Refinanciamiento de Deuda de Programas de Posgrado - ACEPTADA"
                elif estado.valor == 3:
                    tituloemail = "Solicitud de Refinanciamiento de Deuda de Programas de Posgrado - RECHAZADA"
                else:
                    tituloemail = "Novedades en justificativos de su Solicitud de Refinanciamiento de Deuda de Programas de Posgrado"

                observaciones = solicitud.observacion

                # send_html_mail(tituloemail,
                #                "emails/notificacion_estado_refinanciamiento_posgrado.html",
                #                {'sistema': u'Posgrado UNEMI',
                #                 'fecha': fechaenvio,
                #                 'hora': horaenvio,
                #                 'saludo': 'Estimada' if solicitud.persona.sexo_id == 1 else 'Estimado',
                #                 'estudiante': solicitud.persona.nombre_completo_inverso(),
                #                 'numero': solicitud.id,
                #                 'estado': estado.valor,
                #                 'observaciones': observaciones,
                #                 't': miinstitucion()
                #                 },
                #                # persona.lista_emails_envio(),
                #                ['isaltosm@unemi.edu.ec'],
                #                [],
                #                cuenta=CUENTAS_CORREOS[cuenta][1]
                #                )
                #
                # # Temporizador para evitar que se bloquee el servicio de gmail
                # # pausaparaemail.sleep(2)

                log(u'Cambió estado de solicitud de refinanciamiento de deuda de posgrado: %s  - %s - %s' % (persona, solicitud, estado.descripcion), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                conexion.rollback()
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'validardocumentocompromiso':
            try:
                id = int(encrypt(request.POST['id']))
                persona = data['persona']
                valorestado = int(request.POST['estadocompromiso'])
                lista_observaciones = []
                # Obtengo estado a asignar: compromiso de pago
                estado = obtener_estado_solicitud(2, valorestado)

                # Obtengo estado a asignar: solicitud
                if estado.valor == 2:
                    estadosolicitud = obtener_estado_solicitud(1, 20)
                else:
                    estadosolicitud = obtener_estado_solicitud(1, 22)

                # Consulto compromiso de pago
                compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                alumno = compromisopago.matricula.inscripcion.persona

                # Si estado es Legalizado, se debe desbloquear matricula
                if estado.valor == 2:
                    # Desbloquear matricula
                    matricula = compromisopago.matricula
                    matricula.bloqueomatricula = False
                    matricula.save(request)

                # Actualizo compromiso de pago
                compromisopago.estado = estado
                compromisopago.personarevisa = persona
                compromisopago.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                compromisopago.save(request)

                # Actualizo la solicitud
                solicitud = compromisopago.solicitudrefinanciamiento
                solicitud.estado = estadosolicitud
                solicitud.save(request)

                # Creo el recorrido de la solicitud
                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                       fecha=datetime.now().date(),
                                                                       observacion='REFINANCIAMIENTO DE DEUDA LEGALIZADO' if valorestado == 2 else compromisopago.observacion,
                                                                       estado=estadosolicitud
                                                                       )
                recorrido.save(request)

                # Obtengo los valores de los campos tipo arreglo del formulario
                tiposdocumentos = request.POST.getlist('tipodocumento[]')
                idstipodocumentos = request.POST.getlist('iddocumento[]')
                estadostipodocumentos = request.POST.getlist('estadodocumento[]')
                observacionesdocumentos = request.POST.getlist('observacionreg[]')

                # Documentos del alumno
                documentospersonales = compromisopago.matricula.inscripcion.persona.documentos_personales()

                # Actualizar el estado de cada uno de los documentos del compromiso de pago
                for tipodoc, idtipodoc, estadotipodoc, observaciondoc in zip(tiposdocumentos, idstipodocumentos, estadostipodocumentos, observacionesdocumentos):
                    print(tipodoc, "-", idtipodoc, "-", estadotipodoc, "-", observaciondoc)

                    if tipodoc == 'CP':#Compromiso de pago
                        compromisopago.estadocompromiso = estadotipodoc
                        compromisopago.observacioncompromiso = observaciondoc.strip().upper()
                        compromisopago.save(request)

                        if estadotipodoc == '3':
                            lista_observaciones.append('Tabla de amortización: ' + observaciondoc.strip().upper())

                    elif tipodoc == 'CM':#Contrato de maestria
                        compromisopago.estadocontrato = estadotipodoc
                        compromisopago.observacioncontrato = observaciondoc.strip().upper()
                        compromisopago.save(request)

                        if estadotipodoc == '3':
                            lista_observaciones.append('Contrato de Maestría: ' + observaciondoc.strip().upper())

                    elif tipodoc == 'PG':# Pagare
                        compromisopago.estadopagare = estadotipodoc
                        compromisopago.observacionpagare = observaciondoc.strip().upper()
                        compromisopago.save(request)

                        if estadotipodoc == '3':
                            lista_observaciones.append('Pagaré: ' + observaciondoc.strip().upper())

                    elif tipodoc == 'CPG': # Comprobante de pago
                        compromisopago.estadocomprobante = estadotipodoc
                        compromisopago.observacioncomprobante = observaciondoc.strip().upper()
                        compromisopago.save(request)

                        if estadotipodoc == '3':
                            lista_observaciones.append('Comprobante de pago: ' + observaciondoc.strip().upper())

                    elif tipodoc in ['CC', 'PV']:#Cedula o papeleta del estudiante
                        if tipodoc == 'CC':#Cedula
                            documentospersonales.estadocedula = estadotipodoc
                            documentospersonales.observacioncedula = observaciondoc.strip().upper()
                            documentospersonales.save(request)

                            if estadotipodoc == '3':
                                lista_observaciones.append('Cédula del alumno: ' + observaciondoc.strip().upper())

                        else:# Papeleta
                            documentospersonales.estadopapeleta = estadotipodoc
                            documentospersonales.observacionpapeleta = observaciondoc.strip().upper()
                            documentospersonales.save(request)

                            if estadotipodoc == '3':
                                lista_observaciones.append('Papaleta de votación del alumno: ' + observaciondoc.strip().upper())
                    else:
                        documento = CompromisoPagoPosgradoGaranteArchivo.objects.get(tipoarchivo=idtipodoc,
                                                                                    garante__compromisopago=compromisopago,
                                                                                    status=True)
                        documento.estado = estadotipodoc
                        documento.observacion = observaciondoc.strip().upper()
                        documento.save(request)

                        if estadotipodoc == '3':
                            lista_observaciones.append(documento.tipoarchivo.descripcion + ': ' + observaciondoc.strip().upper())

                # Agrego recorrido de compromiso de pago
                recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                            fecha=datetime.now().date(),
                                                            observacion='REFINANCIAMIENTO DE DEUDA LEGALIZADO' if valorestado == 2 else compromisopago.observacion,
                                                            estado=estado
                                                            )
                recorrido.save(request)

                # Envio de email de notificación al estudiante
                # listacuentascorreo = [23, 24, 25, 26, 27]
                # posgrado1_unemi@unemi.edu.ec
                # posgrado2_unemi@unemi.edu.ec
                # posgrado3_unemi@unemi.edu.ec
                # posgrado4_unemi@unemi.edu.ec
                # posgrado5_unemi@unemi.edu.ec

                listacuentascorreo = [18]  # posgrado@unemi.edu.ec

                fechaenvio = datetime.now().date()
                horaenvio = datetime.now().time()
                cuenta = cuenta_email_disponible_para_envio(listacuentascorreo)

                tituloemail = "Refinanciamiento de Deudas de Programas de Posgrado Legalizado" if valorestado == 2 else "Novedades en Carga de Documentos - Refinanciamiento Deudas de Programas de Posgrado"

                compromisopago.observacion = compromisopago.observacion + ". " + ", ".join(lista_observaciones)
                compromisopago.save(request)

                observaciones = compromisopago.observacion

                send_html_mail(tituloemail,
                               "emails/notificacion_estado_compromisopago.html",
                               {'sistema': u'Posgrado UNEMI',
                                'fecha': fechaenvio,
                                'hora': horaenvio,
                                'saludo': 'Estimada' if alumno.sexo.id == 1 else 'Estimado',
                                'estudiante': alumno.nombre_completo_inverso(),
                                'estado': estado.valor,
                                'tipocompromiso': compromisopago.tipo,
                                'observaciones': observaciones,
                                'destinatario': 'ALUMNO',
                                't': miinstitucion()
                                },
                               alumno.lista_emails_envio(),
                               # ['isaltosm@unemi.edu.ec'],
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicio de gmail
                pausaparaemail.sleep(1)

                log(u'Cambió estado de compromiso de pago por refinanciamiento de programas de posgrado: %s  - %s - %s' % (persona, compromisopago, estado.descripcion), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'verificar_solicitudes_existentes':
            try:
                if SolicitudRefinanciamientoPosgrado.objects.filter(status=True).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes de refinanciamiento de deudas para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})



        elif action == 'verificar_solicitudes_validadas_reporte':
            try:
                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                    if SolicitudDevolucionDinero.objects.filter(status=True, estado=2, fechavalida__range=(desde, hasta)).exists():
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes validadas en el rango de fechas"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_solicitudes_rechazadas':
            try:
                if SolicitudDevolucionDinero.objects.filter(status=True, estado=3).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes rechazadas para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_solicitudes_pendientes_revisar':
            try:
                if SolicitudDevolucionDinero.objects.filter(status=True, estado=1).exists():
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "No existen solicitudes pendientes de revisar para generar el reporte"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'mostrarrecorrido':
                try:
                    data = {}
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['recorrido'] = solicitud.solicitudrefinanciamientoposgradorecorrido_set.filter(status=True).order_by('id')
                    template = get_template("alu_refinanciamientoposgrado/recorridosolicitud.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'anularsolicitud':
                try:
                    data['title'] = u'Anular Proceso de Refinanciamiento'
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['id'])))
                    return render(request, "adm_refinanciamientoposgrado/anulaproceso.html", data)
                except Exception as ex:
                    pass

            elif action == 'validarjustificativo':
                try:
                    data['title'] = u'Revisar/Validar Justificativos'
                    data['ids'] = int(encrypt(request.GET['ids']))

                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['ids'])))

                    # data['estadodocumento'] = request.GET['estadodocumento']
                    data['estadodocumento'] = 0

                    # Consulto el estado que voy a asignar: EN REVISION
                    estado = obtener_estado_solicitud(1, 4)

                    if solicitud.personarevisa:
                        if solicitud.personarevisa != persona and solicitud.estado.valor != 1:
                            return JsonResponse({"result": "bad", "mensaje": "La solicitud está siendo revisada por %s." % (solicitud.personarevisa.nombre_completo_inverso())})
                        else:
                            if solicitud.estado.valor == 1 or solicitud.estado.valor == 6:
                                # Actualizo la solicitud
                                solicitud.personarevisa = persona
                                solicitud.estado = estado
                                solicitud.save(request)
                                # Agrego recorrido de la solicitud
                                recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                                       fecha=datetime.now().date(),
                                                                                       observacion='EN REVISIÓN DE JUSTIFICATIVOS',
                                                                                       estado=estado
                                                                                       )
                                recorrido.save(request)
                    else:
                        # Actualizo la solicitud
                        solicitud.personarevisa = persona
                        solicitud.estado = estado
                        solicitud.save(request)
                        # Agrego recorrido de la solicitud
                        recorrido = SolicitudRefinanciamientoPosgradoRecorrido(solicitud=solicitud,
                                                                               fecha=datetime.now().date(),
                                                                               observacion='EN REVISIÓN DE JUSTIFICATIVOS',
                                                                               estado=estado
                                                                               )
                        recorrido.save(request)

                    # Si tiene estado SOLICITADO o EN REVISION SE PODRA EDITAR
                    if solicitud.estado.valor in [1, 4, 6]:
                        data['permite_modificar'] = True
                    else:
                        data['permite_modificar'] = False
                    # Estados a asignar
                    data['estadossolicitud'] = obtener_estados_solicitud(1, [2, 3, 5])
                    # Archivos cargados en la solicitud
                    cantidadjustificativo = 0
                    if solicitud.motivo == 1:
                        data['evidencia1'] = solicitud.evidencia1.url
                        data['titulo1'] = "Certificado Médico"
                        cantidadjustificativo = 1
                    elif solicitud.motivo == 2:
                        data['evidencia1'] = solicitud.evidencia1.url
                        data['evidencia2'] = solicitud.evidencia2.url
                        data['titulo1'] = "Certificado Culminación Relación Laboral"
                        data['titulo2'] = "Certificado Afiliación Seguro"
                        cantidadjustificativo = 2
                    elif solicitud.motivo == 3:
                        data['evidencia1'] = solicitud.evidencia1.url
                        data['titulo1'] = "Acta de Defunción de Familiar"
                        cantidadjustificativo = 1
                    elif solicitud.motivo == 4:
                        data['evidencia1'] = solicitud.evidencia1.url
                        data['titulo1'] = "Certificado Médico por Enfermedad de Familiar"
                        cantidadjustificativo = 1
                    elif solicitud.motivo == 6:
                        data['evidencia1'] = solicitud.evidencia1.url
                        data['titulo1'] = "Certificado / Rol de Pago"
                        cantidadjustificativo = 1
                    else:
                        data['evidencia1'] = solicitud.evidencia1.url
                        data['titulo1'] = "Justificativo"
                        cantidadjustificativo = 1

                    data['cantidadjustificativo'] = cantidadjustificativo
                    template = get_template("adm_refinanciamientoposgrado/validarjustificativo.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'elaborarpropuesta':
                try:
                    data['title'] = u'Elaborar Propuesta de Refinanciamiento de Deudas de Posgrado'
                    data['id'] = idsol = int(encrypt(request.GET['id']))
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=idsol)

                    # Consulto los rubros con saldo pendiente
                    rubros = Rubro.objects.filter(status=True, matricula=solicitud.matricula, saldo__gt=0).order_by('fechavence')
                    listarubros = []
                    novencidas = 0
                    fechaprimeranovencida = ""
                    for rubro in rubros:

                        vencido = "--"
                        if not rubro.cancelado:
                            vencido = "SI" if datetime.now().date() > rubro.fechavence else "NO"
                            color = "" if vencido == "SI" else ""

                            if datetime.now().date() > rubro.fechavence:
                                vencido = "SI"
                                color = "red"
                                font_weight = "bold"
                            else:
                                vencido = "NO"
                                color = "black"
                                font_weight = "normal"
                                novencidas += 1
                                if fechaprimeranovencida == "":
                                    fechaprimeranovencida = rubro.fechavence

                        listarubros.append([rubro.id, rubro.fecha, rubro.fechavence, rubro.saldo, vencido, color, font_weight])


                    # detalleactividades = ""
                    # if actividad.detalle_actividades_profesor():
                    #     detalleactividades = "|".join([str(a.id) + "~" + a.detalle + "~" + str(a.horas) + "~" + a.observacion for a in actividad.detalle_actividades_profesor()])
                    #Exception = {type} <class 'Exception'>
                    data['detalle'] = ""
                    data['listarubros'] = listarubros
                    data['novencidas'] = novencidas
                    data['fechaprimeranovencida'] = fechaprimeranovencida if fechaprimeranovencida != "" else datetime.now().date()
                    template = get_template("adm_refinanciamientoposgrado/elaborapropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'validarpago':
                try:
                    data['title'] = u'Validar Pago y Generar Rubros por Refinanciamiento'
                    data['ids'] = int(encrypt(request.GET['ids']))

                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=int(encrypt(request.GET['ids'])))

                    # data['estadodocumento'] = request.GET['estadodocumento']
                    data['estadodocumento'] = 0

                    # Si tiene estado COMP.PAGO C. SE PODRA EDITAR
                    if solicitud.estado.valor == 10:
                        data['permite_modificar'] = True
                    else:
                        data['permite_modificar'] = False

                    # Cuotas del compromiso de pago anterior
                    compromisoanterior = []
                    rubros = Rubro.objects.filter(status=True, matricula=solicitud.matricula).order_by('fechavence')
                    for rubro in rubros:
                        fechapago = None
                        vencido = False

                        pagosrubro = rubro.pago_set.filter(status=True).order_by('-fecha')

                        if pagosrubro:
                            fechapago = pagosrubro[0].fecha

                        if not rubro.cancelado:
                            vencido = datetime.now().date() > rubro.fechavence

                        compromisoanterior.append([rubro.id, rubro.nombre, rubro.valor, rubro.fecha, rubro.fechavence, fechapago, rubro.valor - rubro.saldo, rubro.saldo, "SI" if vencido else "NO"])

                    # Cuotas del nuevo compromiso de pago
                    compromisonuevo = []
                    propuesta = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('id')
                    for cuota in propuesta:
                        compromisonuevo.append([cuota.numerocuota, 'RUBRO # ' + str(cuota.numerocuota), cuota.valorcuota, datetime.now().date(), cuota.fechacuota])

                    # Rubros para que el usuario le asigne al nuevo compromiso de pago
                    rubros = TipoOtroRubro.objects.filter(interface=True, activo=True).order_by('nombre')

                    # Estados a asignar
                    data['estadossolicitud'] = obtener_estados_solicitud(1, [11, 12])
                    # Archivo del comprobante de pago
                    data['comprobante'] = solicitud.comprobantepago.url

                    data['compromisoanterior'] = compromisoanterior
                    data['compromisonuevo'] = compromisonuevo
                    data['rubros'] = rubros

                    template = get_template("adm_refinanciamientoposgrado/validarpago.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'validardocumentocompromiso':
                try:
                    data['title'] = u'Legalizar Refinanciamiento de Maestría'
                    data['idm'] = int(encrypt(request.GET['idm']))
                    persona = data['persona']

                    matricula = Matricula.objects.get(pk=encrypt(request.GET['idm']))

                    data['compromisopago'] = compromisopago = matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=2)[0]

                    primerdocumento = {}
                    primerdocumento['descripcion'] = 'Tabla de amortización'
                    primerdocumento['url'] = compromisopago.archivocompromiso.url
                    data['primerdocumento'] = primerdocumento

                    documentos = []
                    documentos.append(['CP', 'Tabla de amortización', compromisopago.archivocompromiso.url, compromisopago.get_estadocompromiso_display(), compromisopago.estadocompromiso, 0, compromisopago.observacioncompromiso])

                    if compromisopago.tipo == 1:
                        documentos.append(['CM', 'Contrato de Maestría', compromisopago.archivocontrato.url, compromisopago.get_estadocontrato_display(), compromisopago.estadocontrato, 0, compromisopago.observacioncontrato])

                    documentos.append(['PG', 'Pagaré', compromisopago.archivopagare.url, compromisopago.get_estadopagare_display(), compromisopago.estadopagare, 0, compromisopago.observacionpagare])

                    # Consulto los documentos personales del alumnos: cedula y papeleta de votación
                    documentospersonales = matricula.inscripcion.persona.documentos_personales()
                    documentos.append(['CC', 'Cédula de ciudadanía', documentospersonales.cedula.url, documentospersonales.get_estadocedula_display(), documentospersonales.estadocedula, 0, documentospersonales.observacioncedula])
                    documentos.append(['PV', 'Papeleta de votación', documentospersonales.papeleta.url, documentospersonales.get_estadopapeleta_display(), documentospersonales.estadopapeleta, 0, documentospersonales.observacionpapeleta])

                    # Agrego el comprobante de pago
                    documentos.append(['CPG', 'Comprobante de pago', compromisopago.archivocomprobante.url, compromisopago.get_estadocomprobante_display(), compromisopago.estadocomprobante, 0, compromisopago.observacioncomprobante])

                    # Consulto los documentos del conyuge
                    conyuge = compromisopago.datos_conyuge()
                    if conyuge:
                        archivocedula = conyuge.archivocedulaconyuge()
                        documentos.append(['OT', archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.tipoarchivo.id, archivocedula.observacion])
                        archivovotacion = conyuge.archivovotacionconyuge()
                        documentos.append(['OT', archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.tipoarchivo.id, archivovotacion.observacion])

                    # Consulto los documentos del garante
                    garante = compromisopago.datos_garante()
                    if garante:
                        archivocedula = garante.archivocedulagarante()
                        documentos.append(['OT', archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.tipoarchivo.id, archivocedula.observacion])
                        archivovotacion = garante.archivovotaciongarante()
                        documentos.append(['OT', archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.tipoarchivo.id, archivovotacion.observacion])

                        # Si no es persona juridica
                        if garante.personajuridica == 2:
                            # si trabaja bajo relacion de dependencia
                            if garante.relaciondependencia == 1:
                                archivorolpagos = garante.archivorolpagos()
                                documentos.append(['OT', archivorolpagos.tipoarchivo.descripcion, archivorolpagos.archivo.url, archivorolpagos.get_estado_display(), archivorolpagos.estado, archivorolpagos.tipoarchivo.id, archivorolpagos.observacion])
                            else:
                                archivopredios = garante.archivoimpuestopredial()
                                documentos.append(['OT', archivopredios.tipoarchivo.descripcion, archivopredios.archivo.url, archivopredios.get_estado_display(), archivopredios.estado, archivopredios.tipoarchivo.id, archivopredios.observacion])
                                archivofacserv = garante.archivofacturaserviciobasico()
                                if archivofacserv:
                                    documentos.append(['OT', archivofacserv.tipoarchivo.descripcion, archivofacserv.archivo.url, archivofacserv.get_estado_display(), archivofacserv.estado, archivofacserv.tipoarchivo.id, archivofacserv.observacion])
                                archivoriseruc = garante.archivoriseruc()
                                documentos.append(['OT', archivoriseruc.tipoarchivo.descripcion, archivoriseruc.archivo.url, archivoriseruc.get_estado_display(), archivoriseruc.estado, archivoriseruc.tipoarchivo.id, archivoriseruc.observacion])
                        else:
                            archivoconstitucion = garante.archivoconstitucion()
                            documentos.append(['OT', archivoconstitucion.tipoarchivo.descripcion, archivoconstitucion.archivo.url, archivoconstitucion.get_estado_display(), archivoconstitucion.estado, archivoconstitucion.tipoarchivo.id, archivoconstitucion.observacion])
                            archivoexistencia = garante.archivoexistencialegal()
                            documentos.append(['OT', archivoexistencia.tipoarchivo.descripcion, archivoexistencia.archivo.url, archivoexistencia.get_estado_display(), archivoexistencia.estado, archivoexistencia.tipoarchivo.id, archivoexistencia.observacion])
                            archivorenta = garante.archivoimpuestorenta()
                            documentos.append(['OT', archivorenta.tipoarchivo.descripcion, archivorenta.archivo.url, archivorenta.get_estado_display(), archivorenta.estado, archivorenta.tipoarchivo.id, archivorenta.observacion])
                            archivorepresentante = garante.archivonombramientorepresentante()
                            documentos.append(['OT', archivorepresentante.tipoarchivo.descripcion, archivorepresentante.archivo.url, archivorepresentante.get_estado_display(), archivorepresentante.estado, archivorepresentante.tipoarchivo.id, archivorepresentante.observacion])
                            archivoacta = garante.archivojuntaaccionistas()
                            documentos.append(['OT', archivoacta.tipoarchivo.descripcion, archivoacta.archivo.url, archivoacta.get_estado_display(), archivoacta.estado, archivoacta.tipoarchivo.id, archivoacta.observacion])
                            archivoruc = garante.archivoruc()
                            documentos.append(['OT', archivoruc.tipoarchivo.descripcion, archivoruc.archivo.url, archivoruc.get_estado_display(), archivoruc.estado, archivoruc.tipoarchivo.id, archivoruc.observacion])

                    # Consulto los documentos del conyuge del garante
                    conyugegarante = compromisopago.datos_conyuge_garante()
                    if conyugegarante:
                        archivocedula = conyugegarante.archivocedulaconyugegarante()
                        documentos.append(['OT', archivocedula.tipoarchivo.descripcion, archivocedula.archivo.url, archivocedula.get_estado_display(), archivocedula.estado, archivocedula.tipoarchivo.id, archivocedula.observacion])
                        archivovotacion = conyugegarante.archivovotacionconyugegarante()
                        documentos.append(['OT', archivovotacion.tipoarchivo.descripcion, archivovotacion.archivo.url, archivovotacion.get_estado_display(), archivovotacion.estado, archivovotacion.tipoarchivo.id, archivovotacion.observacion])

                    data['documentos'] = documentos

                    # Consulto el estado que voy a asignar: EN REVISION
                    estado = obtener_estado_solicitud(2, 5)

                    if compromisopago.personarevisa:
                        if compromisopago.solicitudrefinanciamiento.estado.valor != 20:
                            if compromisopago.personarevisa != persona and compromisopago.estado.valor != 3:
                                return JsonResponse({"result": "bad", "mensaje": "Los documentos del compromiso de pago está siendo revisada por %s." % (compromisopago.personarevisa.nombre_completo_inverso())})
                    else:
                        # Actualizo el compromiso de pago
                        compromisopago.personarevisa = persona
                        compromisopago.estado = estado
                        compromisopago.save(request)

                        # Creo el recorrido del compromiso de pago
                        recorrido = CompromisoPagoPosgradoRecorrido(compromisopago=compromisopago,
                                                                    fecha=datetime.now().date(),
                                                                    observacion='DOCUMENTOS EN REVISIÓN',
                                                                    estado=estado
                                                                    )
                        recorrido.save(request)

                    # Si tiene estado DOCUMENTOS CARGADOS o EN REVISION SE PODRA EDITAR
                    if compromisopago.estado.valor in [3, 5]:
                        data['permite_modificar'] = True
                    else:
                        data['permite_modificar'] = False
                    # Estados a asignar
                    data['estadossolicitud'] = obtener_estados_solicitud(2, [2, 4])

                    template = get_template("adm_refinanciamientoposgrado/validardocumento.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'listadosolicitudes':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalwrap = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalwrap.alignment.wrap = True
                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_refinanciamiento_' + random.randint(1, 10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                    ws.write_merge(2, 2, 0, 10, 'LISTADO DE SOLICITUDES DE REFINANCIAMIENTO DE DEUDA DE PROGRAMAS DE POSGRADO', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA SOLICITUD", 3500),
                        (u"PROGRAMA", 10000),
                        (u"COHORTE", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"MOTIVO REFINANCIAMIENTO", 10000),
                        (u"TOTAL PENDIENTE", 5000),
                        (u"PAGO REQUERIDO", 5000),
                        (u"TOTAL REFINANCIAR", 5000),
                        (u"ESTADO", 5000),
                        (u"OBSERVACIÓN", 10000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudRefinanciamientoPosgrado.objects.filter(status=True).order_by('-id')

                    for solicitud in solicitudes:
                        row_num += 1
                        alumno = solicitud.matricula.inscripcion.persona
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fecha_creacion, fuentefecha)
                        ws.write(row_num, 2, solicitud.matricula.inscripcion.carrera.nombre, fuentenormal)
                        ws.write(row_num, 3, solicitud.matricula.nivel.periodo.nombre, fuentenormal)
                        ws.write(row_num, 4, alumno.identificacion(), fuentenormal)
                        ws.write(row_num, 5, alumno.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 6, alumno.email, fuentenormal)
                        ws.write(row_num, 7, alumno.emailinst, fuentenormal)
                        ws.write(row_num, 8, alumno.telefono_conv, fuentenormal)
                        ws.write(row_num, 9, alumno.telefono, fuentenormal)
                        ws.write(row_num, 10, solicitud.get_motivo_display() if solicitud.motivo != 5 else solicitud.otromotivo, fuentenormal)
                        ws.write(row_num, 11, solicitud.pendiente, fuentemoneda)

                        if solicitud.pagorequerido:
                            ws.write(row_num, 12, solicitud.pagorequerido, fuentemoneda)
                        else:
                            ws.write(row_num, 12, "", fuentenormal)

                        if solicitud.montorefinanciar:
                            ws.write(row_num, 13, solicitud.montorefinanciar, fuentemoneda)
                        else:
                            ws.write(row_num, 13, "", fuentenormal)

                        ws.write(row_num, 14, solicitud.estado.descripcion, fuentenormal)
                        ws.write(row_num, 15, solicitud.estado.observacion, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'mostrarpropuesta':
                try:
                    data['title'] = u'Propuesta de Refinanciamiento de Deudas de Posgrado'
                    data['id'] = idsol = int(encrypt(request.GET['id']))
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=idsol)
                    data['detallecuotas'] = detalle = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('numerocuota')
                    data['totalcuotas'] = detalle.count()

                    template = get_template("adm_refinanciamientoposgrado/mostrarpropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'editarcuotaspropuesta':
                try:
                    data['title'] = u'Editar Cuotas de Propuesta de Refinanciamiento de Deudas de Posgrado'
                    data['id'] = idsol = int(encrypt(request.GET['id']))
                    data['solicitud'] = solicitud = SolicitudRefinanciamientoPosgrado.objects.get(pk=idsol)
                    data['detallecuotas'] = detalle = solicitud.solicitudrefinanciamientoposgradopropuesta_set.filter(status=True).order_by('numerocuota')
                    data['fechaultimacuota'] = detalle.last().fechacuota
                    data['totalcuotas'] = detalle.count()

                    template = get_template("adm_refinanciamientoposgrado/editpropuesta.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'generarbeneficiarioscsv':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150;')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=beneficiarios_' + random.randint(1,10000).__str__() + '.csv'

                    row_num = 0

                    for col_num in range(12):
                        ws.col(col_num).width = 5000

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                           cuentabancariapersona__archivo__isnull=False,
                                           inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                           inscripcion__becasolicitud__becaasignacion__status=True,
                                           cuentabancariapersona__fechavalida__range=(desde, hasta),
                                           cuentabancariapersona__archivoesigef=False).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        ws.write(row_num, 0, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 1, remover_caracteres_tildes_unicode(beneficiario.nombre_completo_inverso()[:100]), fuentenormal)
                        ws.write(row_num, 2, remover_caracteres_tildes_unicode(beneficiario.direccion_completa()[:300]), fuentenormal)
                        ws.write(row_num, 3, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 4, '0', fuentenormal)
                        ws.write(row_num, 5, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 6, beneficiario.cuentabancaria().banco.codigo, fuentenormal)
                        ws.write(row_num, 7, beneficiario.cuentabancaria().tipocuentabanco.id, fuentenormal)
                        ws.write(row_num, 8, beneficiario.cuentabancaria().numero, fuentenormal)
                        ws.write(row_num, 9, 'C', fuentenormal)
                        ws.write(row_num, 10, 'N', fuentenormal)
                        row_num += 1

                        cuentabeneficiario = beneficiario.cuentabancaria()
                        cuentabeneficiario.archivoesigef = True
                        cuentabeneficiario.save(request)


                    wb.save(response)
                    return response
                except Exception as ex:
                    transaction.set_rollback(True)
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentasrechazadas':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cuentas_rechazadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 15, 'LISTADO DE BENEFICIARIOS CON CUENTAS RECHAZADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"PROVINCIA", 5000),
                        (u"CANTÓN", 5000),
                        (u"PARROQUIA", 5000),
                        (u"DIRECCIÓN", 15000),
                        (u"REFERENCIA", 15000),
                        (u"SECTOR", 15000),
                        (u"# CASA", 5000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"OBSERVACIÓN", 20000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       cuentabancariapersona__estadorevision=3).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        row_num += 1
                        ws.write(row_num, 0, beneficiario.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 1, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 2, str(beneficiario.provincia) if beneficiario.provincia else '', fuentenormal)
                        ws.write(row_num, 3, str(beneficiario.canton) if beneficiario.canton else '', fuentenormal)
                        ws.write(row_num, 4, str(beneficiario.parroquia) if beneficiario.parroquia else '', fuentenormal)
                        ws.write(row_num, 5, beneficiario.direccion_corta().upper(), fuentenormal)
                        ws.write(row_num, 6, beneficiario.referencia.upper(), fuentenormal)
                        ws.write(row_num, 7, beneficiario.sector.upper(), fuentenormal)
                        ws.write(row_num, 8, beneficiario.num_direccion, fuentenormal)
                        ws.write(row_num, 9, beneficiario.email, fuentenormal)
                        ws.write(row_num, 10, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 11, beneficiario.telefono_conv, fuentenormal)
                        ws.write(row_num, 12, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 13, beneficiario.get_tipocelular_display() if beneficiario.tipocelular else '', fuentenormal)
                        cuentabeneficiario = beneficiario.cuentabancaria()
                        ws.write(row_num, 14, cuentabeneficiario.observacion, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'solicitudesvalidadas':
                try:
                    __author__ = 'Unemi'

                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_validadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO DE SOLICITUDES DE DEVOLUCIÓN DE DINERO VALIDADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA APROBACIÓN", 3500),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"MOTIVO DEVOLUCIÓN", 10000),
                        (u"TOTAL DEPOSITADO", 5000),
                        (u"TOTAL A DEVOLVER", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudDevolucionDinero.objects.filter(status=True, estado=2, fechavalida__range=(desde, hasta)).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    for solicitud in solicitudes:
                        row_num += 1
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fechavalida, fuentefecha)
                        ws.write(row_num, 2, solicitud.persona.identificacion(), fuentenormal)
                        ws.write(row_num, 3, solicitud.persona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 4, solicitud.persona.email, fuentenormal)
                        ws.write(row_num, 5, solicitud.persona.emailinst, fuentenormal)
                        ws.write(row_num, 6, solicitud.persona.telefono_conv, fuentenormal)
                        ws.write(row_num, 7, solicitud.persona.telefono, fuentenormal)
                        ws.write(row_num, 8, solicitud.persona.get_tipocelular_display() if solicitud.persona.tipocelular else '', fuentenormal)
                        ws.write(row_num, 9, solicitud.motivo.strip(), fuentenormal)
                        ws.write(row_num, 10, solicitud.monto, fuentemoneda)
                        ws.write(row_num, 11, solicitud.montodevolver, fuentemoneda)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'solicitudesrechazadas':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')

                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')

                    fuentenormalwrap = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalwrap.alignment.wrap = True

                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_rechazadas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO DE SOLICITUDES DE DEVOLUCIÓN DE DINERO RECHAZADAS', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA RECHAZO", 3500),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"MOTIVO DEVOLUCIÓN", 10000),
                        (u"TOTAL DEPOSITADO", 5000),
                        (u"OBSERVACIÓN", 30000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudDevolucionDinero.objects.filter(status=True, estado=3).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    for solicitud in solicitudes:
                        row_num += 1
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fecha_modificacion, fuentefecha)
                        ws.write(row_num, 2, solicitud.persona.identificacion(), fuentenormal)
                        ws.write(row_num, 3, solicitud.persona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 4, solicitud.persona.email, fuentenormal)
                        ws.write(row_num, 5, solicitud.persona.emailinst, fuentenormal)
                        ws.write(row_num, 6, solicitud.persona.telefono_conv, fuentenormal)
                        ws.write(row_num, 7, solicitud.persona.telefono, fuentenormal)
                        ws.write(row_num, 8, solicitud.persona.get_tipocelular_display() if solicitud.persona.tipocelular else '', fuentenormal)
                        ws.write(row_num, 9, solicitud.motivo.strip(), fuentenormal)
                        ws.write(row_num, 10, solicitud.monto, fuentemoneda)
                        ws.write(row_num, 11, solicitud.observacion.strip(), fuentenormalwrap)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'solicitudespendientesrevisar':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')

                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')

                    fuentenormalwrap = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalwrap.alignment.wrap = True

                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')

                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Solicitudes')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=solicitudes_pendientes_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 10, 'LISTADO DE SOLICITUDES DE DEVOLUCIÓN DE DINERO PENDIENTES DE REVISAR', titulo2)

                    row_num = 4
                    columns = [
                        (u"# SOLICITUD", 3000),
                        (u"FECHA SOLICITUD", 3500),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000),
                        (u"MOTIVO DEVOLUCIÓN", 10000),
                        (u"TOTAL DEPOSITADO", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    solicitudes = SolicitudDevolucionDinero.objects.filter(status=True, estado=1).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')

                    for solicitud in solicitudes:
                        row_num += 1
                        ws.write(row_num, 0, str(solicitud.id).zfill(5), fuentenormalcent)
                        ws.write(row_num, 1, solicitud.fecha_creacion, fuentefecha)
                        ws.write(row_num, 2, solicitud.persona.identificacion(), fuentenormal)
                        ws.write(row_num, 3, solicitud.persona.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 4, solicitud.persona.email, fuentenormal)
                        ws.write(row_num, 5, solicitud.persona.emailinst, fuentenormal)
                        ws.write(row_num, 6, solicitud.persona.telefono_conv, fuentenormal)
                        ws.write(row_num, 7, solicitud.persona.telefono, fuentenormal)
                        ws.write(row_num, 8, solicitud.persona.get_tipocelular_display() if solicitud.persona.tipocelular else '', fuentenormal)
                        ws.write(row_num, 9, solicitud.motivo.strip(), fuentenormal)
                        ws.write(row_num, 10, solicitud.monto, fuentemoneda)

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'beneficiarioscuentaspendientesrevisar':
                try:
                    __author__ = 'Unemi'

                    fuentenormal = easyxtitulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Beneficiarios')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cuentas_pendientes_revisar_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 14, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo2)
                    ws.write_merge(2, 2, 0, 14, 'LISTADO DE BENEFICIARIOS CON CUENTAS PENDIENTES DE REVISAR', titulo2)

                    row_num = 4
                    columns = [
                        (u"NOMBRES COMPLETOS", 10000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"PROVINCIA", 5000),
                        (u"CANTÓN", 5000),
                        (u"PARROQUIA", 5000),
                        (u"DIRECCIÓN", 15000),
                        (u"REFERENCIA", 15000),
                        (u"SECTOR", 15000),
                        (u"# CASA", 5000),
                        (u"CORREO PERSONAL", 8000),
                        (u"CORREO UNEMI", 8000),
                        (u"TELÉFONO", 5000),
                        (u"CELULAR", 5000),
                        (u"OPERADORA", 5000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    beneficiarios = Persona.objects.filter(cuentabancariapersona__status=True,
                                       cuentabancariapersona__archivo__isnull=False,
                                       inscripcion__becasolicitud__periodo_id__in=[110, 90],
                                       inscripcion__becasolicitud__becaasignacion__status=True,
                                       inscripcion__becasolicitud__becaasignacion__tipo=1,
                                       inscripcion__becasolicitud__becaasignacion__cargadocumento=True,
                                       cuentabancariapersona__estadorevision=1).distinct().order_by('apellido1', 'apellido2', 'nombres')

                    for beneficiario in beneficiarios:
                        row_num += 1
                        ws.write(row_num, 0, beneficiario.nombre_completo_inverso(), fuentenormal)
                        ws.write(row_num, 1, beneficiario.identificacion(), fuentenormal)
                        ws.write(row_num, 2, str(beneficiario.provincia) if beneficiario.provincia else '', fuentenormal)
                        ws.write(row_num, 3, str(beneficiario.canton) if beneficiario.canton else '', fuentenormal)
                        ws.write(row_num, 4, str(beneficiario.parroquia) if beneficiario.parroquia else '', fuentenormal)
                        ws.write(row_num, 5, beneficiario.direccion_corta().upper(), fuentenormal)
                        ws.write(row_num, 6, beneficiario.referencia.upper(), fuentenormal)
                        ws.write(row_num, 7, beneficiario.sector.upper(), fuentenormal)
                        ws.write(row_num, 8, beneficiario.num_direccion, fuentenormal)
                        ws.write(row_num, 9, beneficiario.email, fuentenormal)
                        ws.write(row_num, 10, beneficiario.emailinst, fuentenormal)
                        ws.write(row_num, 11, beneficiario.telefono_conv, fuentenormal)
                        ws.write(row_num, 12, beneficiario.telefono, fuentenormal)
                        ws.write(row_num, 13, beneficiario.get_tipocelular_display() if beneficiario.tipocelular else '', fuentenormal)
                        # cuentabeneficiario = beneficiario.cuentabancaria()

                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Gestión Refinanciamiento de Deudas Programas de Posgrado'
            search = None
            ids = None

            if 's' in request.GET:
                search = request.GET['s'].strip()
                ss = search.split(' ')
                if len(ss) == 1:
                    solicitudes = SolicitudRefinanciamientoPosgrado.objects.filter(Q(matricula__inscripcion__persona__nombres__icontains=search)|
                                                     Q(matricula__inscripcion__persona__apellido1__icontains=search)|
                                                     Q(matricula__inscripcion__persona__apellido2__icontains=search)|
                                                     Q(matricula__inscripcion__persona__cedula__icontains=search)|
                                                     Q(matricula__inscripcion__persona__ruc__icontains=search)|
                                                     Q(matricula__inscripcion__persona__pasaporte__icontains=search), status=True).order_by('-id')
                else:
                    solicitudes = SolicitudRefinanciamientoPosgrado.objects.filter(Q(matricula__inscripcion__persona__apellido1__icontains=ss[0]) &
                                                                           Q(matricula__inscripcion__persona__apellido2__icontains=ss[1])
                                                                           ,status=True).order_by('-id')
            elif 'id' in request.GET:
                ids = request.GET['id']
                solicitudes = SolicitudRefinanciamientoPosgrado.objects.filter(id=ids, status=True).order_by('persona__apellido1', 'persona__apellido2', 'persona__nombres')
            else:
                solicitudes = SolicitudRefinanciamientoPosgrado.objects.filter(status=True).order_by('-id')

            estadodocumento = 0
            if 'estadodocumento' in request.GET:
                estadodocumento = int(request.GET['estadodocumento'])
                if estadodocumento > 0:
                    solicitudes = solicitudes.filter(estado__valor=estadodocumento)

            # Si es usuario de epunemi solo pueden ver las solicitues con estado LEGALIZADO
            if es_consulta_epunemi:
                solicitudes = solicitudes.filter(estado__valor=20)

            paging = MiPaginador(solicitudes, 25)
            # paging = MiPaginador(solicitudes, 8)
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
            data['ids'] = ids if ids else ""
            data['solicitudes'] = page.object_list

            if not es_consulta_epunemi:
                data['estados'] = EstadoSolicitud.objects.filter(status=True, opcion_id=1).exclude(valor__in=[10 ,11 ,12]).order_by('valor')
            else:
                data['estados'] = EstadoSolicitud.objects.filter(status=True, opcion_id=1, valor=20)

            data['totalsolicitudes'] = total = solicitudes.count()
            data['totalaprobadas'] = aprobadas = solicitudes.filter(estado=2).count()
            data['totalrechazadas'] = rechazadas = solicitudes.filter(estado=3).count()
            data['totalrevision'] = revision = solicitudes.filter(estado=5).count()
            data['totalpendiente'] = total - (aprobadas + rechazadas + revision)
            data['estadodocumento'] = estadodocumento

            data['esconsultaepunemi'] = es_consulta_epunemi


            data['fechaactual'] = datetime.now().strftime('%d-%m-%Y')
            return render(request, "adm_refinanciamientoposgrado/view.html", data)
