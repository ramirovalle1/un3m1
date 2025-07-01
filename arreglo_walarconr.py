import os
import sys

# solicitudes = BecaSolicitud.objects.filter(becaaceptada=3, status=True, periodo_id=317)
# count = 0
# for solicitud in solicitudes:
#     cuenta = solicitud.inscripcion.persona.cuentabancariapersona_set.filter(status=True, activapago=True, estadorevision__in=[1,2,5])
#     if cuenta:
#         becatipoconfiguracion = solicitud.obtener_configuracionbecatipoperiodo()
#         montobeca = becatipoconfiguracion.becamonto
#         meses = becatipoconfiguracion.becameses
#         montomensual = becatipoconfiguracion.monto_x_mes()
#         if not BecaAsignacion.objects.filter(solicitud=solicitud, activo=True).exists():
#             solicitud.becaaceptada = 2
#             solicitud.save()
#
#             beca = BecaAsignacion(solicitud=solicitud, montomensual=montomensual,
#                                   cantidadmeses=meses, montobeneficio=montobeca,
#                                   fecha=solicitud.fecha_creacion,
#                                   activo=True, grupopago=None,
#                                   tipo=solicitud.tiposolicitud, notificar=True,
#                                   estadobeca=None, infoactualizada=False,
#                                   cargadocumento=True)
#             if solicitud.cumple_todos_documentos_requeridos():
#                 beca.infoactualizada = True
#                 beca.cargadocumento = False
#             beca.save()
#             count += 1
#             print(f"Se ha cambiado el estado de la solicitud de beca a 2: {solicitud.id}, contador: {count}")
#     if count >= 500:
#         break

#PROCESO COMPLETAR BECAS DE ESTUDIANTES
# becatotal = BecaSolicitud.objects.values('inscripcion_id').filter(periodo_id=317, status=True)
# cantidad_limite_becados = BecaPeriodo.objects.get(periodo_id=317, status=True)
# cuentas = CuentaBancariaPersona.objects.values('persona_id').filter(estadorevision__in=[1, 2, 5], activapago=True)
# becaincluir = BecaSolicitud.objects.values('inscripcion_id').filter(status=True, becaaceptada=2,
#                                                                     inscripcion__persona_id__in=(cuentas)).exclude(
#     periodo_id=317)
# cantidad_estudiantes_becados = BecaSolicitud.objects.values('id').filter(status=True, periodo_id=317).exclude(
#     becaaceptada=3).count()
# preinscriones = PreInscripcionBeca.objects.filter(inscripcion_id__in=becaincluir, periodo_id=317).order_by('orden')
# # while cantidad_estudiantes_becados < cantidad_limite_becados.limitebecados:
# print("inicia proceso solicitar beca")
# contingres = 0
# for prei in preinscriones:
#     if cantidad_estudiantes_becados < cantidad_limite_becados.limitebecados:
#         if not BecaSolicitud.objects.filter(status=True, periodo_id=317, periodocalifica_id=153,
#                                             inscripcion=prei.inscripcion).exists():
#             becado = BecaSolicitud(inscripcion=prei.inscripcion,
#                                    becatipo=prei.becatipo,
#                                    periodo_id=317,
#                                    periodocalifica_id=153,
#                                    estado=1,
#                                    tiposolicitud=2,
#                                    observacion=f'SEMESTRE REGULAR {prei.periodo.nombre}')
#             becado.save(usuario_id=1)
#             recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=1).first()
#             prei.seleccionado = True
#             prei.save(usuario_id=1)
#             if recorrido is None:
#                 recorrido = BecaSolicitudRecorrido(solicitud=becado,
#                                                    observacion="SOLICITUD AUTOMÁTICA",
#                                                    estado=1)
#                 recorrido.save(usuario_id=1)
#                 recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=4).first()
#                 # REGISTRO EN ESTADO DE REVISION
#                 if recorrido is None:
#                     becado.estado = 4
#                     becado.save(usuario_id=1)
#                     recorrido = BecaSolicitudRecorrido(solicitud=becado,
#                                                        observacion="EN REVISION",
#                                                        estado=4)
#                     recorrido.save(usuario_id=1)
#                     # log(u'Agrego recorrido de beca: %s' % recorrido, request, "add")
#
#                 recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=2).first()
#                 if recorrido is None:
#                     becado.estado = 2
#                     becado.becaaceptada = 1
#                     becado.save(usuario_id=1)
#                     recorrido = BecaSolicitudRecorrido(solicitud=becado,
#                                                        observacion="PENDIENTE DE ACEPTACIÓN O RECHAZO",
#                                                        estado=2)
#                     recorrido.save(usuario_id=1)
#                     # log(u'Agrego recorrido de beca: %s' % recorrido, request, "add")
#
#                     cantidad_estudiantes_becados = BecaSolicitud.objects.values('id').filter(status=True,
#                                                                                              periodo_id=317).exclude(
#                         becaaceptada=3).count()
#                     contingres += 1
#                     print(contingres, 'registrado', becado)
#     else:
#         break


# ACTUALIZAR IVA AL 15% DE RUBROS
# try:
#     from sagest.models import Rubro
#     list_cedula = ['0904451697', '0925989758', '0916365547', '0920735800', '0914192000', '0915814917']
#     for cedula in list_cedula:
#         rubros = Rubro.objects.filter(persona__cedula=cedula, status=True, cancelado=False, iva_id__in=[2, 3])
#         for rubro in rubros:
#             if not rubro.tiene_pagos() and rubro.iva_id != 4:
#                 rubro.iva_id = 4
#                 rubro.save()
#                 print(f"Rubro {rubro.id} actualizado")
#
# except Exception as e:
#     print(e)


# def generar_reporte_datos_personales():
#     try:
#         from django.db.models import Q, F, Count
#
#         __author__ = 'Unemi'
#         directorio = os.path.join(os.path.join(MEDIA_ROOT, 'reportes', 'reportes_mouse_track'))
#         try:
#             os.stat(directorio)
#         except:
#             os.mkdir(directorio)
#
#         try:
#             nombrearchivo = "reporte_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"
#
#             print("INICIO DE REPORTE")
#             wb = xlsxwriter.Workbook(directorio + '/' + nombrearchivo)
#             ws = wb.add_worksheet("resultados")
#             title = wb.add_format({'font_name': 'Times New Roman', 'color': 'blue', 'bold': True, 'align': 'center'})
#             # Estilo de fuente
#             font_style = wb.add_format({'bold': True})
#             font_style2 = wb.add_format()
#             # ws.merge_range(0, 0, 0, 27, 'LISTADO ACTIVIDADES', title)
#             columns = [
#                 (u"Nro.", 5),  # 0
#                 (u"NOMBRES Y APELLIDOS", 35),  # 1
#                 (u"CEDULA", 15),  # 2
#                 (u"CORREO PERSONAL", 35),  # 3
#                 (u"CORREO INSTITUCIONAL", 35),  # 4
#                 (u"TELEFONO DOMICILIO", 20),  # 5
#                 (u"CELULAR", 20),  # 6
#                 (u"TELÉFONO DE TRABAJO", 20),  # 7
#                 (u"DIRECCIÓN DE DOMICILIO", 60),  # 8
#                 (u"DIRECCIÓN DE TRABAJO", 35),  # 9
#                 (u"FECHA DE NACIMIENTO", 10),  # 10
#             ]
#             row_num = 0
#             print("Columnas creadas")
#             for col_num, (column_name, column_width) in enumerate(columns):
#                 ws.write(row_num, col_num, column_name, font_style)
#                 ws.set_column(col_num, col_num, column_width)
#
#             row_num = 1
#
#             list_cedulas = [
#                 "1707325062",
#                 "0703621953",
#                 "1204683971",
#             ]
#
#             for index, cedula in enumerate(list_cedulas):
#                 if len(cedula) < 10:
#                     cedula = "0" + cedula
#                 persona = Persona.objects.filter(status=True, cedula=cedula).first()
#                 if persona:
#                     dir_trabajo = 'Cdla. universitaria km. 1 1/2 vía km 26' if persona.mis_cargos_vigente() else 'INFORMACIÓN NO ENCONTRADA'
#                     ws.write(row_num, 0, index + 1, font_style2)
#                     ws.write(row_num, 1, persona.nombre_completo_inverso(), font_style2)
#                     ws.write(row_num, 2, persona.cedula, font_style2)
#                     ws.write(row_num, 3, persona.email if persona.email else 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     ws.write(row_num, 4, persona.emailinst if persona.emailinst else 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     ws.write(row_num, 5, persona.telefono_conv if persona.telefono_conv else 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     ws.write(row_num, 6, persona.telefono if persona.telefono else 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     ws.write(row_num, 7, 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     ws.write(row_num, 8, persona.direccion_corta() if persona.direccion_corta() else 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     ws.write(row_num, 9, dir_trabajo, font_style2)
#                     ws.write(row_num, 10, persona.nacimiento.strftime('%d/%m/%Y') if persona.nacimiento else 'INFORMACIÓN NO ENCONTRADA', font_style2)
#                     row_num += 1
#                     print(f"Fila creada: { index + 1}")
#                 else:
#                     print(f"No existe persona con la cedula {cedula}")
#         except Exception as e:
#             print(f"Error en la fila {row_num} {e} - {sys.exc_info()[-1].tb_lineno}")
#             pass
#
#         wb.close()
#         print("FIN DE REPORTE DE ACTIVIDADES MOUSE TRACKING")
#         response = HttpResponse(directorio,
#                                 content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
#         response['Content-Disposition'] = 'attachment; filename=%s' % directorio
#         url_file = "{}/reportes/reportes_mouse_track/{}".format(MEDIA_ROOT, nombrearchivo).replace("\\", "/")
#         print(url_file)
#         print(response['Content-Disposition'])
#         print("FIN")
#
#     except Exception as ex:
#         pass

# activos = ActivoFijo.objects.filter(codigogobierno='31584810')
# 1 = bueno
# 2 = regular
# 4 = obsoleto
# 3 = defectuodo - malo
# 5 = defectuoso

# ESTADO_BAJA = (
#     (1, u"INSERVIBLE"),
#     (2, u"OBSOLETO"),
#     (3, u"NO OBSOLETO"),
#     (4, u'BUENO')
# )

# def actualizacion_estado_activos():
#     try:
#         from django.db import transaction
#
#         activos = ActivoFijo.objects.filter(status=True).order_by('-fechaingreso').distinct()
#         total = activos.count()
#         actualizados = 0
#
#         for index, activo in enumerate(activos):
#             try:
#                 with transaction.atomic():  # Ensure atomic transaction for each activo update
#                     save_historial = False
#
#                     if activo.estado.id == 1:  # bueno
#                         activo.condicionestado = 4
#                         activo.enuso = True
#                     elif activo.estado.id == 2:  # regular
#                         activo.enuso = True
#                     elif activo.estado.id == 3:
#                         historial = HistorialEstadoActivo(
#                             activo=activo,
#                             estado_id=5,
#                             # condicionestado=1,
#                             observacion='Migración de estado',
#                             tiporegistro=4
#                         )
#                         save_historial = True
#                         activo.condicionestado = 1
#                         activo.enuso = False
#                     elif activo.estado.id == 4:
#                         historial = HistorialEstadoActivo(
#                             activo=activo,
#                             estado_id=activo.estado.id,
#                             # condicionestado=1,
#                             observacion='Migración de estado',
#                             tiporegistro=4
#                         )
#                         save_historial = True
#                         activo.estado_id = 3  # Note: use activo.estado_id to avoid FK issues
#                         activo.condicionestado = 1
#                         activo.enuso = False
#
#                     if save_historial:
#                         historial.save()
#
#                     activo.save()
#                     actualizados += 1
#
#                     print(f"{index + 1} de {total} - {activo.codigogobierno}")
#             except Exception as ex:
#                 print(f'Error processing activo {activo.codigogobierno}: {ex} - {sys.exc_info()[-1].tb_lineno}')
#
#         print(f"Total actualizados: {actualizados}")
#     except Exception as ex:
#         print(f'Error: {ex} - {sys.exc_info()[-1].tb_lineno}')
#
#
#
# documentos = DocumentoFirmaInformeBaja.objects.filter(status=True, informe__status=True,
#                                                                       informe__tipoinforme=2, estadofirma=1,
#                                                                       responsablefirma__isnull=False).order_by('-id')
#
# for index,documento in enumerate(documentos):
#     ultimohistorial = HistorialDocumentoInformeBaja.objects.filter(documentoinforme=documento).last()
#     if ultimohistorial:
#         if ultimohistorial.estadofirma == 4:
#             ultimohistorial.persona_id=1
#             ultimohistorial.save()
#             print(f"{index + 1} de {documentos.count()} | {documento.id} actualizado")


def marcar_individual():
    from sagest.models import HistorialJornadaTrabajador, LogMarcada, LogDia
    from sga.models import Persona
    cedula = '0603972456'
    if cedula:
        servidor = Persona.objects.filter(Q(cedula=cedula)|Q(pasaporte=cedula),status=True)
        if servidor:
            servidor = servidor[0]
            hoy = datetime.now()
            fecha = date(2024, 1, 24)
            secuencia = 4
            jornada = HistorialJornadaTrabajador.objects.filter(status=True, persona=servidor,
                                                                fechainicio__lte=hoy,
                                                                fechafin__isnull=True).first()
            if jornada:
                detalles = jornada.jornada.detalle_jornada()
                detalles = detalles.filter(dia=2)
                logdia = LogDia.objects.filter(status=True, fecha=fecha, persona=servidor).first()
                if not logdia:
                    logdia = LogDia(fecha=fecha, persona=servidor, jornada=jornada.jornada)
                    logdia.save()
                marcadas_old = LogMarcada.objects.filter(logdia=logdia)
                marcadas_old.delete()
                for deta in detalles:
                    fin = datetime(fecha.year, fecha.month, fecha.day, deta.horafin.hour, deta.horafin.minute,
                                   deta.horafin.second)
                    inicio = datetime(fecha.year, fecha.month, fecha.day, deta.horainicio.hour,
                                      deta.horainicio.minute, deta.horainicio.second)
                    secuencia += 1
                    marcada_inicio = LogMarcada(status=True, logdia=logdia, time=inicio, secuencia=secuencia, similitud=98.880)
                    marcada_inicio.save()
                    secuencia += 1
                    marcada_fin = LogMarcada(status=True, logdia=logdia, time=fin, secuencia=secuencia, similitud=99.780)
                    marcada_fin.save()
                total = logdia.logmarcada_set.all().count()
                logdia.cantidadmarcadas = total
                logdia.save()
def marcar_individual_unica():
    from sagest.models import HistorialJornadaTrabajador, LogMarcada, LogDia
    from sga.models import Persona
    from datetime import datetime, date, time
    cedula = '0603972456'
    if cedula:
        servidor = Persona.objects.filter(Q(cedula=cedula)|Q(pasaporte=cedula),status=True)
        if servidor:
            servidor = servidor[0]
            hoy = datetime.now()
            secuencia = 1
            fecha = date(2024, 10, 2)
            hora = time(18, 35, 13)
            datetime_obj = fecha_y_hora = datetime.combine(fecha, hora)
            jornada = HistorialJornadaTrabajador.objects.filter(status=True, persona=servidor,
                                                                fechainicio__lte=hoy,
                                                                fechafin__isnull=True).first()
            if jornada:
                logdia = LogDia.objects.filter(status=True, fecha=fecha, persona=servidor).first()
                if not logdia:
                    logdia = LogDia(fecha=fecha, persona=servidor, jornada=jornada.jornada)
                    logdia.save()
                marcada = LogMarcada(status=True, logdia=logdia, time=datetime_obj, secuencia=secuencia, similitud=98.880)
                marcada.save()
                total = logdia.logmarcada_set.all().count()
                logdia.cantidadmarcadas = total
                logdia.save()
def firmar_facturas_masivo():
    import subprocess
    from django.db import transaction
    import os
    from sga.funciones import notificacion as notify
    from sga.models import Persona
    from settings import FORMA_PAGO_EFECTIVO, FORMA_PAGO_TARJETA, FORMA_PAGO_CHEQUE, FORMA_PAGO_DEPOSITO, \
        FORMA_PAGO_TRANSFERENCIA, \
        DESCUENTOS_EN_FACTURAS, FORMA_PAGO_ELECTRONICO, FORMA_PAGO_CUENTA_PORCOBRAR, TIPO_AMBIENTE_FACTURACION, \
        JR_JAVA_COMMAND, JR_RUN_SING_SIGNCLI, PASSSWORD_SIGNCLI, SERVER_URL_SIGNCLI, SERVER_USER_SIGNCLI, \
        SERVER_PASS_SIGNCLI, SITE_STORAGE, REPORTE_PDF_FACTURA_ID, JR_RUN, DATABASES, URL_SERVICIO_ENVIO_SRI_PRUEBAS, \
        URL_SERVICIO_ENVIO_SRI_PRODUCCION, URL_SERVICIO_AUTORIZACION_SRI_PRUEBAS, \
        URL_SERVICIO_AUTORIZACION_SRI_PRODUCCION, \
        DEBUG, SUBREPOTRS_FOLDER, RUBRO_ARANCEL, RUBRO_MATRICULA
    from sagest.models import Factura
    adm1 = Persona.objects.get(id=27762)
    adm2 = Persona.objects.get(id=36111)
    mensaje_notificacion = f'Proceso de facturación: '
    try:
        facturas = Factura.objects.filter(Q(autorizada=False) | Q(enviadacliente=False), valida=True, xmlgenerado=True,
                                          firmada=False, enviadasri=False, autorizada=False,
                                          enviadacliente=False).distinct()
        count = facturas.count()
        adm1 = Persona.objects.get(id=27762)
        adm2 = Persona.objects.get(id=36111)
        mensaje = f'# Facturas: {count}'
        titulo = 'Proceso de facturación'

        notify(titulo, mensaje, adm1, None, '/notificacion', adm1.pk, 1, 'sga-sagest', Factura, None)
        notify(titulo, mensaje, adm2, None, '/notificacion', adm2.pk, 1, 'sga-sagest', Factura, None)
        for factura in facturas:
            token = miinstitucion().token
            if not token:
                notify('No hay token', '', adm2, None,
                       f'', adm2.id, 2, 'sga-sagest',
                       Persona, None)

            runjrcommand = [JR_JAVA_COMMAND, '-jar',
                            os.path.join(JR_RUN_SING_SIGNCLI, 'SignCLI.jar'),
                            token.file.name,
                            PASSSWORD_SIGNCLI,
                            SERVER_URL_SIGNCLI + "/sign_factura/" + factura.weburl]
            if SERVER_USER_SIGNCLI and SERVER_PASS_SIGNCLI:
                runjrcommand.append(SERVER_USER_SIGNCLI)
                runjrcommand.append(SERVER_PASS_SIGNCLI)
            runjr = subprocess.call(runjrcommand)
            mensaje_notificacion += ' | ' + str(runjr)
        notify('Finalizado con éxito', f'{mensaje_notificacion}', adm2, None,
               f'', adm2.id, 2, 'sga-sagest',
               Persona, None)
    except Exception as ex:
        # transaction.set_rollback(True)
        mensaje = 'Error ({}) al firmar en la linea: {}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
        notify('Error en firmar', mensaje, adm2, None,
               f'', adm2.id, 2, 'sga-sagest',
               Persona, None)






