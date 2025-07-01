# coding=utf-8
import json
from datetime import datetime
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import RequestContext, Context
from django.template.loader import get_template

from decorators import secure_module
from sagest.commonviews import anio_ejercicio, secuencia_presupuesto, null_to_decimal, Sum
from sagest.forms import ImportarArchivoCSVForm, PartidaDetallesForm, ComrpomisoPartidaForm, \
    ComrpomisoCertificacionForm, \
    ReformaPartidaForm, DetalleCertificacionForm, DetalleReformaPartidaForm, \
    DetalleCompromisoForm, FechaCertificacionForm, PartidaSaldoForm
from sagest.models import PartidasSaldo, Partida, ReformaPartida, AnioEjercicio, PartidaEntidad, \
    PartidaUnidadEjecutoria, PartidaUnidadDesconcentrada, PartidaPrograma, PartidaSubprograma, PartidaProyecto, \
    PartidaActividad, PartidaObra, PartidaGeografico, PartidaFuente, PartidaOrganismo, PartidaCorrelativo, \
    FechaCertificacion, \
    ReformaClaseRegistro, CompromisoClaseRegistro, CompromisoClaseModificacion, CompromisoClaseGasto, \
    CertificacionPartida, CompromisoPartida, DetalleCertificacion, PresupuestoTipoDocumentoRespaldo, \
    PresupuestoClaseDocumentoRespaldo, DetalleReformaPartida, DetalleCompromiso, Proveedor
from settings import EMAIL_DOMAIN, ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha
from sga.models import Archivo


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if 'aniofiscalpresupuesto' in request.session:
        anio = request.session['aniofiscalpresupuesto']
    else:
        anio = anio_ejercicio().anioejercicio
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addPartida':
            try:
                f = PartidaSaldoForm(request.POST)
                if f.is_valid():
                    filtro = PartidasSaldo(
                    partida=f.cleaned_data['partida'],
                    anioejercicio =f.cleaned_data['anioejercicio'],
                    entidad =f.cleaned_data['entidad'],
                    unidadejecutoria =f.cleaned_data['unidadejecutoria'],
                    unidaddesconcentrada = f.cleaned_data['unidaddesconcentrada'],
                    programa = f.cleaned_data['programa'],
                    subprograma = f.cleaned_data['subprograma'],
                    proyecto = f.cleaned_data['proyecto'],
                    actividad =f.cleaned_data['actividad'],
                    obra = f.cleaned_data['obra'],
                    geografico = f.cleaned_data['geografico'],
                    fuente = f.cleaned_data['fuente'],
                    organismo = f.cleaned_data['organismo'],
                    correlativo = f.cleaned_data['correlativo'],
                    asignado = f.cleaned_data['asignado'],
                    codificado = 0, # f.cleaned_data['codificado'],
                    reservadonegativo = 0, #f.cleaned_data['reservadonegativo'],
                    precompromiso = 0 ,# f.cleaned_data['precompromiso'],
                    compromiso = 0, #f.cleaned_data['compromiso'],
                    devengado =f.cleaned_data['devengado'],
                    pagado = 0 ,#f.cleaned_data['pagado'],
                    recaudado =0 ,# f.cleaned_data['recaudado'],
                    recaudadoesigef = 0 ,#f.cleaned_data['recaudadoesigef'],
                    disponible = 0, #f.cleaned_data['disponible'],
                    )
                    filtro.save(request)
                    log(u'Adicionó partida para presupuesto dip: %s' % filtro, request, "add")
                    return JsonResponse({"result": False}, safe=False)
                else:
                    raise NameError('Error')

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Datos erróneos, intente nuevamente."}, safe=False)

        if action == 'importar':
            try:
                form = ImportarArchivoCSVForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION SALDOS DE PARTIDAS PRESUPUESTARIAS',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save()
                    with open(archivo.archivo.file.name, 'r') as f:
                        data = f.readlines()
                        linea = 1
                        for line in data:
                            if linea >= 2:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                if len(cols) != 25 and len(cols) > 1:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"No cumple con la estructura adecuada para la exportación en la línea %s." % linea})
                            linea += 1
                        linea = 1
                        f.seek(0)
                        saldopartida = None
                        for line in data:
                            if linea >= 2:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                if len(cols) > 1:
                                    anioe = int(str(cols[0]).strip().replace('"', ''))
                                    if not AnioEjercicio.objects.filter(anioejercicio=anioe):
                                        anio = AnioEjercicio(anioejercicio=anioe)
                                        anio.save(request)
                                    else:
                                        anio = AnioEjercicio.objects.get(anioejercicio=anioe)
                                    # BUSCAMOS LA PARTIDA PRESUPUESTARIA
                                    if not Partida.objects.values('id').filter(codigo=str(int(cols[9]))).exists():
                                        partida = Partida(codigo=str(int(cols[9])),
                                                          nombre='SIN DEFINIR',
                                                          tipo=1)
                                        partida.save(request)
                                    else:
                                        partida = Partida.objects.get(codigo=str(int(cols[9])))
                                    if not PartidaEntidad.objects.values('id').filter(
                                            codigo=str(int(cols[1]))).exists():
                                        entidad = PartidaEntidad(codigo=str(int(cols[1])),
                                                                 nombre=cols[14])
                                        entidad.save(request)
                                    else:
                                        entidad = PartidaEntidad.objects.get(codigo=str(int(cols[1])))
                                    if not PartidaUnidadEjecutoria.objects.values('id').filter(
                                            codigo=str(int(cols[2]))).exists():
                                        ejecutoria = PartidaUnidadEjecutoria(codigo=str(int(cols[2])),
                                                                             nombre='SIN DEFINIR')
                                        ejecutoria.save(request)
                                    else:
                                        ejecutoria = PartidaUnidadEjecutoria.objects.get(codigo=str(int(cols[2])))
                                    if not PartidaUnidadDesconcentrada.objects.values('id').filter(
                                            codigo=str(int(cols[3]))).exists():
                                        udesc = PartidaUnidadDesconcentrada(codigo=str(int(cols[3])),
                                                                            nombre='SIN DEFINIR')
                                        udesc.save(request)
                                    else:
                                        udesc = PartidaUnidadDesconcentrada.objects.get(codigo=str(int(cols[3])))
                                    if not PartidaPrograma.objects.values('id').filter(
                                            codigo=str(int(cols[4]))).exists():
                                        prog = PartidaPrograma(codigo=str(int(cols[4])),
                                                               nombre='SIN DEFINIR')
                                        prog.save(request)
                                    else:
                                        prog = PartidaPrograma.objects.get(codigo=str(int(cols[4])))
                                    if not PartidaSubprograma.objects.values('id').filter(
                                            codigo=str(int(cols[5]))).exists():
                                        sub = PartidaSubprograma(codigo=str(int(cols[5])),
                                                                 nombre='SIN DEFINIR')
                                        sub.save(request)
                                    else:
                                        sub = PartidaSubprograma.objects.get(codigo=str(int(cols[5])))
                                    if not PartidaProyecto.objects.values('id').filter(
                                            codigo=str(int(cols[6]))).exists():
                                        proyec = PartidaProyecto(codigo=str(int(cols[6])),
                                                                 nombre='SIN DEFINIR')
                                        proyec.save(request)
                                    else:
                                        proyec = PartidaProyecto.objects.get(codigo=str(int(cols[6])))
                                    codiactividad = str(int(cols[4])) + "." + str(int(cols[7]))
                                    if not PartidaActividad.objects.values('id').filter(codigo=codiactividad).exists():
                                        act = PartidaActividad(codigo=codiactividad,
                                                               nombre='SIN DEFINIR')
                                        act.save(request)
                                    else:
                                        act = PartidaActividad.objects.get(codigo=codiactividad)

                                    if not PartidaObra.objects.values('id').filter(codigo=str(int(cols[8]))).exists():
                                        obra = PartidaObra(codigo=str(int(cols[8])),
                                                           nombre='SIN DEFINIR')
                                        obra.save(request)
                                    else:
                                        obra = PartidaObra.objects.get(codigo=str(int(cols[8])))
                                    if not PartidaGeografico.objects.values('id').filter(
                                            codigo=str(int(cols[10]))).exists():
                                        geo = PartidaGeografico(codigo=str(int(cols[10])),
                                                                nombre=cols[15])
                                        geo.save(request)
                                    else:
                                        geo = PartidaGeografico.objects.get(codigo=str(int(cols[10])))
                                    if not PartidaFuente.objects.values('id').filter(
                                            codigo=str(int(cols[11]))).exists():
                                        fuente = PartidaFuente(codigo=str(int(cols[11])),
                                                               nombre='SIN DEFINIR')
                                        fuente.save(request)
                                    else:
                                        fuente = PartidaFuente.objects.get(codigo=str(int(cols[11])))
                                    if not PartidaOrganismo.objects.values('id').filter(
                                            codigo=str(int(cols[12]))).exists():
                                        org = PartidaOrganismo(codigo=str(int(cols[12])),
                                                               nombre='SIN DEFINIR')
                                        org.save(request)
                                    else:
                                        org = PartidaOrganismo.objects.get(codigo=str(int(cols[12])))
                                    if not PartidaCorrelativo.objects.values('id').filter(
                                            codigo=str(int(cols[13]))).exists():
                                        cor = PartidaCorrelativo(codigo=str(int(cols[13])),
                                                                 nombre='SIN DEFINIR')
                                        cor.save(request)
                                    else:
                                        cor = PartidaCorrelativo.objects.get(codigo=str(int(cols[13])))
                                    if not PartidasSaldo.objects.values('id').filter(anioejercicio=anio,
                                                                                     entidad=entidad,
                                                                                     unidadejecutoria=ejecutoria,
                                                                                     unidaddesconcentrada=udesc,
                                                                                     programa=prog, subprograma=sub,
                                                                                     proyecto=proyec, actividad=act,
                                                                                     obra=obra, partida=partida,
                                                                                     geografico=geo, fuente=fuente,
                                                                                     organismo=org,
                                                                                     correlativo=cor).exists():
                                        saldopartida = PartidasSaldo(anioejercicio=anio,
                                                                     entidad=entidad,
                                                                     unidadejecutoria=ejecutoria,
                                                                     unidaddesconcentrada=udesc,
                                                                     programa=prog,
                                                                     subprograma=sub,
                                                                     proyecto=proyec,
                                                                     actividad=act,
                                                                     obra=obra,
                                                                     partida=partida,
                                                                     geografico=geo,
                                                                     fuente=fuente,
                                                                     organismo=org,
                                                                     correlativo=cor,
                                                                     asignado=Decimal(cols[16]),
                                                                     codificado=Decimal(cols[17]),
                                                                     reservadonegativo=Decimal(cols[18]),
                                                                     precompromiso=Decimal(cols[19]),
                                                                     recaudadoesigef=0,
                                                                     compromiso=Decimal(cols[20]),
                                                                     devengado=Decimal(cols[21]),
                                                                     pagado=Decimal(cols[22]),
                                                                     disponible=Decimal(cols[23]))
                                        saldopartida.save(request)
                                        saldopartida.recaudado = null_to_decimal(
                                            saldopartida.resumencomprobantepartida_set.aggregate(valor=Sum('valor'))[
                                                'valor'])
                                        saldopartida.save(request)
                                        # saldopartida.actualizar_saldos(request)
                                    else:
                                        saldopartida = PartidasSaldo.objects.filter(anioejercicio=anio, entidad=entidad,
                                                                                    unidadejecutoria=ejecutoria,
                                                                                    unidaddesconcentrada=udesc,
                                                                                    programa=prog, subprograma=sub,
                                                                                    proyecto=proyec, actividad=act,
                                                                                    obra=obra, partida=partida,
                                                                                    geografico=geo, fuente=fuente,
                                                                                    organismo=org, correlativo=cor)[0]
                                        saldopartida.asignado = Decimal(cols[16])
                                        saldopartida.codificado = Decimal(cols[17])
                                        saldopartida.reservadonegativo = Decimal(cols[18])
                                        saldopartida.precompromiso = Decimal(cols[19])
                                        saldopartida.compromiso = Decimal(cols[20])
                                        saldopartida.devengado = Decimal(cols[21])
                                        saldopartida.pagado = Decimal(cols[22])
                                        saldopartida.disponible = Decimal(cols[23])
                                        saldopartida.recaudado = null_to_decimal(
                                            saldopartida.resumencomprobantepartida_set.aggregate(valor=Sum('valor'))[
                                                'valor'])
                                        saldopartida.save(request)
                                        # saldopartida.actualizar_saldos(request)
                            linea += 1
                    log(u'Importo saldos de partidas: %s' % nfile._name, request, "edit")
                    secuencia = secuencia_presupuesto(request)
                    secuencia.fechaultimasaldosegreso = datetime.now()
                    secuencia.usuariomodificaegresos = usuario
                    secuencia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importar_ingresos':
            try:
                form = ImportarArchivoCSVForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION SALDOS INGRESOS DE PARTIDAS PRESUPUESTARIAS',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save()
                    with open(archivo.archivo.file.name, 'r') as f:
                        data = f.readlines()
                        linea = 1
                        for line in data:
                            if linea >= 2:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"').replace('."', '"."')
                                cols = datolinea.split('";"')
                                if len(cols) != 16 and len(cols) > 1:
                                    transaction.set_rollback(True)
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"No cumple con la estructura adecuada para la exportación en la línea %s." % linea})
                            linea += 1
                        linea = 1
                        f.seek(0)
                        saldopartida = None
                        if not AnioEjercicio.objects.filter(anioejercicio=anio):
                            anioe = AnioEjercicio(anioejercicio=anio)
                            anioe.save(request)
                        else:
                            anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                        for line in data:
                            if linea >= 2:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('";"')
                                if len(cols) > 1:
                                    # BUSCAMOS LA PARTIDA PRESUPUESTARIA
                                    if not Partida.objects.values('id').filter(
                                            codigo=str(int(cols[9].replace('"', '')))).exists():
                                        partida = Partida(codigo=str(int(cols[9].replace('"', ''))),
                                                          nombre=str(cols[7][1:].strip()),
                                                          tipo=2)
                                        partida.save(request)
                                    else:
                                        partida = Partida.objects.get(codigo=str(int(cols[9].replace('"', ''))))

                                    if not PartidaFuente.objects.values('id').filter(
                                            codigo=str(cols[10].replace('"', '').strip())).exists():
                                        fuente = PartidaFuente(codigo=str(cols[10].replace('"', '').strip()),
                                                               nombre=str(cols[6].strip()))
                                        fuente.save(request)
                                    else:
                                        fuente = PartidaFuente.objects.get(
                                            codigo=str(cols[10].replace('"', '').strip()))
                                        fuente.nombre = str(cols[6].strip())
                                        fuente.save(request)

                                    if not PartidasSaldo.objects.values('id').filter(anioejercicio=anioe, fuente=fuente,
                                                                                     partida=partida).exists():
                                        saldopartida = PartidasSaldo(anioejercicio=anioe,
                                                                     fuente=fuente,
                                                                     asignado=Decimal(cols[12].replace('\n', '')),
                                                                     codificado=0,
                                                                     reservadonegativo=0,
                                                                     recaudadoesigef=0,
                                                                     precompromiso=0,
                                                                     compromiso=0,
                                                                     partida=partida,
                                                                     devengado=Decimal(cols[13].replace('\n', '')),
                                                                     pagado=0,
                                                                     disponible=0)
                                        saldopartida.save(request)
                                    else:
                                        saldopartida = PartidasSaldo.objects.filter(anioejercicio=anioe, fuente=fuente,
                                                                                    partida=partida)[0]
                                        saldopartida.asignado = Decimal(cols[12].replace('\n', ''))
                                        saldopartida.codificado = 0
                                        saldopartida.reservadonegativo = 0
                                        saldopartida.recaudadoesigef = 0
                                        saldopartida.devengado = Decimal(cols[13].replace('\n', ''))
                                        saldopartida.save(request)
                                    saldopartida.actualizar_saldos(request)
                            linea += 1
                    log(u'Importo saldos de partidas: %s [%s]' % (nfile._name, archivo.id), request, "edit")
                    secuencia = secuencia_presupuesto(request)
                    secuencia.fechaultimasaldosingreso = datetime.now()
                    secuencia.usuariomodificaingresos = usuario
                    secuencia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importar_reformas':
            try:
                form = ImportarArchivoCSVForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION REFORMAS DE PARTIDA',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save()
                    with open(archivo.archivo.file.name, 'r') as f:
                        data = f.readlines()
                        linea = 1
                        for line in data:
                            if linea >= 2:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                if len(cols) != 29 and len(cols) > 1:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"No cumple con la estructura adecuada para la exportación en la línea %s." % linea})
                            linea += 1
                        linea = 1
                        f.seek(0)
                        saldopartida = None
                        for line in data:
                            if linea >= 2:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                if len(cols) > 1:
                                    anioe = int(str(cols[0]).strip().replace('"', ''))
                                    if not AnioEjercicio.objects.filter(anioejercicio=anioe):
                                        anio = AnioEjercicio(anioejercicio=anioe)
                                        anio.save(request)
                                    else:
                                        anio = AnioEjercicio.objects.get(anioejercicio=anioe)
                                    # BUSCAMOS EL SALDO DE LA PARTIDA PRESUPUESTARIA
                                    if not Partida.objects.values('id').filter(codigo=str(int(cols[22]))).exists():
                                        partida = Partida(codigo=str(int(cols[22])),
                                                          nombre='SIN DEFINIR')
                                        partida.save(request)
                                    else:
                                        partida = Partida.objects.get(codigo=str(int(cols[22])))
                                    if not PartidaEntidad.objects.values('id').filter(
                                            codigo=str(int(cols[1]))).exists():
                                        entidad = PartidaEntidad(codigo=str(int(cols[1])),
                                                                 nombre=cols[4])
                                        entidad.save(request)
                                    else:
                                        entidad = PartidaEntidad.objects.get(codigo=str(int(cols[1])))
                                    if not PartidaUnidadEjecutoria.objects.values('id').filter(
                                            codigo=str(int(cols[2]))).exists():
                                        ejecutoria = PartidaUnidadEjecutoria(codigo=str(int(cols[2])),
                                                                             nombre='SIN DEFINIR')
                                        ejecutoria.save(request)
                                    else:
                                        ejecutoria = PartidaUnidadEjecutoria.objects.get(codigo=str(int(cols[2])))
                                    if not PartidaUnidadDesconcentrada.objects.values('id').filter(
                                            codigo=str(int(cols[3]))).exists():
                                        udesc = PartidaUnidadDesconcentrada(codigo=str(int(cols[3])),
                                                                            nombre='SIN DEFINIR')
                                        udesc.save(request)
                                    else:
                                        udesc = PartidaUnidadDesconcentrada.objects.get(codigo=str(int(cols[3])))
                                    if not PartidaPrograma.objects.values('id').filter(
                                            codigo=str(int(cols[17]))).exists():
                                        prog = PartidaPrograma(codigo=str(int(cols[17])),
                                                               nombre='SIN DEFINIR')
                                        prog.save(request)
                                    else:
                                        prog = PartidaPrograma.objects.get(codigo=str(int(cols[17])))
                                    if not PartidaSubprograma.objects.values('id').filter(
                                            codigo=str(int(cols[18]))).exists():
                                        sub = PartidaSubprograma(codigo=str(int(cols[18])),
                                                                 nombre='SIN DEFINIR')
                                        sub.save(request)
                                    else:
                                        sub = PartidaSubprograma.objects.get(codigo=str(int(cols[18])))
                                    if not PartidaProyecto.objects.values('id').filter(
                                            codigo=str(int(cols[19]))).exists():
                                        proyec = PartidaProyecto(codigo=str(int(cols[19])),
                                                                 nombre='SIN DEFINIR')
                                        proyec.save(request)
                                    else:
                                        proyec = PartidaProyecto.objects.get(codigo=str(int(cols[19])))
                                    if not PartidaActividad.objects.values('id').filter(
                                            codigo=str(int(cols[20]))).exists():
                                        act = PartidaActividad(codigo=str(int(cols[20])),
                                                               nombre='SIN DEFINIR')
                                        act.save(request)
                                    else:
                                        act = PartidaActividad.objects.get(codigo=str(int(cols[20])))
                                    if not PartidaObra.objects.values('id').filter(codigo=str(int(cols[21]))).exists():
                                        obra = PartidaObra(codigo=str(int(cols[21])),
                                                           nombre='SIN DEFINIR')
                                        obra.save(request)
                                    else:
                                        obra = PartidaObra.objects.get(codigo=str(int(cols[21])))
                                    if not PartidaGeografico.objects.values('id').filter(
                                            codigo=str(int(cols[23]))).exists():
                                        geo = PartidaGeografico(codigo=str(int(cols[23])),
                                                                nombre='SIN DEFINIR')
                                        geo.save(request)
                                    else:
                                        geo = PartidaGeografico.objects.get(codigo=str(int(cols[23])))
                                    if not PartidaFuente.objects.values('id').filter(
                                            codigo=str(int(cols[24]))).exists():
                                        fuente = PartidaFuente(codigo=str(int(cols[24])),
                                                               nombre='SIN DEFINIR')
                                        fuente.save(request)
                                    else:
                                        fuente = PartidaFuente.objects.get(codigo=str(int(cols[24])))
                                    if not PartidaOrganismo.objects.values('id').filter(
                                            codigo=str(int(cols[25]))).exists():
                                        org = PartidaOrganismo(codigo=str(int(cols[25])),
                                                               nombre='SIN DEFINIR')
                                        org.save(request)
                                    else:
                                        org = PartidaOrganismo.objects.get(codigo=str(int(cols[25])))
                                    if not PartidaCorrelativo.objects.values('id').filter(
                                            codigo=str(int(cols[26]))).exists():
                                        cor = PartidaCorrelativo(codigo=str(int(cols[26])),
                                                                 nombre='SIN DEFINIR')
                                        cor.save(request)
                                    else:
                                        cor = PartidaCorrelativo.objects.get(codigo=str(int(cols[26])))
                                    if PartidasSaldo.objects.values('id').filter(anioejercicio=anio, entidad=entidad,
                                                                                 unidadejecutoria=ejecutoria,
                                                                                 unidaddesconcentrada=udesc,
                                                                                 programa=prog, subprograma=sub,
                                                                                 proyecto=proyec, actividad=act,
                                                                                 obra=obra, partida=partida,
                                                                                 geografico=geo, fuente=fuente,
                                                                                 organismo=org,
                                                                                 correlativo=cor).exists():
                                        saldopartida = PartidasSaldo.objects.filter(anioejercicio=anio, entidad=entidad,
                                                                                    unidadejecutoria=ejecutoria,
                                                                                    unidaddesconcentrada=udesc,
                                                                                    programa=prog, subprograma=sub,
                                                                                    proyecto=proyec, actividad=act,
                                                                                    obra=obra, partida=partida,
                                                                                    geografico=geo, fuente=fuente,
                                                                                    organismo=org, correlativo=cor)[0]
                                    else:
                                        saldopartida = PartidasSaldo(partida=partida,
                                                                     anioejercicio=anio,
                                                                     entidad=entidad,
                                                                     unidadejecutoria=ejecutoria,
                                                                     unidaddesconcentrada=udesc,
                                                                     programa=prog,
                                                                     subprograma=sub,
                                                                     proyecto=proyec,
                                                                     actividad=act,
                                                                     obra=obra,
                                                                     geografico=geo,
                                                                     fuente=fuente,
                                                                     organismo=org,
                                                                     correlativo=cor,
                                                                     asignado=0,
                                                                     codificado=0,
                                                                     reservadonegativo=0,
                                                                     precompromiso=0,
                                                                     compromiso=0,
                                                                     devengado=0,
                                                                     pagado=0,
                                                                     disponible=0)
                                        saldopartida.save(request)
                                    nocur = int(str(cols[5]).strip())
                                    if not ReformaClaseRegistro.objects.values('id').filter(
                                            codigo=str(cols[6].strip())).exists():
                                        claseregistro = ReformaClaseRegistro(codigo=str(cols[6].strip()),
                                                                             nombre='SIN DEFINIR')
                                        claseregistro.save(request)
                                    else:
                                        claseregistro = ReformaClaseRegistro.objects.get(codigo=str(cols[6].strip()))
                                    montoaprobado = Decimal(cols[8])
                                    descripcion = cols[9].decode('utf-8', 'ignore')
                                    fecimputacion = None
                                    try:
                                        fecimputacion = convertir_fecha(cols[10])
                                    except:
                                        pass
                                    disposicionlegal = str(cols[11]).strip()
                                    fecdisposicion = None
                                    try:
                                        fecdisposicion = convertir_fecha(cols[12])
                                    except:
                                        pass
                                    solicitado = cols[13]
                                    aprobado = cols[14]
                                    error = int(str(cols[15]).strip())
                                    tipodocumento = int(str(cols[16]).strip())
                                    montosolicitado = Decimal(cols[27])
                                    if not ReformaPartida.objects.values('id').filter(nocur=nocur).exists():
                                        reformapartida = ReformaPartida(nocur=nocur,
                                                                        claseregistro=claseregistro,
                                                                        descripcion=descripcion,
                                                                        fecimputacion=fecimputacion,
                                                                        disposicionlegal=disposicionlegal,
                                                                        fecdisposicion=fecdisposicion,
                                                                        solicitado=solicitado,
                                                                        aprobado=aprobado,
                                                                        error=error,
                                                                        tipodocumento=tipodocumento)
                                        reformapartida.save(request)
                                    else:
                                        reformapartida = ReformaPartida.objects.filter(nocur=int(str(cols[5]).strip()))[
                                            0]
                                    if not DetalleReformaPartida.objects.values('id').filter(partidassaldo=saldopartida,
                                                                                             reformapartida=reformapartida).exists():
                                        detallereforma = DetalleReformaPartida(montoaprobado=montosolicitado,
                                                                               montosolicitado=montosolicitado,
                                                                               partidassaldo=saldopartida,
                                                                               reformapartida=reformapartida,
                                                                               decrementa=False if montosolicitado > 0 else True)
                                        detallereforma.save(request)
                                    else:
                                        detallereforma = \
                                        DetalleReformaPartida.objects.filter(partidassaldo=saldopartida,
                                                                             reformapartida=reformapartida)[0]
                                    reformapartida.totales(request)
                                    saldopartida.actualizar_saldos(request)
                            linea += 1
                    log(u'Importo reformas de partidas: %s [%s]' % (nfile._name, archivo.id), request, "edit")
                    secuencia = secuencia_presupuesto(request)
                    secuencia.fechaultimareformas = datetime.now()
                    secuencia.usuariomodificareformas = usuario
                    secuencia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importar_certificacion':
            try:
                form = ImportarArchivoCSVForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION REFORMAS DE PARTIDA',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save()
                    with open(archivo.archivo.file.name, 'r') as f:
                        data = f.readlines()
                        linea = 1
                        for line in data:
                            if linea >= 3:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                if len(cols) < 32:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"No cumple con la estructura adecuada para la exportación en la línea %s." % linea})
                            linea += 1
                        linea = 1
                        f.seek(0)
                        saldopartida = None
                        for line in data:
                            if linea >= 3:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                anioe = int(str(cols[0]).strip().replace('"', ''))
                                if anioe > 0:
                                    if not AnioEjercicio.objects.filter(anioejercicio=anioe):
                                        anio = AnioEjercicio(anioejercicio=anioe)
                                        anio.save(request)
                                    else:
                                        anio = AnioEjercicio.objects.get(anioejercicio=anioe)
                                    # BUSCAMOS EL SALDO DE LA PARTIDA PRESUPUESTARIA
                                    if not Partida.objects.values('id').filter(codigo=str(int(cols[9]))).exists():
                                        partida = Partida(codigo=str(int(cols[9])),
                                                          nombre='SIN DEFINIR',
                                                          tipo=1)
                                        partida.save(request)
                                    else:
                                        partida = Partida.objects.get(codigo=str(int(cols[9])))
                                    if not PartidaEntidad.objects.values('id').filter(
                                            codigo=str(int(cols[1]))).exists():
                                        entidad = PartidaEntidad(codigo=str(int(cols[1])),
                                                                 nombre='SIN DEFINIR')
                                        entidad.save(request)
                                    else:
                                        entidad = PartidaEntidad.objects.get(codigo=str(int(cols[1])))
                                    if not PartidaUnidadEjecutoria.objects.values('id').filter(
                                            codigo=str(int(cols[2]))).exists():
                                        ejecutoria = PartidaUnidadEjecutoria(codigo=str(int(cols[2])),
                                                                             nombre='SIN DEFINIR')
                                        ejecutoria.save(request)
                                    else:
                                        ejecutoria = PartidaUnidadEjecutoria.objects.get(codigo=str(int(cols[2])))
                                    if not PartidaUnidadDesconcentrada.objects.values('id').filter(
                                            codigo=str(int(cols[3]))).exists():
                                        udesc = PartidaUnidadDesconcentrada(codigo=str(int(cols[3])),
                                                                            nombre='SIN DEFINIR')
                                        udesc.save(request)
                                    else:
                                        udesc = PartidaUnidadDesconcentrada.objects.get(codigo=str(int(cols[3])))
                                    if not PartidaPrograma.objects.values('id').filter(
                                            codigo=str(int(cols[5]))).exists():
                                        prog = PartidaPrograma(codigo=str(int(cols[5])),
                                                               nombre='SIN DEFINIR')
                                        prog.save(request)
                                    else:
                                        prog = PartidaPrograma.objects.get(codigo=str(int(cols[5])))
                                    if not PartidaSubprograma.objects.values('id').filter(
                                            codigo=str(int(cols[6]))).exists():
                                        sub = PartidaSubprograma(codigo=str(int(cols[6])),
                                                                 nombre='SIN DEFINIR')
                                        sub.save(request)
                                    else:
                                        sub = PartidaSubprograma.objects.get(codigo=str(int(cols[6])))
                                    if not PartidaProyecto.objects.values('id').filter(
                                            codigo=str(int(cols[7]))).exists():
                                        proyec = PartidaProyecto(codigo=str(int(cols[7])),
                                                                 nombre='SIN DEFINIR')
                                        proyec.save(request)
                                    else:
                                        proyec = PartidaProyecto.objects.get(codigo=str(int(cols[7])))
                                    if not PartidaActividad.objects.values('id').filter(
                                            codigo=str(int(cols[8]))).exists():
                                        act = PartidaActividad(codigo=str(int(cols[8])),
                                                               nombre='SIN DEFINIR')
                                        act.save(request)
                                    else:
                                        act = PartidaActividad.objects.get(codigo=str(int(cols[8])))
                                    if not PartidaGeografico.objects.values('id').filter(
                                            codigo=str(int(cols[10]))).exists():
                                        geo = PartidaGeografico(codigo=str(int(cols[10])),
                                                                nombre='SIN DEFINIR')
                                        geo.save(request)
                                    else:
                                        geo = PartidaGeografico.objects.get(codigo=str(int(cols[10])))
                                    if not PartidaFuente.objects.values('id').filter(
                                            codigo=str(int(cols[11]))).exists():
                                        fuente = PartidaFuente(codigo=str(int(cols[11])),
                                                               nombre='SIN DEFINIR')
                                        fuente.save(request)
                                    else:
                                        fuente = PartidaFuente.objects.get(codigo=str(int(cols[11])))
                                    if not PartidaOrganismo.objects.values('id').filter(
                                            codigo=str(int(cols[12]))).exists():
                                        org = PartidaOrganismo(codigo=str(int(cols[12])),
                                                               nombre='SIN DEFINIR')
                                        org.save(request)
                                    else:
                                        org = PartidaOrganismo.objects.get(codigo=str(int(cols[12])))
                                    if not PartidaCorrelativo.objects.values('id').filter(
                                            codigo=str(int(cols[13]))).exists():
                                        cor = PartidaCorrelativo(codigo=str(int(cols[13])),
                                                                 nombre='SIN DEFINIR')
                                        cor.save(request)
                                    else:
                                        cor = PartidaCorrelativo.objects.get(codigo=str(int(cols[13])))
                                    if PartidasSaldo.objects.filter(anioejercicio=anio, entidad=entidad,
                                                                    unidadejecutoria=ejecutoria,
                                                                    unidaddesconcentrada=udesc, programa=prog,
                                                                    subprograma=sub, proyecto=proyec, actividad=act,
                                                                    partida=partida, geografico=geo, fuente=fuente,
                                                                    organismo=org, correlativo=cor).exists():
                                        saldopartida = PartidasSaldo.objects.filter(anioejercicio=anio, entidad=entidad,
                                                                                    unidadejecutoria=ejecutoria,
                                                                                    unidaddesconcentrada=udesc,
                                                                                    programa=prog, subprograma=sub,
                                                                                    proyecto=proyec, actividad=act,
                                                                                    partida=partida, geografico=geo,
                                                                                    fuente=fuente, organismo=org,
                                                                                    correlativo=cor)[0]
                                    else:
                                        saldopartida = PartidasSaldo(partida=partida,
                                                                     anioejercicio=anio,
                                                                     entidad=entidad,
                                                                     unidadejecutoria=ejecutoria,
                                                                     unidaddesconcentrada=udesc,
                                                                     programa=prog,
                                                                     subprograma=sub,
                                                                     proyecto=proyec,
                                                                     actividad=act,
                                                                     geografico=geo,
                                                                     fuente=fuente,
                                                                     organismo=org,
                                                                     correlativo=cor,
                                                                     asignado=0,
                                                                     codificado=0,
                                                                     reservadonegativo=0,
                                                                     precompromiso=0,
                                                                     compromiso=0,
                                                                     devengado=0,
                                                                     pagado=0,
                                                                     disponible=0)
                                        saldopartida.save(request)
                                    nocur = str(cols[14]).strip()
                                    numerocertificacion = int(str(cols[4]))
                                    if numerocertificacion == 763:
                                        pass
                                    monto = Decimal(cols[23])
                                    descripcion = cols[32].decode('utf-8', 'ignore')
                                    ruc = str(cols[21])
                                    fecha = None
                                    try:
                                        fecha = convertir_fecha(cols[28])
                                    except:
                                        pass
                                    valorliquidado = 0
                                    if str(cols[29]).strip() == 'APROBADO':
                                        estado = 1
                                    elif str(cols[29]).strip() == 'ERRADO':
                                        estado = 2
                                    else:
                                        estado = 3
                                        valorliquidado = Decimal(cols[24])
                                    claseregistro = None
                                    clasemodificacion = None
                                    clasegasto = None
                                    if not str(cols[15]) == '-':
                                        if not CompromisoClaseRegistro.objects.filter(codigo=str(cols[15])).exists():
                                            claseregistro = CompromisoClaseRegistro(codigo=str(cols[15]),
                                                                                    nombre='SIN DEFINIR')
                                            claseregistro.save(request)
                                        else:
                                            claseregistro = CompromisoClaseRegistro.objects.get(codigo=str(cols[15]))
                                    if not str(cols[16]) == '-':
                                        if not CompromisoClaseModificacion.objects.filter(
                                                codigo=str(cols[16])).exists():
                                            clasemodificacion = CompromisoClaseModificacion(codigo=str(cols[16]),
                                                                                            nombre='SIN DEFINIR')
                                            clasemodificacion.save(request)
                                        else:
                                            clasemodificacion = CompromisoClaseModificacion.objects.get(
                                                codigo=str(cols[16]))
                                    if not str(cols[15]) == '-':
                                        if not CompromisoClaseGasto.objects.filter(codigo=str(cols[17])).exists():
                                            clasegasto = CompromisoClaseGasto(codigo=str(cols[17]),
                                                                              nombre='SIN DEFINIR')
                                            clasegasto.save(request)
                                        else:
                                            clasegasto = CompromisoClaseGasto.objects.get(codigo=str(cols[17]))
                                    if not CertificacionPartida.objects.filter(numerocertificacion=numerocertificacion,
                                                                               anioejercicio=anio,
                                                                               local=False).exists():
                                        certificacionpartida = CertificacionPartida(
                                            numerocertificacion=numerocertificacion,
                                            anioejercicio=anio,
                                            claseregistro=claseregistro,
                                            clasemodificacion=clasemodificacion,
                                            clasegasto=clasegasto,
                                            descripcion=descripcion,
                                            fecha=fecha)
                                        certificacionpartida.save(request)
                                    else:
                                        certificacionpartida = \
                                        CertificacionPartida.objects.filter(numerocertificacion=numerocertificacion,
                                                                            local=False)[0]
                                    if not DetalleCertificacion.objects.filter(partidassaldo=saldopartida,
                                                                               certificacion=certificacionpartida).exists():
                                        detallecertificacion = DetalleCertificacion(estado=estado,
                                                                                    monto=monto,
                                                                                    saldo=monto,
                                                                                    liquidado=valorliquidado,
                                                                                    partidassaldo=saldopartida,
                                                                                    certificacion=certificacionpartida)
                                        detallecertificacion.save(request)
                                    else:
                                        detallecertificacion = \
                                        DetalleCertificacion.objects.filter(partidassaldo=saldopartida,
                                                                            certificacion=certificacionpartida)[0]
                                    detallecertificacion.actualiza_saldo(request)
                                    certificacionpartida.totales(request)
                                    certificacionpartida.actualiza_estado(request)
                                    saldopartida.actualizar_saldos(request)
                            linea += 1
                    log(u'Importo certificaciones de partidas: %s [%s]' % (nfile._name, archivo.id), request, "edit")
                    secuencia = secuencia_presupuesto(request)
                    secuencia.fechaultimacertificaciones = datetime.now()
                    secuencia.usuariomodificacertificacion = usuario
                    secuencia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'importar_compromiso':
            try:
                form = ImportarArchivoCSVForm(request.POST, request.FILES)
                if form.is_valid():
                    hoy = datetime.now().date()
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("importacion_", nfile._name)
                    archivo = Archivo(nombre='IMPORTACION REFORMAS DE PARTIDA',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save()
                    with open(archivo.archivo.file.name, 'r') as f:
                        data = f.readlines()
                        linea = 1
                        for line in data:
                            if linea >= 3:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                if len(cols) < 32:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"No cumple con la estructura adecuada para la exportación en la línea %s." % linea})
                            linea += 1
                        linea = 1
                        f.seek(0)
                        saldopartida = None
                        for line in data:
                            if linea >= 3:
                                datolinea = line
                                datolinea = datolinea.replace('NULL', '"NULL"')
                                cols = datolinea.split('"."')
                                anioe = int(str(cols[0]).strip().replace('"', ''))
                                if anioe > 0:
                                    if not AnioEjercicio.objects.filter(anioejercicio=anioe):
                                        anio = AnioEjercicio(anioejercicio=anioe)
                                        anio.save(request)
                                    else:
                                        anio = AnioEjercicio.objects.get(anioejercicio=anioe)
                                    # BUSCAMOS EL SALDO DE LA PARTIDA PRESUPUESTARIA
                                    if not Partida.objects.filter(codigo=str(int(cols[9]))).exists():
                                        partida = Partida(codigo=str(int(cols[9])),
                                                          nombre='SIN DEFINIR',
                                                          tipo=1)
                                        partida.save(request)
                                    else:
                                        partida = Partida.objects.get(codigo=str(int(cols[9])))
                                    if not PartidaEntidad.objects.filter(codigo=str(int(cols[1]))).exists():
                                        entidad = PartidaEntidad(codigo=str(int(cols[1])),
                                                                 nombre='SIN DEFINIR')
                                        entidad.save(request)
                                    else:
                                        entidad = PartidaEntidad.objects.get(codigo=str(int(cols[1])))
                                    if not PartidaUnidadEjecutoria.objects.filter(codigo=str(int(cols[2]))).exists():
                                        ejecutoria = PartidaUnidadEjecutoria(codigo=str(int(cols[2])),
                                                                             nombre='SIN DEFINIR')
                                        ejecutoria.save(request)
                                    else:
                                        ejecutoria = PartidaUnidadEjecutoria.objects.get(codigo=str(int(cols[2])))
                                    if not PartidaUnidadDesconcentrada.objects.filter(
                                            codigo=str(int(cols[3]))).exists():
                                        udesc = PartidaUnidadDesconcentrada(codigo=str(int(cols[3])),
                                                                            nombre='SIN DEFINIR')
                                        udesc.save(request)
                                    else:
                                        udesc = PartidaUnidadDesconcentrada.objects.get(codigo=str(int(cols[3])))
                                    if not PartidaPrograma.objects.filter(codigo=str(int(cols[5]))).exists():
                                        prog = PartidaPrograma(codigo=str(int(cols[5])),
                                                               nombre='SIN DEFINIR')
                                        prog.save(request)
                                    else:
                                        prog = PartidaPrograma.objects.get(codigo=str(int(cols[5])))
                                    if not PartidaSubprograma.objects.filter(codigo=str(int(cols[6]))).exists():
                                        sub = PartidaSubprograma(codigo=str(int(cols[6])),
                                                                 nombre='SIN DEFINIR')
                                        sub.save(request)
                                    else:
                                        sub = PartidaSubprograma.objects.get(codigo=str(int(cols[6])))
                                    if not PartidaProyecto.objects.filter(codigo=str(int(cols[7]))).exists():
                                        proyec = PartidaProyecto(codigo=str(int(cols[7])),
                                                                 nombre='SIN DEFINIR')
                                        proyec.save(request)
                                    else:
                                        proyec = PartidaProyecto.objects.get(codigo=str(int(cols[7])))
                                    if not PartidaActividad.objects.filter(codigo=str(int(cols[8]))).exists():
                                        act = PartidaActividad(codigo=str(int(cols[8])),
                                                               nombre='SIN DEFINIR')
                                        act.save(request)
                                    else:
                                        act = PartidaActividad.objects.get(codigo=str(int(cols[8])))
                                    if not PartidaGeografico.objects.filter(codigo=str(int(cols[10]))).exists():
                                        geo = PartidaGeografico(codigo=str(int(cols[10])),
                                                                nombre='SIN DEFINIR')
                                        geo.save(request)
                                    else:
                                        geo = PartidaGeografico.objects.get(codigo=str(int(cols[10])))
                                    if not PartidaFuente.objects.filter(codigo=str(int(cols[11]))).exists():
                                        fuente = PartidaFuente(codigo=str(int(cols[11])),
                                                               nombre='SIN DEFINIR')
                                        fuente.save(request)
                                    else:
                                        fuente = PartidaFuente.objects.get(codigo=str(int(cols[11])))
                                    if not PartidaOrganismo.objects.filter(codigo=str(int(cols[12]))).exists():
                                        org = PartidaOrganismo(codigo=str(int(cols[12])),
                                                               nombre='SIN DEFINIR')
                                        org.save(request)
                                    else:
                                        org = PartidaOrganismo.objects.get(codigo=str(int(cols[12])))
                                    if not PartidaCorrelativo.objects.filter(codigo=str(int(cols[13]))).exists():
                                        cor = PartidaCorrelativo(codigo=str(int(cols[13])),
                                                                 nombre='SIN DEFINIR')
                                        cor.save(request)
                                    else:
                                        cor = PartidaCorrelativo.objects.get(codigo=str(int(cols[13])))
                                    if PartidasSaldo.objects.filter(anioejercicio=anio, entidad=entidad,
                                                                    unidadejecutoria=ejecutoria,
                                                                    unidaddesconcentrada=udesc, programa=prog,
                                                                    subprograma=sub, proyecto=proyec, actividad=act,
                                                                    partida=partida, geografico=geo, fuente=fuente,
                                                                    organismo=org, correlativo=cor).exists():
                                        saldopartida = PartidasSaldo.objects.filter(anioejercicio=anio, entidad=entidad,
                                                                                    unidadejecutoria=ejecutoria,
                                                                                    unidaddesconcentrada=udesc,
                                                                                    programa=prog, subprograma=sub,
                                                                                    proyecto=proyec, actividad=act,
                                                                                    partida=partida, geografico=geo,
                                                                                    fuente=fuente, organismo=org,
                                                                                    correlativo=cor)[0]
                                    else:
                                        saldopartida = PartidasSaldo(partida=partida,
                                                                     anioejercicio=anio,
                                                                     entidad=entidad,
                                                                     unidadejecutoria=ejecutoria,
                                                                     unidaddesconcentrada=udesc,
                                                                     programa=prog,
                                                                     subprograma=sub,
                                                                     proyecto=proyec,
                                                                     actividad=act,
                                                                     geografico=geo,
                                                                     fuente=fuente,
                                                                     organismo=org,
                                                                     correlativo=cor,
                                                                     asignado=0,
                                                                     codificado=0,
                                                                     reservadonegativo=0,
                                                                     precompromiso=0,
                                                                     compromiso=0,
                                                                     devengado=0,
                                                                     pagado=0,
                                                                     disponible=0)
                                        saldopartida.save(request)
                                    nocur = str(cols[14]).strip()
                                    numerocertificacion = int(cols[4])
                                    monto = Decimal(cols[19])
                                    descripcion = cols[32].decode('utf-8', 'ignore')
                                    claseregistro = None
                                    clasemodificacion = None
                                    clasegasto = None
                                    if not str(cols[15]) == '-':
                                        if not CompromisoClaseRegistro.objects.filter(codigo=str(cols[15])).exists():
                                            claseregistro = CompromisoClaseRegistro(codigo=str(cols[15]),
                                                                                    nombre='SIN DEFINIR')
                                            claseregistro.save(request)
                                        else:
                                            claseregistro = CompromisoClaseRegistro.objects.get(codigo=str(cols[15]))
                                    if not str(cols[16]) == '-':
                                        if not CompromisoClaseModificacion.objects.filter(
                                                codigo=str(cols[16])).exists():
                                            clasemodificacion = CompromisoClaseModificacion(codigo=str(cols[16]),
                                                                                            nombre='SIN DEFINIR')
                                            clasemodificacion.save(request)
                                        else:
                                            clasemodificacion = CompromisoClaseModificacion.objects.get(
                                                codigo=str(cols[16]))
                                    if not str(cols[15]) == '-':
                                        if not CompromisoClaseGasto.objects.filter(codigo=str(cols[17])).exists():
                                            clasegasto = CompromisoClaseGasto(codigo=str(cols[17]),
                                                                              nombre='SIN DEFINIR')
                                            clasegasto.save(request)
                                        else:
                                            clasegasto = CompromisoClaseGasto.objects.get(codigo=str(cols[17]))
                                    fecha = None
                                    try:
                                        fecha = convertir_fecha(cols[28])
                                    except:
                                        pass
                                    if str(cols[29]).strip() == 'APROBADO':
                                        estado = 1
                                    elif str(cols[29]).strip() == 'ERRADO':
                                        estado = 2
                                    else:
                                        estado = 3
                                    if not DetalleCertificacion.objects.filter(
                                            certificacion__numerocertificacion=numerocertificacion,
                                            partidassaldo=saldopartida).exists():
                                        return JsonResponse({"result": "bad",
                                                             "mensaje": u"No se puede importar debido a que no existe la certificación N° %s." % numerocertificacion})
                                    certificacion = DetalleCertificacion.objects.filter(
                                        certificacion__numerocertificacion=numerocertificacion,
                                        partidassaldo=saldopartida)[0]
                                    if not nocur == '-':
                                        nocur = int(nocur)
                                        if not CompromisoPartida.objects.filter(nocur=nocur, local=False).exists():
                                            compromisopartida = CompromisoPartida(nocur=nocur,
                                                                                  claseregistro=claseregistro,
                                                                                  clasemodificacion=clasemodificacion,
                                                                                  clasegasto=clasegasto,
                                                                                  descripcion=descripcion,
                                                                                  fecha=fecha,
                                                                                  estado=estado)
                                            compromisopartida.save(request)
                                            certificacion.ruc = str(cols[21])
                                            certificacion.nitnombre = str(cols[22].decode('utf-8', 'ignore'))
                                            certificacion.save(request)
                                        else:
                                            compromisopartida = CompromisoPartida.objects.filter(nocur=nocur)[0]
                                        if not DetalleCompromiso.objects.filter(detallecertificacion=certificacion,
                                                                                comrpomiso=compromisopartida).exists():
                                            detallecompromiso = DetalleCompromiso(detallecertificacion=certificacion,
                                                                                  monto=monto,
                                                                                  comrpomiso=compromisopartida)
                                            detallecompromiso.save(request)
                                        else:
                                            detallecompromiso = \
                                            DetalleCompromiso.objects.filter(detallecertificacion=certificacion,
                                                                             comrpomiso=compromisopartida)[0]
                                        compromisopartida.monto_total(request)
                                    certificacion.actualiza_saldo(request)
                                    certificacion.certificacion.totales(request)
                                    certificacion.certificacion.actualiza_estado(request)
                                    saldopartida.actualizar_saldos(request)
                            linea += 1
                    log(u'Importo compromisos de partidas: %s [%s]' % (nfile._name, archivo.id), request, "edit")
                    secuencia = secuencia_presupuesto(request)
                    secuencia.fechaultimacompromisos = datetime.now()
                    secuencia.usuariomodificacompromiso = usuario
                    secuencia.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'detalle':
            try:
                data = {}
                data['detalle'] = PartidasSaldo.objects.get(pk=int(request.POST['id']))
                template = get_template('pre_saldo_partida/detalle.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_ingreso':
            try:
                data = {}
                data['detalle'] = PartidasSaldo.objects.get(pk=int(request.POST['id']))
                template = get_template('pre_saldo_partida/detalle_ingreso.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_certificacion':
            try:
                data = {}
                data['certificacion'] = certificacion = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                data['detalles'] = certificacion.detallecertificacion_set.all()
                template = get_template('pre_saldo_partida/detalle_certificacion.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_compromiso':
            try:
                data = {}
                data['compromiso'] = compromiso = CompromisoPartida.objects.get(pk=int(request.POST['id']))
                data['detalles'] = compromiso.detallecompromiso_set.all()
                template = get_template('pre_saldo_partida/detalle_compromiso.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'detalle_reforma':
            try:
                data = {}
                data['reforma'] = reforma = ReformaPartida.objects.get(pk=int(request.POST['id']))
                data['detalles'] = reforma.detallereformapartida_set.all()
                template = get_template('pre_saldo_partida/detalle_reforma.html')
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'addentidad':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaEntidad.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una entidad con ese código."})
                    entidad = PartidaEntidad(codigo=f.cleaned_data['codigo'],
                                             nombre=f.cleaned_data['descripcion'])
                    entidad.save(request)
                    log(u'adiciono entidad : %s' % entidad, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcompromiso':
            try:
                f = ComrpomisoCertificacionForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                    proveedor = Proveedor.objects.get(id=int(f.cleaned_data['nitnombre']))
                    fecha = f.cleaned_data['fecha']
                    if not fecha.year == anio:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La fecha escogida se encuentra fuera del año fiscal"})
                    compromisopartida = CompromisoPartida(descripcion=f.cleaned_data['descripcion'],
                                                          fecha=f.cleaned_data['fecha'],
                                                          claseregistro=f.cleaned_data['claseregistro'],
                                                          clasemodificacion=f.cleaned_data['clasemodificacion'],
                                                          clasegasto=f.cleaned_data['clasegasto'],
                                                          estado=1,
                                                          local=True)
                    compromisopartida.save(request)
                    secuencia = secuencia_presupuesto(request)
                    secuencia.compromisos += 1
                    secuencia.save(request)
                    compromisopartida.nocur = secuencia.compromisos
                    compromisopartida.save(request)
                    for d in datos:
                        detcertificacion = DetalleCertificacion.objects.get(pk=int(d['id']))
                        saldopartida = detcertificacion.partidassaldo
                        if not saldopartida.disponible > 0:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"No existe saldo disponible en la partida %s." % saldopartida})
                        detallecompromiso = DetalleCompromiso(comrpomiso=compromisopartida,
                                                              detallecertificacion=detcertificacion,
                                                              monto=Decimal(d['monto']))
                        detallecompromiso.save(request)
                        detcertificacion.actualiza_saldo(request)
                        saldopartida.actualizar_saldos(request)
                        detcertificacion.ruc = proveedor.identificacion
                        detcertificacion.nitnombre = proveedor.nombre
                        detcertificacion.save(request)
                        certificacion = detcertificacion.certificacion
                        certificacion.totales(request)
                        saldopartida.actualizar_saldos(request)
                    compromisopartida.monto_total(request)
                    log(u'adiciono compromiso : %s' % compromisopartida.id, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'datos_certificacion':
            try:
                data = {}
                data['certificacion'] = certificacion = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                data['detalles'] = certificacion.detallecertificacion_set.all()
                template = get_template("pre_saldo_partida/datoscertificacion.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'datos': json_content, 'concepto': certificacion.descripcion})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'addcertificacion':
            try:
                f = ComrpomisoPartidaForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                    fecha = f.cleaned_data['fecha']
                    if not fecha.year == anio:
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La fecha escogida se encuentra fuera del año fiscal"})
                    certificacionpartida = CertificacionPartida(descripcion=f.cleaned_data['descripcion'],
                                                                anioejercicio=anioe,
                                                                fecha=f.cleaned_data['fecha'],
                                                                claseregistro=f.cleaned_data['claseregistro'],
                                                                clasemodificacion=f.cleaned_data['clasemodificacion'],
                                                                clasegasto=f.cleaned_data['clasegasto'],
                                                                tipodocumento=f.cleaned_data['tipodoc'],
                                                                clasedocumento=f.cleaned_data['clasedoc'],
                                                                estado=1,
                                                                local=True)
                    certificacionpartida.save(request)
                    for d in datos:
                        saldopartida = PartidasSaldo.objects.get(pk=int(d['id']))
                        if not saldopartida.disponible > 0:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"No existe saldo disponible en la partida %s." % saldopartida})
                        detallecertificacion = DetalleCertificacion(certificacion=certificacionpartida,
                                                                    partidassaldo=saldopartida,
                                                                    estado=1,
                                                                    monto=Decimal(d['monto']),
                                                                    saldo=Decimal(d['monto']))
                        detallecertificacion.save(request)
                        detallecertificacion.actualiza_saldo(request)
                        saldopartida.actualizar_saldos(request)
                    certificacionpartida.totales(request)
                    secuencia = secuencia_presupuesto(request)
                    secuencia.certificacion += 1
                    secuencia.save(request)
                    certificacionpartida.numerocertificacion = secuencia.certificacion
                    certificacionpartida.save(request)
                    log(u'adiciono certificacion : %s [%s]' % (certificacionpartida, certificacionpartida.id), request,
                        "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addreforma':
            try:
                f = ReformaPartidaForm(request.POST)
                if f.is_valid():
                    datos = json.loads(request.POST['lista_items1'])
                    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                    fecimputacion = f.cleaned_data['fecimputacion']
                    fecdisposicion = f.cleaned_data['fecdisposicion']
                    if not fecimputacion.year == anio or not fecimputacion.year == anio:
                        return JsonResponse({"result": "bad",
                                             "mensaje": u"Una de las fechas escogidas se encuentra fuera del año fiscal"})
                    reformapartida = ReformaPartida(descripcion=f.cleaned_data['descripcion'],
                                                    claseregistro=f.cleaned_data['claseregistro'],
                                                    disposicionlegal=f.cleaned_data['disposicionlegal'],
                                                    fecimputacion=f.cleaned_data['fecimputacion'],
                                                    fecdisposicion=f.cleaned_data['fecdisposicion'],
                                                    aprobado='S',
                                                    solicitado='S',
                                                    local=True)
                    reformapartida.save(request)
                    for d in datos:
                        saldopartida = PartidasSaldo.objects.get(pk=int(d['id']))
                        if not saldopartida.disponible > 0:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"No existe saldo disponible en la partida %s." % saldopartida})
                        detallereforma = DetalleReformaPartida(reformapartida=reformapartida,
                                                               partidassaldo=saldopartida,
                                                               montosolicitado=Decimal(d['monto']),
                                                               montoaprobado=Decimal(d['monto']),
                                                               decrementa=False if Decimal(d['monto']) > 0 else True)
                        detallereforma.save(request)
                        saldopartida.actualizar_saldos(request)
                    reformapartida.totales(request)
                    if not reformapartida.montoaprobado == 0:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": "bad", "mensaje": u"Los valores ingresados no concuerdan."})
                    secuencia = secuencia_presupuesto(request)
                    secuencia.reforma += 1
                    secuencia.save(request)
                    reformapartida.nocur = secuencia.reforma
                    reformapartida.save(request)
                    log(u'adiciono reforma : %s [%s]' % (reformapartida, reformapartida.id), request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editreforma':
            try:
                f = ReformaPartidaForm(request.POST)
                if f.is_valid():
                    reforma = ReformaPartida.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista_items1'])
                    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                    reforma.claseregistro = f.cleaned_data['claseregistro']
                    reforma.disposicionlegal = f.cleaned_data['disposicionlegal']
                    reforma.save(request)
                    if reforma.local:
                        fecimputacion = f.cleaned_data['fecimputacion']
                        fecdisposicion = f.cleaned_data['fecdisposicion']
                        if not fecimputacion.year == anio or not fecimputacion.year == anio:
                            return JsonResponse({"result": "bad",
                                                 "mensaje": u"Una de las fechas escogidas se encuentra fuera del año fiscal"})
                        reforma.descripcion = f.cleaned_data['descripcion']
                        reforma.fecimputacion = f.cleaned_data['fecimputacion']
                        reforma.fecdisposicion = f.cleaned_data['fecdisposicion']
                        partida_anterior = []
                        for anterior in reforma.detallereformapartida_set.all():
                            partida_anterior.append(anterior.partidassaldo)
                        reforma.detallereformapartida_set.all().delete()
                        for d in datos:
                            saldopartida = PartidasSaldo.objects.get(pk=int(d['id']))
                            if not saldopartida.disponible > 0:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"No existe saldo disponible en la partida %s." % saldopartida})
                            detallepartida = DetalleReformaPartida(reformapartida=reforma,
                                                                   partidassaldo=saldopartida,
                                                                   decrementa=False if Decimal(
                                                                       d['monto']) > 0 else True,
                                                                   montosolicitado=Decimal(d['monto']),
                                                                   montoaprobado=Decimal(d['monto']))
                            detallepartida.save(request)
                            saldopartida.actualizar_saldos(request)
                        for partida in partida_anterior:
                            partida.actualizar_saldos(request)
                    reforma.totales(request)
                    log(u'edito reforma : %s [%s]' % (reforma, reforma.id), request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addunidadejec':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaUnidadEjecutoria.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una unidad con ese código."})
                    unidad = PartidaUnidadEjecutoria(codigo=f.cleaned_data['codigo'],
                                                     nombre=f.cleaned_data['descripcion'])
                    unidad.save(request)
                    log(u'adiciono unidad de ejecucion: %s' % unidad, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addclasereg':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if CompromisoClaseRegistro.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe una clase de registro con ese código."})
                    claseregistro = CompromisoClaseRegistro(codigo=f.cleaned_data['codigo'],
                                                            nombre=f.cleaned_data['descripcion'])
                    claseregistro.save(request)
                    log(u'adiciono clase : %s' % claseregistro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addclasegasto':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if CompromisoClaseGasto.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe una clase de gasto con ese código."})
                    clasegasto = CompromisoClaseGasto(codigo=f.cleaned_data['codigo'],
                                                      nombre=f.cleaned_data['descripcion'])
                    clasegasto.save(request)
                    log(u'adiciono clase gasto: %s' % clasegasto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addclasemod':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if CompromisoClaseModificacion.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe una clase de modificación con ese código."})
                    clasemodificacion = CompromisoClaseModificacion(codigo=f.cleaned_data['codigo'],
                                                                    nombre=f.cleaned_data['descripcion'])
                    clasemodificacion.save(request)
                    log(u'adiciono clase modificacion: %s' % clasemodificacion, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addtipodoc':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PresupuestoTipoDocumentoRespaldo.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe un tipo de documento respaldo con ese código."})
                    tipodocumento = PresupuestoTipoDocumentoRespaldo(codigo=f.cleaned_data['codigo'],
                                                                     nombre=f.cleaned_data['descripcion'])
                    tipodocumento.save(request)
                    log(u'adiciono tipo documento : %s' % tipodocumento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addclasedoc':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PresupuestoClaseDocumentoRespaldo.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"Ya existe una clase de documento respaldo con ese código."})
                    clasedocumento = PresupuestoClaseDocumentoRespaldo(codigo=f.cleaned_data['codigo'],
                                                                       nombre=f.cleaned_data['descripcion'])
                    clasedocumento.save(request)
                    log(u'adiciono clase documento: %s' % clasedocumento, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addunidaddes':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaUnidadDesconcentrada.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una unidad con ese código."})
                    unidad = PartidaUnidadDesconcentrada(codigo=f.cleaned_data['codigo'],
                                                         nombre=f.cleaned_data['descripcion'])
                    unidad.save(request)
                    log(u'adiciono unidades : %s' % unidad, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addprograma':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaPrograma.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un programa con ese código."})
                    programa = PartidaPrograma(codigo=f.cleaned_data['codigo'],
                                               nombre=f.cleaned_data['descripcion'])
                    programa.save(request)
                    log(u'adiciono programa : %s' % programa, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addsub':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaSubprograma.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un subprograma con ese código."})
                    programa = PartidaSubprograma(codigo=f.cleaned_data['codigo'],
                                                  nombre=f.cleaned_data['descripcion'])
                    programa.save(request)
                    log(u'adiciono partida subprograma : %s' % programa, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addproyecto':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaProyecto.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un proyecto con ese código."})
                    proyecto = PartidaProyecto(codigo=f.cleaned_data['codigo'],
                                               nombre=f.cleaned_data['descripcion'])
                    proyecto.save(request)
                    log(u'adiciono proyecto: %s' % proyecto, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addactividad':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaActividad.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una actividad con ese código."})
                    act = PartidaActividad(codigo=f.cleaned_data['codigo'],
                                           nombre=f.cleaned_data['descripcion'])
                    act.save(request)
                    log(u'adiciono actividad : %s' % act, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addobra':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaObra.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una obra con ese código."})
                    obra = PartidaObra(codigo=f.cleaned_data['codigo'],
                                       nombre=f.cleaned_data['descripcion'])
                    obra.save(request)
                    log(u'adiciono obra : %s' % obra, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addgeo':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaGeografico.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un detalle con ese código."})
                    geo = PartidaGeografico(codigo=f.cleaned_data['codigo'],
                                            nombre=f.cleaned_data['descripcion'])
                    geo.save(request)
                    log(u'adiciono partida geografico : %s' % geo, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addfuente':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaFuente.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una fuente con ese código."})
                    fuente = PartidaFuente(codigo=f.cleaned_data['codigo'],
                                           nombre=f.cleaned_data['descripcion'])
                    fuente.save(request)
                    log(u'adiciono partida fuente : %s' % fuente, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addorg':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaOrganismo.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un detalle con ese código."})
                    org = PartidaOrganismo(codigo=f.cleaned_data['codigo'],
                                           nombre=f.cleaned_data['descripcion'])
                    org.save(request)
                    log(u'adiciono partida organismo : %s' % org, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addcor':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if PartidaCorrelativo.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una obra con ese código."})
                    cor = PartidaCorrelativo(codigo=f.cleaned_data['codigo'],
                                             nombre=f.cleaned_data['descripcion'])
                    cor.save(request)
                    log(u'adiciono partiva correlativo : %s' % cor, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addpar':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    if Partida.objects.filter(codigo=f.cleaned_data['codigo']):
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una obra con ese código."})
                    par = Partida(codigo=f.cleaned_data['codigo'],
                                  nombre=f.cleaned_data['descripcion'])
                    par.save(request)
                    log(u'adiciono partida : %s' % par, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editentidad':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaEntidad.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'adiciono entidad : %s' % detalle, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteentidad':
            try:
                detalle = PartidaEntidad.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino entidad: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editclasereg':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = CompromisoClaseRegistro.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Clase Registro Compormiso : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteclasereg':
            try:
                detalle = CompromisoClaseRegistro.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino clase registro: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editclasemod':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = CompromisoClaseModificacion.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Clase Modificacion Compormiso : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteclasemod':
            try:
                detalle = CompromisoClaseModificacion.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino clase modificación: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editclasegasto':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = CompromisoClaseGasto.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Clase Gasto Compormiso : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteclasegasto':
            try:
                detalle = CompromisoClaseGasto.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino clase gasto: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editclasedoc':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PresupuestoClaseDocumentoRespaldo.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Clase Gasto Compormiso : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteclasedoc':
            try:
                detalle = PresupuestoClaseDocumentoRespaldo.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino clase documento: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edittipodoc':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PresupuestoTipoDocumentoRespaldo.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito presupuesto tipo documento respaldo: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletetipodoc':
            try:
                detalle = PresupuestoTipoDocumentoRespaldo.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino tipo documento: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editunidadejec':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaUnidadEjecutoria.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito partida unidad ejecutora : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteunidadejec':
            try:
                detalle = PartidaUnidadEjecutoria.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino unidad: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editunidaddesc':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaUnidadDesconcentrada.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Unidad Desconcentrada : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'liquidarcert':
            try:
                certificacion = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                saldo = certificacion.saldo
                certificacion.liquidado = saldo
                certificacion.estado = 3
                certificacion.save(request)
                for detalle in certificacion.detallecertificacion_set.all():
                    detalle.liquidado = detalle.saldo
                    detalle.estado = 3
                    detalle.actualiza_saldo(request)
                    detalle.partidassaldo.actualizar_saldos(request)
                certificacion.totales(request)
                log(u'Adiciono Certificacion de Partida Presupuestaria: %s' % certificacion, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcertificacion':
            try:
                f = ComrpomisoPartidaForm(request.POST)
                if f.is_valid():
                    certificacion = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                    datos = json.loads(request.POST['lista_items1'])
                    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                    certificacion.clasemodificacion = f.cleaned_data['clasemodificacion']
                    certificacion.claseregistro = f.cleaned_data['claseregistro']
                    certificacion.clasegasto = f.cleaned_data['clasegasto']
                    certificacion.tipodocumento = f.cleaned_data['tipodoc']
                    certificacion.clasedocumento = f.cleaned_data['clasedoc']
                    certificacion.save(request)
                    if certificacion.local:
                        fecha = f.cleaned_data['fecha']
                        if not fecha.year == anio:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha escogida se encuentra fuera del año fiscal"})
                        certificacion.descripcion = f.cleaned_data['descripcion']
                        certificacion.fecha = f.cleaned_data['fecha']
                        partida_anterior = []
                        for anterior in certificacion.detallecertificacion_set.all():
                            partida_anterior.append(anterior.partidassaldo)
                        certificacion.detallecertificacion_set.all().delete()
                        for d in datos:
                            saldopartida = PartidasSaldo.objects.get(pk=int(d['id']))
                            if not saldopartida.disponible > 0:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"No existe saldo disponible en la partida %s." % saldopartida})
                            detallecertificacion = DetalleCertificacion(certificacion=certificacion,
                                                                        partidassaldo=saldopartida,
                                                                        estado=1,
                                                                        monto=Decimal(d['monto']),
                                                                        saldo=Decimal(d['monto']))
                            detallecertificacion.save(request)
                            detallecertificacion.actualiza_saldo(request)
                            saldopartida.actualizar_saldos(request)
                        for partida in partida_anterior:
                            partida.actualizar_saldos(request)
                    certificacion.totales(request)
                    log(u'Edito Certificacion de Partida Presupuestaria: %s' % certificacion, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcompromiso':
            try:
                f = ComrpomisoCertificacionForm(request.POST)
                if f.is_valid():
                    compromiso = CompromisoPartida.objects.get(pk=int(request.POST['id']))
                    compromiso.descripcion = f.cleaned_data['descripcion']
                    compromiso.claseregistro = f.cleaned_data['claseregistro']
                    compromiso.clasemodificacion = f.cleaned_data['clasemodificacion']
                    compromiso.clasegasto = f.cleaned_data['clasegasto']
                    proveedor = Proveedor.objects.get(id=int(f.cleaned_data['nitnombre']))
                    datos = json.loads(request.POST['lista_items1'])
                    anioe = AnioEjercicio.objects.get(anioejercicio=anio)
                    if compromiso.local:
                        fecha = f.cleaned_data['fecha']
                        if not fecha.year == anio:
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"La fecha escogida se encuentra fuera del año fiscal"})
                        compromiso.fecha = f.cleaned_data['fecha']
                        partida_anterior = []
                        for anterior in compromiso.detallecompromiso_set.all():
                            partida_anterior.append(anterior.detallecertificacion.partidassaldo)
                            compromiso.detallecompromiso_set.all().delete()
                        for d in datos:
                            detcertificacion = DetalleCertificacion.objects.get(pk=int(d['id']))
                            saldopartida = detcertificacion.partidassaldo
                            if not saldopartida.disponible > 0:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"No existe saldo disponible en la partida %s." % saldopartida})
                            detallecompromiso = DetalleCompromiso(comrpomiso=compromiso,
                                                                  detallecertificacion=detcertificacion,
                                                                  monto=Decimal(d['monto']))
                            detallecompromiso.save(request)
                            detcertificacion.actualiza_saldo(request)
                            saldopartida.actualizar_saldos(request)
                            detcertificacion.ruc = proveedor.identificacion
                            detcertificacion.nitnombre = proveedor.nombre
                            detcertificacion.save(request)
                            certificacion = detcertificacion.certificacion
                            certificacion.totales(request)
                            saldopartida.actualizar_saldos(request)
                        for partida in partida_anterior:
                            partida.actualizar_saldos(request)
                    compromiso.monto_total(request)
                    log(u'Edito Compormiso de Partida Presupuestaria: %s' % compromiso, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletecertificacion':
            try:
                certificacion = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                saldopartidaanterior = certificacion.partidassaldo
                certificacion.delete()
                saldopartidaanterior.actualizar_saldos(request)
                log(u'Elimino certificación: %s' % certificacion, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletereforma':
            try:
                reforma = ReformaPartida.objects.get(pk=int(request.POST['id']))
                saldopartidaanterior = reforma.partidassaldo
                reforma.delete()
                saldopartidaanterior.actualizar_saldos(request)
                log(u'Elimino reforma: %s' % reforma, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletecompromiso':
            try:
                compromiso = CompromisoPartida.objects.get(pk=int(request.POST['id']))
                certificacion = compromiso.certificacion
                saldopartidaanterior = certificacion.partidassaldo
                certificacion.nitnombre = ''
                certificacion.ruc = ''
                certificacion.actualiza_saldo(request)
                certificacion.save(request)
                compromiso.delete()
                saldopartidaanterior.actualizar_saldos(request)
                log(u'Elimino compromiso: %s' % compromiso, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteunidaddesc':
            try:
                detalle = PartidaUnidadDesconcentrada.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino unidad: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editprog':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaPrograma.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Elimino unidad: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteprog':
            try:
                detalle = PartidaPrograma.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino programa: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editsub':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaSubprograma.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Subprograma: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletesub':
            try:
                detalle = PartidaSubprograma.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino subprograma: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editproyecto':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaProyecto.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Proyecto: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteproyecto':
            try:
                detalle = PartidaProyecto.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino proyecto: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editact':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaActividad.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Actividad: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteact':
            try:
                detalle = PartidaActividad.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino actividad: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editobra':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaObra.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Obra: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteobra':
            try:
                detalle = PartidaObra.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino obra: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editgeo':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaGeografico.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Geografico: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletegeo':
            try:
                detalle = PartidaGeografico.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino geográfico: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editfuente':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaFuente.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Fuente: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletefuente':
            try:
                detalle = PartidaFuente.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino fuente: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editorg':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaOrganismo.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Organismo: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deleteorg':
            try:
                detalle = PartidaOrganismo.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino organismo: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcor':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = PartidaCorrelativo.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida Correlativo: %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletecor':
            try:
                detalle = PartidaCorrelativo.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino correlativo: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editpar':
            try:
                f = PartidaDetallesForm(request.POST)
                if f.is_valid():
                    detalle = Partida.objects.get(pk=int(request.POST['id']))
                    detalle.nombre = f.cleaned_data['descripcion']
                    detalle.save(request)
                    log(u'Edito Partida : %s' % detalle, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'deletepar':
            try:
                detalle = Partida.objects.get(pk=int(request.POST['id']))
                detalle.delete()
                log(u'Elimino partida: %s' % detalle, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'ingresar_fecha':
            try:
                certificado = CertificacionPartida.objects.get(pk=int(request.POST['id']))
                numero = certificado.numerocertificacion
                anioejercicio = certificado.anioejercicio
                if FechaCertificacion.objects.filter(numerocertificacion=numero, status=True).exists():
                    fechacertificacion = FechaCertificacion.objects.filter(numerocertificacion=numero, status=True)[0]
                    if request.POST['fechainicio'] != '':
                        fechacertificacion.fechainicio = convertir_fecha(request.POST['fechainicio'])
                    else:
                        fechacertificacion.fechainicio = None
                    if request.POST['fechafin'] != '':
                        fechacertificacion.fechafin = convertir_fecha(request.POST['fechafin'])
                    else:
                        fechacertificacion.fechafin = None
                    fechacertificacion.save(request)
                else:
                    fechainicio = None
                    if request.POST['fechainicio'] != '':
                        fechainicio = convertir_fecha(request.POST['fechainicio'])

                    fechafin = None
                    if request.POST['fechafin'] != '':
                        fechafin = convertir_fecha(request.POST['fechafin'])

                    fechacertificacion = FechaCertificacion(numerocertificacion=numero,
                                                            fechainicio=fechainicio,
                                                            fechafin=fechafin,
                                                            anioejercicio=anioejercicio)
                    fechacertificacion.save(request)
                log(u'Ingreso fecha en certificado: %s' % certificado, request, "edit")
                return JsonResponse({"result": "ok"})

            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:

            data['action'] = action = request.GET['action']
            if action == 'addPartida':
                try:
                    data['form2'] = PartidaSaldoForm()
                    template = get_template("pre_saldo_partida/modal/formpartida.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            if action == 'importar':
                try:
                    data['title'] = u'Importar datos del sistema de gobierno'
                    data['form'] = ImportarArchivoCSVForm()
                    return render(request, "pre_saldo_partida/importar.html", data)
                except Exception as ex:
                    pass

            if action == 'importar_ingresos':
                try:
                    data['title'] = u'Importar datos del sistema de gobierno'
                    data['form'] = ImportarArchivoCSVForm()
                    return render(request, "pre_saldo_partida/importaringresos.html", data)
                except Exception as ex:
                    pass

            if action == 'importar_certificacion':
                try:
                    data['title'] = u'Importar Certificaciones'
                    data['form'] = ImportarArchivoCSVForm()
                    return render(request, "pre_saldo_partida/importar_partida.html", data)
                except Exception as ex:
                    pass

            if action == 'importar_compromiso':
                try:
                    data['title'] = u'Importar Compromisos'
                    data['form'] = ImportarArchivoCSVForm()
                    return render(request, "pre_saldo_partida/importar_compromiso.html", data)
                except Exception as ex:
                    pass

            if action == 'cambioperiodo':
                try:
                    anio = AnioEjercicio.objects.get(id=int(request.GET['id']))
                    request.session['aniofiscalpresupuesto'] = anio.anioejercicio
                except Exception as ex:
                    pass

            if action == 'importar_reformas':
                try:
                    data['title'] = u'Importar Reformas'
                    data['form'] = ImportarArchivoCSVForm()
                    return render(request, "pre_saldo_partida/importar_reformas.html", data)
                except Exception as ex:
                    pass

            if action == 'addentidad':
                try:
                    data['title'] = u'Adicionar Entidades de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addentidad.html', data)
                except Exception as ex:
                    pass

            if action == 'addcertificacion':
                try:
                    data['title'] = u'Adicionar Certificación'
                    data['form'] = ComrpomisoPartidaForm()
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    form = DetalleCertificacionForm()
                    form.adicionar(anio)
                    data['form2'] = form
                    return render(request, 'pre_saldo_partida/addcertificacion.html', data)
                except Exception as ex:
                    pass

            if action == 'addcompromiso':
                try:
                    data['title'] = u'Adicionar Compromiso'
                    form = ComrpomisoCertificacionForm()
                    certificacion = None
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    if 'id' in request.GET:
                        certificacion = CertificacionPartida.objects.get(pk=int(request.GET['id']))
                    form.adicionar(anio, certificacion)
                    data['form'] = form
                    data['form2'] = DetalleCompromisoForm()
                    data['certificacion'] = certificacion
                    return render(request, 'pre_saldo_partida/addcompromiso.html', data)
                except Exception as ex:
                    pass

            if action == 'addcertificacion':
                try:
                    data['title'] = u'Adicionar Certificación'
                    data['form'] = ComrpomisoPartidaForm()
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    form = DetalleCertificacionForm()
                    form.adicionar(anio)
                    data['form2'] = form
                    return render(request, 'pre_saldo_partida/addcertificacion.html', data)
                except Exception as ex:
                    pass

            if action == 'addreforma':
                try:
                    data['title'] = u'Adicionar Reforma'
                    data['form'] = ReformaPartidaForm()
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    form = DetalleReformaPartidaForm()
                    form.adicionar(anio)
                    data['form2'] = form
                    return render(request, 'pre_saldo_partida/addreforma.html', data)
                except Exception as ex:
                    pass

            if action == 'addunidadejec':
                try:
                    data['title'] = u'Adicionar Unidades Ejecutoria de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addunidadeject.html', data)
                except Exception as ex:
                    pass

            if action == 'addunidaddes':
                try:
                    data['title'] = u'Adicionar Unidades Desc de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addunidaddes.html', data)
                except Exception as ex:
                    pass

            if action == 'addprograma':
                try:
                    data['title'] = u'Adicionar Programas de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addprograma.html', data)
                except Exception as ex:
                    pass

            if action == 'addsub':
                try:
                    data['title'] = u'Adicionar Subprogramas de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addsub.html', data)
                except Exception as ex:
                    pass

            if action == 'addproyecto':
                try:
                    data['title'] = u'Adicionar Proyectos de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addproyecto.html', data)
                except Exception as ex:
                    pass

            if action == 'addactividad':
                try:
                    data['title'] = u'Adicionar Actividad de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addactividad.html', data)
                except Exception as ex:
                    pass

            if action == 'addobra':
                try:
                    data['title'] = u'Adicionar Obras de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addobra.html', data)
                except Exception as ex:
                    pass

            if action == 'addgeo':
                try:
                    data['title'] = u'Adicionar Geográfico de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addgeo.html', data)
                except Exception as ex:
                    pass

            if action == 'addfuente':
                try:
                    data['title'] = u'Adicionar Fuentes de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addfuente.html', data)
                except Exception as ex:
                    pass

            if action == 'addorg':
                try:
                    data['title'] = u'Adicionar Organismo de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addorg.html', data)
                except Exception as ex:
                    pass

            if action == 'addcor':
                try:
                    data['title'] = u'Adicionar Correlativo de Partidas'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addcor.html', data)
                except Exception as ex:
                    pass

            if action == 'addpar':
                try:
                    data['title'] = u'Adicionar Partida'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addpar.html', data)
                except Exception as ex:
                    pass

            if action == 'editentidad':
                try:
                    data['title'] = u'Editar Entidad de Partida'
                    data['entidad'] = entidad = PartidaEntidad.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': entidad.nombre,
                                                        'codigo': entidad.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editentidad.html", data)
                except Exception as ex:
                    pass

            if action == 'liquidarcert':
                try:
                    data['title'] = u'Confirmar liquidar certificacion'
                    data['certificacion'] = CertificacionPartida.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/liquidarcert.html", data)
                except:
                    pass

            if action == 'editcompromiso':
                try:
                    data['title'] = u'Editar Compromiso'
                    certificacion = None
                    data['compromiso'] = compromiso = CompromisoPartida.objects.get(pk=int(request.GET['id']))
                    data['detalles'] = compromiso.detallecompromiso_set.all()
                    detallec = compromiso.detallecompromiso_set.all()[0].detallecertificacion
                    certificacion = detallec.certificacion
                    proveedor = Proveedor.objects.filter(identificacion=detallec.ruc)[0]
                    form = ComrpomisoCertificacionForm(initial={'certificacion': certificacion,
                                                                'descripcion': compromiso.descripcion,
                                                                'fecha': compromiso.fecha,
                                                                'claseregistro': compromiso.claseregistro,
                                                                'clasemodificacion': compromiso.clasemodificacion,
                                                                'nitnombre': proveedor.id,
                                                                'clasegasto': compromiso.clasegasto})
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    form.editar(proveedor)
                    data['form'] = form
                    data['form2'] = DetalleCompromisoForm
                    return render(request, 'pre_saldo_partida/editcompromiso.html', data)
                except Exception as ex:
                    pass

            if action == 'editcertificacion':
                try:
                    data['title'] = u'Editar Certificacion'
                    data['certificacion'] = certificacion = CertificacionPartida.objects.get(pk=int(request.GET['id']))
                    data['detalles'] = certificacion.detallecertificacion_set.all()
                    form = ComrpomisoPartidaForm(initial={'descripcion': certificacion.descripcion,
                                                          'numerocertificacion': certificacion.numerocertificacion,
                                                          'clasegasto': certificacion.clasegasto,
                                                          'claseregistro': certificacion.claseregistro,
                                                          'clasemodificacion': certificacion.clasemodificacion,
                                                          'tipodoc': certificacion.tipodocumento,
                                                          'clasedoc': certificacion.clasedocumento,
                                                          'fecha': certificacion.fecha,
                                                          'monto': certificacion.monto})
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    form.editar(certificacion)
                    data['form'] = form
                    data['form2'] = DetalleCertificacionForm()
                    return render(request, 'pre_saldo_partida/editcertificacion.html', data)
                except Exception as ex:
                    pass

            if action == 'editreforma':
                try:
                    data['title'] = u'Editar Reforma'
                    data['reforma'] = reforma = ReformaPartida.objects.get(pk=int(request.GET['id']))
                    data['detalles'] = reforma.detallereformapartida_set.all()
                    form = ReformaPartidaForm(initial={'descripcion': reforma.descripcion,
                                                       'claseregistro': reforma.claseregistro,
                                                       'fecimputacion': reforma.fecimputacion,
                                                       'disposicionlegal': reforma.disposicionlegal,
                                                       'fecdisposicion': reforma.fecdisposicion})
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    form.editar(reforma)
                    data['form'] = form
                    data['form2'] = DetalleReformaPartidaForm()
                    return render(request, 'pre_saldo_partida/editreforma.html', data)
                except Exception as ex:
                    pass

            if action == 'deletecertificacion':
                try:
                    data['title'] = u'Confirmar eliminar Certificación de Partida'
                    data['certificacion'] = CertificacionPartida.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletecertificacion.html", data)
                except Exception as ex:
                    pass

            if action == 'deletereforma':
                try:
                    data['title'] = u'Confirmar eliminar Reforma de Partida'
                    data['reforma'] = ReformaPartida.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletereforma.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecompromiso':
                try:
                    data['title'] = u'Confirmar eliminar Compromiso'
                    data['compromiso'] = CompromisoPartida.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletecompromiso.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteentidad':
                try:
                    data['title'] = u'Confirmar eliminar Entidad'
                    data['entidad'] = entidad = PartidaEntidad.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteentidad.html", data)
                except Exception as ex:
                    pass

            if action == 'editunidadejec':
                try:
                    data['title'] = u'Editar Unidad Ejecutoria de Partida'
                    data['detalle'] = detalle = PartidaUnidadEjecutoria.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editunidadejec.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteunidadejec':
                try:
                    data['title'] = u'Confirmar eliminar Unidad'
                    data['detalle'] = detalle = PartidaUnidadEjecutoria.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteunidadeject.html", data)
                except Exception as ex:
                    pass

            if action == 'editunidaddesc':
                try:
                    data['title'] = u'Editar Unidad Desconcentrada de Partida'
                    data['detalle'] = detalle = PartidaUnidadDesconcentrada.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editunidaddesc.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteunidaddesc':
                try:
                    data['title'] = u'Confirmar eliminar Unidad'
                    data['detalle'] = detalle = PartidaUnidadDesconcentrada.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteunidaddesc.html", data)
                except Exception as ex:
                    pass

            if action == 'editprog':
                try:
                    data['title'] = u'Editar Programa de Partida'
                    data['detalle'] = detalle = PartidaPrograma.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editprog.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteprog':
                try:
                    data['title'] = u'Confirmar eliminar Programa'
                    data['detalle'] = detalle = PartidaPrograma.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteprog.html", data)
                except Exception as ex:
                    pass

            if action == 'editsub':
                try:
                    data['title'] = u'Editar SubPrograma de Partida'
                    data['detalle'] = detalle = PartidaSubprograma.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editsub.html", data)
                except Exception as ex:
                    pass

            if action == 'deletesub':
                try:
                    data['title'] = u'Confirmar eliminar SubPrograma'
                    data['detalle'] = detalle = PartidaSubprograma.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletesub.html", data)
                except Exception as ex:
                    pass

            if action == 'editproyecto':
                try:
                    data['title'] = u'Editar Proyecto de Partida'
                    data['detalle'] = detalle = PartidaProyecto.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editproyecto.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteproyecto':
                try:
                    data['title'] = u'Confirmar eliminar Proyecto'
                    data['detalle'] = detalle = PartidaProyecto.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteproyecto.html", data)
                except Exception as ex:
                    pass

            if action == 'editact':
                try:
                    data['title'] = u'Editar Actividad de Partida'
                    data['detalle'] = detalle = PartidaActividad.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editact.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteact':
                try:
                    data['title'] = u'Confirmar eliminar Actividad'
                    data['detalle'] = detalle = PartidaActividad.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteact.html", data)
                except Exception as ex:
                    pass

            if action == 'editobra':
                try:
                    data['title'] = u'Editar Obra de Partida'
                    data['detalle'] = detalle = PartidaObra.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editobra.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteobra':
                try:
                    data['title'] = u'Confirmar eliminar Obra'
                    data['detalle'] = detalle = PartidaObra.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteobra.html", data)
                except Exception as ex:
                    pass

            if action == 'editfuente':
                try:
                    data['title'] = u'Editar Fuente'
                    data['detalle'] = detalle = PartidaFuente.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editfuente.html", data)
                except Exception as ex:
                    pass

            if action == 'deletefuente':
                try:
                    data['title'] = u'Confirmar eliminar Fuente'
                    data['detalle'] = detalle = PartidaFuente.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletefuente.html", data)
                except Exception as ex:
                    pass

            if action == 'editorg':
                try:
                    data['title'] = u'Editar Organismo de Partida'
                    data['detalle'] = detalle = PartidaOrganismo.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editorg.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteorg':
                try:
                    data['title'] = u'Confirmar eliminar Organismo'
                    data['detalle'] = detalle = PartidaOrganismo.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteorg.html", data)
                except Exception as ex:
                    pass

            if action == 'editgeo':
                try:
                    data['title'] = u'Editar Geográfico'
                    data['detalle'] = detalle = PartidaGeografico.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editgeo.html", data)
                except Exception as ex:
                    pass

            if action == 'deletegeo':
                try:
                    data['title'] = u'Confirmar eliminar Geográfico'
                    data['detalle'] = detalle = PartidaGeografico.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletegeo.html", data)
                except Exception as ex:
                    pass

            if action == 'editcor':
                try:
                    data['title'] = u'Editar Correlativo de Partida'
                    data['detalle'] = detalle = PartidaCorrelativo.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editcor.html", data)
                except Exception as ex:
                    pass

            if action == 'deletecor':
                try:
                    data['title'] = u'Confirmar eliminar Correlativo'
                    data['detalle'] = detalle = PartidaCorrelativo.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletecor.html", data)
                except Exception as ex:
                    pass

            if action == 'editpar':
                try:
                    data['title'] = u'Editar Partida'
                    data['detalle'] = detalle = Partida.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editpar.html", data)
                except Exception as ex:
                    pass

            if action == 'deletepar':
                try:
                    data['title'] = u'Confirmar eliminar Partida'
                    data['detalle'] = detalle = Partida.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletepar.html", data)
                except Exception as ex:
                    pass

            if action == 'addclasereg':
                try:
                    data['title'] = u'Adicionar Clase Registro'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addclasereg.html', data)
                except Exception as ex:
                    pass

            if action == 'editclasereg':
                try:
                    data['title'] = u'Editar Clase Registro'
                    data['detalle'] = detalle = CompromisoClaseRegistro.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre,
                                                        'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editclasereg.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteclasereg':
                try:
                    data['title'] = u'Confirmar eliminar Clase Registro'
                    data['detalle'] = detalle = CompromisoClaseRegistro.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteclasereg.html", data)
                except Exception as ex:
                    pass

            if action == 'addclasegasto':
                try:
                    data['title'] = u'Adicionar Clase Gasto'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addclasegasto.html', data)
                except Exception as ex:
                    pass

            if action == 'editclasegasto':
                try:
                    data['title'] = u'Editar Clase Gasto'
                    data['detalle'] = detalle = CompromisoClaseGasto.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre, 'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editclasegasto.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteclasegasto':
                try:
                    data['title'] = u'Confirmar eliminar Clase Gasto'
                    data['detalle'] = detalle = CompromisoClaseGasto.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteclasegasto.html", data)
                except Exception as ex:
                    pass

            if action == 'addclasemod':
                try:
                    data['title'] = u'Adicionar Clase Modificacion'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addclasemod.html', data)
                except Exception as ex:
                    pass

            if action == 'editclasemod':
                try:
                    data['title'] = u'Editar Clase Modificacion'
                    data['detalle'] = detalle = CompromisoClaseModificacion.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre, 'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editclasemod.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteclasemod':
                try:
                    data['title'] = u'Confirmar eliminar Clase Modificacion'
                    data['detalle'] = detalle = CompromisoClaseModificacion.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteclasemod.html", data)
                except Exception as ex:
                    pass

            if action == 'addtipodoc':
                try:
                    data['title'] = u'Adicionar Tipo de Documento'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addtipodoc.html', data)
                except Exception as ex:
                    pass

            if action == 'edittipodoc':
                try:
                    data['title'] = u'Editar Tipo de Documento'
                    data['detalle'] = detalle = PresupuestoTipoDocumentoRespaldo.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre, 'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/edittipodoc.html", data)
                except Exception as ex:
                    pass

            if action == 'deletetipodoc':
                try:
                    data['title'] = u'Confirmar eliminar Tipo de Documento'
                    data['detalle'] = detalle = PresupuestoTipoDocumentoRespaldo.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deletetipodoc.html", data)
                except Exception as ex:
                    pass

            if action == 'addclasedoc':
                try:
                    data['title'] = u'Adicionar Clase Documento'
                    data['form'] = PartidaDetallesForm()
                    return render(request, 'pre_saldo_partida/addclasedoc.html', data)
                except Exception as ex:
                    pass

            if action == 'editclasedoc':
                try:
                    data['title'] = u'Editar Clase Documento'
                    data['detalle'] = detalle = PresupuestoClaseDocumentoRespaldo.objects.get(pk=int(request.GET['id']))
                    form = PartidaDetallesForm(initial={'descripcion': detalle.nombre, 'codigo': detalle.codigo})
                    form.editar()
                    data['form'] = form
                    return render(request, "pre_saldo_partida/editclasedoc.html", data)
                except Exception as ex:
                    pass

            if action == 'deleteclasedoc':
                try:
                    data['title'] = u'Confirmar eliminar Clase Documento'
                    data['detalle'] = detalle = PresupuestoClaseDocumentoRespaldo.objects.get(pk=int(request.GET['id']))
                    return render(request, "pre_saldo_partida/deleteclasedoc.html", data)
                except Exception as ex:
                    pass

            if action == 'mantenimiento':
                try:
                    data['title'] = u'Mantenimientos.'
                    data['partidas'] = Partida.objects.all()
                    data['entidades'] = PartidaEntidad.objects.all()
                    data['unidadesejec'] = PartidaUnidadEjecutoria.objects.all()
                    data['unidadesdesc'] = PartidaUnidadDesconcentrada.objects.all()
                    data['programas'] = PartidaPrograma.objects.all()
                    data['subprogramas'] = PartidaSubprograma.objects.all()
                    data['proyectos'] = PartidaProyecto.objects.all()
                    data['actividades'] = PartidaActividad.objects.all()
                    data['obras'] = PartidaObra.objects.all()
                    data['geograficos'] = PartidaGeografico.objects.all()
                    data['fuentes'] = PartidaFuente.objects.all()
                    data['organismos'] = PartidaOrganismo.objects.all()
                    data['correlativos'] = PartidaCorrelativo.objects.all()
                    data['claseregistros'] = CompromisoClaseRegistro.objects.all()
                    data['clasegastos'] = CompromisoClaseGasto.objects.all()
                    data['clasemodificaciones'] = CompromisoClaseModificacion.objects.all()
                    data['tipodocumentos'] = PresupuestoTipoDocumentoRespaldo.objects.all()
                    data['clasedocumentos'] = PresupuestoClaseDocumentoRespaldo.objects.all()
                    return render(request, "pre_saldo_partida/mantenimiento.html", data)
                except Exception as ex:
                    pass

            if action == 'listcertificaciones':
                try:
                    data['title'] = u'Certificaciones de Partidas Presupuestaria.'
                    search = None
                    ids = None
                    idc = None
                    saldos = None
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    certificaciones = CertificacionPartida.objects.filter(anioejercicio__anioejercicio=anio)
                    if 's' in request.GET:
                        search = request.GET['s']
                    data['tipo'] = 1
                    if 't' in request.GET:
                        data['tipo'] = request.GET['t']
                    if search:
                        if search.isdigit():
                            certificaciones = certificaciones.filter(Q(numerocertificacion=search) |
                                                                     Q(detallecertificacion__partidassaldo__partida__codigo__icontains=search),
                                                                     anioejercicio__anioejercicio=anio).distinct()
                        else:
                            certificaciones = certificaciones.filter(Q(descripcion__icontains=search) | Q(
                                detallecertificacion__partidassaldo__partida__codigo__icontains=search),
                                                                     anioejercicio__anioejercicio=anio).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        certificaciones = certificaciones.filter(id=ids, anioejercicio__anioejercicio=anio)
                    elif 'idc' in request.GET:
                        idc = request.GET['idc']
                        certificaciones = certificaciones.filter(detallecertificacion__partidassaldo__id=idc)
                    paging = MiPaginador(certificaciones, 50)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['idc'] = idc if idc else ""
                    data['certificaciones'] = page.object_list
                    data['anios'] = AnioEjercicio.objects.all()
                    data['anioejercicio'] = anio_ejercicio().anioejercicio
                    data['secuencia'] = secuencia_presupuesto(request)
                    data['reporte_0'] = obtener_reporte('certificacion_presupuestaria')
                    data['mianio'] = anio
                    data['form'] = FechaCertificacionForm
                    return render(request, "pre_saldo_partida/certificaciones.html", data)
                except Exception as ex:
                    pass

            if action == 'listreformas':
                try:
                    data['title'] = u'Reformas de Partidas Presupuestaria.'
                    search = None
                    ids = None
                    idc = None
                    saldos = None
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    reformas = ReformaPartida.objects.filter(
                        detallereformapartida__partidassaldo__anioejercicio__anioejercicio=anio).distinct().order_by(
                        '-nocur')
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        if search.isdigit():
                            reformas = reformas.filter(nocur=search,
                                                       detallereformapartida__partidassaldo__anioejercicio__anioejercicio=anio).distinct().order_by(
                                '-nocur').distinct()
                        else:
                            reformas = reformas.filter(Q(descripcion__icontains=search),
                                                       detallereformapartida__partidassaldo__anioejercicio__anioejercicio=anio).distinct().order_by(
                                '-nocur').distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        reformas = reformas.filter(id=ids,
                                                   detallereformapartida__partidassaldo__anioejercicio__anioejercicio=anio).distinct().order_by(
                            '-nocur')
                    elif 'idc' in request.GET:
                        idc = request.GET['idc']
                        reformas = reformas.filter(detallereformapartida__partidassaldo__id=idc).distinct().order_by(
                            '-nocur')
                    paging = MiPaginador(reformas, 50)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['idc'] = idc if idc else ""
                    data['reformas'] = page.object_list
                    data['anioejercicio'] = anio_ejercicio().anioejercicio
                    data['mianio'] = anio
                    data['secuencia'] = secuencia_presupuesto(request)
                    data['anios'] = AnioEjercicio.objects.all()
                    return render(request, "pre_saldo_partida/reformas.html", data)
                except Exception as ex:
                    pass

            if action == 'listcompromisos':
                try:
                    data['title'] = u'Compromisos de Partidas Presupuestaria.'
                    search = None
                    ids = None
                    idc = None
                    certificacion = None
                    saldos = None
                    if 'aniofiscalpresupuesto' in request.session:
                        anio = request.session['aniofiscalpresupuesto']
                    else:
                        anio = anio_ejercicio().anioejercicio
                    compromisos = CompromisoPartida.objects.filter(
                        detallecompromiso__detallecertificacion__certificacion__anioejercicio__anioejercicio=anio)
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        if search.isdigit():
                            compromisos = compromisos.filter(nocur=search,
                                                             detallecompromiso__detallecertificacion__certificacion__anioejercicio__anioejercicio=anio).distinct()
                        else:
                            compromisos = compromisos.filter(Q(descripcion__icontains=search),
                                                             detallecompromiso__detallecertificacion__certificacion__anioejercicio__anioejercicio=anio).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        compromisos = compromisos.filter(id=ids,
                                                         detallecompromiso__detallecertificacion__certificacion__anioejercicio__anioejercicio=anio)
                    elif 'idc' in request.GET:
                        idc = request.GET['idc']
                        compromisos = compromisos.filter(detallecompromiso__detallecertificacion__certificacion__id=idc,
                                                         detallecompromiso__detallecertificacion__certificacion__anioejercicio__anioejercicio=anio)
                        data['certificacion'] = CertificacionPartida.objects.get(id=idc)
                    paging = MiPaginador(compromisos, 50)
                    p = 1
                    try:
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        page = paging.page(p)
                    except:
                        page = paging.page(1)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['idc'] = idc if idc else ""
                    data['compromisos'] = page.object_list
                    data['anioejercicio'] = anio_ejercicio().anioejercicio
                    data['mianio'] = anio
                    data['secuencia'] = secuencia_presupuesto(request)
                    data['anios'] = AnioEjercicio.objects.all()
                    return render(request, "pre_saldo_partida/compromisos.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Saldos de Partidas Presupuestaria.'
            search = None
            ids = None
            saldos = None
            data['mianio'] = anio
            saldos = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio)
            data['tipoid'] = tipo = 1
            if 't' in request.GET:
                data['tipoid'] = tipo = int(request.GET['t'])
            if 's' in request.GET:
                search = request.GET['s']
                saldos = PartidasSaldo.objects.filter(Q(partida__codigo=search) |
                                                      Q(partida__nombre__icontains=search) |
                                                      Q(geografico__nombre__icontains=search) |
                                                      Q(entidad__nombre__icontains=search) |
                                                      Q(unidadejecutoria__nombre__icontains=search) |
                                                      Q(unidaddesconcentrada__nombre__icontains=search),
                                                      anioejercicio__anioejercicio=anio, partida__tipo=tipo).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                saldos = PartidasSaldo.objects.filter(id=ids, anioejercicio__anioejercicio=anio, partida__tipo=tipo)
            else:
                saldos = PartidasSaldo.objects.filter(anioejercicio__anioejercicio=anio, partida__tipo=tipo)
            paging = MiPaginador(saldos, 50)
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
            data['partidas'] = page.object_list
            data['anios'] = AnioEjercicio.objects.all()
            data['secuencia'] = secuencia_presupuesto(request)
            data['anioejercicio'] = anio_ejercicio().anioejercicio
            data['email_domain'] = EMAIL_DOMAIN
            return render(request, 'pre_saldo_partida/view.html', data)
