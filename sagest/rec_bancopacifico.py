# coding=utf-8
import base64
import os
import collections
import sys
from datetime import datetime, date, timedelta

import openpyxl
import xlrd
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt

from decorators import last_access, secure_module
from sagest.commonviews import anio_ejercicio
from sagest.funciones import reajuste_rubro_matriculacion
from sagest.models import RecaudacionBanco, CuentaBanco, Rubro, ArchivoGeneradoRecaudacionBanco, TipoOtroRubro, \
    AnioEjercicio, PartidasSaldo, Pago, ArchivoCuentaBancoRubroDetalle, ArchivoCuentaBancoVerificadoDetalle, \
    DetallePagoArchivoCuentaBanco, Factura, SecuencialRecaudaciones
from sagest.rec_finanzas import pagaryfacturar, pagaryemitirrecibocajamatriculas1718diciembre
from settings import FORMA_PAGO_DEPOSITO, BANCO_PACIFICO_ID, COMISION_BANCO_PACIFICO, TIPOS_RUBROS_BANCO, \
    COMISION_BANCO_RUBRO_ID, \
    COBRA_COMISION_BANCO, SITE_STORAGE, DEBUG, RUBRO_ARANCEL, RUBRO_MATRICULA, RUBRO_SOLICITUD_SECRETARIA_ID
from sga.commonviews import adduserdata
from sga.forms import ArchivoBancaonlineForm, ArchivoBancaonlineVerificadoForm
from sga.funciones import convertir_fecha, convertir_fecha_invertida, log, bad_json, ok_json, generar_nombre, \
    remover_caracteres_especiales_unicode, null_to_decimal, variable_valor
from sga.models import MESES_CHOICES, Persona, Periodo, Carrera
from moodle import moodle
unicode = str


def fecha_importacion(fecha):
    return date(int(fecha[4:8]), int(fecha[2:4]), int(fecha[:2]))

def pagaryfacturarexcel(request, idrubro, valorpagado, caja):
    rub = Rubro.objects.get(pk=idrubro)
@csrf_exempt
@login_required(redirect_field_name='ret', login_url='/login')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']

    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'pagar':
                try:
                    with transaction.atomic():
                        idsrubros = request.POST['pagos'].split(",")
                        cab = ArchivoCuentaBancoVerificadoDetalle.objects.get(pk=int(request.POST['id']))
                        rubros = Rubro.objects.filter(id__in=idsrubros)
                        totalafacturar = 0
                        valor=cab.saldofinal
                        for r in rubros:
                            totalafacturar += r.saldo
                        if totalafacturar >= valor:
                            cab.saldofinal = 0
                        else:
                            cab.saldofinal= cab.saldofinal - totalafacturar
                            valor = totalafacturar
                        cab.save()

                        caja = persona.caja()
                        sesioncaja = caja.sesion_caja()
                        cuenta = cab.cab.cuentabanco
                        fechadep = "{}-{}-{}".format(str(cab.fechamov).split('-')[2],str(cab.fechamov).split('-')[1],str(cab.fechamov).split('-')[0])
                        #fechadep = "{}-{}-{}".format(str(datetime.today().date()).split('-')[2],str(datetime.today().date()).split('-')[1],str(datetime.today().date()).split('-')[0])
                        pagos = [{'tipo': FORMA_PAGO_DEPOSITO, 'valor': valor,
                                  'fechadep': fechadep,
                                  'referenciadep': cab.referenciadep,
                                  'cuentadep': cuenta.id}, ]

                        rubros = [{'rubro': x.id} for x in
                                  Rubro.objects.filter(persona=cab.persona, cancelado=False, id__in=idsrubros,
                                                       status=True).order_by('fechavence')]
                        result = pagaryfacturar(request, caja,
                                                extra={'pagos': pagos, 'rubros': rubros, 'id': cab.persona.id})
                        if dict(result)['result'] != 'ok':
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "ERROR AL FACTURAR INTENTELO MÁS TARDE"},
                                                safe=False)

                        if cab.saldofinal==0:
                            cab.pagado = True
                            cab.valido = True

                        factura = Factura.objects.get(id=result['id'])
                        for pagof in factura.pagos.all():
                            detallepago = DetallePagoArchivoCuentaBanco(pagobanco=cab, pago=pagof,
                                                                        valor=pagof.valortotal)
                            detallepago.save(request)
                        cab.save(request,update_fields=['saldofinal','pagado','valido'])

                        return JsonResponse({"result": "ok"})
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al procesar pago."})

            if action == 'subir':
                try:
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile.size > 41943040:
                            raise NameError(u"Tamaño de archivo Maximo permitido es de 40Mb")

                    if not persona.puede_recibir_pagos() or not persona.ultima_sesioncaja():
                        raise NameError(u"No existe una sesion de caja abierta.")

                    if not PartidasSaldo.objects.values('id').filter(anioejercicio__anioejercicio=anio, status=True).exists():
                        raise NameError("No existen Registros de saldos de Partidas para el año %s." % (str(anio)))

                    caja = persona.caja()
                    sesioncaja = caja.sesion_caja()
                    fecha = convertir_fecha(request.POST['fecha'])
                    cuenta = CuentaBanco.objects.get(pk=int(request.POST['cuenta']))
                    f = ArchivoBancaonlineForm(request.POST, request.FILES)
                    if not f.is_valid():
                        raise NameError('Formulario no valido')
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = ArchivoGeneradoRecaudacionBanco(fecha=datetime.now().date(),
                                                              archivo=nfile,
                                                              cuentabanco=cuenta)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)

                    # Inicio: Verificar si existe el rubro, si esta pagado, si existe persona, rubro repetido
                    cedula_no_existe = []
                    rubro_no_existe = []
                    rubro_pagado = []
                    rubro_repetido = []
                    rubro_sin_partida = []
                    rubros = []

                    linea = 1
                    for rowx in range(sheet.nrows):
                        cols = sheet.row_values(rowx)
                        if linea >= 2:
                            identificacion = cols[32].strip().upper()
                            id_rubro = cols[4][6:]
                            rubros.append(id_rubro)
                            if not Persona.objects.values("id").filter(Q(cedula=identificacion) | Q(pasaporte=identificacion) | Q(ruc=identificacion), status=True).exists():
                                cedula_no_existe.append(identificacion)
                            if not Rubro.objects.values("id").filter(pk=int(id_rubro)).exists():
                                rubro_no_existe.append(id_rubro)
                            elif Rubro.objects.values("id").filter(pk=int(id_rubro), cancelado=True).exists():
                                rubro_pagado.append(id_rubro)
                            else:
                                rubro_banco = Rubro.objects.get(pk=id_rubro)
                                if not rubro_banco.tipo.partida_saldo(anio):
                                    rubro_sin_partida.append(id_rubro)

                        linea += 1

                    rubro_repetido = [x for x, y in collections.Counter(rubros).items() if y > 1]

                    if cedula_no_existe:
                        raise NameError(u"Las siguientes identificaciones no existen: %s." % cedula_no_existe)

                    if rubro_no_existe:
                        raise NameError(u"Los siguientes rubros no existen: %s." % rubro_no_existe)

                    if rubro_sin_partida:
                        raise NameError(u"Los siguientes rubros no tienen saldo de partida asociado: %s." % rubro_sin_partida)

                    if rubro_pagado:
                        raise NameError(u"Los siguientes rubros ya constan como pagados: %s." % rubro_pagado)

                    if rubro_repetido:
                        raise NameError(u"Los siguientes rubros están repetidos: %s." % rubro_repetido)

                    # Fin: Verificar si existe el rubro, si esta pagado, si existe persona, rubro repetido

                    linea = 1
                    valorrecaudado = 0
                    for rowx in range(sheet.nrows):
                        cols = sheet.row_values(rowx)
                        if linea >= 2:
                            identificacion = cols[32].strip().upper()
                            if fecha == xlrd.xldate.xldate_as_datetime(cols[6], workbook.datemode).date():
                                id_rubro = cols[4][6:]
                                if not Persona.objects.values("id").filter(Q(cedula=identificacion) | Q(pasaporte=identificacion) | Q(ruc=identificacion), status=True).exists():
                                    raise NameError(u"No existe una persona con esta identificación: %s." % identificacion)
                                persona = Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion) | Q(ruc=identificacion), status=True).distinct()[0]
                                valor = Decimal(cols[3]).quantize(Decimal('.01'))
                                if not Rubro.objects.values("id").filter(pk=int(id_rubro)):
                                    raise NameError(u"Rubro %s esta eliminado." % cols[4])
                                rubro = Rubro.objects.get(pk=int(id_rubro))

                                rubrorelacionadoid = None
                                if Rubro.objects.values('id').filter(relacionados_id=rubro.id,status=True).exists():
                                    rubrorelacionadoid = Rubro.objects.get(relacionados_id=rubro.id).id

                                # if not rubro.status:
                                #     raise NameError(u"Rubro %s esta anulado." % cols[4])
                                if COBRA_COMISION_BANCO:
                                    if not valor - Decimal(COMISION_BANCO_PACIFICO) == rubro.saldo:
                                        raise NameError(u"No coincide con el valor pendiente de pago. %s" % id_rubro)
                                    rubrocomision = Rubro(persona=persona,
                                                          nombre='COMISION BANCO',
                                                          fecha=datetime.now().date(),
                                                          tipo_id=COMISION_BANCO_RUBRO_ID,
                                                          fechavence=datetime.now().date(),
                                                          valor=Decimal(COMISION_BANCO_PACIFICO),
                                                          iva_id=1,
                                                          valortotal=Decimal(COMISION_BANCO_PACIFICO),
                                                          saldo=Decimal(COMISION_BANCO_PACIFICO))
                                    rubrocomision.save(request)
                                    pagos = [{'tipo': FORMA_PAGO_DEPOSITO,
                                              'comision': Decimal(COMISION_BANCO_PACIFICO), 'valor': valor,
                                              'fechadep': fecha.strftime('%d-%m-%Y'),
                                              'referenciadep': str(cols[23]), 'cuentadep': cuenta.id}, ]
                                    rubros = [{'rubro': x.id} for x in
                                              Rubro.objects.filter(persona=persona, cancelado=False,
                                                                   id__in=[rubro.id, rubrocomision.id],
                                                                   status=True).order_by('fechavence')]
                                    result = pagaryfacturar(request, caja,
                                                            extra={'pagos': pagos, 'rubros': rubros,
                                                                   'id': persona.id})
                                else:
                                    # QUITAR ESTA VALIDACION
                                    # if not valor == rubro.saldo:
                                    #     transaction.set_rollback(True)
                                    #     return JsonResponse({"result": "bad", "mensaje": u"No coincide con el valor pendiente de pago. %s" % cols[4]})
                                    # QUITAR ESTA VALIDACION
                                    pagos = [{'tipo': FORMA_PAGO_DEPOSITO, 'valor': valor,
                                              'fechadep': fecha.strftime('%d-%m-%Y'),
                                              'referenciadep': str(cols[23]), 'cuentadep': cuenta.id}, ]

                                    rubros = [{'rubro': x.id} for x in Rubro.objects.filter(persona=persona, cancelado=False, id__in=[rubro.id, rubrorelacionadoid], status=True).order_by('fechavence')]

                                    result = pagaryfacturar(request, caja,
                                                            extra={'pagos': pagos, 'rubros': rubros,
                                                                   'id': persona.id})
                                    # result = pagaryemitirrecibocajamatriculas1718diciembre(request, caja, extra={'pagos': pagos, 'rubros': rubros, 'id': persona.id})
                                matricula = rubro.matricula
                                #aqui el proceso con la variable global

                                BANCO_ACTUALIZA_MATRICULA = variable_valor('BANCO_ACTUALIZA_MATRICULA')

                                if BANCO_ACTUALIZA_MATRICULA:
                                    if matricula:
                                        matricula.actualiza_matricula()
                                        if matricula.inscripcion.coordinacion_id == 9:
                                            tipourl = 2
                                        else:
                                            tipourl = 1
                                        # for materiaasignada in matricula.mis_materias_sin_retiro():
                                        #     materiaasignada.materia.crear_actualizar_un_estudiante_curso(moodle,tipourl,matricula)
                                        if matricula.inscripcion.coordinacion_id == 7:
                                            if matricula.bloqueo_matricula_pago():
                                                matricula.bloqueomatricula = True
                                                log(u'%s: %s' % (u'Bloquear matricula Subida Archivo', matricula), request, "edit")

                                valorrecaudado += valor
                        linea += 1
                    if valorrecaudado:
                        recaudacion = RecaudacionBanco(sesioncaja=sesioncaja,
                                                       fecha=fecha,
                                                       cuentabanco=cuenta,
                                                       valor=valorrecaudado)
                        recaudacion.save(request)
                    log(u'Subio archivo generado en recaudacion en banco: %s [%s] - recaudacion en banco: %s [valor: %s]' % (archivo, archivo.id, RecaudacionBanco, valorrecaudado), request, "add")
                    return ok_json()
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

            if action == 'generar':
                try:
                    # if not DEBUG:
                    #     raise NameError(u"Módulo en mantenimiento")
                    fechai = convertir_fecha(request.POST['fechai'])
                    fechaf = convertir_fecha(request.POST['fechaf'])
                    tipo_id = int(request.POST['rubro']) if 'rubro' in request.POST and int(request.POST['rubro']) else None
                    if tipo_id is None:
                        raise NameError(u"Ocurrio un error, tipo de rubro no encontrado")
                    cuenta = CuentaBanco.objects.get(pk=int(request.POST['id']))

                    ## DEBE SER GENERADO EN UN CRON PROCESO MUY PESADO
                    # result, error = reajuste_rubro_matriculacion(fechai, fechaf, tipo_id)
                    #                     # if not result:
                    #                     #     raise NameError(error)

                    eRubros = Rubro.objects.filter(epunemi=False, cancelado=False, saldo__gt=0, fecha__gte=fechai, fecha__lte=fechaf, status=True).exclude(pago__pagoliquidacion__status=True).distinct().order_by('fecha')
                    if tipo_id in [RUBRO_ARANCEL, RUBRO_MATRICULA]:
                        eRubros_1 = eRubros.filter(tipo__id=RUBRO_ARANCEL).order_by('fecha')
                        eRubros_2 = eRubros.filter(tipo__id=RUBRO_MATRICULA).order_by('fecha')
                        eRubros = eRubros_1 | eRubros_2
                    else:
                        eRubros = eRubros.filter(tipo__id=tipo_id).order_by('fecha')
                        #cambio de estado solicitud de certificado.
                        for rubro in eRubros:
                            if rubro.solicitud:
                                solicitud = rubro.solicitud
                                solicitud.verificar_proceso(persona)

                    def escribirlinea(eRubro):
                        tipoarchivo = '1'
                        transaccion = 'OCP'
                        codigoservicio = 'OC'
                        tipocuenta = '  '
                        numerocuenta = '          '
                        if COBRA_COMISION_BANCO:
                            valorconvertido = (('%s' % Decimal(eRubro.valor_total_cobrar_intermatico() + Decimal(COMISION_BANCO_PACIFICO)).quantize(Decimal('.01'))).replace(',', '').replace('.', '')).zfill(13)
                        else:
                            valorconvertido = (('%s' % Decimal(eRubro.valor_total_cobrar_intermatico()).quantize(Decimal('.01'))).replace(',', '').replace('.', '')).zfill(13)
                        anio_mes = eRubro.anio_mes()
                        identificacionrubro = str(anio_mes).ljust(15)[:15]
                        rubronombre = eRubro.nombre.ljust(20)[:20]
                        formapago = 'RE'
                        moneda = 'USD'
                        tercero = remover_caracteres_especiales_unicode(eRubro.persona.nombre_completo().ljust(30)[:30])
                        noutilizado = '    '
                        tipoidentificacion = eRubro.persona.tipo_identificacion()
                        identificacion = eRubro.persona.identificacion().ljust(14)[:14]
                        noutilizado2 = ''.ljust(83)[:83]
                        valoriva = (('%.2f' % eRubro.valoriva).replace(',', '').replace('.', '')).zfill(9)
                        presentacion = 'S'
                        dataln = tipoarchivo + transaccion + codigoservicio + tipocuenta + numerocuenta + valorconvertido + identificacionrubro + rubronombre + formapago + moneda + tercero + noutilizado + tipoidentificacion + identificacion + noutilizado2 + valoriva + presentacion + '\r\n'
                        dataln = dataln.encode("latin-1")
                        f.write(dataln)
                    contador_rubro = 0
                    suma_rubros = 0
                    contadorinicial = eRubros.count()
                    banderacierre=False

                    for eRubro in eRubros:
                        generarrubro = True
                        contadorinicial -= 1
                        if contador_rubro==0:
                            banderacierre = False
                            direccion = os.path.join(SITE_STORAGE, 'media', 'recaudaciones', 'bancopacifico')
                            archivoname = generar_nombre('Deuda_Generada', 'fichero.txt')
                            filename = os.path.join(direccion, archivoname)
                            # filename = 'E:/svn/academico/media/recaudaciones/bancopacifico/Deuda_Generada20191113111631.txt'
                            f = open(filename, "wb")
                            d = datetime.now()
                        # with open(filename, 'wb') as fichero:
                        if eRubro.matricula:
                            if eRubro.matricula.termino==False and (eRubro.matricula.automatriculapregrado or eRubro.matricula.automatriculaadmision):
                                generarrubro = False
                        if generarrubro:
                            escribirlinea(eRubro)
                            contador_rubro += 1
                            valor = null_to_decimal(eRubro.valor_total_cobrar_intermatico(), 2)
                            if COBRA_COMISION_BANCO:
                                valor = null_to_decimal((valor + null_to_decimal(COMISION_BANCO_PACIFICO, 2)), 2)
                            suma_rubros = null_to_decimal((null_to_decimal(suma_rubros, 2) + null_to_decimal(valor, 2)), 2)

                            # Actualizo campo archivogenerado para que ya no puedan editarlo ni eliminarlo en otros procesos
                            ## cambie el update solo por el campo requerido y no por todos los capos
                            Rubro.objects.filter(pk=eRubro.id).update(archivogenerado=True)
                            # Actualizo el rubro relacionado
                            try:
                                if eRubro.relacionados:
                                    ## cambie el update solo por el campo requerido y no por todos los capos
                                    Rubro.objects.filter(pk=eRubro.relacionados.id).update(archivogenerado=True)
                            except Exception as ex:
                                pass
                            if contador_rubro >10000 or contadorinicial<=0:
                                banderacierre = True
                                contador_rubro = 0
                                f.close()
                                archivo = ArchivoGeneradoRecaudacionBanco(fecha=datetime.now(),
                                                                          cuentabanco=cuenta)
                                archivo.save(request)
                                archivo.archivo.name = 'recaudaciones/bancopacifico/%s' % archivoname
                                archivo.save(request)
                                log(u'Generado archivo recaudacion en banco: %s [%s] - archivo: %s' % (archivo, archivo.id, archivo.archivo.name), request, "add")
                    if not banderacierre:
                        f.close()
                        archivo = ArchivoGeneradoRecaudacionBanco(fecha=datetime.now(),
                                                                  cuentabanco=cuenta)
                        archivo.save(request)
                        archivo.archivo.name = 'recaudaciones/bancopacifico/%s' % archivoname
                        archivo.save(request)
                        log(u'Generado archivo recaudacion en banco: %s [%s] - archivo: %s' % (
                        archivo, archivo.id, archivo.archivo.name), request, "add")

                    return JsonResponse({"result": "ok", "valor": suma_rubros})
                except Exception as ex:
                    import sys
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar los datos. %s  - %s" % (ex,format(sys.exc_info()[-1].tb_lineno))})

            if action == 'periodo_carrera':
                try:
                    periodo = Periodo.objects.get(pk=int(request.POST['id']))
                    lista = []
                    for carrera in Carrera.objects.filter(inscripcion__matricula__nivel__periodo=periodo).distinct():
                        if [carrera.id, carrera.nombre] not in lista:
                            lista.append([carrera.id, carrera.nombre])
                    return JsonResponse({"result": "ok", "lista": lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'verificar':
                index_row = 1
                try:
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        if newfile.size > 41943040:
                            raise NameError(u"Tamaño de archivo Maximo permitido es de 40Mb")

                    if not persona.puede_recibir_pagos() or not persona.ultima_sesioncaja():
                        raise NameError("No existe una sesion de caja abierta.")

                    if not PartidasSaldo.objects.values('id').filter(anioejercicio__anioejercicio=anio, status=True).exists():
                        raise NameError("No existen Registros de saldos de Partidas para el año %s." % (str(anio)))
                    filtro = CuentaBanco.objects.get(pk=request.POST['id'])
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("verificacion_", nfile._name)
                    caja = persona.caja()
                    sesioncaja = caja.sesion_caja()
                    cuenta = CuentaBanco.objects.get(pk=int(request.POST['id']))
                    fecha = convertir_fecha(request.POST['fecha'])

                    cab = RecaudacionBanco(sesioncaja=sesioncaja,
                                           fecha=fecha,
                                           archivo=nfile,
                                           cuentabanco=filtro)
                    cab.save(request)
                    # Inicio: Verificar si existe el rubro, si esta pagado, si existe persona, rubro repetido
                    cedula_no_existe = []
                    rubro_no_existe = []
                    totalrecaudado = 0
                    rubro_pagado = []
                    result = None
                    rubro_repetido = []
                    rubro_sin_partida = []
                    rubroslistaexcel = []
                    rubro_valido = []
                    rubvalidos = 0
                    excel = request.FILES['archivo']
                    wb = openpyxl.load_workbook(excel)
                    worksheet = wb.worksheets[0]
                    linea = 1
                    for row in worksheet.iter_rows():
                        cols = [cell.value for cell in row]
                        if linea >= 2:
                            # print(cols)
                            banderarepetido = False
                            if cols[32]:
                                identificacion = cols[32].replace('"', '').replace('=', '').strip().upper()
                                id_rubro = int(cols[4].replace('"', '').replace('=', '')[6:])
                                rubroslistaexcel.append(id_rubro)
                                forma = cols[2] if cols[2] != 'None' else ''
                                valor = Decimal(cols[3]) if cols[3] != 'None' else ''
                                codtercero = cols[4].replace('"', '').replace('=', '') if cols[4] != 'None' else ''
                                if  type(cols[6]) == str:
                                    fechamov = convertir_fecha(str(cols[6]).split(" ")[0])
                                else:
                                    fechamov = cols[6].date()
                                banco = cols[7] if cols[7] != 'None' else ''
                                tipocta = cols[11] if cols[11] != 'None' else ''
                                numcta = cols[12] if cols[12] != 'None' else ''
                                if type(cols[13]) == str:
                                    fchainipago = convertir_fecha(str(cols[13]).split(" ")[0])
                                else:
                                    fchainipago = cols[13].date()
                                referenciadep = str(cols[23])
                                localidad = cols[14] if cols[14] != 'None' else ''
                                ordenemp = cols[17] if cols[17] != 'None' else ''
                                nucadquiriente = cols[32].replace('"', '').replace('=', '') if cols[32] != 'None' else ''
                                if type(cols[33]) == str:
                                    fechavcto = convertir_fecha(str(cols[33]).split(" ")[0])
                                else:
                                    fechavcto = cols[33].date()
                                canal = cols[46] if cols[46] != 'None' else ''
                                persona = None
                                rubadd = None
                                saldoinicial = 0
                                valortotal = 0
                                totalrecaudado += valor
                                if fechamov > cab.fecha:
                                    raise NameError("EL ARCHIVO CONTIENE FECHAS QUE NO PERTENECEN A LA CARGA")
                                if not Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion) | Q(ruc=identificacion), status=True).exists():
                                    cedula_no_existe.append(identificacion)
                                    raise NameError("PERSONA {} NO EXISTE.".format(identificacion))
                                else:
                                    persona = Persona.objects.filter(Q(cedula=identificacion) | Q(pasaporte=identificacion) | Q(ruc=identificacion), status=True)[0]

                                if ArchivoCuentaBancoVerificadoDetalle.objects.filter(cab=cab, rubro_id=int(id_rubro)).exists():
                                    banderarepetido = True

                                detarc = ArchivoCuentaBancoVerificadoDetalle(cab=cab,
                                                                             persona=persona,
                                                                             forma=forma,
                                                                             valor=Decimal(valor),
                                                                             saldofinal=Decimal(valor),
                                                                             codtercero=codtercero,
                                                                             fechamov=fechamov,
                                                                             banco=banco,
                                                                             referenciadep=referenciadep,
                                                                             tipocuenta=tipocta,
                                                                             numcta=numcta,
                                                                             fechainipago=fchainipago,
                                                                             localidad=localidad,
                                                                             ordenemp=ordenemp,
                                                                             nucadquiriente=nucadquiriente,
                                                                             fechavcto=fechavcto,
                                                                             canal=canal,
                                                                             valido=False)
                                if not Rubro.objects.values("id").filter(pk=int(id_rubro), persona=persona).exists() or banderarepetido:
                                    rubro_no_existe.append(id_rubro)
                                    # RUBRONOEXISTE
                                    detarc.rubroidstr = id_rubro
                                    detarc.valido = False
                                    detarc.observacion="RUBRO NO EXISTE"
                                    detarc.save(request)
                                    cab.incorrecto = True
                                    cab.save()
                                else:
                                    rubvalidos += 1
                                    rubroget = Rubro.objects.get(pk=int(id_rubro), persona=persona)
                                    banderapago = True
                                    if rubroget.cancelado:
                                        detarc.observacion = "RUBRO YA FUE FACTURADO ANTERIORMENTE {}.".format(id_rubro)
                                        detarc.pagado = False
                                        detarc.save(request)
                                        banderapago = False
                                        cab.incorrecto = True
                                        cab.save()

                                    if not rubroget.tipo.partida_saldo(anio):
                                        raise NameError("RUBRO NO CUENTA CON PARTIDA {}.".format(id_rubro))
                                    else:
                                        if banderapago:
                                            detarc.rubro = rubroget
                                            saldoinicial = Decimal(rubroget.total_adeudado())
                                            valortotal = saldoinicial
                                            detarc.saldoinicial = saldoinicial
                                            detarc.valido = True
                                            detarc.save(request)
                                            detarc.total = valortotal
                                            detarc.save(request)
                                            if round(valor, 2) <= round(detarc.total, 2):
                                                rubro = rubroget
                                                listrubrosid = [rubro.pk]
                                                rubrorelacionadoid = None
                                                # for rub in Rubro.objects.filter(relacionados_id=rubro.id):
                                                #     listrubrosid.append(rub.id)
                                                if rubro.status:
                                                    if COBRA_COMISION_BANCO:
                                                        if not valor - Decimal(COMISION_BANCO_PACIFICO) == rubro.saldo:
                                                            raise NameError(u"No coincide con el valor pendiente de pago. %s" % id_rubro)
                                                        rubrocomision = Rubro(persona=persona,
                                                                              nombre='COMISION BANCO',
                                                                              fecha=datetime.now().date(),
                                                                              tipo_id=COMISION_BANCO_RUBRO_ID,
                                                                              fechavence=datetime.now().date(),
                                                                              valor=Decimal(COMISION_BANCO_PACIFICO),
                                                                              iva_id=1,
                                                                              valortotal=Decimal(COMISION_BANCO_PACIFICO),
                                                                              saldo=Decimal(COMISION_BANCO_PACIFICO))
                                                        rubrocomision.save(request)
                                                        pagos = [{'tipo': FORMA_PAGO_DEPOSITO,
                                                                  'comision': Decimal(COMISION_BANCO_PACIFICO),
                                                                  'valor': valor,
                                                                  'fechadep': fecha.strftime('%d-%m-%Y'),
                                                                  'referenciadep': str(cols[23]),
                                                                  'cuentadep': cuenta.id}, ]
                                                        rubros = [{'rubro': x.id} for x in Rubro.objects.filter(persona=persona, cancelado=False, id__in=listrubrosid, status=True).order_by('fechavence')]
                                                        result = pagaryfacturar(request, caja, extra={'pagos': pagos, 'rubros': rubros, 'id': persona.id})

                                                    else:
                                                        pagos = [{'tipo': FORMA_PAGO_DEPOSITO, 'valor': valor,
                                                                  'fechadep': fecha.strftime('%d-%m-%Y'),
                                                                  'referenciadep': str(cols[23]),
                                                                  'cuentadep': cuenta.id}, ]

                                                        rubros = [{'rubro': x.id} for x in Rubro.objects.filter(persona=persona, cancelado=False, id__in=listrubrosid, status=True).order_by('fechavence')]
                                                        result = pagaryfacturar(request, caja, extra={'pagos': pagos, 'rubros': rubros, 'id': persona.id, 'fecha_verificacion': datetime.now()})
                                                    if dict(result)['result'] != 'ok':
                                                        raise NameError(u"Errores en la facturación")
                                                    detarc.pagado = True
                                                    factura = Factura.objects.get(id=result['id'])
                                                    for pagof in factura.pagos.all():
                                                        detallepago = DetallePagoArchivoCuentaBanco(pagobanco=detarc,pago=pagof,valor=pagof.valortotal)
                                                        detallepago.save(request)
                                                        detarc.saldofinal=detarc.saldofinal-pagof.valortotal
                                                    detarc.save()
                                                    matricula = rubro.matricula
                                                    BANCO_ACTUALIZA_MATRICULA = variable_valor('BANCO_ACTUALIZA_MATRICULA')
                                                    if BANCO_ACTUALIZA_MATRICULA:
                                                        if matricula:
                                                            matricula.actualiza_matricula()
                                                            # if matricula.inscripcion.coordinacion_id == 9:
                                                            #     tipourl = 2
                                                            # else:
                                                            #     tipourl = 1
                                                            # for materiaasignada in matricula.mis_materias_sin_retiro():
                                                            #     materiaasignada.materia.crear_actualizar_un_estudiante_curso(moodle,tipourl,matricula)
                                                            # if matricula.bloqueo_matricula_pago():
                                                            #     matricula.bloqueomatricula = True
                                                            #     log(u'%s: %s' % (u'Bloquear matricula Subida Archivo', matricula), request, "edit")
                                                else:
                                                    detarc.observacion = "RUBRO NO EXISTE {}.".format(
                                                        id_rubro)
                                                    detarc.pagado = False
                                                    detarc.save(request)
                                                    banderapago = False
                                                    cab.incorrecto = True
                                                    cab.save()
                                            else:
                                                detarc.observacion = 'SE SALTO VALIDACIÓN DE TOTAL {} {}'.format(valor, detarc.total)
                                                cab.incorrecto = True
                                                cab.save()
                                                detarc.save(request)
                        linea += 1
                        index_row += 1
                    cab.valor = totalrecaudado
                    cab.save(request)

                    #ACTUALIZA EL SECUENCIAL DE FACTURA EN SECUENCIA DE RECAUDACIÓN
                    qsbasesecuencial = SecuencialRecaudaciones.objects.filter(puntoventa=caja.puntoventa).first()
                    ultima_factura = Factura.objects.filter(status=True).order_by('numero').last()
                    qsbasesecuencial.factura = ultima_factura.numero
                    qsbasesecuencial.save(request)
                    # rubro_repetido = [x for x, y in collections.Counter(rubroslistaexcel).items() if y > 1]
                    # if rubro_repetido.__len__() > 0:
                    #     transaction.set_rollback(True)
                    #     return JsonResponse({"result": True, "mensaje": "EXISTEN RUBROS REPETIDOS VERIFIQUE EL ARCHIVO DE EXCEL {}".format(rubro_repetido)}, safe=False)
                    return JsonResponse({"result": False, "to": request.path}, safe=False)
                except Exception as ex:
                    import sys
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": f"Ocurrio un error: {ex.__str__()} / Linea: {sys.exc_info()[-1].tb_lineno} - row: {index_row}"}, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Manejo de pagos del sevicio de ventanilla Banco Pacífico'
        fecha = datetime.now().date()
        panio = fecha.year
        pmes = fecha.month

        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'subir':
                try:
                    data['title'] = u'Subir archivo de pagos'
                    data['fecha'] = request.GET['f']
                    data['form'] = ArchivoBancaonlineForm()
                    data['cuenta'] = CuentaBanco.objects.get(pk=int(request.GET['cuenta']))
                    return render(request, "rec_bancopacifico/subir.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'procesar':
                try:
                    data['title'] = u'Procesar Pagos'
                    data['fecha'] = fechasubida = convertir_fecha(request.GET['f'])
                    data['cuenta'] = cuentabanco = CuentaBanco.objects.get(pk=int(request.GET['cuenta']))
                    data['cab'] = cab = RecaudacionBanco.objects.filter(cuentabanco=cuentabanco, fecha=fechasubida)[0]
                    det = ArchivoCuentaBancoVerificadoDetalle.objects.filter(cab=cab).order_by('rubroidstr')
                    data['totalcount'] = det.count()
                    data['totalpagados'] = det.filter(pagado=True).count()
                    data['totalconnovedad'] = det.filter(pagado=False).count()
                    data['totalsobrante'] = det.filter(pagado=False).aggregate(suma=Sum('saldofinal'))
                    data['det'] = det.filter(pagado=False)
                    return render(request, "rec_bancopacifico/procesados.html", data)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            if action == 'verificar':
                try:
                    data['title'] = u'Verificar Archivo'
                    data['fecha'] = request.GET['add']
                    data['id'] = id = request.GET['id']
                    data['cuenta'] = CuentaBanco.objects.get(pk=int(request.GET['id']))
                    data['form2'] = ArchivoBancaonlineVerificadoForm()
                    template = get_template("rec_bancopacifico/verificar.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'verdetalle':
                try:
                    data['title'] = u'Detalle'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ArchivoCuentaBancoVerificadoDetalle.objects.get(pk=int(request.GET['id']))
                    data['det'] = det = ArchivoCuentaBancoRubroDetalle.objects.filter(det=filtro).order_by('rubro')
                    template = get_template("rec_bancopacifico/verdetalle.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'matchpagos':
                try:
                    data['title'] = u'Devengar Pago'
                    data['id'] = id = request.GET['id']
                    data['filtro'] = filtro = ArchivoCuentaBancoVerificadoDetalle.objects.get(pk=int(request.GET['id']))
                    rubros = Rubro.objects.filter(persona=filtro.persona, status=True, cancelado=False).order_by('fechavence')
                    listaexclude = []
                    for r in rubros:
                        if not r.tipo.partida_saldo(anio):
                            listaexclude.append(r.pk)
                    data['det'] = rubros.exclude(pk__in=listaexclude)
                    data['puede_pagar'] = data['persona'].puede_recibir_pagos()
                    template = get_template("rec_bancopacifico/match.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'buscararchivos':
                try:
                    desde = datetime.strptime(request.GET['desde'], '%Y-%m-%d')
                    hasta = datetime.strptime(request.GET['hasta'], '%Y-%m-%d') + timedelta(days=1)
                    cuenta = int(request.GET['cuenta'])
                    lista = []
                    archivos = ArchivoGeneradoRecaudacionBanco.objects.filter(cuentabanco_id=cuenta, status=True, fecha_creacion__range=(desde.date(), hasta.date())).order_by('-fecha')
                    for archivo in archivos:
                        lista.append({'fecha': archivo.fecha.strftime("%Y-%m-%d | %H:%M:%S"), 'url': archivo.archivo.url})
                    return JsonResponse({"result": True, 'context': lista})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            if 'mover' in request.GET:
                mover = request.GET['mover']

                if mover == 'anterior':
                    mes = int(request.GET['mes'])
                    anio = int(request.GET['anio'])
                    pmes = mes - 1
                    if pmes == 0:
                        pmes = 12
                        panio = anio - 1
                    else:
                        panio = anio

                elif mover == 'proximo':
                    mes = int(request.GET['mes'])
                    anio = int(request.GET['anio'])
                    pmes = mes + 1
                    if pmes == 13:
                        pmes = 1
                        panio = anio + 1
                    else:
                        panio = anio

        data['cuentasbanco'] = cuentas = CuentaBanco.objects.filter(banco__id=BANCO_PACIFICO_ID, status=True)
        if 'cuenta' in request.GET:
            data['cuenta'] = CuentaBanco.objects.get(pk=int(request.GET['cuenta']))
        else:
            if cuentas:
                data['cuenta'] = cuentas[0]
            else:
                data['cuenta'] = None
        data['actividades'] = RecaudacionBanco.objects.filter(cuentabanco=data['cuenta'], status=True)
        s_anio = panio
        s_mes = pmes
        s_dia = 1
        data['mes'] = MESES_CHOICES[s_mes - 1]
        data['ws'] = [0, 7, 14, 21, 28, 35]
        lista = {}
        listaactividades = {}
        for i in range(1, 43, 1):
            dia = {i: 'no'}
            actividaddia = {i: None}
            lista.update(dia)
            listaactividades.update(actividaddia)
        comienzo = False
        fin = False
        for i in lista.items():
            try:
                fecha = date(s_anio, s_mes, s_dia)
                if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                    comienzo = True
            except Exception as ex:
                pass
            if comienzo:
                try:
                    fecha = date(s_anio, s_mes, s_dia)
                except Exception as ex:
                    fin = True
            if comienzo and fin is False:
                dia = {i[0]: s_dia}
                s_dia += 1
                lista.update(dia)
                actividaddia = RecaudacionBanco.objects.filter(fecha=fecha, cuentabanco=data['cuenta'], status=True)
                diaact = []
                if actividaddia.exists():
                    valor = str(actividaddia[0].valor)
                else:
                    valor = ""
                act = [valor, (fecha < datetime.now().date() and valor == ""), actividaddia.count(),
                       fecha.strftime('%d-%m-%Y')]
                diaact.append(act)
                listaactividades.update({i[0]: diaact})
        data['dias_mes'] = lista
        data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
        data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
        data['daymonth'] = 1
        data['s_anio'] = s_anio
        data['s_mes'] = s_mes
        data['lista'] = lista
        data['listaactividades'] = listaactividades
        data['archivo'] = None
        if ArchivoGeneradoRecaudacionBanco.objects.filter(cuentabanco=data['cuenta'], status=True).exists():
            data['archivo'] = ArchivoGeneradoRecaudacionBanco.objects.filter(cuentabanco=data['cuenta'], status=True).order_by('-fecha')[0]
        persona = request.session['persona']
        puedefacturar = persona.puede_recibir_pagos()

        data['caja'] = None
        if puedefacturar:
            caja = persona.lugarrecaudacion_set.all()[0]
            data['caja'] = caja
            data['sessioncaja'] = caja.sesion_caja()
        data['puedefacturar'] = puedefacturar
        data['check_session'] = False
        data['fechainicio'] = date(datetime.now().year, 1, 1)
        data['fechafin'] = datetime.now().date()
        data['rubros_exportar'] = TipoOtroRubro.objects.filter(exportabanco=True, status=True)
        data['periodos'] = Periodo.objects.filter(status=True).order_by("-id")
        return render(request, "rec_bancopacifico/view.html", data)
