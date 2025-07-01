# -*- coding: latin-1 -*-
import time as pausaparaemail
import json
import random
from builtins import filter
import calendar
from decimal import Decimal, ROUND_UP
import os


from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.db.models import Sum, Q, Count, F
from django.db.models.functions import ExtractYear, TruncYear, ExtractMonth
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from xlwt import *

from Moodle_Funciones import updaterubroepunemi
from decorators import secure_module, last_access
from investigacion.funciones import FORMATOS_CELDAS_EXCEL
from posgrado.commonviews import matricularposgrado, secuencia_contratopagare
from posgrado.models import MaestriasAdmision, CohorteMaestria, ConfigFinanciamientoCohorte, Contrato
from sagest.commonviews import obtener_estado_solicitud, obtener_estados_solicitud
from sagest.models import Rubro, Pago, null_to_decimal, datetime, TipoOtroRubro, PagoLiquidacion, \
    CompromisoPagoPosgradoRecorrido, CompromisoPagoPosgrado, CompromisoPagoPosgradoGaranteArchivo
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sga.forms import MatriculaNovedadForm
from sagest.forms import ValorMaestriaForm, ConfiCohorteMaestriaForm, TipoOtroRubroIpecRubForm, InscripcionesMaestriasForm, ConfigFinanciamientoCohorteForm
from django.forms import model_to_dict
from sga.funciones import variable_valor, generar_nombre, log, convertir_fecha, MiPaginador, \
    cuenta_email_disponible_para_envio, fechatope
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Inscripcion, Periodo, Carrera, Matricula, miinstitucion, MatriculaNovedad, CUENTAS_CORREOS, \
    TIPO_MATRICULA_NOVEDAD, PeriodoCarreraCosto, ProfesorMateria, DescuentoPosgradoMatricula, DetNotificacionDeuda, \
    MESES_CHOICES, Nivel, Notificacion
from django.template import Context
from django.template.loader import get_template
from sga.tasks import send_html_mail, conectar_cuenta
from xlwt import *
from xlwt import easyxf
import xlwt

from sga.templatetags.sga_extras import encrypt
from datetime import date, timedelta
from sga.funciones_templatepdf import contratoconsultadeuda
from sga.excelbackground import reporte_cartera_vencida_general_rubro_version_final_background, reporte_presupuesto_anual_background, reporte_cartera_vencida_general_vs_cobros_rubro_version_final_background

import io
import xlsxwriter
from urllib.request import urlopen
from django.db.models.query_utils import Q
from typing import Any, Hashable, Iterable, Optional

def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    data['persona']  = request.session['persona']
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

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

        elif action == 'novedad_matricula':
            try:
                f = MatriculaNovedadForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 8388608:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 8 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        extensiones = []
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx'  or ext == '.zip'  or ext == '.rar' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx.,zip.,rar."})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})

                if f.is_valid():
                    if int(f.cleaned_data['tipo']) == 2:
                        if not 'archivo' in request.FILES:
                            return JsonResponse({"result": "bad", "mensaje": u"Debe seleccionar un archivo"})

                    matricula = Matricula.objects.get(pk=int(request.POST['idmatricula1']))

                    if MatriculaNovedad.objects.filter(matricula=matricula, tipo=f.cleaned_data['tipo']).exists():
                        tiponovedad = TIPO_MATRICULA_NOVEDAD[int(f.cleaned_data['tipo'])-1][1]
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe una novedad del tipo %s registrada para %s" % (tiponovedad, matricula)})

                    if f.cleaned_data['tipo'] == 1:
                        matriculanovedad = MatriculaNovedad(matricula = matricula,
                                                            tipo = f.cleaned_data['tipo'],
                                                            motivo = f.cleaned_data['motivo'])
                        matriculanovedad.save(request)
                    else:
                        matriculanovedad = MatriculaNovedad(matricula=matricula,
                                                            tipo=f.cleaned_data['tipo'],
                                                            motivo=f.cleaned_data['motivo'],
                                                            tipodescuento=f.cleaned_data['tipodescuento'],
                                                            porcentajedescuento=f.cleaned_data['porcentajedescuento'])
                        matriculanovedad.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("novedad_matricula_", newfile._name)
                        matriculanovedad.archivo = newfile
                        matriculanovedad.save(request)

                    # solo por retiro
                    # if matriculanovedad.tipo == '2':
                    #     if not matricula.retirado():
                    #         matricula.retiro_academico(f.cleaned_data['motivo'])
                    #         log(u'Retiro la matricula: %s' % matricula, request, "edit")
                    #     else:
                    #         transaction.set_rollback(True)
                    #         return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra retirado de la matricula."})
                    #     matricula.elimina_rubro_matricula_adicional()

                    return JsonResponse({"result": "ok", "mensaje": "Novedad Guardada"})

                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        elif action == 'editnovedad_matricula':
            try:
                f = MatriculaNovedadForm(request.POST, request.FILES)
                if 'archivo' in request.FILES:
                    d = request.FILES['archivo']
                    if d.size > 8388608:
                        return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 8 Mb."})
                    else:
                        newfiles = request.FILES['archivo']
                        newfilesd = newfiles._name
                        ext = newfilesd[newfilesd.rfind("."):]
                        extensiones = []
                        if ext == '.pdf' or  ext == '.doc' or ext == '.docx'  or ext == '.zip'  or ext == '.rar' :
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .pdf,.doc,docx.,zip.,rar."})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"No existe archivo"})

                if f.is_valid():
                    novedadmatricula = MatriculaNovedad.objects.get(pk=int(request.POST['idnovedad']))

                    if novedadmatricula.tipo == 2 and novedadmatricula.tipo != int(f.cleaned_data['tipo']):
                        return JsonResponse({"result": "bad", "mensaje": u"El tipo de novedad debe ser %s." % novedadmatricula.get_tipo_display() })

                    novedadmatricula.tipo = f.cleaned_data['tipo']
                    novedadmatricula.motivo = f.cleaned_data['motivo']

                    if novedadmatricula.tipo == '1':
                        novedadmatricula.tipodescuento = f.cleaned_data['tipodescuento']
                        novedadmatricula.porcentajedescuento = f.cleaned_data['porcentajedescuento']

                    novedadmatricula.save(request)
                    if 'archivo' in request.FILES:
                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre("novedad_matricula_", newfile._name)
                        novedadmatricula.archivo = newfile
                        novedadmatricula.save(request)

                    # solo por retiro
                    # if novedadmatricula.tipo == '2':
                    #     if not novedadmatricula.matricula.retirado():
                    #         novedadmatricula.matricula.retiro_academico(f.cleaned_data['motivo'])
                    #         log(u'Retiro la matricula: %s' % novedadmatricula.matricula, request, "edit")
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": u"Ya se encuentra retirado de la matricula."})
                    #     novedadmatricula.matricula.elimina_rubro_matricula_adicional()
                    # else:
                    #     if novedadmatricula.matricula.retirado():
                    #         RetiroMatricula.objects.filter(matricula=novedadmatricula.matricula).delete()

                    return JsonResponse({"result": "ok", "mensaje": "Novedad Guardada"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        elif action == 'consulnovedad_matricula':
            try:
                novedadmatricula = MatriculaNovedad.objects.get(pk=int(request.POST['idnovedad']))
                motivo = novedadmatricula.motivo
                tipo = novedadmatricula.tipo
                if novedadmatricula.tipodescuento:
                    tipodescuento = novedadmatricula.tipodescuento.id
                    porcentajedescuento = novedadmatricula.porcentajedescuento
                else:
                    tipodescuento = 0
                    porcentajedescuento = 0
                return JsonResponse({"result": "ok", "porcentajedescuento": porcentajedescuento, "motivo": motivo, "tipo": tipo, "tipodescuento": tipodescuento})
            except Exception as ex:
                pass

        elif action == 'estudiante_carrera':
            try:
                periodo = Periodo.objects.get(pk=int(request.POST['periodo']))
                carrera = Carrera.objects.get(pk=int(request.POST['id']))
                lista = []
                for ins in Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct():
                    if [ins.id, ins.inscripcion.persona.nombre_completo()] not in lista:
                        lista.append([ins.id, ins.inscripcion.persona.nombre_completo()])
                return JsonResponse({"result": "ok", "lista": lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'listarubrosmatriculas':
            try:
                matricularubro = Matricula.objects.select_related().get(pk=request.POST['idmatricula'])
                listarubros1 = Rubro.objects.filter(persona=matricularubro.inscripcion.persona, matricula__isnull=True, status=True).order_by('id')
                listarubros2 = Rubro.objects.filter(persona=matricularubro.inscripcion.persona, matricula=matricularubro, status=True).order_by('id')
                listarubros = listarubros1 | listarubros2
                lista = []
                nombrespersona = matricularubro.inscripcion.persona.apellido1 + ' ' + matricularubro.inscripcion.persona.apellido2 + ' ' + matricularubro.inscripcion.persona.nombres
                for rubros in listarubros:
                    datadoc = {}
                    datadoc['idrub'] = rubros.id
                    if rubros.matricula_id:
                        datadoc['matri'] = rubros.matricula_id
                    else:
                        datadoc['matri'] = 0
                    datadoc['tipo'] = rubros.tipo.nombre
                    datadoc['rubro'] = rubros.nombre
                    datadoc['per'] = matricularubro.inscripcion.persona.id
                    # datadoc['valor'] = listarespuesta.valor
                    # datadoc['orden'] = listarespuesta.orden
                    lista.append(datadoc)
                return JsonResponse({'result': 'ok','lista':lista,'nombrespersona':nombrespersona })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'asignarrubro':
            try:
                cadena = request.POST['listavisto'].rstrip(',')
                lista = cadena.split(',')
                nocadena = request.POST['listanovisto'].rstrip(',')
                nolista = nocadena.split(',')
                codigomatricula = request.POST['codigomatricula']
                if request.POST['listavisto']:
                    listarubros = Rubro.objects.filter(pk__in=lista)
                    for lista in listarubros:
                        lista.matricula_id = codigomatricula
                        lista.save(request)
                if request.POST['listanovisto']:
                    listarubrosnovisto = Rubro.objects.filter(pk__in=nolista)
                    for nolista in listarubrosnovisto:
                        nolista.matricula_id = None
                        nolista.save(request)
                log(u'Asigno Rubro en rec_consultaalumno: lista visto: %s - lista no visto: %s' % (lista,nolista), request, "add")
                return JsonResponse({'result': 'ok' })
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'notificar_deuda':
            try:
                datos = json.loads(request.POST['lista'])
                fecha = datetime.now()
                if datos:
                    for elemento in datos:
                        matricula = Matricula.objects.get(pk=int(elemento))
                        valor_deuda = matricula.bloqueo_matricula_deuda()
                        meses_deuda = matricula.bloqueo_matricula_meses()
                        lista=[]
                        for m in matricula.inscripcion.persona.lista_emails_interno():
                            lista.append(m)
                        ntfs = DetNotificacionDeuda(inscripcion=matricula, valordeuda=valor_deuda, fechanoti=datetime.now().date(), horanoti=datetime.now().time())
                        ntfs.save(request)
                        send_html_mail("Notificación de valores pendientes en programa de maestría", "emails/notificacion_deuda.html",
                                       {'sistema': u'Sistema de Gestión Administrativa', 'matricula': matricula, 'valor_deuda': valor_deuda,
                                        'meses_deuda': meses_deuda, 'fechadescarga': fecha,
                                        't': miinstitucion()}, lista, [], cuenta=CUENTAS_CORREOS[4][1])

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'bloqueo_matricula':
            try:
                datos = json.loads(request.POST['lista'])
                if datos:
                    for elemento in datos:
                        matricula = Matricula.objects.get(pk=int(elemento[0]))
                        matricula.bloqueomatricula = elemento[1]
                        matricula.save(request)
                        log(u'%s: %s' % (u'Desbloquear matricula IPEC' if elemento[1] else u'Bloquear matricula IPEC', matricula), request, "edit")

                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'segmento':
            try:
                from django.db.models import Q
                data['periodo'] = periodo = Periodo.objects.get(pk=int(request.POST['periodo']))
                data['carrera'] = carrera = Carrera.objects.get(pk=int(request.POST['carrera']))
                fdesde, fhasta, search = None, None, None


                if request.POST['search']:
                    data['search'] = search = request.POST['search']
                if request.POST['desde']:
                    data['fdesde'] = fdesde = request.POST['desde']
                if request.POST['hasta']:
                    data['fhasta'] = fhasta = request.POST['hasta']

                if periodo.id == 142 or periodo.id == 135 or periodo.id == 157 or periodo.id == 154:
                    data['cohorte'] = CohorteMaestria.objects.get(status=True, periodoacademico__id=int(request.POST['periodo']))

                data['totalcostomaestria'] = costotal = periodo.periodocarreracosto_set.filter(carrera=carrera, status=True).aggregate(costo=Sum('costo'))['costo']

                if search:
                    filtro = Q(nivel__periodo=periodo) & Q(inscripcion__carrera=carrera) & (Q(inscripcion__persona__nombres__icontains=search) |
                                                                                  Q(inscripcion__persona__apellido1__icontains=search) |
                                                                                  Q(inscripcion__persona__apellido2__icontains=search) |
                                                                                  Q(inscripcion__persona__cedula__icontains=search) |
                                                                                  Q(inscripcion__persona__pasaporte__icontains=search))
                    data['matriculas'] = matricula = Matricula.objects.filter(filtro).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                else:
                    data['matriculas'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                # data['matriculas'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera, inscripcion__persona__cedula='1204683971').distinct().order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')

                #data['matriculas'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera, inscripcion__persona__cedula__in=['0920180783', '1201429246', '0912500212','0922211180','0925004970']).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')

                # Total generado rubros
                filtro = Q(tipo__subtiporubro=1)& Q(matricula__nivel__periodo=periodo)& Q(matricula__inscripcion__carrera=carrera)& Q(matricula__retiradomatricula=False)& Q(status=True)
                # if fdesde:
                #     filtro = filtro & Q(fechavence__gte=fdesde)
                if fhasta:
                    filtro = filtro & Q(fechavence__lte=fhasta)
                if search:
                    filtro = filtro & (Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__cedula__icontains=search) |
                                                                                  Q(matricula__inscripcion__persona__pasaporte__icontains=search))
                totalproyectado = Decimal(null_to_decimal(Rubro.objects.values_list('valor').filter(filtro).aggregate(valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))
                costotalmaestria = 0
                if costotal:
                    costotalmaestria = costotal * matricula.count()
                data['costotal'] = costotalmaestria
                # Total anulado rubros
                filtro = Q(rubro__tipo__subtiporubro=1,
                             rubro__matricula__nivel__periodo=periodo,
                             rubro__matricula__inscripcion__carrera=carrera,
                             rubro__matricula__retiradomatricula=False,
                             status=True,
                             rubro__status=True,
                             factura__valida=False,
                             factura__status=True)
                if fdesde:
                    filtro = filtro & Q(fecha__gte=fdesde)
                if fhasta:
                    filtro = filtro & Q(fecha__lte=fhasta)
                if search:
                    filtro = filtro & (Q(rubro__matricula__inscripcion__persona__nombres__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido1__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido2__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__cedula__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__pasaporte__icontains=search))
                totalanulado = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(filtro).aggregate(
                    valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                # Total liquidado rubros
                filtro = Q(rubro__tipo__subtiporubro=1,
                           rubro__matricula__nivel__periodo=periodo,
                           rubro__matricula__inscripcion__carrera=carrera,
                           rubro__matricula__retiradomatricula=False,
                           status=True,
                           rubro__status=True,
                           pagoliquidacion__isnull=False,
                           pagoliquidacion__status=True)
                if fdesde:
                    filtro = filtro & Q(fecha__gte=fdesde)
                if fhasta:
                    filtro = filtro & Q(fecha__lte=fhasta)
                if search:
                    filtro = filtro & (Q(rubro__matricula__inscripcion__persona__nombres__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido1__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido2__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__cedula__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__pasaporte__icontains=search))
                totalliquidado = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(filtro).aggregate(
                    valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                # Total generado alumnos retirados
                totalproyectadoretirados = 0
                totalsaldoretirados = 0

                filtro = Q(retiradomatricula=True) & Q(nivel__periodo=periodo) & Q(inscripcion__carrera=carrera)
                if search:
                    filtro = filtro & (
                                Q(inscripcion__persona__nombres__icontains=search) |
                                Q(inscripcion__persona__apellido1__icontains=search) |
                                Q(inscripcion__persona__apellido2__icontains=search) |
                                Q(inscripcion__persona__cedula__icontains=search) |
                                Q(inscripcion__persona__pasaporte__icontains=search))
                retirados = Matricula.objects.filter(filtro
                                                     ).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')

                if retirados:
                    for ar in retirados:
                        montoretirado = ar.total_generado_alumno_retirado()
                        montosaldo = ar.total_saldo_alumno_retirado()
                        totalproyectadoretirados += montoretirado
                        totalsaldoretirados += montosaldo

                # Total pagado rubros
                filtro = Q(pagoliquidacion__isnull=True,
                          rubro__tipo__subtiporubro=1,
                          rubro__matricula__nivel__periodo=periodo,
                          rubro__matricula__inscripcion__carrera=carrera,
                          status=True,
                          rubro__status=True)
                if fdesde:
                    filtro = filtro & Q(fecha__gte=fdesde)
                if fhasta:
                    filtro = filtro & Q(fecha__lte=fhasta)
                if search:
                    filtro = filtro & (Q(rubro__matricula__inscripcion__persona__nombres__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido1__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido2__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__cedula__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__pasaporte__icontains=search))
                totalpagado1 = Decimal(
                    null_to_decimal(Pago.objects.values_list('valortotal').filter(filtro
                                                                                  ).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))[
                                        'valor'], 2)).quantize(Decimal('.01'))

                totalpagado = totalpagado1

                # Total vencido rubros
                filtro = Q(tipo__subtiporubro=1,
                             matricula__nivel__periodo=periodo,
                             matricula__inscripcion__carrera=carrera,
                             matricula__retiradomatricula=False,
                             status=True)
                if fdesde:
                    filtro = filtro & Q(fechavence__gte=fdesde)
                if fhasta:
                    filtro = filtro & Q(fechavence__lte=fhasta)
                else:
                    filtro = filtro & Q(fechavence__lt = datetime.now().date())
                if search:
                    filtro = filtro & (Q(matricula__inscripcion__persona__nombres__icontains=search) |
                                       Q(matricula__inscripcion__persona__apellido1__icontains=search) |
                                       Q(matricula__inscripcion__persona__apellido2__icontains=search) |
                                       Q(matricula__inscripcion__persona__cedula__icontains=search) |
                                       Q(matricula__inscripcion__persona__pasaporte__icontains=search))
                totalvencido = Decimal(null_to_decimal(Rubro.objects.values_list('saldo').filter(filtro).aggregate(
                    valor=Sum('saldo'))['valor'], 2)).quantize(Decimal('.01'))

                # # Otros rubros adicionales
                # cabecera_rubros_adicionales = []
                # cabecera_rubros_adicionales.append({"etiqueta": "N°", "ancho": "2"})
                # cabecera_rubros_adicionales.append({"etiqueta": "Cédula", "ancho": "10"})
                # cabecera_rubros_adicionales.append({"etiqueta": "Nombre", "ancho": "58"})
                # cabecera_rubros_adicionales.append({"etiqueta": "Total Mód.Rep.", "ancho": "10", "titulo": "Total Pago por módulos reprobados"})
                # cabecera_rubros_adicionales.append({"etiqueta": "Total Prorr.Tit.", "ancho": "10", "titulo": "Total Pago por prórroga titulación"})
                # cabecera_rubros_adicionales.append({"etiqueta": "Total", "ancho": "10", "titulo": "Total Pago Rubros adicionales"})
                #
                # listado_rubros_adicionales = []
                # totalgenrubrorep = 0
                # totalgenrubroprorr = 0
                # secuencia = 1
                # for m in matricula:
                #     rubros = []
                #     totalrubrosalu = 0
                #
                #     totalrubro = m.total_rubro_modulo_reprobado_alumno()
                #     rubros.append({"valor": totalrubro})
                #     totalrubrosalu += totalrubro
                #     totalgenrubrorep += totalrubro
                #
                #     totalrubro = m.total_rubro_modulo_prorroga_alumno()
                #     rubros.append({"valor": totalrubro})
                #     totalrubrosalu += totalrubro
                #     totalgenrubroprorr += totalrubro
                #
                #     listado_rubros_adicionales.append({
                #         "secuencia": secuencia,
                #         "cedula": m.inscripcion.persona.cedula,
                #         "nombres": m.inscripcion.persona.nombre_completo_inverso(),
                #         "rubros": rubros,
                #         "total": totalrubrosalu
                #         }
                #     )
                #     secuencia += 1
                #
                # pie_rubros_adicionales = []
                # pie_rubros_adicionales.append({"etiqueta": "Total Mód.Rep.", "total": totalgenrubrorep})
                # pie_rubros_adicionales.append({"etiqueta": "Total Prorr.Tit.", "total": totalgenrubroprorr})
                # pie_rubros_adicionales.append({"etiqueta": "Total General", "total": totalgenrubrorep + totalgenrubroprorr})


                # # Total rubros de modulos reprobados
                # totalreprobado = 0
                #
                # # codigos_personas_matriculadas = Matricula.objects.values_list("inscripcion__persona", flat=True).filter(nivel__periodo=periodo, inscripcion__carrera=carrera, retiradomatricula=False).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                #
                # totalreprobado = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(pagoliquidacion__isnull=True,
                #                                                       # rubro__persona__in=codigos_personas_matriculadas,
                #                                                       rubro__matricula__nivel__periodo=periodo,
                #                                                       rubro__matricula__inscripcion__carrera=carrera,
                #                                                       # rubro__matricula__retiradomatricula=False,
                #                                                       status=True,
                #                                                       rubro__status=True,
                #                                                       rubro__tipo__subtiporubro=2,
                #                                                       ).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                #
                # totalprorroga = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(pagoliquidacion__isnull=True,
                #                                                                                        # rubro__persona__in=codigos_personas_matriculadas,
                #                                                                                        rubro__matricula__nivel__periodo=periodo,
                #                                                                                        rubro__matricula__inscripcion__carrera=carrera,
                #                                                                                        # rubro__matricula__retiradomatricula=False,
                #                                                                                        status=True,
                #                                                                                        rubro__status=True,
                #                                                                                        rubro__tipo__subtiporubro=3,
                #                                                                                        ).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                filtro = Q(~Q(rubro__tipo__subtiporubro=1),
                                pagoliquidacion__isnull=True,
                                rubro__matricula__nivel__periodo=periodo,
                                rubro__matricula__inscripcion__carrera=carrera,
                                status=True,
                                rubro__status=True,)
                if fdesde:
                    filtro = filtro & Q(fecha__gte=fdesde)
                if fhasta:
                    filtro = filtro & Q(fecha__lte=fhasta)
                if search:
                    filtro = filtro & (Q(rubro__matricula__inscripcion__persona__nombres__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido1__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__apellido2__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__cedula__icontains=search) |
                                       Q(rubro__matricula__inscripcion__persona__pasaporte__icontains=search))
                totaladicional = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(
                    filtro
                ).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))


                totalvencido += totalsaldoretirados
                totalproyectado = (totalproyectado - (totalliquidado + totalanulado)) + totalproyectadoretirados
                totalpendiente = totalproyectado - totalpagado


                data['sumatotalgenerado'] = totalproyectado
                data['sumatotalpagado'] = totalpagado
                data['sumatotalvencido'] = totalvencido
                data['sumatotalpendiente'] = totalpendiente
                # data['sumatotalreprobado'] = totalreprobado
                # data['sumatotalprorroga'] = totalprorroga
                data['sumatotaladicional'] = totaladicional


                data['reporte_0'] = obtener_reporte("cartera_vencida")
                data['reporte_1'] = obtener_reporte("deudas_estudiantes")
                data['reporte_2'] = obtener_reporte("deuda_individual")

                data['reporte_tarp'] = obtener_reporte("tabla_amortizacion_refinanciamiento_posgrado")
                data['reporte_tap'] = obtener_reporte("tabla_amortizacion_posgrado")

                # data['cabecera_rubros_adicionales'] = cabecera_rubros_adicionales
                # data['listado_rubros_adicionales'] = listado_rubros_adicionales
                # data['pie_rubros_adicionales'] = pie_rubros_adicionales

                template = get_template("rec_consultaalumnos/segmento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        elif action == 'reporte_anual':
            try:
                tiporeporte = int(request.POST['tiporeporte'])
                anio = request.POST['anio']
                desde = request.POST['desde']
                hasta = request.POST['hasta']

                if tiporeporte == 1:
                    fechadesde = datetime.strptime(anio + '-01-01', '%Y-%m-%d').date()
                    fechahasta = datetime.strptime(anio + '-12-31', '%Y-%m-%d').date()
                else:
                    fechadesde = datetime.strptime(desde, '%Y-%m-%d').date()
                    fechahasta = datetime.strptime(hasta, '%Y-%m-%d').date()

                listaporcentajes = json.loads(request.POST['listaporcentaje'])

                anio = fechadesde.year

                __author__ = 'Unemi'
                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))
                style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                title2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                style1 = easyxf(num_format_str='DD/mm/YYYY')
                # style2 = easyxf(num_format_str='HH:mm')
                style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre; borders: top thin')

                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')

                fuentemonedafv = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour lime',
                    num_format_str=' "$" #,##0.00')

                fuentemonedafn = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour light_orange',
                    num_format_str=' "$" #,##0.00')

                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, height 150, bold on; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str=' "$" #,##0.00')

                fuentenormal2 = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegcent2 = easyxf('font: name Verdana, bold on, color-index black, height 150; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalneg2 = easyxf('font: name Verdana, bold on, color-index black, height 150')

                wb = Workbook(encoding='utf-8')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1, 10000).__str__() + '.xls'
                nombre = "PROYECCIONANUAL_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre
                ws = wb.add_sheet('PROY PRESU')
                ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write_merge(1, 1, 0, 10, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', title2)
                ws.write_merge(2, 2, 0, 10, 'PROYECCION DEL PRESUPUESTO GENERAL ' + str(anio), title2)
                ws.write_merge(4, 4, 0, 0, u'INGRESOS', fuentenormalneg2)
                ws.write_merge(5, 5, 0, 0, u'PERIODO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 1, 1, u'PROGRAMAS EN EJECUCIÓN', fuentenormalnegcent2)
                ws.write_merge(5, 5, 2, 2, u'INGRESO BRUTO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 3, 3, u'RETIRADO%-MORA%-BECA%', fuentenormalnegcent2)
                ws.write_merge(5, 5, 4, 4, u'INGRESO NETO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 5, 5, u'PAGOS UNEMI', fuentenormalnegcent2)
                ws.write_merge(5, 5, 6, 6, u'PAGOS EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(5, 5, 7, 7, u'INGRESO PAGADO/TESORERIA', fuentenormalnegcent2)
                row_num = 6
                valor_total = 0
                ingreso_neto_total = 0
                valor_pagado_total = 0
                valor_pagado_total_unemi = 0
                valor_pagado_total_epunemi = 0


                valor_reprobado_total = 0
                valor_reprobado_total_unemi = 0
                valor_reprobado_total_epunemi = 0

                lp1 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__fechavence__year=anio , tipo__id__in=[3, 4]).distinct().order_by('id')


                lp1 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__fechavence__gte=fechadesde, nivel__matricula__rubro__fechavence__lte=fechahasta, tipo__id__in=[3, 4]).distinct().order_by('id')


                lp2 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__pago__fecha__year=anio, tipo__id__in=[3, 4]).distinct().order_by('id')


                lp2 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__pago__fecha__gte=fechadesde, nivel__matricula__rubro__pago__fecha__lte=fechahasta, tipo__id__in=[3, 4]).distinct().order_by('id')

                lista_periodos = (lp1 | lp2).distinct().order_by('id')

                lc1 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__fechavence__year=anio, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')


                lc1 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__fechavence__gte=fechadesde, inscripcion__matricula__rubro__fechavence__lte=fechahasta, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')


                lc2 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__pago__fecha__year=anio, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')


                lc2 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__pago__fecha__gte=fechadesde, inscripcion__matricula__rubro__pago__fecha__lte=fechahasta,  inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')


                lista_carreras = (lc1 | lc2).distinct().order_by('nombre')

                pagos = Pago.objects.filter(pagoliquidacion__isnull=True,

                                            fecha__gte=fechadesde,
                                            fecha__lte=fechahasta,

                                            rubro__matricula__nivel__periodo_id__in=lista_periodos,
                                            rubro__matricula__inscripcion__carrera_id__in=lista_carreras,
                                            status=True,
                                            rubro__status=True
                                            ).exclude(factura__valida=False).order_by('fecha', 'rubro__matricula__nivel__periodo_id',
                                                                                      'rubro__matricula__inscripcion__carrera')

                pagosunemi = pagos.filter(idpagoepunemi=0).annotate(anio=ExtractYear('fecha')).values_list('anio',
                                                                                                           'rubro__matricula__nivel__periodo_id',
                                                                                                           'rubro__matricula__inscripcion__carrera_id').annotate(
                    tpagado=Sum('valortotal'))

                pagosepunemi = pagos.filter(~Q(idpagoepunemi=0)).annotate(anio=ExtractYear('fecha')).values_list('anio',
                                                                                                                 'rubro__matricula__nivel__periodo_id',
                                                                                                                 'rubro__matricula__inscripcion__carrera_id').annotate(
                    tpagado=Sum('valortotal'))

                pagos = pagos.annotate(anio=ExtractYear('fecha')).values_list('anio',
                                                                              'rubro__matricula__nivel__periodo_id',
                                                                              'rubro__matricula__inscripcion__carrera_id').annotate(
                    tpagado=Sum('valortotal'))


                for p in Periodo.objects.filter(pk__in=lista_periodos).order_by('id'):
                    for carrera in Carrera.objects.filter(inscripcion__matricula__nivel__periodo=p, pk__in=lista_carreras).distinct().order_by('nombre'):

                        porcentaje = 0
                        for lp in listaporcentajes:
                            if int(lp['periodo']) == p.id and int(lp['carrera']) == carrera.id:
                                porcentaje = Decimal(lp['porcentaje']).quantize(Decimal('.01'))
                                break

                        ws.write_merge(row_num, row_num, 0, 0, p.nombre, fuentenormal2)
                        ws.write_merge(row_num, row_num, 1, 1, carrera.nombre, fuentenormal2)
                        valor = Decimal(null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p, matricula__inscripcion__carrera=carrera, fechavence__year=anio, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)).quantize(Decimal('.01'))

                        # Total generado rubros
                        totalproyectado = Decimal(
                            null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                                                                 matricula__inscripcion__carrera=carrera,
                                                                 status=True,
                                                                 # fechavence__year=anio,

                                                                 fechavence__gte=fechadesde,
                                                                 fechavence__lte=fechahasta

                                                                 ).aggregate(
                                valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))

                        # Total anulado rubros
                        totalanulado = Decimal(
                            null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                rubro__matricula__inscripcion__carrera=carrera,
                                                                status=True,
                                                                rubro__status=True,
                                                                # rubro__fechavence__year=anio,

                                                                rubro__fechavence__gte=fechadesde,
                                                                rubro__fechavence__lte=fechahasta,

                                                                factura__valida=False,
                                                                factura__status=True).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        # Total liquidado rubros
                        totalliquidado = Decimal(
                            null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                rubro__matricula__inscripcion__carrera=carrera,
                                                                status=True,
                                                                rubro__status=True,
                                                                # rubro__fechavence__year=anio,

                                                                rubro__fechavence__gte=fechadesde,
                                                                rubro__fechavence__lte=fechahasta,

                                                                pagoliquidacion__isnull=False,
                                                                pagoliquidacion__status=True).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        valor_bruto = totalproyectado - (totalanulado + totalliquidado)
                        valor = valor_bruto

                        totalpagado = 0
                        totalpagadounemi = 0
                        totalpagadoepunemi = 0

                        aniofila = 0
                        periodofila = 0
                        carrerafila = 0

                        for rp in pagos:
                            if rp[0] == anio and rp[1] == p.id and rp[2] == carrera.id:
                                totalpagado += Decimal(rp[3])
                                aniofila = rp[0]
                                periodofila = rp[1]
                                carrerafila = rp[2]
                            elif aniofila != 0 and aniofila != rp[0] and periodofila != rp[1] and carrerafila != rp[2]:
                                break

                        aniofila = 0
                        periodofila = 0
                        carrerafila = 0
                        for une in pagosunemi:
                            if une[0] == anio and une[1] == p.id and une[2] == carrera.id:
                                totalpagadounemi += Decimal(une[3])
                                aniofila = une[0]
                                periodofila = une[1]
                                carrerafila = une[2]
                            elif aniofila != 0 and aniofila != une[0] and periodofila != une[1] and carrerafila != une[2]:
                                break
                        aniofila = 0
                        periodofila = 0
                        carrerafila = 0
                        for epu in pagosepunemi:
                            if epu[0] == anio and epu[1] == p.id and epu[2] == carrera.id:
                                totalpagadoepunemi += Decimal(epu[3])
                                aniofila = epu[0]
                                periodofila = epu[1]
                                carrerafila = epu[2]
                            elif aniofila != 0 and aniofila != epu[0] and periodofila != epu[1] and carrerafila != epu[2]:
                                break


                        valor_pagado = totalpagado
                        valor_pagado_unemi = totalpagadounemi
                        valor_pagado_epunemi = totalpagadoepunemi

                        valor_descuento = Decimal(((valor *porcentaje)/100)).quantize(Decimal('.01'))

                        ingreso_neto = valor - valor_descuento
                        valor_total += valor
                        valor_pagado_total += valor_pagado

                        valor_pagado_total_unemi += valor_pagado_unemi
                        valor_pagado_total_epunemi += valor_pagado_epunemi

                        ingreso_neto_total += ingreso_neto


                        ws.write_merge(row_num, row_num, 2, 2, valor, fuentemoneda)
                        ws.write_merge(row_num, row_num, 3, 3, valor_descuento, fuentemoneda)
                        ws.write_merge(row_num, row_num, 4, 4, ingreso_neto, fuentemoneda)
                        ws.write_merge(row_num, row_num, 5, 5, valor_pagado_unemi, fuentemonedafv)
                        ws.write_merge(row_num, row_num, 6, 6, valor_pagado_epunemi, fuentemonedafn)
                        ws.write_merge(row_num, row_num, 7, 7, valor_pagado, fuentemoneda)

                        row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'SUBTOTAL DE EJECUCIÓN', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 2, 2, valor_total, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 4, 4, ingreso_neto_total, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 5, 5, valor_pagado_total_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 6, 6, valor_pagado_total_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 7, 7, valor_pagado_total, fuentemonedaneg)

                # busco otros tipos rubros que tengan en la descripcion MAESTRIA y que sea de la partida 101
                # codigo_rubro = TipoOtroRubro.objects.values_list('id', flat=True).filter(partida__id=101, nombre__icontains='MAESTR', status=True)
                codigo_rubro = TipoOtroRubro.objects.values_list('id', flat=True).filter(tiporubro=1, status=True)
                # codigo_rubro = TipoOtroRubro.objects.values_list('id', flat=True).filter(pk__in=[2845,2957,2926,2958,3002,2915,2927,2989,2902,3009,2925,2870,2912,3010,3017,2956,3025], activo=True, status=True)
                # valornoadmitidos = Decimal(null_to_decimal(Rubro.objects.filter(fechavence__year__lte=anio, status=True, matricula__isnull=True, tipo__in=codigo_rubro).aggregate(valor=Sum('saldo'))['valor'],2)).quantize(Decimal('.01'))



                # valornoadmitidos = Decimal(null_to_decimal(Pago.objects.filter(rubro__matricula__isnull=True, rubro__tipo_id__in=codigo_rubro, status=True, rubro__status=True, fecha__year=anio).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                valornoadmitidos = Decimal(null_to_decimal(Pago.objects.filter(rubro__matricula__isnull=True, rubro__tipo_id__in=codigo_rubro, status=True, rubro__status=True, fecha__gte=fechadesde, fecha__lte=fechahasta).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                # Rubros Adicionales Pagados
                pagosadicionales = Pago.objects.filter(
                    ~Q(rubro__tipo__subtiporubro=1),
                    rubro__tipo_id__in=codigo_rubro,
                    pagoliquidacion__isnull=True,
                    rubro__matricula__isnull=False,
                    status=True,
                    rubro__status=True,
                    fecha__gte=fechadesde,
                    fecha__lte=fechahasta
                ).exclude(factura__valida=False)

                # Obtengo el total pagado por rubros adicionales
                valoradicionales = Decimal(null_to_decimal(pagosadicionales.aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                rubrosadicionales = Rubro.objects.values_list('tipo_id', 'tipo__nombre').filter(
                    ~Q(tipo__subtiporubro=1),
                    tipo_id__in=codigo_rubro,
                    pago__pagoliquidacion__isnull=True,
                    matricula__isnull=False,
                    status=True,
                    pago__status=True,
                    pago__fecha__gte=fechadesde,
                    pago__fecha__lte=fechahasta
                ).exclude(pago__factura__valida=False).order_by('tipo__nombre').distinct()

                row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'NO ADMITIDOS', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 7, 7, valornoadmitidos, fuentemonedaneg)

                row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'RUBROS ADICIONALES', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 7, 7, valoradicionales, fuentemonedaneg)

                row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'TOTAL DE INGRESOS', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 7, 7, valornoadmitidos+valor_pagado_total+valoradicionales, fuentemonedaneg)

                columns = [
                    (u"", 9000),
                    (u"", 9000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000)
                ]
                row_num += 1
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style2)
                    ws.col(col_num).width = columns[col_num][1]

                row_num += 1
                # LISTADO DE RUBROS NO ADMITIDOS
                ws.write_merge(row_num, row_num, 0, 0, u'NO ADMITIDOS', fuentenormalneg2)
                row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'RUBRO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 1, 1, u'RUBRO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 2, 2, u'TOTAL UNEMI', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 3, 3, u'TOTAL EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 4, 4, u'TOTAL', fuentenormalnegcent2)

                valor_total = 0
                valor_total_unemi = 0
                valor_total_epunemi = 0
                row_num += 1

                # listadorubros = Rubro.objects.values_list('tipo_id', 'tipo__nombre').filter(pago__fecha__year=anio, status=True, matricula__isnull=True, tipo__in=codigo_rubro).distinct()
                listadorubros = Rubro.objects.values_list('tipo_id', 'tipo__nombre').filter(pago__fecha__gte=fechadesde, pago__fecha__lte=fechahasta, status=True, matricula__isnull=True, tipo__in=codigo_rubro).distinct()

                for lista in listadorubros:
                    ws.write_merge(row_num, row_num, 0, 0, 'RUBRO', fuentenormal2)
                    ws.write_merge(row_num, row_num, 1, 1, lista[1], fuentenormal2)

                    # valor_pagado = Decimal(null_to_decimal(Pago.objects.filter(rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__year=anio).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    valor_pagado = Decimal(null_to_decimal(Pago.objects.filter(rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__gte=fechadesde, fecha__lte=fechahasta).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    # valor_pagado_unemi = Decimal(null_to_decimal(Pago.objects.filter(idpagoepunemi=0, rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__year=anio).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    valor_pagado_unemi = Decimal(null_to_decimal(Pago.objects.filter(idpagoepunemi=0, rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__gte=fechadesde, fecha__lte=fechahasta).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    # valor_pagado_epunemi = Decimal(null_to_decimal(Pago.objects.filter(~Q(idpagoepunemi=0), rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__year=anio).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    valor_pagado_epunemi = Decimal(null_to_decimal(Pago.objects.filter(~Q(idpagoepunemi=0), rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__gte=fechadesde, fecha__lte=fechahasta).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    ws.write_merge(row_num, row_num, 2, 2, valor_pagado_unemi, fuentemonedafv)
                    ws.write_merge(row_num, row_num, 3, 3, valor_pagado_epunemi, fuentemonedafn)
                    ws.write_merge(row_num, row_num, 4, 4, valor_pagado, fuentemoneda)
                    valor_total += valor_pagado
                    valor_total_unemi += valor_pagado_unemi
                    valor_total_epunemi += valor_pagado_epunemi
                    row_num += 1
                ws.write_merge(row_num, row_num, 0, 1, u'TOTAL NO ADMITIDOS', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 2, 2, valor_total_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 3, 3, valor_total_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 4, 4, valor_total, fuentemonedaneg)

                columns = [
                    (u"", 9000),
                    (u"", 9000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000)]
                row_num += 1
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style2)
                    ws.col(col_num).width = columns[col_num][1]
                row_num += 1

                # LISTADO DE RUBROS ADICIONALES
                ws.write_merge(row_num, row_num, 0, 0, u'RUBROS ADICIONALES', fuentenormalneg2)
                row_num += 1
                ws.write_merge(row_num, row_num, 0, 1, u'RUBRO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 2, 2, u'TOTAL UNEMI', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 3, 3, u'TOTAL EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 4, 4, u'TOTAL', fuentenormalnegcent2)

                valor_total = 0
                valor_total_unemi = 0
                valor_total_epunemi = 0
                row_num += 1
                for rubroadicional in rubrosadicionales:
                    ws.write_merge(row_num, row_num, 0, 1, rubroadicional[1], fuentenormal2)
                    valor_pagado_unemi = Decimal(null_to_decimal(pagosadicionales.filter(idpagoepunemi=0, rubro__tipo_id=rubroadicional[0]).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    valor_pagado_epunemi = Decimal(null_to_decimal(pagosadicionales.filter(~Q(idpagoepunemi=0), rubro__tipo_id=rubroadicional[0]).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    valor_pagado = valor_pagado_unemi + valor_pagado_epunemi
                    ws.write_merge(row_num, row_num, 2, 2, valor_pagado_unemi, fuentemonedafv)
                    ws.write_merge(row_num, row_num, 3, 3, valor_pagado_epunemi, fuentemonedafn)
                    ws.write_merge(row_num, row_num, 4, 4, valor_pagado, fuentemoneda)
                    valor_total += valor_pagado
                    valor_total_unemi += valor_pagado_unemi
                    valor_total_epunemi += valor_pagado_epunemi
                    row_num += 1

                ws.write_merge(row_num, row_num, 0, 1, u'TOTAL RUBROS ADICIONALES', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 2, 2, valor_total_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 3, 3, valor_total_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 4, 4, valor_total, fuentemonedaneg)

                # cartera vencida
                row_num += 2
                ws.write_merge(row_num, row_num, 0, 0, u'CARTERA VENCIDA AL ' + fechahasta.strftime("%d/%m/%Y") , fuentenormalneg2)
                row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'PERIODO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 1, 1, u'PROGRAMAS EN EJECUCIÓN', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 2, 2, u'TOTAL', fuentenormalnegcent2)
                valor_total = 0
                row_num += 1

                for p in Periodo.objects.filter(pk__in=lista_periodos).order_by('id'):
                    for carrera in Carrera.objects.filter(inscripcion__matricula__nivel__periodo=p, pk__in=lista_carreras).distinct().order_by('nombre'):
                        vencidoprograma = 0
                        ws.write_merge(row_num, row_num, 0, 0, p.nombre, fuentenormal2)
                        ws.write_merge(row_num, row_num, 1, 1, carrera.nombre, fuentenormal2)

                        matriculaspos = Matricula.objects.filter(status=True, inscripcion__carrera=carrera, nivel__periodo=p).order_by('id')

                        for matriculap in matriculaspos:
                            vencidopersona = 0
                            datos = matriculap.rubros_maestria_vencidos_detalle_version_final(fechahasta)
                            if not matriculap.retirado_programa_maestria():
                                if datos['rubrosnovencidos']:  # Se considera a los no vencidos que tienen saldo negativo
                                    for rubro_no_vencido in datos['rubrosnovencidos']:
                                        vencidopersona += rubro_no_vencido[5]

                                if datos['rubrosvencidos']:
                                    for rubro_vencido in datos['rubrosvencidos']:
                                        vencidopersona += rubro_vencido[5]
                            else:
                                vencidopersona = datos['totalvencido']

                            vencidoprograma += vencidopersona

                        valor_total += vencidoprograma
                        ws.write_merge(row_num, row_num, 2, 2, vencidoprograma, fuentemoneda)
                        row_num += 1

                ws.write_merge(row_num, row_num, 0, 0, u'TOTAL CARTERA VENCIDA', fuentenormalneg2)
                ws.write_merge(row_num, row_num, 2, 2, valor_total, fuentemonedaneg)

                row_num += 2
                ws.write_merge(row_num, row_num, 0, 0, u'FECHA ARCHIVO  '+str(datetime.now())[0:19], fuentenormalneg2)


                ws = wb.add_sheet('FLUJO INGRESO')
                ws.write_merge(0, 0, 0, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write_merge(1, 1, 0, 4, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', title2)
                ws.write_merge(2, 2, 0, 4, 'FLUJO DE INGRESOS VS GASTOS ' + str(anio), title2)

                ws.write_merge(4, 4, 0, 3, u'INGRESOS', fuentenormalneg2)
                ws.write_merge(4, 4, 4, 16, u'PROYECCIÓN', fuentenormalneg2)

                ws.write_merge(5, 6, 0, 0, u'PERIODO', fuentenormalnegcent2)
                ws.write_merge(5, 6, 1, 2, u'PROGRAMAS EN EJECUCIÓN', fuentenormalnegcent2)
                ws.write_merge(5, 6, 3, 3, u'INGR. MENSUAL', fuentenormalnegcent2)
                ws.write_merge(5, 6, 4, 4, u'ENERO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 5, 7, u'ENERO PAGADO', fuentenormalnegcent2)# +4
                ws.write_merge(6, 6, 5, 5, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 6, 6, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 7, 7, u'PROGRAMA', fuentenormalnegcent2)# +4
                ws.write_merge(5, 6, 8, 8, u'FEBRERO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 9, 11, u'FEBRERO PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 9, 9, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 10, 10, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 11, 11, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 12, 12, u'MARZO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 13, 15, u'MARZO PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 13, 13, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 14, 14, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 15, 15, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 16, 16, u'ABRIL PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 17, 19, u'ABRIL PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 17, 17, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 18, 18, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 19, 19, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 20, 20, u'MAYO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 21, 23, u'MAYO PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 21, 21, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 22, 22, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 23, 23, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 24, 24, u'JUNIO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 25, 27, u'JUNIO PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 25, 25, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 26, 26, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 27, 27, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 28, 28, u'JULIO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 29, 31, u'JULIO PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 29, 29, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 30, 30, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 31, 31, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 32, 32, u'AGOSTO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 33, 35, u'AGOSTO PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 33, 33, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 34, 34, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 35, 35, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 36, 36, u'SEPTIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 37, 39, u'SEPTIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 37, 37, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 38, 38, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 39, 39, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 40, 40, u'OCTUBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 41, 43, u'OCTUBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 41, 41, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 42, 42, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 43, 43, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 44, 44, u'NOVIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 45, 47, u'NOVIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 45, 45, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 46, 46, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 47, 47, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 48, 48, u'DICIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 5, 49, 51, u'DICIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(6, 6, 49, 49, u'PROG.UNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 50, 50, u'PROG.EPUNEMI', fuentenormalnegcent2)
                ws.write_merge(6, 6, 51, 51, u'PROGRAMA', fuentenormalnegcent2)
                ws.write_merge(5, 6, 52, 52, u'TOTAL PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(5, 6, 53, 53, u'TOTAL PAGADO PROGRAMA', fuentenormalnegcent2)

                row_num = 7
                valor_total_bruto = 0
                valor_mes1_pagado = 0
                valor_mes1_pagado_unemi = 0
                valor_mes1_pagado_epunemi = 0
                valor_mes2_pagado = 0
                valor_mes2_pagado_unemi = 0
                valor_mes2_pagado_epunemi = 0
                valor_mes3_pagado = 0
                valor_mes3_pagado_unemi = 0
                valor_mes3_pagado_epunemi = 0
                valor_mes4_pagado = 0
                valor_mes4_pagado_unemi = 0
                valor_mes4_pagado_epunemi = 0
                valor_mes5_pagado = 0
                valor_mes5_pagado_unemi = 0
                valor_mes5_pagado_epunemi = 0
                valor_mes6_pagado = 0
                valor_mes6_pagado_unemi = 0
                valor_mes6_pagado_epunemi = 0
                valor_mes7_pagado = 0
                valor_mes7_pagado_unemi = 0
                valor_mes7_pagado_epunemi = 0
                valor_mes8_pagado = 0
                valor_mes8_pagado_unemi = 0
                valor_mes8_pagado_epunemi = 0
                valor_mes9_pagado = 0
                valor_mes9_pagado_unemi = 0
                valor_mes9_pagado_epunemi = 0
                valor_mes10_pagado = 0
                valor_mes10_pagado_unemi = 0
                valor_mes10_pagado_epunemi = 0
                valor_mes11_pagado = 0
                valor_mes11_pagado_unemi = 0
                valor_mes11_pagado_epunemi = 0
                valor_mes12_pagado = 0
                valor_mes12_pagado_unemi = 0
                valor_mes12_pagado_epunemi = 0

                valor_total_neto = 0
                valor_mes1_neto = 0
                valor_mes2_neto = 0
                valor_mes3_neto = 0
                valor_mes4_neto = 0
                valor_mes5_neto = 0
                valor_mes6_neto = 0
                valor_mes7_neto = 0
                valor_mes8_neto = 0
                valor_mes9_neto = 0
                valor_mes10_neto = 0
                valor_mes11_neto = 0
                valor_mes12_neto = 0

                pagos = Pago.objects.filter(pagoliquidacion__isnull=True,

                                            fecha__gte=fechadesde,
                                            fecha__lte=fechahasta,

                                            rubro__matricula__nivel__periodo_id__in=lista_periodos,
                                            rubro__matricula__inscripcion__carrera_id__in=lista_carreras,
                                            status=True,
                                            rubro__status=True
                                            ).exclude(factura__valida=False).order_by('fecha', 'rubro__matricula__nivel__periodo_id',
                                                                                      'rubro__matricula__inscripcion__carrera')

                pagosunemi = pagos.filter(idpagoepunemi=0).annotate(anio=ExtractYear('fecha'), mes=ExtractMonth('fecha')).values_list('anio', 'mes',
                                                                                                                                      'rubro__matricula__nivel__periodo_id',
                                                                                                                                      'rubro__matricula__inscripcion__carrera_id').annotate(tpagado=Sum('valortotal'))
                pagosepunemi = pagos.filter(~Q(idpagoepunemi=0)).annotate(anio=ExtractYear('fecha'), mes=ExtractMonth('fecha')).values_list('anio',
                                                                                                                                            'mes',
                                                                                                                                            'rubro__matricula__nivel__periodo_id',
                                                                                                                                            'rubro__matricula__inscripcion__carrera_id').annotate(tpagado=Sum('valortotal'))
                pagos = pagos.annotate(anio=ExtractYear('fecha'), mes=ExtractMonth('fecha')).values_list('anio', 'mes',
                                                                                                         'rubro__matricula__nivel__periodo_id',
                                                                                                         'rubro__matricula__inscripcion__carrera_id').annotate(tpagado=Sum('valortotal'))

                for p in Periodo.objects.filter(pk__in=lista_periodos).order_by('id'):
                    for carrera in Carrera.objects.filter(inscripcion__matricula__nivel__periodo=p, pk__in=lista_carreras).distinct().order_by('nombre'):

                        porcentaje = 0
                        for lp in listaporcentajes:
                            if int(lp['periodo']) == p.id and int(lp['carrera']) == carrera.id:
                                porcentaje = Decimal(lp['porcentaje']).quantize(Decimal('.01'))
                                break

                        ws.write_merge(row_num, row_num, 0, 0, p.nombre, fuentenormal2)
                        ws.write_merge(row_num, row_num, 1, 1, carrera.nombre, fuentenormal2)
                        mesdesde = 1
                        valor_mes_pagado = 0
                        valor_mes_pagado_une = 0
                        valor_mes_pagado_epu = 0
                        valor_mes_neto = 0
                        bandera_mes = 0
                        fila = 4
                        while mesdesde <= 12:
                            valor_bruto = 0
                            valor_pagado = 0

                            # Total generado rubros
                            totalproyectado = Decimal(
                                null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                                                                     matricula__inscripcion__carrera=carrera,
                                                                     status=True,
                                                                     fechavence__year=anio, fechavence__month=mesdesde,

                                                                     fechavence__gte=fechadesde, fechavence__lte=fechahasta

                                                                     ).aggregate(
                                    valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))

                            # Total anulado rubros
                            totalanulado = Decimal(
                                null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                    rubro__matricula__inscripcion__carrera=carrera,
                                                                    status=True,
                                                                    rubro__status=True,
                                                                    rubro__fechavence__year=anio,
                                                                    rubro__fechavence__month=mesdesde,

                                                                    rubro__fechavence__gte=fechadesde,
                                                                    rubro__fechavence__lte=fechahasta,

                                                                    factura__valida=False,
                                                                    factura__status=True).aggregate(
                                    valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                            # Total liquidado rubros
                            totalliquidado = Decimal(
                                null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                    rubro__matricula__inscripcion__carrera=carrera,
                                                                    status=True,
                                                                    rubro__status=True,
                                                                    rubro__fechavence__year=anio,
                                                                    rubro__fechavence__month=mesdesde,

                                                                    rubro__fechavence__gte=fechadesde,
                                                                    rubro__fechavence__lte=fechahasta,

                                                                    pagoliquidacion__isnull=False,
                                                                    pagoliquidacion__status=True).aggregate(
                                    valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                            valor_bruto = totalproyectado - (totalanulado + totalliquidado)

                            totalpagado = 0
                            totalpagadoune = 0
                            totalpagadoepu = 0
                            aniofila = 0
                            mesfila = 0
                            periodofila = 0
                            carrerafila = 0

                            for rp in pagos:
                                if rp[0] == anio and rp[1] == mesdesde and rp[2] == p.id and rp[3] == carrera.id:
                                    totalpagado += Decimal(rp[4])
                                    aniofila = rp[0]
                                    mesfila =rp[1]
                                    periodofila = rp[2]
                                    carrerafila = rp[3]
                                elif aniofila != 0 and aniofila != rp[0] and mesfila!= rp[1] and periodofila != rp[2] and carrerafila != rp[3]:
                                    break

                            aniofila = 0
                            mesfila = 0
                            periodofila = 0
                            carrerafila = 0

                            for ru in pagosunemi:
                                if ru[0] == anio and ru[1] == mesdesde and ru[2] == p.id and ru[3] == carrera.id:
                                    totalpagadoune += Decimal(ru[4])
                                    aniofila = ru[0]
                                    mesfila = ru[1]
                                    periodofila = ru[2]
                                    carrerafila = ru[3]
                                elif aniofila != 0 and aniofila != ru[0] and mesfila != ru[1] and periodofila != ru[
                                    2] and carrerafila != ru[3]:
                                    break

                            aniofila = 0
                            mesfila = 0
                            periodofila = 0
                            carrerafila = 0

                            for re in pagosepunemi:
                                if re[0] == anio and re[1] == mesdesde and re[2] == p.id and re[3] == carrera.id:
                                    totalpagadoepu += Decimal(re[4])
                                    aniofila = re[0]
                                    mesfila = re[1]
                                    periodofila = re[2]
                                    carrerafila = re[3]
                                elif aniofila != 0 and aniofila != re[0] and mesfila != re[1] and periodofila != re[
                                    2] and carrerafila != re[3]:
                                    break



                            valor_pagado = totalpagado
                            valor_pagado_unemi = totalpagadoune
                            valor_pagado_epunemi = totalpagadoepu

                            valor_neto = Decimal(0).quantize(Decimal('.01'))
                            valor_originsal = valor_bruto
                            if valor_bruto > 0:
                                valor_descuento = Decimal(((valor_bruto * porcentaje) / 100)).quantize(Decimal('.01'))

                                valor_neto = valor_bruto - valor_descuento

                            if mesdesde == 1:
                                valor_mes1_pagado += valor_pagado
                                valor_mes1_pagado_unemi += valor_pagado_unemi
                                valor_mes1_pagado_epunemi += valor_pagado_epunemi
                                valor_mes1_neto += valor_neto
                            elif mesdesde == 2:
                                valor_mes2_pagado += valor_pagado
                                valor_mes2_pagado_unemi += valor_pagado_unemi
                                valor_mes2_pagado_epunemi += valor_pagado_epunemi
                                valor_mes2_neto += valor_neto
                            elif mesdesde == 3:
                                valor_mes3_pagado += valor_pagado
                                valor_mes3_pagado_unemi += valor_pagado_unemi
                                valor_mes3_pagado_epunemi += valor_pagado_epunemi
                                valor_mes3_neto += valor_neto
                            elif mesdesde == 4:
                                valor_mes4_pagado += valor_pagado
                                valor_mes4_pagado_unemi += valor_pagado_unemi
                                valor_mes4_pagado_epunemi += valor_pagado_epunemi
                                valor_mes4_neto += valor_neto
                            elif mesdesde == 5:
                                valor_mes5_pagado += valor_pagado
                                valor_mes5_pagado_unemi += valor_pagado_unemi
                                valor_mes5_pagado_epunemi += valor_pagado_epunemi
                                valor_mes5_neto += valor_neto
                            elif mesdesde == 6:
                                valor_mes6_pagado += valor_pagado
                                valor_mes6_pagado_unemi += valor_pagado_unemi
                                valor_mes6_pagado_epunemi += valor_pagado_epunemi
                                valor_mes6_neto += valor_neto
                            elif mesdesde == 7:
                                valor_mes7_pagado += valor_pagado
                                valor_mes7_pagado_unemi += valor_pagado_unemi
                                valor_mes7_pagado_epunemi += valor_pagado_epunemi
                                valor_mes7_neto += valor_neto
                            elif mesdesde == 8:
                                valor_mes8_pagado += valor_pagado
                                valor_mes8_pagado_unemi += valor_pagado_unemi
                                valor_mes8_pagado_epunemi += valor_pagado_epunemi
                                valor_mes8_neto += valor_neto
                            elif mesdesde == 9:
                                valor_mes9_pagado += valor_pagado
                                valor_mes9_pagado_unemi += valor_pagado_unemi
                                valor_mes9_pagado_epunemi += valor_pagado_epunemi
                                valor_mes9_neto += valor_neto
                            elif mesdesde == 10:
                                valor_mes10_pagado += valor_pagado
                                valor_mes10_pagado_unemi += valor_pagado_unemi
                                valor_mes10_pagado_epunemi += valor_pagado_epunemi
                                valor_mes10_neto += valor_neto
                            elif mesdesde == 11:
                                valor_mes11_pagado += valor_pagado
                                valor_mes11_pagado_unemi += valor_pagado_unemi
                                valor_mes11_pagado_epunemi += valor_pagado_epunemi
                                valor_mes11_neto += valor_neto
                            elif mesdesde == 12:
                                valor_mes12_pagado += valor_pagado
                                valor_mes12_pagado_unemi += valor_pagado_unemi
                                valor_mes12_pagado_epunemi += valor_pagado_epunemi
                                valor_mes12_neto += valor_neto
                            if valor_bruto > 0:
                                bandera_mes += 1

                            valor_mes_pagado += valor_pagado
                            valor_mes_pagado_une += valor_pagado_unemi
                            valor_mes_pagado_epu += valor_pagado_epunemi

                            valor_mes_neto += valor_neto
                            ws.write_merge(row_num, row_num, fila, fila, valor_neto, fuentemoneda)
                            fila += 1
                            ws.write_merge(row_num, row_num, fila, fila, valor_pagado_unemi, fuentemonedafv)
                            fila += 1
                            ws.write_merge(row_num, row_num, fila, fila, valor_pagado_epunemi, fuentemonedafn)
                            fila += 1
                            ws.write_merge(row_num, row_num, fila, fila, valor_pagado, fuentemoneda)
                            fila += 1

                            mesdesde += 1
                        ws.write_merge(row_num, row_num, 52, 52, valor_mes_neto, fuentemoneda)
                        ws.write_merge(row_num, row_num, 53, 53, valor_mes_pagado, fuentemoneda)
                        ws.write_merge(row_num, row_num, 2, 2, valor_mes_neto, fuentemoneda)
                        ws.write_merge(row_num, row_num, 3, 3, str(bandera_mes), fuentenormal2)

                        row_num += 1

                ws.write_merge(row_num, row_num, 4, 4, valor_mes1_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 5, 5, valor_mes1_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 6, 6, valor_mes1_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 7, 7, valor_mes1_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 8, 8, valor_mes2_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 9, 9, valor_mes2_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 10, 10, valor_mes2_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 11, 11, valor_mes2_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 12, 12, valor_mes3_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 13, 13, valor_mes3_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 14, 14, valor_mes3_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 15, 15, valor_mes3_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 16, 16, valor_mes4_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 17, 17, valor_mes4_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 18, 18, valor_mes4_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 19, 19, valor_mes4_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 20, 20, valor_mes5_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 21, 21, valor_mes5_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 22, 22, valor_mes5_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 23, 23, valor_mes5_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 24, 24, valor_mes6_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 25, 25, valor_mes6_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 26, 26, valor_mes6_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 27, 27, valor_mes6_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 28, 28, valor_mes7_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 29, 29, valor_mes7_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 30, 30, valor_mes7_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 31, 31, valor_mes7_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 32, 32, valor_mes8_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 33, 33, valor_mes8_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 34, 34, valor_mes8_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 35, 35, valor_mes8_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 36, 36, valor_mes9_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 37, 37, valor_mes9_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 38, 38, valor_mes9_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 39, 39, valor_mes9_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 40, 40, valor_mes10_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 41, 41, valor_mes10_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 42, 42, valor_mes10_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 43, 43, valor_mes10_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 44, 44,valor_mes11_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 45, 45, valor_mes11_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 46, 46, valor_mes11_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 47, 47, valor_mes11_pagado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 48, 48, valor_mes12_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 49, 49, valor_mes12_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 50, 50, valor_mes12_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 51, 51, valor_mes12_pagado, fuentemonedaneg)

                sumatotalproyectado = valor_mes1_neto+valor_mes2_neto+valor_mes3_neto+valor_mes4_neto+valor_mes5_neto+valor_mes6_neto+valor_mes7_neto+valor_mes8_neto+valor_mes9_neto+valor_mes10_neto+valor_mes11_neto+valor_mes12_neto
                sumatotalpagado = valor_mes1_pagado+valor_mes2_pagado+valor_mes3_pagado+valor_mes4_pagado+valor_mes5_pagado+valor_mes6_pagado+valor_mes7_pagado+valor_mes8_pagado+valor_mes9_pagado+valor_mes10_pagado+valor_mes11_pagado+valor_mes12_pagado

                ws.write_merge(row_num, row_num, 52, 52, sumatotalproyectado, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 53, 53, sumatotalpagado, fuentemonedaneg)

                columns = [
                    (u"", 9000),
                    (u"", 9000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000)]
                row_num += 2

                #for col_num in range(3:97):

                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style2)
                    ws.col(col_num).width = columns[col_num][1]

                columns = [
                    (u"", 9000),
                    (u"", 9000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000),
                    (u"", 5000)]
                row_num += 1
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style2)
                    ws.col(col_num).width = columns[col_num][1]
                row_num += 1
                # cartera vencida

                ws.write_merge(row_num, row_num, 0, 0, u'NO ADMITIDOS', fuentenormalneg2)
                row_num += 1
                ws.write_merge(row_num, row_num, 0, 0, u'RUBROS', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 1, 1, u'RUBROS', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 2, 2, u'', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 3, 3, u'', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 4, 4, u'ENERO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 5, 5, u'ENERO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 6, 6, u'ENERO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 7, 7, u'ENERO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 8, 8, u'FEBRERO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 9, 9, u'FEBRERO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 10, 10, u'FEBRERO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 11, 11, u'FEBRERO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 12, 12, u'MARZO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 13, 13, u'MARZO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 14, 14, u'MARZO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 15, 15, u'MARZO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 16, 16, u'ABRIL PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 17, 17, u'ABRIL PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 18, 18, u'ABRIL PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 19, 19, u'ABRIL PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 20, 20, u'MAYO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 21, 21, u'MAYO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 22, 22, u'MAYO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 23, 23, u'MAYO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 24, 24, u'JUNIO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 25, 25, u'JUNIO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 26, 26, u'JUNIO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 27, 27, u'JUNIO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 28, 28, u'JULIO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 29, 29, u'JULIO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 30, 30, u'JULIO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 31, 31, u'JULIO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 32, 32, u'AGOSTO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 33, 33, u'AGOSTO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 34, 34, u'AGOSTO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 35, 35, u'AGOSTO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 36, 36, u'SEPTIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 37, 37, u'SEPTIEMBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 38, 38, u'SEPTIEMBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 39, 39, u'SEPTIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 40, 40, u'OCTUBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 41, 41, u'OCTUBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 42, 42, u'OCTUBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 43, 43, u'OCTUBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 44, 44, u'NOVIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 45, 45, u'NOVIEMBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 46, 46, u'NOVIEMBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 47, 47, u'NOVIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 48, 48, u'DICIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 49, 49, u'DICIEMBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 50, 50, u'DICIEMBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 51, 51, u'DICIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 52, 52, u'TOTAL PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 53, 53, u'TOTAL PAGADO', fuentenormalnegcent2)
                valor_total = 0
                valor_total_bruto = 0
                valor_mes1_pagado = 0
                valor_mes1_pagado_unemi = 0
                valor_mes1_pagado_epunemi = 0
                valor_mes2_pagado = 0
                valor_mes2_pagado_unemi = 0
                valor_mes2_pagado_epunemi = 0
                valor_mes3_pagado = 0
                valor_mes3_pagado_unemi = 0
                valor_mes3_pagado_epunemi = 0
                valor_mes4_pagado = 0
                valor_mes4_pagado_unemi = 0
                valor_mes4_pagado_epunemi = 0
                valor_mes5_pagado = 0
                valor_mes5_pagado_unemi = 0
                valor_mes5_pagado_epunemi = 0
                valor_mes6_pagado = 0
                valor_mes6_pagado_unemi = 0
                valor_mes6_pagado_epunemi = 0
                valor_mes7_pagado = 0
                valor_mes7_pagado_unemi = 0
                valor_mes7_pagado_epunemi = 0
                valor_mes8_pagado = 0
                valor_mes8_pagado_unemi = 0
                valor_mes8_pagado_epunemi = 0
                valor_mes9_pagado = 0
                valor_mes9_pagado_unemi = 0
                valor_mes9_pagado_epunemi = 0
                valor_mes10_pagado = 0
                valor_mes10_pagado_unemi = 0
                valor_mes10_pagado_epunemi = 0
                valor_mes11_pagado = 0
                valor_mes11_pagado_unemi = 0
                valor_mes11_pagado_epunemi = 0
                valor_mes12_pagado = 0
                valor_mes12_pagado_unemi = 0
                valor_mes12_pagado_epunemi = 0

                valor_total_neto = 0
                valor_mes1_neto = 0
                valor_mes2_neto = 0
                valor_mes3_neto = 0
                valor_mes4_neto = 0
                valor_mes5_neto = 0
                valor_mes6_neto = 0
                valor_mes7_neto = 0
                valor_mes8_neto = 0
                valor_mes9_neto = 0
                valor_mes10_neto = 0
                valor_mes11_neto = 0
                valor_mes12_neto = 0
                row_num += 1
                # valornoadmitidos = Decimal(null_to_decimal(Rubro.objects.filter(pago__factura__fecha__year=anio, pago__factura__valida=True, status=True, matricula__isnull=True, tipo__in=codigo_rubro).aggregate(valor=Sum('pago__subtotal0'))['valor'], 2)).quantize(Decimal('.01'))

                for lista in listadorubros:
                    ws.write_merge(row_num, row_num, 0, 0, 'RUBRO', fuentenormal2)
                    ws.write_merge(row_num, row_num, 1, 1, lista[1], fuentenormal2)
                    # ws.write_merge(row_num, row_num, 2, 2, 0, font_style2)
                    # ws.write_merge(row_num, row_num, 3, 3, 0, font_style2)
                    mesdesde = 1
                    valor_mes_pagado = 0
                    valor_mes_neto = 0
                    bandera_mes = 0


                    fila = 4
                    while mesdesde <= 12:
                        valor_bruto = 0
                        valor_pagado = 0

                        # valor_bruto = Decimal(null_to_decimal(Rubro.objects.filter(tipo_id=lista[0], fechavence__year=anio, matricula__isnull=True, fechavence__month=mesdesde, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)).quantize(Decimal('.01'))
                        valor_bruto = Decimal(null_to_decimal(Rubro.objects.filter(tipo_id=lista[0], fechavence__year=anio, matricula__isnull=True, fechavence__month=mesdesde, fechavence__gte=fechadesde, fechavence__lte=fechahasta, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)).quantize(Decimal('.01'))

                        # pagosotros = Pago.objects.filter(rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__year=anio, fecha__month=mesdesde)
                        pagosotros = Pago.objects.filter(rubro__matricula__isnull=True, rubro__tipo_id=lista[0], status=True, rubro__status=True, fecha__year=anio, fecha__month=mesdesde, fecha__gte=fechadesde, fecha__lte=fechahasta)

                        valor_pagado = Decimal(null_to_decimal(pagosotros.aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        valor_pagado_unemi = Decimal(null_to_decimal(pagosotros.filter(idpagoepunemi=0).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        valor_pagado_epunemi = Decimal(null_to_decimal(pagosotros.filter(~Q(idpagoepunemi=0)).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        valor_neto = Decimal(0).quantize(Decimal('.01'))

                        if mesdesde == 1:
                            valor_mes1_pagado += valor_pagado
                            valor_mes1_pagado_unemi += valor_pagado_unemi
                            valor_mes1_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 2:
                            valor_mes2_pagado += valor_pagado
                            valor_mes2_pagado_unemi += valor_pagado_unemi
                            valor_mes2_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 3:
                            valor_mes3_pagado += valor_pagado
                            valor_mes3_pagado_unemi += valor_pagado_unemi
                            valor_mes3_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 4:
                            valor_mes4_pagado += valor_pagado
                            valor_mes4_pagado_unemi += valor_pagado_unemi
                            valor_mes4_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 5:
                            valor_mes5_pagado += valor_pagado
                            valor_mes5_pagado_unemi += valor_pagado_unemi
                            valor_mes5_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 6:
                            valor_mes6_pagado += valor_pagado
                            valor_mes6_pagado_unemi += valor_pagado_unemi
                            valor_mes6_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 7:
                            valor_mes7_pagado += valor_pagado
                            valor_mes7_pagado_unemi += valor_pagado_unemi
                            valor_mes7_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 8:
                            valor_mes8_pagado += valor_pagado
                            valor_mes8_pagado_unemi += valor_pagado_unemi
                            valor_mes8_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 9:
                            valor_mes9_pagado += valor_pagado
                            valor_mes9_pagado_unemi += valor_pagado_unemi
                            valor_mes9_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 10:
                            valor_mes10_pagado += valor_pagado
                            valor_mes10_pagado_unemi += valor_pagado_unemi
                            valor_mes10_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 11:
                            valor_mes11_pagado += valor_pagado
                            valor_mes11_pagado_unemi += valor_pagado_unemi
                            valor_mes11_pagado_epunemi += valor_pagado_epunemi
                        elif mesdesde == 12:
                            valor_mes12_pagado += valor_pagado
                            valor_mes12_pagado_unemi += valor_pagado_unemi
                            valor_mes12_pagado_epunemi += valor_pagado_epunemi


                        if mesdesde == 1: valor_mes1_neto += valor_neto
                        if mesdesde == 2: valor_mes2_neto += valor_neto
                        if mesdesde == 3: valor_mes3_neto += valor_neto
                        if mesdesde == 4: valor_mes4_neto += valor_neto
                        if mesdesde == 5: valor_mes5_neto += valor_neto
                        if mesdesde == 6: valor_mes6_neto += valor_neto
                        if mesdesde == 7: valor_mes7_neto += valor_neto
                        if mesdesde == 8: valor_mes8_neto += valor_neto
                        if mesdesde == 9: valor_mes9_neto += valor_neto
                        if mesdesde == 10: valor_mes10_neto += valor_neto
                        if mesdesde == 11: valor_mes11_neto += valor_neto
                        if mesdesde == 12: valor_mes12_neto += valor_neto

                        if valor_bruto > 0:
                            bandera_mes += 1
                        valor_mes_pagado += valor_pagado
                        valor_mes_neto += valor_neto
                        ws.write_merge(row_num, row_num, fila, fila, valor_neto, fuentemoneda)
                        fila += 1
                        ws.write_merge(row_num, row_num, fila, fila, valor_pagado_unemi, fuentemonedafv)
                        fila += 1
                        ws.write_merge(row_num, row_num, fila, fila, valor_pagado_epunemi, fuentemonedafn)
                        fila += 1
                        ws.write_merge(row_num, row_num, fila, fila, valor_pagado, fuentemoneda)
                        fila += 1

                        mesdesde += 1

                    ws.write_merge(row_num, row_num, 52, 52, valor_mes_neto, fuentemoneda)
                    ws.write_merge(row_num, row_num, 53, 53, valor_mes_pagado, fuentemoneda)
                    ws.write_merge(row_num, row_num, 2, 2, valor_mes_neto , fuentemoneda)
                    ws.write_merge(row_num, row_num, 3, 3, str(bandera_mes), fuentenormal2)
                    row_num += 1

                ws.write_merge(row_num, row_num, 4, 4, valor_mes1_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 5, 5, valor_mes1_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 6, 6, valor_mes1_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 7, 7, valor_mes1_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 8, 8, valor_mes2_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 9, 9, valor_mes2_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 10, 10, valor_mes2_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 11, 11, valor_mes2_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 12, 12, valor_mes3_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 13, 13, valor_mes3_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 14, 14, valor_mes3_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 15, 15, valor_mes3_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 16, 16, valor_mes4_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 17, 17, valor_mes4_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 18, 18, valor_mes4_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 19, 19, valor_mes4_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 20, 20, valor_mes5_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 21, 21, valor_mes5_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 22, 22, valor_mes5_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 23, 23, valor_mes5_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 24, 24, valor_mes6_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 25, 25, valor_mes6_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 26, 26, valor_mes6_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 27, 27, valor_mes6_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 28, 28, valor_mes7_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 29, 29, valor_mes7_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 30, 30, valor_mes7_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 31, 31, valor_mes7_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 32, 32, valor_mes8_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 33, 33, valor_mes8_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 34, 34, valor_mes8_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 35, 35, valor_mes8_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 36, 36, valor_mes9_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 37, 37, valor_mes9_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 38, 38, valor_mes9_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 39, 39, valor_mes9_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 40, 40, valor_mes10_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 41, 41, valor_mes10_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 42, 42, valor_mes10_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 43, 43, valor_mes10_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 44, 44, valor_mes11_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 45, 45, valor_mes11_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 46, 46, valor_mes11_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 47, 47, valor_mes11_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 48, 48, valor_mes12_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 49, 49, valor_mes12_pagado_unemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 50, 50, valor_mes12_pagado_epunemi, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 51, 51, valor_mes12_pagado, fuentemonedaneg)

                ws.write_merge(row_num, row_num, 52, 52, valor_mes1_neto + valor_mes2_neto + valor_mes3_neto + valor_mes4_neto + valor_mes5_neto + valor_mes6_neto + valor_mes7_neto + valor_mes8_neto + valor_mes9_neto + valor_mes10_neto + valor_mes11_neto + valor_mes12_neto, fuentemonedaneg)
                ws.write_merge(row_num, row_num, 53, 53, valor_mes1_pagado + valor_mes2_pagado + valor_mes3_pagado + valor_mes4_pagado + valor_mes5_pagado + valor_mes6_pagado + valor_mes7_pagado + valor_mes8_pagado + valor_mes9_pagado + valor_mes10_pagado + valor_mes11_pagado + valor_mes12_pagado, fuentemonedaneg)

                row_num += 3
                ws.write_merge(row_num, row_num, 0, 0, u'RUBROS ADICIONALES', fuentenormalneg2)
                row_num += 1

                ws.write_merge(row_num, row_num, 0, 3, u'RUBROS', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 4, 4, u'ENERO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 5, 5, u'ENERO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 6, 6, u'ENERO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 7, 7, u'ENERO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 8, 8, u'FEBRERO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 9, 9, u'FEBRERO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 10, 10, u'FEBRERO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 11, 11, u'FEBRERO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 12, 12, u'MARZO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 13, 13, u'MARZO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 14, 14, u'MARZO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 15, 15, u'MARZO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 16, 16, u'ABRIL PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 17, 17, u'ABRIL PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 18, 18, u'ABRIL PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 19, 19, u'ABRIL PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 20, 20, u'MAYO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 21, 21, u'MAYO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 22, 22, u'MAYO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 23, 23, u'MAYO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 24, 24, u'JUNIO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 25, 25, u'JUNIO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 26, 26, u'JUNIO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 27, 27, u'JUNIO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 28, 28, u'JULIO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 29, 29, u'JULIO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 30, 30, u'JULIO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 31, 31, u'JULIO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 32, 32, u'AGOSTO PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 33, 33, u'AGOSTO PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 34, 34, u'AGOSTO PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 35, 35, u'AGOSTO PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 36, 36, u'SEPTIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 37, 37, u'SEPTIEMBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 38, 38, u'SEPTIEMBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 39, 39, u'SEPTIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 40, 40, u'OCTUBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 41, 41, u'OCTUBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 42, 42, u'OCTUBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 43, 43, u'OCTUBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 44, 44, u'NOVIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 45, 45, u'NOVIEMBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 46, 46, u'NOVIEMBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 47, 47, u'NOVIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 48, 48, u'DICIEMBRE PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 49, 49, u'DICIEMBRE PAG.UNE', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 50, 50, u'DICIEMBRE PAG.EPU', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 51, 51, u'DICIEMBRE PAGADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 52, 52, u'TOTAL PROYECTADO', fuentenormalnegcent2)
                ws.write_merge(row_num, row_num, 53, 53, u'TOTAL PAGADO', fuentenormalnegcent2)

                totalesadicionales = [[Decimal(0.0) for i in range(3)] for j in range(12)]

                row_num += 1

                for rubroadicional in rubrosadicionales:
                    ws.write_merge(row_num, row_num, 0, 3, rubroadicional[1], fuentenormal2)
                    col = 4
                    totalrubroadicional = Decimal(0)
                    for nmes in range(1, 13):
                        ws.write_merge(row_num, row_num, col, col, 0, fuentemoneda)

                        valor_adicional_mes = Decimal(null_to_decimal(pagosadicionales.filter(rubro__tipo_id=rubroadicional[0], fecha__month=nmes).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        valor_adicional_mes_une = Decimal(null_to_decimal(pagosadicionales.filter(idpagoepunemi=0, rubro__tipo_id=rubroadicional[0], fecha__month=nmes).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        valor_adicional_mes_epu = Decimal(null_to_decimal(pagosadicionales.filter(~Q(idpagoepunemi=0), rubro__tipo_id=rubroadicional[0], fecha__month=nmes).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        ws.write_merge(row_num, row_num, col + 1, col + 1, valor_adicional_mes_une, fuentemonedafv)
                        ws.write_merge(row_num, row_num, col + 2, col + 2, valor_adicional_mes_epu, fuentemonedafn)
                        ws.write_merge(row_num, row_num, col + 3, col + 3, valor_adicional_mes, fuentemoneda)
                        col += 4

                        totalesadicionales[nmes - 1][0] += valor_adicional_mes_une
                        totalesadicionales[nmes - 1][1] += valor_adicional_mes_epu
                        totalesadicionales[nmes - 1][2] += valor_adicional_mes
                        totalrubroadicional += valor_adicional_mes


                    ws.write_merge(row_num, row_num, col, col, 0, fuentemoneda)
                    ws.write_merge(row_num, row_num, col + 1, col + 1, totalrubroadicional, fuentemoneda)
                    row_num += 1

                col = 4
                for nmes in range(1, 13):
                    ws.write_merge(row_num, row_num, col, col, 0, fuentemonedaneg)
                    ws.write_merge(row_num, row_num, col + 1, col + 1, totalesadicionales[nmes - 1][0], fuentemonedaneg)
                    ws.write_merge(row_num, row_num, col + 2, col + 2, totalesadicionales[nmes - 1][1], fuentemonedaneg)
                    ws.write_merge(row_num, row_num, col + 3, col + 3, totalesadicionales[nmes - 1][2], fuentemonedaneg)
                    col += 4

                ws.write_merge(row_num, row_num, col, col, 0, fuentemonedaneg)
                ws.write_merge(row_num, row_num, col + 1, col + 1, valoradicionales, fuentemonedaneg)

                wb.save(filename)
                # return book
                return JsonResponse({'result': 'ok', 'archivo': ruta})

            except Exception as ex:
                msg = ex.__str__()
                print("error")
                print(msg)
                pass

        elif action == 'reporte_anual_background':
            try:
                tiporeporte = int(request.POST['tiporeporte'])
                anio = request.POST['anio']
                desde = request.POST['desde']
                hasta = request.POST['hasta']
                listaporcentajes = json.loads(request.POST['listaporcentaje'])

                # Guardar la notificación
                notificacion = Notificacion(
                    cuerpo='Generación de reporte de excel en progreso',
                    titulo='Reporte Excel Presupuesto Anual',
                    destinatario=persona,
                    url='',
                    prioridad=1,
                    app_label='SGA',
                    fecha_hora_visible=datetime.now() + timedelta(days=1),
                    tipo=2,
                    en_proceso=True
                )
                notificacion.save(request)

                reporte_presupuesto_anual_background(request=request, data=data, idnotificacion=notificacion.id, tiporeporte=tiporeporte, anio=anio, desde=desde, hasta=hasta, listaporcentajes=listaporcentajes).start()

                return JsonResponse({"result": "ok",
                                     "mensaje": u"El reporte se está generando. Verifique su apartado de notificaciones después de unos minutos.",
                                     "btn_notificaciones": traerNotificaciones(request, data, persona)})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                print("error")
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})

        elif action == 'calculosdescuento':
            try:
                idmatricula = int(request.POST['idm'])
                costomaestria = Decimal(request.POST['cpro']).quantize(Decimal('.01'))
                porcentaje = Decimal(request.POST['pd']).quantize(Decimal('.01'))
                matricula = Matricula.objects.get(pk=idmatricula)
                totalpagado = matricula.total_pagado_alumno()

                valordescuento = Decimal(null_to_decimal((costomaestria * porcentaje) / 100, 2)).quantize(Decimal('.01'))
                costofinalmaestria = costomaestria - valordescuento
                valordevolver = 0
                if totalpagado > costofinalmaestria:
                    valordevolver = totalpagado - costofinalmaestria

                data['maestrante'] = matricula.inscripcion.persona
                data['programa'] = matricula.inscripcion.carrera
                data['periodo'] = matricula.nivel.periodo
                data['costomaestria'] = costomaestria
                data['valordescuento'] = valordescuento
                data['costofinalmaestria'] = costofinalmaestria
                data['totalpagado'] = totalpagado
                data['valordevolver'] = valordevolver

                template = get_template("rec_consultaalumnos/calculodescuento.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                print("error")
                return JsonResponse({"result": "bad"})

        elif action == 'porcentajereporte':
            try:
                tiporeporte = int(request.POST['tiporeporte'])
                anio = request.POST['anio']
                desde = request.POST['desde']
                hasta = request.POST['hasta']

                if tiporeporte == 1:
                    fechadesde = datetime.strptime(anio + '-01-01', '%Y-%m-%d').date()
                    fechahasta = datetime.strptime(anio + '-12-31', '%Y-%m-%d').date()
                else:
                    fechadesde = datetime.strptime(desde, '%Y-%m-%d').date()
                    fechahasta = datetime.strptime(hasta, '%Y-%m-%d').date()

                anio = fechadesde.year

                data['anio'] = anio
                data['tiporeporteanual'] = tiporeporte
                data['fechadesde'] = desde
                data['fechahasta'] = hasta

                lista = []

                # lp1 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__fechavence__year=anio , tipo__id__in=[3, 4]).distinct().order_by('id')

                lp1 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__fechavence__gte=fechadesde, nivel__matricula__rubro__fechavence__lte=fechahasta, tipo__id__in=[3, 4]).distinct().order_by('id')

                # lp2 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__pago__fecha__year=anio, tipo__id__in=[3, 4]).distinct().order_by('id')

                lp2 = Periodo.objects.values_list('id', flat=True).filter(nivel__matricula__rubro__pago__fecha__gte=fechadesde, nivel__matricula__rubro__pago__fecha__lte=fechahasta, tipo__id__in=[3, 4]).distinct().order_by('id')

                lista_periodos = (lp1 | lp2).distinct().order_by('id')

                # lc1 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__fechavence__year=anio, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')

                lc1 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__fechavence__gte=fechadesde, inscripcion__matricula__rubro__fechavence__lte=fechahasta, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')

                # lc2 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__pago__fecha__year=anio, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')

                lc2 = Carrera.objects.values_list('id', flat=True).filter(inscripcion__matricula__rubro__pago__fecha__gte=fechadesde, inscripcion__matricula__rubro__pago__fecha__lte=fechahasta, inscripcion__matricula__nivel__periodo_id__in=lista_periodos, inscripcion__matricula__nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by('nombre')


                lista_carreras = (lc1 | lc2).distinct().order_by('nombre')


                # pagos = Pago.objects.filter(pagoliquidacion__isnull=True,
                #                             rubro__matricula__nivel__periodo_id__in=lista_periodos,
                #                             rubro__matricula__inscripcion__carrera_id__in=lista_carreras,
                #                             status=True,
                #                             rubro__status=True
                #                             ).exclude(factura__valida=False).order_by('fecha', 'rubro__matricula__nivel__periodo_id',
                #                                                                       'rubro__matricula__inscripcion__carrera')

                pagos = Pago.objects.filter(pagoliquidacion__isnull=True,
                                            fecha__gte=fechadesde,
                                            fecha__lte=fechahasta,
                                            rubro__matricula__nivel__periodo_id__in=lista_periodos,
                                            rubro__matricula__inscripcion__carrera_id__in=lista_carreras,
                                            status=True,
                                            rubro__status=True
                                            ).exclude(factura__valida=False).order_by('fecha',
                                                                                      'rubro__matricula__nivel__periodo_id',
                                                                                      'rubro__matricula__inscripcion__carrera')

                pagos = pagos.annotate(anio=ExtractYear('fecha')).values_list('anio','rubro__matricula__nivel__periodo_id','rubro__matricula__inscripcion__carrera_id').annotate(tpagado=Sum('valortotal'))


                for p in Periodo.objects.filter(pk__in=lista_periodos).order_by('id'):
                    for carrera in Carrera.objects.filter(inscripcion__matricula__nivel__periodo=p,
                                                          pk__in=lista_carreras).distinct().order_by('nombre'):

                        datos = {}

                        datos['periodo'] = p.nombre
                        datos['programa'] = carrera.nombre
                        datos['periodoid'] = p.id
                        datos['programaid'] = carrera.id

                        valor = Decimal(null_to_decimal(
                            Rubro.objects.filter(matricula__nivel__periodo=p, matricula__inscripcion__carrera=carrera,
                                                 fechavence__year=anio, status=True).aggregate(valor=Sum('saldo'))[
                                'valor'], 2)).quantize(Decimal('.01'))

                        # Total generado rubros
                        # totalproyectado = Decimal(
                        #     null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                        #                                          matricula__inscripcion__carrera=carrera,
                        #                                          status=True,
                        #                                          fechavence__year=anio
                        #                                          ).aggregate(
                        #         valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))

                        totalproyectado = Decimal(
                            null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                                                                 matricula__inscripcion__carrera=carrera,
                                                                 status=True,
                                                                 fechavence__gte=fechadesde,
                                                                 fechavence__lte=fechahasta
                                                                 ).aggregate(
                                valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))

                        # Total anulado rubros
                        # totalanulado = Decimal(
                        #     null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                        #                                         rubro__matricula__inscripcion__carrera=carrera,
                        #                                         status=True,
                        #                                         rubro__status=True,
                        #                                         rubro__fechavence__year=anio,
                        #                                         factura__valida=False,
                        #                                         factura__status=True).aggregate(
                        #         valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        totalanulado = Decimal(
                            null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                rubro__matricula__inscripcion__carrera=carrera,
                                                                status=True,
                                                                rubro__status=True,
                                                                rubro__fechavence__gte=fechadesde,
                                                                rubro__fechavence__lte=fechahasta,
                                                                factura__valida=False,
                                                                factura__status=True).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        # Total liquidado rubros
                        # totalliquidado = Decimal(
                        #     null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                        #                                         rubro__matricula__inscripcion__carrera=carrera,
                        #                                         status=True,
                        #                                         rubro__status=True,
                        #                                         rubro__fechavence__year=anio,
                        #                                         pagoliquidacion__isnull=False,
                        #                                         pagoliquidacion__status=True).aggregate(
                        #         valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        totalliquidado = Decimal(
                            null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                rubro__matricula__inscripcion__carrera=carrera,
                                                                status=True,
                                                                rubro__status=True,
                                                                rubro__fechavence__gte=fechadesde,
                                                                rubro__fechavence__lte=fechahasta,
                                                                pagoliquidacion__isnull=False,
                                                                pagoliquidacion__status=True).aggregate(
                                valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        valor_bruto = totalproyectado - (totalanulado + totalliquidado)

                        datos['totalproyectado'] = valor_bruto

                        totalpagado = 0
                        aniofila = 0
                        periodofila = 0
                        carrerafila = 0

                        for rp in pagos:
                            if rp[0] == anio and rp[1] == p.id and rp[2] == carrera.id:
                                totalpagado += Decimal(rp[3])
                                aniofila = rp[0]
                                periodofila = rp[1]
                                carrerafila = rp[2]
                            elif aniofila != 0 and aniofila != rp[0] and periodofila != rp[1] and carrerafila != rp[2]:
                                break

                        valor_descuento = Decimal(0.00).quantize(Decimal('.01'))
                        ingreso_neto = valor_bruto - valor_descuento

                        datos['totalpagado'] = totalpagado
                        datos['valordescuento'] = valor_descuento
                        datos['ingresoneto'] = ingreso_neto
                        lista.append(datos)

                data['programas'] = lista
                template = get_template("rec_consultaalumnos/porcentajereporte.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                print("error")
                return JsonResponse({"result": "bad"})

        elif action == 'validardocumentocompromiso':
            try:
                id = int(encrypt(request.POST['id']))
                persona = data['persona']
                valorestado = int(request.POST['estadocompromiso'])
                lista_observaciones = []
                # Obtengo estado a asignar
                estado = obtener_estado_solicitud(2, valorestado)

                # Consulto compromiso de pago
                compromisopago = CompromisoPagoPosgrado.objects.get(pk=id)
                alumno = compromisopago.matricula.inscripcion.persona

                # Actualizo compromiso de pago
                compromisopago.estado = estado
                compromisopago.personarevisa = persona
                compromisopago.observacion = request.POST['observacion'].strip().upper() if 'observacion' in request.POST else ''
                compromisopago.save(request)

                # Si el estado es LEGALIZADO se debe bloquear los rubros para evitar edición o eliminación
                if valorestado == 2:
                    Rubro.objects.filter(status=True, compromisopago=compromisopago).update(bloqueado=True)

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
                                                            observacion='COMPROMISO DE PAGO LEGALIZADO' if valorestado == 2 else compromisopago.observacion,
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

                tituloemail = "Contrato de Programas de Posgrado Legalizado" if valorestado == 2 else "Novedades en Carga de Documentos - Contrato de Programas de Posgrado"

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
                                'observaciones': observaciones,
                                'destinatario': 'ALUMNO',
                                't': miinstitucion()
                                },
                               compromisopago.matricula.inscripcion.persona.lista_emails_envio(),
                               # ['isaltosm@unemi.edu.ec'],
                               [],
                               cuenta=CUENTAS_CORREOS[cuenta][1]
                               )

                # Temporizador para evitar que se bloquee el servicio de gmail
                pausaparaemail.sleep(1)

                log(u'Cambió estado de compromiso de pago de programas de posgrado: %s  - %s - %s' % (persona, compromisopago, estado.descripcion), request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        elif action == 'bloquear':
            try:
                data['title'] = u'Bloqueo Matriculas'
                periodoid = int(request.POST['idperiodo'])
                carreraid = int(request.POST['idcarrera'])
                data['carrera'] = carrera = Carrera.objects.get(pk=carreraid)
                data['periodo'] = periodo = Periodo.objects.get(pk=periodoid)
                data['matriculas'] = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                template = get_template("rec_consultaalumnos/bloquear.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad"})

        elif action == 'activarepunemi':
            try:
                valor = 0
                if Rubro.objects.filter(id=request.POST['id'], status=True).exists():
                    rubro = Rubro.objects.get(id=request.POST['id'], status=True)
                    if not rubro.epunemi:
                        rubro.epunemi = True
                        valor = 1
                    elif rubro.epunemi == False:
                        rubro.epunemi = True
                        valor = 1
                    else:
                        rubro.epunemi = False
                    rubro.save(request)
                return JsonResponse({"result": "ok", "valor": valor})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

        elif action == 'reporte_detallado_general':
            try:
                __author__ = 'Unemi'

                title = easyxf('font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
                title2 = easyxf('font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')
                fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalneg = easyxf('font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalder = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf('font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                                         num_format_str=' "$" #,##0.00')
                fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('Listado')

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'documentos'))
                nombre = "INFORME_MOVIMIENTOS_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)

                fechainicorte = convertir_fecha(request.POST['fechai'])
                fechacorte = convertir_fecha(request.POST['fechaf'])

                ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                ws.write_merge(1, 1, 0, 6, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                ws.write_merge(2, 2, 0, 6, 'DEUDAS DE ESTUDIANTES', title)
                ws.write_merge(3, 3, 0, 6, 'FECHA DE CORTE: %s' % fechacorte, title)
                ws.write_merge(4, 4, 0, 6, 'FECHA DE DESCARGA: %s' % datetime.now().date(), title)

                row_num = 5

                columns = [
                    (u"N°", 700),
                    (u"PER/INI", 3000),
                    (u"PER/FIN", 3000),
                    (u"COHORTE", 3500),
                    (u"PROGRAMAS", 4000),
                    (u"IDENTIFICACION", 3500),
                    (u"ESTUDIANTE", 8000),
                    (u"FECHA MATRICULA", 3000),
                    (u"PORCENTAJE DESCUENTO", 3000),
                    (u"RETIRADO", 3000),
                    (u"FECHA RUBRO", 3000),
                    (u"TIPO MOVIMIENTO", 3000),
                    (u"VALOR MAESTRIA", 3000),
                    (u"DESCUENTO", 3000),
                    (u"VALOR NETO", 3000),
                    (u"VALOR CUOTA GENERADA", 3000),
                    (u"DIFERENCIA NO GENERADA", 3000),
                    (u"#CUOTA", 1500),
                    (u"FECHA VENCE PAGO", 3000),
                    (u"MONTO CUOTA", 3000),
                    (u"PAGADO", 3000),
                    (u"FECHA PAGO", 3000),
                    (u"MONTO PAGO", 3000),
                    (u"VENCIDO", 3000),
                    (u"POR VENCER", 3000),
                    (u"DEUDA", 3000),
                    (u"FACTURA", 4500),
                    (u"#INGRESO CAJA", 2500),
                    (u"FORMA PAGO", 3500),
                    (u"MOTIVO DESCUENTO", 10000),
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                date_format = xlwt.XFStyle()
                date_format.num_format_str = 'yyyy/mm/dd'

                secuencia = 0

                matriculas = Matricula.objects.db_manager('default').select_related().filter(nivel__periodo__tipo_id__in=[3, 4], status=True, fecha__gte=fechainicorte, fecha__lte=fechacorte).distinct().order_by('nivel__periodo', 'inscripcion__carrera', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')

                for lista in matriculas:
                    row_num += 1
                    secuencia += 1
                    fila_totales = row_num
                    persomama = lista.inscripcion.persona
                    alumno = persomama.nombre_completo_inverso()
                    identificacion = persomama.identificacion()
                    periodo = lista.nivel.periodo
                    carrera = lista.inscripcion.carrera
                    valorvencido = lista.vencido_a_la_fechamatricula_concorte(fechacorte)

                    valormaestria = PeriodoCarreraCosto.objects.db_manager('default').values("costo").get(periodo_id=periodo.id, carrera_id=carrera.id).get('costo') if PeriodoCarreraCosto.objects.db_manager('default').filter(periodo_id=periodo.id, carrera_id=carrera.id).exists() else 0
                    ws.write(row_num, 0, secuencia, fuentenormalder)
                    ws.write(row_num, 1, u'%s' % periodo.inicio, date_format)
                    ws.write(row_num, 2, u'%s' % periodo.fin, date_format)
                    ws.write(row_num, 3, u'%s' % periodo.cohorte, fuentenormal)
                    ws.write(row_num, 4, u'%s' % carrera.alias, fuentenormal)
                    ws.write(row_num, 5, u'%s' % identificacion, fuentenormal)
                    ws.write(row_num, 6, u'%s' % alumno, fuentenormal)
                    ws.write(row_num, 7, lista.fecha, date_format)

                    valordescontado = 0
                    porcentaje = 0
                    motivo = ''
                    if lista.matriculanovedad_set.db_manager('default').exists():
                        novedad = lista.matriculanovedad_set.all()[0]
                        motivo = '%s' % novedad.motivo
                        porcentaje = novedad.porcentajedescuento if novedad.porcentajedescuento else 0
                        if porcentaje > 0:
                            valordescontado = Decimal(null_to_decimal((valormaestria * porcentaje) / 100, 2)).quantize(Decimal('.01'))

                    ws.write(row_num, 8, porcentaje if porcentaje > 0 else '', fuentenormal)
                    ws.write(row_num, 9, 'SI' if lista.retiradomatricula else '', fuentenormal)
                    ws.write(row_num, 10, '', fuentenormal)
                    ws.write(row_num, 11, 'COSTO', fuentenormal)
                    ws.write(row_num, 12, valormaestria, fuentemonedaneg)
                    ws.write(row_num, 13, valordescontado if valordescontado > 0 else '', fuentemonedaneg)
                    valorneto = null_to_decimal(valormaestria - float(valordescontado))
                    # diferencia = null_to_decimal(valorneto - float(valorgenerado), 2)
                    ws.write(row_num, 14, valorneto, fuentemonedaneg)
                    # ws.write(row_num, 15, valorgenerado, fuentemonedaneg)
                    # ws.write(row_num, 16, diferencia if diferencia != 0 else '', fuentemonedaneg)
                    ws.write(row_num, 17, '', fuentenormal)
                    ws.write(row_num, 18, '', fuentenormal)
                    ws.write(row_num, 19, '', fuentenormal)
                    ws.write(row_num, 22, '', fuentenormal)
                    ws.write(row_num, 23, valorvencido, fuentemonedaneg)
                    # porvencer = null_to_decimal(valorpendiente - float(valorvencido), 2)
                    # ws.write(row_num, 24, porvencer, fuentemonedaneg)
                    # ws.write(row_num, 25, valorpendiente, fuentemonedaneg)
                    ws.write(row_num, 26, '', fuentenormal)
                    ws.write(row_num, 27, '', fuentenormal)
                    ws.write(row_num, 28, '', fuentenormal)
                    ws.write(row_num, 29, motivo, fuentenormal)
                    cuota = 0
                    for rubro in lista.rubro_set.db_manager('default').values("id", "valortotal", "fecha", "fechavence").filter(status=True, fechavence__lte=fechacorte).distinct().order_by('cuota', "fechavence"):
                        anulado = Decimal(null_to_decimal(Pago.objects.db_manager('default').filter(rubro_id=rubro.get("id"),status=True, factura__valida=False, factura__status=True).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        liquidado = Decimal(null_to_decimal(PagoLiquidacion.objects.db_manager('default').filter(status=True, pagos__rubro_id=rubro.get("id")).aggregate(valor=Sum('pagos__valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        if (rubro.get("valortotal") - (liquidado + anulado)) > 0:
                            row_num += 1
                            secuencia += 1
                            cuota += 1
                            ws.write(row_num, 0, secuencia, fuentenormalder)
                            ws.write(row_num, 1, u'%s' % periodo.inicio, date_format)
                            ws.write(row_num, 2, u'%s' % periodo.fin, date_format)
                            ws.write(row_num, 3, u'%s' % periodo.cohorte, fuentenormal)
                            ws.write(row_num, 4, u'%s' % lista.inscripcion.carrera.alias, fuentenormal)
                            ws.write(row_num, 5, u'%s' % identificacion, fuentenormal)
                            ws.write(row_num, 6, u'%s' % alumno, fuentenormal)
                            ws.write(row_num, 7, '', fuentenormal)
                            ws.write(row_num, 8, '', fuentenormal)
                            ws.write(row_num, 9, '', fuentenormal)
                            ws.write(row_num, 10, rubro.get("fecha"), date_format)
                            ws.write(row_num, 11, 'CUOTA', fuentenormal)
                            ws.write(row_num, 12, '', fuentenormal)
                            ws.write(row_num, 13, '', fuentenormal)
                            ws.write(row_num, 14, '', fuentenormal)
                            ws.write(row_num, 15, '', fuentenormal)
                            ws.write(row_num, 16, '', fuentenormal)
                            ws.write(row_num, 17, cuota, fuentenormal)
                            ws.write(row_num, 18, rubro.get("fechavence"), date_format)
                            ws.write(row_num, 19, (rubro.get("valortotal") - (liquidado + anulado)), fuentemoneda)
                            ws.write(row_num, 20, '', fuentemoneda)
                            ws.write(row_num, 21, '', fuentenormal)
                            ws.write(row_num, 22, '', fuentenormal)
                            ws.write(row_num, 23, '', fuentenormal)
                            ws.write(row_num, 24, '', fuentenormal)
                            ws.write(row_num, 25, '', fuentenormal)
                            ws.write(row_num, 26, '', fuentenormal)
                            ws.write(row_num, 27, '', fuentenormal)
                            ws.write(row_num, 28, '', fuentenormal)
                            ws.write(row_num, 29, '', fuentenormal)


                            for pago in Pago.objects.db_manager('default').select_related().filter(rubro_id=rubro.get("id"),status=True, pagoliquidacion__isnull=True, fecha__gte=fechainicorte, fecha__lte=fechacorte).exclude(factura__valida=False, factura__status=True):
                                row_num += 1
                                secuencia += 1
                                ws.write(row_num, 0, secuencia, fuentenormalder)
                                ws.write(row_num, 1, u'%s' % periodo.inicio, date_format)
                                ws.write(row_num, 2, u'%s' % periodo.fin, date_format)
                                ws.write(row_num, 3, u'%s' % periodo.cohorte, fuentenormal)
                                ws.write(row_num, 4, u'%s' % lista.inscripcion.carrera.alias, fuentenormal)
                                ws.write(row_num, 5, u'%s' % identificacion, fuentenormal)
                                ws.write(row_num, 6, u'%s' % alumno, fuentenormal)
                                ws.write(row_num, 7, '', fuentenormal)
                                ws.write(row_num, 8, '', fuentenormal)
                                ws.write(row_num, 9, '', fuentenormal)
                                ws.write(row_num, 10, '', fuentenormal)
                                ws.write(row_num, 11, 'PAGO', fuentenormal)
                                ws.write(row_num, 12, '', fuentenormal)
                                ws.write(row_num, 13, '', fuentenormal)
                                ws.write(row_num, 14, '', fuentenormal)
                                ws.write(row_num, 15, '', fuentenormal)
                                ws.write(row_num, 16, '', fuentenormal)
                                ws.write(row_num, 17, cuota, fuentenormal)
                                ws.write(row_num, 18, '', fuentenormal)
                                ws.write(row_num, 19, '', fuentenormal)
                                ws.write(row_num, 20, '', fuentenormal)
                                ws.write(row_num, 21, pago.fecha, date_format)
                                ws.write(row_num, 22, pago.valortotal, fuentemoneda)
                                ws.write(row_num, 23, '', fuentenormal)
                                ws.write(row_num, 24, '', fuentenormal)
                                ws.write(row_num, 25, '', fuentenormal)
                                ws.write(row_num, 26, pago.factura().numerocompleto if pago.factura() else '', fuentenormal)
                                ws.write(row_num, 27, pago.comprobante.numero if pago.comprobante else '', fuentenormal)
                                ws.write(row_num, 28, pago.tipo(), fuentenormal)
                                ws.write(row_num, 29, '', fuentenormal)

                    ws.write(fila_totales, 15, Formula("SUM(T%s:T%s" % (fila_totales + 1, row_num + 1) + ")"), fuentemonedaneg)
                    ws.write(fila_totales, 16, Formula("O%s - P%s" % (fila_totales + 1, fila_totales + 1)), fuentemonedaneg)
                    ws.write(fila_totales, 24, Formula("Z%s - X%s" % (fila_totales + 1, fila_totales + 1)), fuentemonedaneg)
                    ws.write(fila_totales, 25, Formula("P%s - U%s" % (fila_totales + 1, fila_totales + 1)), fuentemonedaneg)
                    ws.write(fila_totales, 20, Formula("SUM(W%s:W%s" % (fila_totales + 1, row_num + 1) + ")"), fuentemonedaneg)
                row_num += 1

                wp = wb.add_sheet('Programas')
                wp.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                wp.write_merge(1, 1, 0, 6, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                wp.write_merge(2, 2, 0, 6, 'DEUDAS DE ESTUDIANTES', title)
                columns = [
                    (u"N°", 700),
                    (u"ALIAS", 3500),
                    (u"PROGRAMAS", 16000),
                ]

                row_num = 5
                secuencia = 0
                for col_num in range(len(columns)):
                    wp.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    wp.col(col_num).width = columns[col_num][1]
                carreras_id = Matricula.objects.db_manager('default').values_list("inscripcion__carrera_id").filter(nivel__periodo__tipo_id__in=[3, 4], status=True, fecha__gte=fechainicorte, fecha__lte=fechacorte).distinct()
                carreras = Carrera.objects.db_manager('default').filter(pk__in=carreras_id)
                for lista in carreras:
                    row_num += 1
                    secuencia += 1
                    wp.write(row_num, 0, secuencia, fuentenormalder)
                    wp.write(row_num, 1, u'%s' % lista.alias, fuentenormal)
                    wp.write(row_num, 2, u'%s' % lista.nombre, fuentenormal)

                wb.save(filename)
                return JsonResponse({"result": "ok", "archivo": '/media/documentos/%s' % nombre})
            except Exception as ex:
                msg = ex.__str__()
                return JsonResponse({"result": "bad", "mensaje": u"Error al procesar el reporte. [%s]" % msg})
                # pass

        elif action == 'addmatriculadonovigente':
            try:
                with transaction.atomic():
                    idperiodo = request.POST['id']
                    if not Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=7,periodo_id=idperiodo, status=True).exists():
                        return JsonResponse({"result": True, "mensaje": "No existe niveles creado en el periodo."}, safe=False)
                    else:
                        nivel = Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=7,periodo_id=idperiodo, status=True)[0]
                    f = InscripcionesMaestriasForm(request.POST)
                    if f.is_valid():
                        inscripcion = Inscripcion.objects.get(pk=f.cleaned_data['inscripcion'])
                        if Matricula.objects.filter(inscripcion_id=f.cleaned_data['inscripcion'],nivel__periodo_id=idperiodo, status=True).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": True, "mensaje": "Está persona ya se encuentra matriculado en el periodo seleccionado."}, safe=False)
                        else:
                            if not inscripcion.matriculado_periodo(nivel.periodo):
                                with transaction.atomic():
                                    matricula = Matricula(inscripcion=inscripcion,
                                                          nivel=nivel,
                                                          pago=False,
                                                          iece=False,
                                                          becado=False,
                                                          porcientobeca=0,
                                                          fecha=datetime.now().date(),
                                                          hora=datetime.now().time(),
                                                          fechatope=fechatope(datetime.now().date()),
                                                          termino=True,
                                                          fechatermino=datetime.now())
                                    matricula.save()
                                    codigoitinerario = 0
                                    matricula.actualizar_horas_creditos()
                                    if not inscripcion.itinerario or inscripcion.itinerario < 1:
                                        inscripcion.itinerario = codigoitinerario
                                        inscripcion.save()
                                with transaction.atomic():
                                    matricula.actualiza_matricula()
                                    matricula.inscripcion.actualiza_estado_matricula()
                                    matricula.calcula_nivel()
                            # return matricularposgrado(inscripcion.id, nivel.id, nivel.periodo_id)
                            # log(u'Adiciono matricula: %s' % matricula, request, "add")
                            return JsonResponse({"result": False}, safe=False)
                    else:
                        transaction.set_rollback(True)
                        return JsonResponse({"result": True, "mensaje": "Complete los datos requeridos."}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'addvalormaestria':
            try:
                f = ValorMaestriaForm(request.POST)
                if f.is_valid():
                    if not PeriodoCarreraCosto.objects.filter(status=True, periodo=f.cleaned_data['periodo'],carrera=f.cleaned_data['carrera']).exists():
                        periodocarreracosto = PeriodoCarreraCosto(periodo=f.cleaned_data['periodo'],
                                                                  carrera=f.cleaned_data['carrera'],
                                                                  costo=f.cleaned_data['costo'],
                                                                  costomatricula=f.cleaned_data['costomatricula'],
                                                                  )
                        periodocarreracosto.save(request)
                        log(u'Adiciono nuevo valor de maestria: %s' % periodocarreracosto, request, "add")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Registro Repetido."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editvalormaestria':
            try:
                periodocarreracosto = PeriodoCarreraCosto.objects.get(pk=request.POST['id'])
                f = ValorMaestriaForm(request.POST)
                if f.is_valid():
                    periodocarreracosto.periodo = f.cleaned_data['periodo']
                    periodocarreracosto.carrera = f.cleaned_data['carrera']
                    periodocarreracosto.costo = f.cleaned_data['costo']
                    periodocarreracosto.costomatricula = f.cleaned_data['costomatricula']
                    periodocarreracosto.save(request)
                    log(u'Modificó valor de maestria: %s' % periodocarreracosto, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deletevalormaestria':
            try:
                periodocarreracosto = PeriodoCarreraCosto.objects.get(pk=request.POST['id'])
                log(u'Eliminó valor de maestria: %s' % periodocarreracosto, request, "del")
                periodocarreracosto.status=False
                periodocarreracosto.save(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'nuevo':
            try:
                matricula = DescuentoPosgradoMatricula.objects.get(pk=request.POST['idmatricula'])
                matricularubro = matricula.matricula
                periodo = matricularubro.nivel.periodo
                carrera = matricularubro.inscripcion.carrera
                costomaestria = Decimal(null_to_decimal((periodo.periodocarreracosto_set.filter(carrera=carrera, status=True).aggregate(costo=Sum('costo'))['costo']),2))
                costomatricula = Decimal(null_to_decimal((periodo.periodocarreracosto_set.filter(carrera=carrera, status=True).aggregate(costomatricula=Sum('costomatricula'))['costomatricula']),2))
                configuracion = matricula.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado
                porcentaje = configuracion.porcentaje
                valortotaldescuento = Decimal(null_to_decimal((((costomaestria-costomatricula) * porcentaje) / 100),2))
                rubros = Rubro.objects.filter(matricula=matricularubro, status=True, cancelado=False).order_by('fechavence')
                cantidadrubros = rubros.count()
                valordescuentorubro = round(Decimal(null_to_decimal((valortotaldescuento / cantidadrubros),2)),2)
                diferencia = 0
                valordescuentorubroaux = 0
                acumuladorvalordescuento = 0
                ultimorubro = None
                for r in rubros:
                    if diferencia > 0:
                        valordescuentorubroaux = valordescuentorubro + round(Decimal(null_to_decimal(diferencia,2)),2)
                        diferencia = 0
                    else:
                        valordescuentorubroaux = valordescuentorubro
                    valorrubro = r.saldo
                    if valorrubro >= valordescuentorubroaux:
                        saldoanterior = r.saldo
                        valor = r.valor - round(Decimal(valordescuentorubroaux),2)
                        valortotal = r.valortotal - round(Decimal(valordescuentorubroaux),2)
                        saldo = r.saldo - round(Decimal(valordescuentorubroaux),2)
                        Rubro.objects.filter(id=r.id).update(saldoanterior=saldoanterior, valor=valor,valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            # updaterubroepunemi(codrubroepunemi)
                        #valor=valor,valortotal=valortotal, saldo=saldo
                        # r.save(request)
                    else:
                        diferencia = round(Decimal(valordescuentorubroaux),2) - valorrubro
                        valordescuentorubroaux = r.saldo
                        saldoanterior = r.saldo
                        valor = 0
                        valortotal = 0
                        saldo = 0
                        Rubro.objects.filter(id=r.id).update(cancelado=True, saldoanterior=saldoanterior, valor=valor,valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            # updaterubroepunemi(codrubroepunemi)
                        # r.save(request)
                    acumuladorvalordescuento += round(Decimal(valordescuentorubroaux),2)
                    ultimorubro = r.id
                #se valida la ultima couta los centavos
                if acumuladorvalordescuento != valortotaldescuento:
                    r = Rubro.objects.get(id=ultimorubro)
                    if acumuladorvalordescuento > valortotaldescuento:
                        # restar
                        diferencia = round(Decimal(null_to_decimal((acumuladorvalordescuento - valortotaldescuento),2)),2)
                        valor = r.valor + diferencia
                        valortotal = r.valortotal + diferencia
                        saldo = r.saldo + diferencia
                        Rubro.objects.filter(id=ultimorubro).update(cancelado=False,valor=valor, valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            # updaterubroepunemi(codrubroepunemi)

                        # ultimorubro.save(request)
                    else:
                        #sumar
                        diferencia = round(Decimal(null_to_decimal((valortotaldescuento - acumuladorvalordescuento),2)),2)
                        valor = r.valor - diferencia
                        valortotal = r.valortotal - diferencia
                        saldo = r.saldo - diferencia
                        Rubro.objects.filter(id=ultimorubro).update(cancelado=False,valor=valor, valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            # updaterubroepunemi(codrubroepunemi)

                matricula.valordescuento = valortotaldescuento
                matricula.save(request)
                log(u'Realizo calculo nuevo a: %s' % matricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al realzar calculo."})

        elif action == 'antiguo':
            try:
                matricula = DescuentoPosgradoMatricula.objects.get(pk=request.POST['idmatricula'])
                matricularubro = matricula.matricula
                configuracion = matricula.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado
                porcentaje = configuracion.porcentaje
                fecharige = configuracion.fecharige
                rubros = Rubro.objects.filter(matricula=matricularubro, status=True, cancelado=False, fechavence__gte=fecharige).order_by('fechavence')
                costomaestria = Decimal(null_to_decimal(rubros.aggregate(valor=Sum('saldo'))['valor'],2))
                valortotaldescuento = Decimal(null_to_decimal(((costomaestria * porcentaje) / 100),2))
                cantidadrubros = rubros.count()
                valordescuentorubro = round(Decimal(null_to_decimal((valortotaldescuento / cantidadrubros),2)),2)
                diferencia = 0
                valordescuentorubroaux = 0
                acumuladorvalordescuento = 0
                ultimorubro = None
                for r in rubros:
                    if diferencia > 0:
                        valordescuentorubroaux = valordescuentorubro + round(Decimal(null_to_decimal(diferencia,2)),2)
                        diferencia = 0
                    else:
                        valordescuentorubroaux = valordescuentorubro
                    valorrubro = r.saldo
                    if valorrubro >= valordescuentorubroaux:
                        saldoanterior = r.saldo
                        valor = r.valor - round(Decimal(valordescuentorubroaux),2)
                        valortotal = r.valortotal - round(Decimal(valordescuentorubroaux),2)
                        saldo = r.saldo - round(Decimal(valordescuentorubroaux),2)
                        Rubro.objects.filter(id=r.id).update(saldoanterior=saldoanterior, valor=valor,valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            updaterubroepunemi(codrubroepunemi)
                        #valor=valor,valortotal=valortotal, saldo=saldo
                        # r.save(request)
                    else:
                        diferencia = round(Decimal(valordescuentorubroaux),2) - valorrubro
                        valordescuentorubroaux = r.saldo
                        saldoanterior = r.saldo
                        valor = 0
                        valortotal = 0
                        saldo = 0
                        Rubro.objects.filter(id=r.id).update(cancelado=True, saldoanterior=saldoanterior, valor=valor,valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            updaterubroepunemi(codrubroepunemi)
                        # r.save(request)
                    acumuladorvalordescuento += round(Decimal(valordescuentorubroaux),2)
                    ultimorubro = r.id
                #se valida la ultima couta los centavos
                if acumuladorvalordescuento != valortotaldescuento:
                    r = Rubro.objects.get(id=ultimorubro)
                    if acumuladorvalordescuento > valortotaldescuento:
                        # restar
                        diferencia = round(Decimal(null_to_decimal((acumuladorvalordescuento - valortotaldescuento),2)),2)
                        valor = r.valor + diferencia
                        valortotal = r.valortotal + diferencia
                        saldo = r.saldo + diferencia
                        Rubro.objects.filter(id=ultimorubro).update(cancelado=False,valor=valor, valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            updaterubroepunemi(codrubroepunemi)

                        # ultimorubro.save(request)
                    else:
                        #sumar
                        diferencia = round(Decimal(null_to_decimal((valortotaldescuento - acumuladorvalordescuento),2)),2)
                        valor = r.valor - diferencia
                        valortotal = r.valortotal - diferencia
                        saldo = r.saldo - diferencia
                        Rubro.objects.filter(id=ultimorubro).update(cancelado=False,valor=valor, valortotal=valortotal, saldo=saldo)
                        #calculo epunemi
                        if r.idrubroepunemi > 0:
                            codrubroepunemi = r.idrubroepunemi
                            updaterubroepunemi(codrubroepunemi)

                        # ultimorubro.save(request)
                matricula.valordescuento = valortotaldescuento
                matricula.save(request)
                log(u'Realizo calculo antiguo a: %s' % matricula, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al realzar calculo."})

        elif action == 'configurarcohorte':
            try:
                f = ConfiCohorteMaestriaForm(request.POST)
                cohorte = CohorteMaestria.objects.get(pk=int(encrypt(request.POST['id'])))

                if f.is_valid():
                    # Valido que el monto de presupuesto para becas que no sea inferior a lo ya utilizado
                    if f.cleaned_data['presupuestobeca'] < cohorte.valor_utilizado_presupuestobecas():
                        return JsonResponse({"result": "bad", "mensaje": u"El monto de prespuesto debe ser mayor o igual a ." % f.cleaned_data['presupuestobeca'] })

                    if f.cleaned_data['tienecostomatricula']:
                        cohorte.tienecostomatricula = f.cleaned_data['tienecostomatricula']
                        cohorte.valormatricula=f.cleaned_data['valormatricula']
                    else:
                        cohorte.tienecostomatricula = False
                        cohorte.valormatricula = 0
                    if f.cleaned_data['tienecostomaestria']:
                        cohorte.tienecostototal = f.cleaned_data['tienecostomaestria']
                        cohorte.valorprograma=f.cleaned_data['costomaestria']
                        # if f.cleaned_data['tipootrorubro']:
                        #     cohorte.tiporubro_id = f.cleaned_data['tipootrorubro']
                    else:
                        cohorte.tienecostototal = False
                        cohorte.valorprograma = 0
                        cohorte.tiporubro_id = None
                    if f.cleaned_data['tipootrorubro']:
                        cohorte.tiporubro_id = f.cleaned_data['tipootrorubro']
                    cohorte.valorprogramacertificado = f.cleaned_data['valorprogramacertificado']
                    cohorte.fechavencerubro = f.cleaned_data['fechavencerubro']
                    cohorte.fechainiordinaria = f.cleaned_data['fechainiordinaria']
                    cohorte.fechafinordinaria = f.cleaned_data['fechafinordinaria']
                    cohorte.fechainiextraordinaria = f.cleaned_data['fechainiextraordinaria']
                    cohorte.fechafinextraordinaria = f.cleaned_data['fechafinextraordinaria']
                    cohorte.presupuestobeca = f.cleaned_data['presupuestobeca']
                    cohorte.save(request)
                    log(u'configuró cohorte: %s' % cohorte, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addfinanciamientocohorte':
            try:
                with transaction.atomic():
                    form = ConfigFinanciamientoCohorteForm(request.POST)
                    if form.is_valid():
                        instance = ConfigFinanciamientoCohorte(descripcion=form.cleaned_data['descripcion'],
                                                               cohorte_id=request.POST['cohorte'],
                                                               valormatricula=form.cleaned_data['valormatricula'],
                                                               valorarancel =form.cleaned_data['valorarancel'],
                                                               valortotalprograma =form.cleaned_data['valortotalprograma'],
                                                               porcentajeminpagomatricula =form.cleaned_data['porcentajeminpagomatricula'],
                                                               porcentajedescuentoconvenio=form.cleaned_data['porcentajedescuentoconvenio'],
                                                               maxnumcuota=form.cleaned_data['maxnumcuota'],
                                                               fecha=form.cleaned_data['fecha'],
                                                               )
                        instance.save(request)
                        log(u'Adicionó Config. Financiamiento Cohorte: %s' % instance, request, "add")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in form.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'editfinanciamientocohorte':
            try:
                with transaction.atomic():
                    instance = ConfigFinanciamientoCohorte.objects.get(pk=request.POST['id'])
                    f = ConfigFinanciamientoCohorteForm(request.POST)
                    if f.is_valid():
                        instance.descripcion= f.cleaned_data['descripcion']
                        instance.valormatricula= f.cleaned_data['valormatricula']
                        instance.valorarancel= f.cleaned_data['valorarancel']
                        instance.valortotalprograma= f.cleaned_data['valortotalprograma']
                        instance.porcentajeminpagomatricula= f.cleaned_data['porcentajeminpagomatricula']
                        instance.porcentajedescuentoconvenio= f.cleaned_data['porcentajedescuentoconvenio']
                        instance.maxnumcuota= f.cleaned_data['maxnumcuota']
                        instance.fecha= f.cleaned_data['fecha']
                        instance.save(request)
                        log(u'Editó Config. Financiamiento Cohorte: %s' % instance, request, "edit")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({'error': True, "form": [{k: v[0]} for k, v in f.errors.items()], "message": "Error en el formulario"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

        elif action == 'delfinanciamientocohorte':
            try:
                info = ConfigFinanciamientoCohorte.objects.get(pk=request.POST['id'])
                info.status = False
                info.save(request)
                log(u'Eliminó Config. Financiamiento Cohorte %s' % info, request, "del")
                return JsonResponse({"result": False,"error":False}, safe=False)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True,"error":True, "mensaje": "Intentelo más tarde."}, safe=False)


        elif action == 'duplicarfinanciamientocohorte':
            try:
                ids = request.POST.getlist('id[]')
                confduplicar = ConfigFinanciamientoCohorte.objects.filter(cohorte_id=ids[0])
                confcohorte = ConfigFinanciamientoCohorte.objects.filter(cohorte_id=ids[1])
                deleteconfduplicar = confduplicar.values_list('descripcion')
                #eliminamos registros que no se encuentren en el duplicado
                for d in confcohorte:
                    if not (d.descripcion,) in deleteconfduplicar:
                        d.delete()
                # registramos datos del duplicar que no esten en la conf base.
                for duplicar in confduplicar:
                    if not (duplicar.descripcion,) in confcohorte.values_list('descripcion'):
                        duplicado = ConfigFinanciamientoCohorte(
                                        descripcion=duplicar.descripcion,
                                        cohorte_id=ids[1],
                                        valormatricula=duplicar.valormatricula,
                                        valorarancel=duplicar.valorarancel,
                                        valortotalprograma=duplicar.valortotalprograma,
                                        porcentajeminpagomatricula=duplicar.porcentajeminpagomatricula,
                                        maxnumcuota=duplicar.maxnumcuota)
                        duplicado.save(request)
                log(u'Duplicó Config. Financiamiento de la Cohorte: %s, a la cohorte: %s' % (confduplicar.last().cohorte,confcohorte.last().cohorte), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Duplicado de configuración de cohorte realizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'addrubros':
            try:
                form = TipoOtroRubroIpecRubForm(request.POST)
                if form.is_valid():
                    registro = TipoOtroRubro(nombre=form.cleaned_data['nombre'],
                                             partida_id=101,
                                             unidad_organizacional_id=115,
                                             programa_id=9,
                                             interface=True,
                                             valor=0,
                                             ivaaplicado_id=1,
                                             activo=True,
                                             tiporubro=1,
                                             exportabanco=False,
                                             nofactura=False)
                    registro.save(request)
                    log(u'Registro nuevo rubro: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'deleterubro':
            try:
                rubro = TipoOtroRubro.objects.get(pk=request.POST['id'], status=True)
                if rubro.se_usa():
                    return JsonResponse({"result": "bad", "mensaje": "El rubro se encuentra en uso."})
                rubro.delete()
                log(u'Eliminó rubro: %s' % rubro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'editrubros':
            try:
                form = TipoOtroRubroIpecRubForm(request.POST)
                if form.is_valid():
                    rubro = TipoOtroRubro.objects.get(pk=int(request.POST['id']))
                    if rubro.se_usa():
                        return JsonResponse({"result": "bad", "mensaje": "El rubro se encuentra en uso."})
                    if TipoOtroRubro.objects.filter(nombre=(request.POST['nombre'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": "Existe un rubro con el mismo nombre."})
                    rubro.nombre = form.cleaned_data['nombre']
                    rubro.save(request)

                    log(u'Registro modificado Rubro: %s' % rubro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al editar los datos."})

        elif action == 'reporte_detalle_movimientos_mensuales':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']

                anio_actual = anio
                mes_actual = mes
                ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                primerdia = "1"

                # Fecha inicio de mes
                iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                # Fecha fin de mes
                finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                # Fecha fin de mes anterior
                fechafinmesanterior = iniciomes - relativedelta(days=1)

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
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
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

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1, 10000).__str__() + '.xls'
                nombre = "R1_DETALLE_MENSUAL_" + meses[int(mes_actual)-1].upper() + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 12, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 12, 'DETALLE DE MOVIMIENTOS MENSUALES DE VALORES DEL MES DE ' + meses[int(mes_actual)-1].upper() + ' DEL ' + anio_actual, titulo2)

                fila = 4
                fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(fechafinmesanterior.year)
                fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

                columnas = [
                    (u"PROGRAMAS", 8000),
                    (u"PROG.", 2500),
                    (u"COHORTE", 2500),
                    (u"FECHA PERIODO INICIAL", 3000),
                    (u"FECHA PERIODO FINAL", 3000),
                    (u"ESTUDIANTE", 10000),
                    (u"IDENTIFICACIÓN", 3900),
                    (u"SALDO INICIAL AL " + fechafinant, 4000),
                    (u"FECHA CUOTA", 3000),
                    (u"MONTO CUOTA", 4000),
                    (u"FECHA PAGO", 3000),
                    (u"MONTO PAGO", 4000),
                    (u"SALDO FINAL AL " + fechafinact, 4000)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]

                # Consultar las matriculas y excluir programas no vigentes
                matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                      # inscripcion__persona__cedula='1207064179'
                                                      # inscripcion__carrera__id=60,
                                                      # nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                                      ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                            'inscripcion__persona__apellido2',
                                                                            'inscripcion__persona__nombres')
                c = 0
                totalalumnos = 0
                totalmatriculas = matriculas.count()

                totalsaldoinicial = 0
                totalrubros = 0
                totalpagado = 0
                totalsaldofinal = 0

                fila = 5
                cedula = ''

                for matricula in matriculas:
                    c += 1
                    print("Procesando ", c, " de ", totalmatriculas)

                    # SALDO ANTERIOR
                    totalrubrosanterior = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                             tipo__subtiporubro=1,
                                                                                             fechavence__lt=iniciomes,
                                                                                             ).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    print("Total rubros anterior:", totalrubrosanterior)

                    totalliquidado = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                        tipo__subtiporubro=1,
                                                                                        fechavence__lt=iniciomes,
                                                                                        pago__pagoliquidacion__isnull=False
                                                                                        ).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    print("Total Liquidado ", totalliquidado)

                    totalanulado = Decimal(null_to_decimal(Pago.objects.filter(
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True,
                        rubro__fechavence__lte=finmes,
                        factura__valida=False,
                        factura__status=True
                    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    print("total anulado: ", totalanulado)

                    # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True
                        # rubro__fechavence__lte=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))
                    print("Total Pagado anterior: ", totalpagosanterior)

                    totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula=matricula,
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gte=iniciomes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidado + totalanulado)
                    saldoanterior += totalvencimientosposterior
                    print("Saldo anterior: ", saldoanterior)

                    # RUBROS DEL MES ACTUAL
                    rubros = matricula.rubro_set.filter(status=True, tipo__subtiporubro=1, fechavence__gte=iniciomes, fechavence__lte=finmes)

                    # ESOS RUBROS DEL MES ACTUAL VERIFICAR SI FUERON PAGADOS EN MESES ANTERIORES Y SI SALDO = 0 NO SE DEBE MOSTRAR

                    # CONSULTAR PAGOS DEL MES PERO QUE SON DE RUBROS POSTERIORES
                    # Pagos del mes que corresponden a rubros de meses posteriores

                    pagos_rubros_posteriores = Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__gte=iniciomes,
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula=matricula,
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gt=finmes
                    ).exclude(factura__valida=False)

                    # PAGOS DEL MES ACTUAL
                    pagos = Pago.objects.filter(fecha__gte=iniciomes, fecha__lte=finmes,
                                                pagoliquidacion__isnull=True,
                                                status=True,
                                                rubro__tipo__subtiporubro=1,
                                                rubro__matricula=matricula,
                                                rubro__status=True
                                                # rubro__fechavence__lte=finmes
                                                ).exclude(factura__valida=False)

                    print("Saldo anterior: ", saldoanterior)

                    if saldoanterior != 0 or rubros or pagos or pagos_rubros_posteriores:
                        totalrubroalumno = totalpagoalumno = 0
                        # if rubros or pagos:
                        totalalumnos += 1
                        print(matricula.inscripcion.carrera.nombre)
                        print(matricula.inscripcion.carrera.alias)
                        print(matricula.nivel.periodo.cohorte)
                        print(matricula.nivel.periodo.inicio)
                        print(matricula.nivel.periodo.fin)
                        print(matricula.inscripcion.persona.nombre_completo_inverso())
                        print(matricula.inscripcion.persona.identificacion())

                        if not cedula:
                            cedula = matricula.inscripcion.persona.identificacion()

                        if cedula != matricula.inscripcion.persona.identificacion():
                            cedula = matricula.inscripcion.persona.identificacion()

                        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                        hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                        hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(),
                                          fuentenormal)
                        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                        hojadestino.write(fila, 7, saldoanterior, fuentemoneda)

                        # if matricula.inscripcion.persona.cedula == '0916853559':
                        #     r = matricula.rubro_set.filter(status=True,
                        #                                fechavence__lt='2021-06-01').order_by('fechavence')
                        #     for ru in r:
                        #         print(ru.id, ru.nombre, ru.status, ru.cancelado, ru.fechavence, ru.valortotal)
                        #         if ru.esta_liquidado():
                        #             print("Liquidado")
                        #
                        #
                        # # REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                        # p = Pago.objects.filter(fecha__lt=iniciomes,
                        #                         pagoliquidacion__isnull=True,
                        #                         status=True,
                        #                         rubro__matricula=matricula,
                        #                         rubro__status=True,
                        #                         rubro__fechavence__lte=finmes
                        #                         ).exclude(factura__valida=False, factura__status=True)
                        # print("---IDPAGO--TOTAL PAGO---FECHA PAGO---RUBRO ID---FECHA RUBRO---")
                        # cp = 0
                        # tp = 0
                        # for pa in p:
                        #     cp += 1
                        #     tp += pa.valortotal
                        #     print("Pago #", cp, "-" , pa.id, pa.valortotal, pa.fecha, pa.rubro.id, pa.rubro.fechavence)
                        # print("Total pagado hasta el ", fechafinmesanterior, " $ ", tp)

                        print("SALDO INICIAL AL", fechafinmesanterior, " $: ", saldoanterior, " *********************")

                        # Rubros del año y mes actual
                        print("======RUBROS MES ACTUAL=======")
                        totalrubrosmesactual = 0
                        cantidad_rubros = 0
                        for rubro in rubros:

                            cantidad_rubros += 1

                            print("FECHA CUOTA: ", rubro.fechavence, " MONTO CUOTA: ", rubro.valortotal, " PAGADO:",
                                  rubro.cancelado)
                            # print(rubro.pagos()[0].fecha)

                            # Preguntar si rubro fue pagado en meses anteriores
                            totalpagadorubro = Decimal(null_to_decimal(Pago.objects.filter(
                                # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                                fecha__lt=iniciomes,
                                pagoliquidacion__isnull=True,
                                status=True,
                                rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                                # rubro__matricula__inscripcion__carrera__id=carrera,
                                # rubro__matricula__nivel__periodo__id__in=periodos,
                                rubro__status=True,
                                rubro__fechavence__gte=iniciomes,
                                rubro__fechavence__lte=finmes,
                                rubro=rubro
                            ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                                Decimal('.01'))

                            valor_neto_rubro = rubro.valortotal - totalpagadorubro

                            # totalrubrosmesactual += rubro.valortotal
                            # totalrubroalumno += rubro.valortotal

                            totalrubrosmesactual += valor_neto_rubro
                            totalrubroalumno += valor_neto_rubro

                            if valor_neto_rubro > 0:
                                if saldoanterior != 0:

                                    if cantidad_rubros == 1:
                                        hojadestino.write(fila, 8, "", fuentenormal)
                                        hojadestino.write(fila, 9, "", fuentenormal)
                                        hojadestino.write(fila, 10, "", fuentenormal)
                                        hojadestino.write(fila, 11, "", fuentenormal)
                                        hojadestino.write(fila, 12, "", fuentenormal)

                                    fila += 1

                                    hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                                    hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                                    hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                                    hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                                    hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                                    hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(),
                                                      fuentenormal)
                                    hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(),
                                                      fuentenormal)
                                    hojadestino.write(fila, 7, 0, fuentemoneda)
                                    hojadestino.write(fila, 8, rubro.fechavence, fuentefecha)
                                    # hojadestino.write(fila, 9, rubro.valortotal, fuentemoneda)
                                    hojadestino.write(fila, 9, valor_neto_rubro, fuentemoneda)
                                    hojadestino.write(fila, 10, "", fuentenormal)
                                    hojadestino.write(fila, 11, "", fuentenormal)
                                    hojadestino.write(fila, 12, "", fuentenormal)
                                else:
                                    if cantidad_rubros > 1:
                                        fila += 1
                                        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                                        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                                        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                                        hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                                        hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                                        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                                        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                                        hojadestino.write(fila, 7, 0, fuentemoneda)

                                    # hojadestino.write(fila, 6, 0, fuentemoneda)
                                    hojadestino.write(fila, 8, rubro.fechavence, fuentefecha)
                                    # hojadestino.write(fila, 9, rubro.valortotal, fuentemoneda)
                                    hojadestino.write(fila, 9, valor_neto_rubro, fuentemoneda)
                                    hojadestino.write(fila, 10, "", fuentenormal)
                                    hojadestino.write(fila, 11, "", fuentenormal)
                                    hojadestino.write(fila, 12, "", fuentenormal)

                        if not rubros:
                            hojadestino.write(fila, 8, "", fuentenormal)
                            hojadestino.write(fila, 9, "", fuentenormal)
                            hojadestino.write(fila, 10, "", fuentenormal)
                            hojadestino.write(fila, 11, "", fuentenormal)
                            hojadestino.write(fila, 12, "", fuentenormal)

                        for pago in pagos_rubros_posteriores:
                            totalrubrosmesactual += pago.valortotal
                            totalrubroalumno += pago.valortotal

                            fila += 1
                            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                            hojadestino.write(fila, 7, 0, fuentemoneda)
                            hojadestino.write(fila, 8, pago.fecha, fuentefecha)
                            hojadestino.write(fila, 9, pago.valortotal, fuentemoneda)
                            hojadestino.write(fila, 10, "", fuentenormal)
                            hojadestino.write(fila, 11, "", fuentenormal)
                            hojadestino.write(fila, 12, "", fuentenormal)

                        # Pagos del año y mes actual
                        print("=====PAGOS MES ACTUAL=====")
                        totalpagosmesactual = 0
                        for pago in pagos:
                            print("FECHA PAGO: ", pago.fecha, " MONTO PAGO: ", pago.valortotal, " FECHA VENCE RUBRO:",
                                  pago.rubro.fechavence)

                            totalpagosmesactual += pago.valortotal
                            totalpagoalumno += pago.valortotal

                            fila += 1
                            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                            hojadestino.write(fila, 7, 0, fuentemoneda)
                            hojadestino.write(fila, 8, "", fuentenormal)
                            hojadestino.write(fila, 9, "", fuentenormal)
                            hojadestino.write(fila, 10, pago.fecha, fuentefecha)
                            hojadestino.write(fila, 11, pago.valortotal, fuentemoneda)
                            hojadestino.write(fila, 12, "", fuentenormal)

                        # if not pagos:
                        #     hojadestino.write(fila, 10, "", fuentenormal)
                        #     hojadestino.write(fila, 11, "", fuentenormal)
                        #     hojadestino.write(fila, 12, "", fuentenormal)

                        saldofinmes = (saldoanterior + totalrubrosmesactual) - totalpagosmesactual

                        fila += 1
                        hojadestino.write(fila, 0, "", fuentenormal)
                        hojadestino.write(fila, 1, "", fuentenormal)
                        hojadestino.write(fila, 2, "", fuentenormal)
                        hojadestino.write(fila, 3, "", fuentenormal)
                        hojadestino.write(fila, 4, "", fuentenormal)
                        hojadestino.write(fila, 5, "TOTAL " + matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormalnegrell)
                        hojadestino.write(fila, 6, "", fuentenormal)
                        hojadestino.write(fila, 7, saldoanterior, fuentemonedaneg)
                        hojadestino.write(fila, 8, "", fuentenormal)
                        hojadestino.write(fila, 9, totalrubroalumno, fuentemonedaneg)
                        hojadestino.write(fila, 10, "", fuentenormal)
                        hojadestino.write(fila, 11, totalpagoalumno, fuentemonedaneg)
                        hojadestino.write(fila, 12, saldofinmes, fuentemonedaneg)

                        print("TOTAL SALDO:", totalrubrosmesactual + saldoanterior)
                        print("TOTAL PAGADO: ", totalpagosmesactual)

                        print("SALDO FINAL AL ", finmes, " $: ", saldofinmes, " *********************")

                        totalsaldoinicial += saldoanterior
                        totalrubros += totalrubrosmesactual
                        totalpagado += totalpagosmesactual
                        totalsaldofinal += saldofinmes

                        fila += 1

                hojadestino.write(fila, 5, "TOTAL GENERAL", fuentenormalnegrell)
                hojadestino.write(fila, 7, totalsaldoinicial, fuentemonedaneg)
                hojadestino.write(fila, 9, totalrubros, fuentemonedaneg)
                hojadestino.write(fila, 11, totalpagado, fuentemonedaneg)
                hojadestino.write(fila, 12, totalsaldofinal, fuentemonedaneg)

                print("Total alumnos para el reporte: ", totalalumnos)

                print("Total saldo anterior: ", totalsaldoinicial)
                print("Total rubros del mes: ", totalrubros)
                print("Total pagado del mes: ", totalpagado)
                print("Total saldo actual: ", totalsaldofinal)

                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                print("error")
                pass

        # elif action == 'reporte_detallado_generalori':
        #     try:
        #         __author__ = 'Unemi'
        #
        #         output = io.BytesIO()
        #         workbook = xlsxwriter.Workbook(output)
        #         ws = workbook.add_worksheet('Listado')
        #
        #         ws.set_column(0, 0, 5)
        #         ws.set_column(1, 1, 15)
        #         ws.set_column(2, 2, 15)
        #         ws.set_column(3, 3, 15)
        #         ws.set_column(4, 4, 40)
        #         ws.set_column(5, 5, 15)
        #         ws.set_column(6, 6, 50)
        #         ws.set_column(7, 7, 15)
        #         ws.set_column(8, 8, 15)
        #         ws.set_column(9, 9, 15)
        #         ws.set_column(10, 10, 15)
        #         ws.set_column(11, 11, 20)
        #         ws.set_column(12, 12, 15)
        #         ws.set_column(13, 13, 15)
        #         ws.set_column(14, 14, 15)
        #         ws.set_column(15, 15, 15)
        #         ws.set_column(16, 16, 15)
        #         ws.set_column(17, 17, 10)
        #         ws.set_column(18, 18, 15)
        #         ws.set_column(19, 19, 15)
        #         ws.set_column(20, 20, 15)
        #         ws.set_column(21, 21, 15)
        #         ws.set_column(22, 22, 15)
        #         ws.set_column(23, 23, 15)
        #         ws.set_column(24, 24, 15)
        #         ws.set_column(25, 25, 25)
        #         ws.set_column(26, 26, 15)
        #         ws.set_column(27, 27, 15)
        #         ws.set_column(28, 28, 15)
        #         ws.set_column(29, 29, 40)
        #
        #         formatotitulo_filtros = workbook.add_format(
        #             {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'left', 'font_size': 14})
        #
        #         formatoceldacab = workbook.add_format(
        #             {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
        #         formatoceldaleft = workbook.add_format(
        #             {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})
        #
        #         formatoceldaleft2 = workbook.add_format(
        #             {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})
        #
        #         formatoceldaleft3 = workbook.add_format(
        #             {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})
        #
        #         fechacorte = convertir_fecha(request.POST['fechaf'])
        #
        #         ws.merge_range('A1:AD1', 'UNIVERSIDAD ESTATAL DE MILAGRO', formatotitulo_filtros)
        #         ws.merge_range('A2:AD2', 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', formatotitulo_filtros)
        #         ws.merge_range('A3:AD3', 'DEUDAS DE ESTUDIANTES', formatotitulo_filtros)
        #         ws.merge_range('A4:AD4', 'FECHA DE CORTE: %s' % fechacorte, formatotitulo_filtros)
        #
        #
        #         ws.write(4, 0, 'N°', formatoceldacab)
        #         ws.write(4, 1, 'PER/INI', formatoceldacab)
        #         ws.write(4, 2, 'PER/FIN', formatoceldacab)
        #         ws.write(4, 3, 'COHORTE', formatoceldacab)
        #         ws.write(4, 4, 'PROGRAMAS', formatoceldacab)
        #         ws.write(4, 5, 'IDENTIFICACION', formatoceldacab)
        #         ws.write(4, 6, 'ESTUDIANTE', formatoceldacab)
        #         ws.write(4, 7, 'FECHA MATRICULA', formatoceldacab)
        #         ws.write(4, 8, 'PORCENTAJE DESCUENTO', formatoceldacab)
        #         ws.write(4, 9, 'RETIRADO', formatoceldacab)
        #         ws.write(4, 10, 'FECHA RUBRO', formatoceldacab)
        #         ws.write(4, 11, 'TIPO MOVIMIENTO', formatoceldacab)
        #         ws.write(4, 12, 'VALOR MAESTRIA', formatoceldacab)
        #         ws.write(4, 13, 'DESCUENTO', formatoceldacab)
        #         ws.write(4, 14, 'VALOR NETO', formatoceldacab)
        #         ws.write(4, 15, 'VALOR CUOTA GENERADA', formatoceldacab)
        #         ws.write(4, 16, 'DIFERENCIA NO GENERADA', formatoceldacab)
        #         ws.write(4, 17, '#CUOTA', formatoceldacab)
        #         ws.write(4, 18, 'FECHA VENCE PAGO', formatoceldacab)
        #         ws.write(4, 19, 'MONTO CUOTA', formatoceldacab)
        #         ws.write(4, 20, 'PAGADO', formatoceldacab)
        #         ws.write(4, 21, 'FECHA PAGO', formatoceldacab)
        #         ws.write(4, 22, 'MONTO PAGO', formatoceldacab)
        #         ws.write(4, 23, 'VENCIDO', formatoceldacab)
        #         ws.write(4, 24, 'POR VENCER', formatoceldacab)
        #         ws.write(4, 25, 'DEUDA', formatoceldacab)
        #         ws.write(4, 26, 'FACTURA', formatoceldacab)
        #         ws.write(4, 27, '#INGRESO CAJA', formatoceldacab)
        #         ws.write(4, 28, 'FORMA PAGO', formatoceldacab)
        #         ws.write(4, 29, 'MOTIVO DESCUENTO', formatoceldacab)
        #
        #         fechacorte = convertir_fecha(request.POST['fechaf'])
        #
        #
        #         filas_recorridas = 5
        #
        #         secuencia = 0
        #
        #         matriculas = Matricula.objects.db_manager('default').select_related().filter(nivel__periodo__tipo_id__in=[3, 4], status=True, fecha__lte=fechacorte).distinct().order_by('nivel__periodo', 'inscripcion__carrera', 'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')[:10]
        #
        #         for lista in matriculas:
        #             filas_recorridas += 1
        #             secuencia += 1
        #             fila_totales = filas_recorridas
        #             persomama = lista.inscripcion.persona
        #             alumno = persomama.nombre_completo_inverso()
        #             identificacion = persomama.identificacion()
        #             periodo = lista.nivel.periodo
        #             carrera = lista.inscripcion.carrera
        #             valorvencido = lista.vencido_a_la_fechamatricula_concorte(fechacorte)
        #
        #
        #             valormaestria = PeriodoCarreraCosto.objects.db_manager('default').values("costo").get(periodo_id=periodo.id, carrera_id=carrera.id).get('costo') if PeriodoCarreraCosto.objects.db_manager('default').filter(periodo_id=periodo.id, carrera_id=carrera.id).exists() else 0
        #
        #             ws.write('A%s' % filas_recorridas, str(secuencia), formatoceldaleft)
        #             ws.write('B%s' % filas_recorridas, str(periodo.inicio), formatoceldaleft)
        #             ws.write('C%s' % filas_recorridas, str(periodo.fin), formatoceldaleft)
        #             ws.write('D%s' % filas_recorridas, str(periodo.cohorte), formatoceldaleft)
        #             ws.write('E%s' % filas_recorridas, str(carrera.alias), formatoceldaleft)
        #             ws.write('F%s' % filas_recorridas, str(identificacion), formatoceldaleft)
        #             ws.write('G%s' % filas_recorridas, str(alumno), formatoceldaleft)
        #             ws.write('H%s' % filas_recorridas, str(lista.fecha), formatoceldaleft)
        #
        #             valordescontado = 0
        #             porcentaje = 0
        #             motivo = ''
        #             if lista.matriculanovedad_set.db_manager('default').exists():
        #                 novedad = lista.matriculanovedad_set.all()[0]
        #                 motivo = '%s' % novedad.motivo
        #                 porcentaje = novedad.porcentajedescuento if novedad.porcentajedescuento else 0
        #                 if porcentaje > 0:
        #                     valordescontado = Decimal(null_to_decimal((valormaestria * porcentaje) / 100, 2)).quantize(Decimal('.01'))
        #
        #
        #             ws.write('I%s' % filas_recorridas, str(porcentaje if porcentaje > 0 else ''), formatoceldaleft)
        #             ws.write('J%s' % filas_recorridas, str('SI' if lista.retiradomatricula else ''), formatoceldaleft)
        #             ws.write('K%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('L%s' % filas_recorridas, str('COSTO'), formatoceldaleft)
        #             ws.write('M%s' % filas_recorridas, str(valormaestria), formatoceldaleft)
        #             ws.write('N%s' % filas_recorridas, str(valordescontado), formatoceldaleft)
        #             valorneto = null_to_decimal(valormaestria - float(valordescontado))
        #             # diferencia = null_to_decimal(valorneto - float(valorgenerado), 2)
        #             ws.write('O%s' % filas_recorridas, str(valorneto), formatoceldaleft)
        #             # ws.write('P%s' % filas_recorridas, str(''), formatoceldaleft)
        #             # ws.write('Q%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('R%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('S%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('T%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('W%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('X%s' % filas_recorridas, str(valorvencido), formatoceldaleft)
        #             # porvencer = null_to_decimal(valorpendiente - float(valorvencido), 2)
        #             # ws.write('Y%s' % filas_recorridas, str(''), formatoceldaleft)
        #             # ws.write('Z%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('AA%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('AB%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('AC%s' % filas_recorridas, str(''), formatoceldaleft)
        #             ws.write('AD%s' % filas_recorridas, str(motivo), formatoceldaleft)
        #             cuota = 0
        #             for rubro in lista.rubro_set.db_manager('default').values("id", "valortotal", "fecha", "fechavence").filter(status=True, fechavence__lte=fechacorte).distinct().order_by('cuota', "fechavence"):
        #                 anulado = Decimal(null_to_decimal(Pago.objects.db_manager('default').filter(rubro_id=rubro.get("id"), status=True, factura__valida=False, factura__status=True).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
        #                 liquidado = Decimal(null_to_decimal(PagoLiquidacion.objects.db_manager('default').filter(status=True, pagos__rubro_id=rubro.get("id")).aggregate(valor=Sum('pagos__valortotal'))['valor'], 2)).quantize(Decimal('.01'))
        #                 if (rubro.get("valortotal") - (liquidado + anulado)) > 0:
        #                     filas_recorridas += 1
        #                     secuencia += 1
        #                     cuota += 1
        #                     ws.write('A%s' % filas_recorridas, str(secuencia), formatoceldaleft)
        #                     ws.write('B%s' % filas_recorridas, str(periodo.inicio), formatoceldaleft)
        #                     ws.write('C%s' % filas_recorridas, str(periodo.fin), formatoceldaleft)
        #                     ws.write('D%s' % filas_recorridas, str(periodo.cohorte), formatoceldaleft)
        #                     ws.write('E%s' % filas_recorridas, str(lista.inscripcion.carrera.alias), formatoceldaleft)
        #                     ws.write('F%s' % filas_recorridas, str(identificacion), formatoceldaleft)
        #                     ws.write('G%s' % filas_recorridas, str(alumno), formatoceldaleft)
        #                     ws.write('H%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('I%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('J%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('K%s' % filas_recorridas, str(rubro.get("fecha")), formatoceldaleft)
        #                     ws.write('L%s' % filas_recorridas, str('CUOTA'), formatoceldaleft)
        #                     ws.write('M%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('N%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('O%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('P%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('Q%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('R%s' % filas_recorridas, str(cuota), formatoceldaleft)
        #                     ws.write('S%s' % filas_recorridas, str(rubro.get("fechavence")), formatoceldaleft)
        #                     ws.write('T%s' % filas_recorridas, str((rubro.get("valortotal") - (liquidado + anulado))), formatoceldaleft)
        #                     ws.write('U%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('V%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('W%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('X%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('Y%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('Z%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('AA%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('AB%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('AC%s' % filas_recorridas, str(''), formatoceldaleft)
        #                     ws.write('AD%s' % filas_recorridas, str(''), formatoceldaleft)
        #
        #                     for pago in Pago.objects.db_manager('default').select_related().filter(rubro_id=rubro.get("id"),status=True, pagoliquidacion__isnull=True, fecha__lte=fechacorte).exclude(factura__valida=False, factura__status=True):
        #                         filas_recorridas += 1
        #                         secuencia += 1
        #                         ws.write('A%s' % filas_recorridas, str(secuencia), formatoceldaleft)
        #                         ws.write('B%s' % filas_recorridas, str(periodo.inicio), formatoceldaleft)
        #                         ws.write('C%s' % filas_recorridas, str(periodo.fin), formatoceldaleft)
        #                         ws.write('D%s' % filas_recorridas, str(periodo.cohorte), formatoceldaleft)
        #                         ws.write('E%s' % filas_recorridas, str(lista.inscripcion.carrera.alias), formatoceldaleft)
        #                         ws.write('F%s' % filas_recorridas, str(identificacion), formatoceldaleft)
        #                         ws.write('G%s' % filas_recorridas, str(alumno), formatoceldaleft)
        #                         ws.write('H%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('I%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('J%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('K%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('L%s' % filas_recorridas, str('PAGO'), formatoceldaleft)
        #                         ws.write('M%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('N%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('O%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('P%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('Q%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('R%s' % filas_recorridas, str(cuota), formatoceldaleft)
        #                         ws.write('S%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('T%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('U%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('V%s' % filas_recorridas, str(pago.fecha), formatoceldaleft)
        #                         ws.write('W%s' % filas_recorridas, str(pago.valortotal), formatoceldaleft)
        #                         ws.write('X%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('Y%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('Z%s' % filas_recorridas, str(''), formatoceldaleft)
        #                         ws.write('AA%s' % filas_recorridas, str(pago.factura().numerocompleto if pago.factura() else ''), formatoceldaleft)
        #                         ws.write('AB%s' % filas_recorridas, str(pago.comprobante.numero if pago.comprobante else ''), formatoceldaleft)
        #                         ws.write('AC%s' % filas_recorridas, str(pago.tipo()), formatoceldaleft)
        #                         ws.write('AD%s' % filas_recorridas, str(''), formatoceldaleft)
        #
        #             # ws.write(fila_totales, 'O%s', Formula("SUM(T%s:T%s" % (fila_totales + 1, filas_recorridas + 1) + ")"), formatoceldaleft)
        #             # ws.write(fila_totales, 'P%s', Formula("O%s - P%s" % (fila_totales + 1, fila_totales + 1)), formatoceldaleft)
        #             # ws.write(fila_totales, 'X%s', Formula("Z%s - X%s" % (fila_totales + 1, fila_totales + 1)), formatoceldaleft)
        #             # ws.write(fila_totales, 'Y%s', Formula("P%s - U%s" % (fila_totales + 1, fila_totales + 1)), formatoceldaleft)
        #             # ws.write(fila_totales, 'T%s', Formula("SUM(W%s:W%s" % (fila_totales + 1, filas_recorridas + 1) + ")"), formatoceldaleft)
        #
        #         filas_recorridas += 1
        #
        #         wp = workbook.add_worksheet('Programas')
        #
        #         wp.set_column(0, 0, 5)
        #         wp.set_column(1, 1, 30)
        #         wp.set_column(2, 2, 45)
        #
        #         wp.merge_range('A1:AD1', 'UNIVERSIDAD ESTATAL DE MILAGRO', formatotitulo_filtros)
        #         wp.merge_range('A2:AD2', 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', formatotitulo_filtros)
        #         wp.merge_range('A3:AD3', 'DEUDAS DE ESTUDIANTES', formatoceldacab)
        #
        #         wp.write(3, 0, 'N°', formatoceldacab)
        #         wp.write(3, 1, 'ALIAS', formatoceldacab)
        #         wp.write(3, 2, 'PROGRAMAS', formatoceldacab)
        #
        #         filas_recorridas = 5
        #         secuencia = 0
        #
        #         carreras_id = Matricula.objects.db_manager('default').values_list("inscripcion__carrera_id").filter(nivel__periodo__tipo_id__in=[3, 4], status=True, fecha__lte=fechacorte).distinct()
        #         carreras = Carrera.objects.db_manager('default').filter(pk__in=carreras_id)
        #         for lista in carreras:
        #             filas_recorridas += 1
        #             secuencia += 1
        #
        #             wp.write('A%s' % filas_recorridas, str(secuencia), formatoceldaleft)
        #             wp.write('B%s' % filas_recorridas, str(lista.alias), formatoceldaleft)
        #             wp.write('C%s' % filas_recorridas, str(lista.nombre), formatoceldaleft)
        #
        #         workbook.close()
        #         output.seek(0)
        #         filename = 'INFORME_MOVIMIENTOS_.xlsx'
        #         response = HttpResponse(output,
        #                                 content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        #         response['Content-Disposition'] = 'attachment; filename=%s' % filename
        #
        #         return response
        #     except Exception as ex:
        #         pass

        elif action == 'reporte_vencimiento_mensual':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']

                anio_actual = anio
                mes_actual = mes
                ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                primerdia = "1"

                # Fecha inicio de mes
                iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                # Fecha fin de mes
                finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                # Fecha fin de mes anterior
                fechafinmesanterior = iniciomes - relativedelta(days=1)

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
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
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

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1, 10000).__str__() + '.xls'
                nombre = "R2_VENCIMIENTO_MENSUAL_" + meses[int(mes_actual) - 1].upper() + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 8, 'VENCIMIENTOS MENSUALES DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

                fila = 4

                columnas = [
                    (u"PROGRAMA DE MAESTRÍA", 7000),
                    (u"PROG.", 2500),
                    (u"COHORTE", 3000),
                    (u"FECHA PERIODO INICIAL", 3000),
                    (u"FECHA PERIODO FINAL", 3000),
                    (u"ESTUDIANTE", 10000),
                    (u"IDENTIFICACIÓN", 5000),
                    (u"FECHA CUOTA", 3000),
                    (u"MONTO CUOTA", 3500)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]

                # fila = 4
                # fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(fechafinmesanterior.year)
                # fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

                matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                      # inscripcion__persona__cedula='0917524696',
                                                      # inscripcion__carrera__id=60,
                                                      # nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                                      ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                            'inscripcion__persona__apellido2',
                                                                            'inscripcion__persona__nombres')
                totalmatriculas = matriculas.count()

                # rubros_vencidos = Rubro.objects.filter(
                #     fechavence__gte=iniciomes,
                #     fechavence__lte=finmes,
                #     status=True,
                #     matricula__status=True,
                #     matricula__nivel__periodo__tipo__id__in=[3, 4],
                #     matricula__inscripcion__carrera__id=60,
                #     matricula__nivel__periodo__id__in=[12, 13, 78, 84, 91],
                #                                        # matricula__inscripcion__persona__cedula='1707325062',
                #                                        ).distinct().order_by(
                #     'matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2',
                #     'matricula__inscripcion__persona__nombres')
                #
                # # total = matriculas.count()
                # # print(total)
                # total2 = rubros_vencidos.count()
                # print(total2)
                # totalrubros = 0
                #
                # # for matricula in matriculas:
                # #     print(matricula.inscripcion.carrera.nombre)
                # #     print(matricula.inscripcion.carrera.alias)
                # #     print(matricula.nivel.periodo.cohorte)
                # #     print(matricula.nivel.periodo.inicio)
                # #     print(matricula.nivel.periodo.fin)
                # #     print(matricula.inscripcion.persona.nombre_completo_inverso())
                # #     print(matricula.inscripcion.persona.identificacion())

                fila = 5
                totalrubros = 0
                cont = 1
                for matricula in matriculas:
                    print("Procesando ", cont, " de ", totalmatriculas)
                    rubros = matricula.rubro_set.filter(status=True, fechavence__gte=iniciomes, fechavence__lte=finmes, tipo__subtiporubro=1)

                    pagos_rubros_posteriores = Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__gte=iniciomes,
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula=matricula,
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gt=finmes
                    ).exclude(factura__valida=False)

                    # agregué esto
                    pagos_rubros_posteriores = [] # s3 puso para no tomar en cuenta pagos de rubros posteriores


                    if rubros or pagos_rubros_posteriores:

                        for rubro in rubros:
                            matricula = rubro.matricula
                            # Preguntar si rubro fue pagado en meses anteriores
                            totalpagadorubro = Decimal(null_to_decimal(Pago.objects.filter(
                                # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                                fecha__lt=iniciomes,
                                pagoliquidacion__isnull=True,
                                status=True,
                                rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                                # rubro__matricula__inscripcion__carrera__id=carrera,
                                # rubro__matricula__nivel__periodo__id__in=periodos,
                                rubro__status=True,
                                rubro__fechavence__gte=iniciomes,
                                rubro__fechavence__lte=finmes,
                                rubro=rubro
                            ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                                Decimal('.01'))

                            # Puse esto para
                            # totalpagadorubro = 0 # no importa si pago, solo se obtiene los que vencen en el mes

                            valor_neto_rubro = rubro.valortotal - totalpagadorubro

                            if valor_neto_rubro > 0:
                                print(matricula.inscripcion.carrera.nombre)
                                print(matricula.inscripcion.carrera.alias)
                                print(matricula.nivel.periodo.cohorte)
                                print(matricula.nivel.periodo.inicio)
                                print(matricula.nivel.periodo.fin)
                                print(matricula.inscripcion.persona.nombre_completo_inverso())
                                print(matricula.inscripcion.persona.identificacion())
                                print("Rubro: ", rubro.id)
                                print("Fecha vence:", rubro.fechavence)
                                print("Valor: ", valor_neto_rubro)
                                totalrubros += valor_neto_rubro

                                hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                                hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                                hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                                hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                                hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                                hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                                hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                                hojadestino.write(fila, 7, rubro.fechavence, fuentefecha)
                                hojadestino.write(fila, 8, valor_neto_rubro, fuentemoneda)

                                fila += 1

                        for pago in pagos_rubros_posteriores:
                            matricula = pago.rubro.matricula

                            print(matricula.inscripcion.carrera.nombre)
                            print(matricula.inscripcion.carrera.alias)
                            print(matricula.nivel.periodo.cohorte)
                            print(matricula.nivel.periodo.inicio)
                            print(matricula.nivel.periodo.fin)
                            print(matricula.inscripcion.persona.nombre_completo_inverso())
                            print(matricula.inscripcion.persona.identificacion())
                            print("Rubro: ", pago.rubro.id)
                            print("Fecha vence:", pago.fecha)
                            print("Valor: ", pago.valortotal)
                            totalrubros += pago.valortotal

                            hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                            hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                            hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                            hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                            hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                            hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                            hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                            hojadestino.write(fila, 7, pago.fecha, fuentefecha)
                            hojadestino.write(fila, 8, pago.valortotal, fuentemoneda)

                            fila += 1

                    cont += 1

                hojadestino.write_merge(fila, fila, 0, 7, 'TOTAL GENERAL', fuentenormalnegrell)
                hojadestino.write(fila, 8, totalrubros, fuentemonedaneg)
                print("Total rubros: ", totalrubros)

                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
                # return JsonResponse({'result': 'ok', 'archivo': filename})
            except Exception as ex:
                print("error")
                pass

        elif action == 'reporte_pago_mensual':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                         "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']

                anio_actual = anio
                mes_actual = mes
                ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                primerdia = "1"

                # Fecha inicio de mes
                iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                # Fecha fin de mes
                finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                # Fecha fin de mes anterior
                fechafinmesanterior = iniciomes - relativedelta(days=1)

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
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
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

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'
                nombre = "R3_PAGO_MENSUAL_" + meses[int(mes_actual) - 1].upper() + "_" + datetime.now().strftime(
                    '%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 8, 'PAGOS MENSUALES DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

                fila = 4

                columnas = [
                    (u"PROGRAMAS", 7000),
                    (u"PROG.", 2500),
                    (u"COHORTE", 3000),
                    (u"FECHA PERIODO INICIAL", 3000),
                    (u"FECHA PERIODO FINAL", 3000),
                    (u"ESTUDIANTE", 10000),
                    (u"IDENTIFICACIÓN", 5000),
                    (u"FECHA PAGO", 3000),
                    (u"MONTO PAGO", 3500)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]

                rubros_pagados = Pago.objects.filter(fecha__gte=iniciomes,
                                                     fecha__lte=finmes,
                                                     status=True,
                                                     pagoliquidacion__isnull=True,
                                                     rubro__tipo__subtiporubro=1,
                                                     rubro__status=True,
                                                     rubro__matricula__status=True,
                                                     rubro__matricula__nivel__periodo__tipo__id__in=[3, 4]
                                                     # rubro__matricula__inscripcion__carrera__id=60,
                                                     # rubro__matricula__nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                                     # rubro__matricula__inscripcion__persona__cedula='0923002976'
                                                     ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).exclude(factura__valida=False).distinct().order_by(
                    'rubro__matricula__inscripcion__persona__apellido1',
                    'rubro__matricula__inscripcion__persona__apellido2',
                    'rubro__matricula__inscripcion__persona__nombres', 'fecha')

                totalpagos = rubros_pagados.count()
                print(totalpagos)
                totalpagado = 0
                fila = 5
                for pago in rubros_pagados:
                    print("Procesando ", fila, " de ", totalpagos)
                    matricula = pago.rubro.matricula

                    hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                    hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                    hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                    hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                    hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                    hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                    hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                    hojadestino.write(fila, 7, pago.fecha, fuentefecha)
                    hojadestino.write(fila, 8, pago.valortotal, fuentemoneda)
                    totalpagado += pago.valortotal
                    fila += 1

                hojadestino.write_merge(fila, fila, 0, 7, 'TOTAL GENERAL', fuentenormalnegrell)
                hojadestino.write(fila, 8, totalpagado, fuentemonedaneg)

                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
                # return JsonResponse({'result': 'ok', 'archivo': filename})
            except Exception as ex:
                print("error")
                pass

        elif action == 'reporte_resumen_mensual':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                         "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']

                anio_actual = anio
                mes_actual = mes
                ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                primerdia = "1"

                # Fecha inicio de mes
                iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                # Fecha fin de mes
                finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                # Fecha fin de mes anterior
                fechafinmesanterior = iniciomes - relativedelta(days=1)

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
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                fuenteporcentaje = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; ',
                    num_format_str='0.00%')
                fuenteporcentajeneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str='0.00%')


                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'
                nombre = "R4_RESUMEN_MENSUAL_" + meses[int(mes_actual) - 1].upper() + "_" + datetime.now().strftime(
                    '%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 9, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 9, 'RESUMEN MENSUAL DE MOVIMIENTOS DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

                fila = 4
                fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(fechafinmesanterior.year)
                fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

                # print(fechafinant)
                # print(fechafinact)

                columnas = [
                    (u"PROGRAMAS", 15000),
                    (u"PROG.", 2500),
                    (u"COHORTE", 3000),
                    (u"FECHA PERIODO INICIAL", 3000),
                    (u"FECHA PERIODO FINAL", 3000),
                    (u"SALDO INICIAL AL " + fechafinant, 4000),
                    (u"VENCIMIENTOS DEL MES", 4000),
                    (u"PAGOS DEL MES", 4000),
                    (u"SALDO FINAL AL " + fechafinact, 4000),
                    (u"% VARIACIÓN CARTERA", 3000)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]

                programas_maestria = Matricula.objects.values('inscripcion__carrera__id').filter(status=True,
                                                                                                 # inscripcion__carrera__id=60,
                                                                                                 # nivel__periodo__id__in=[12, 13, 78, 84, 91],
                                                                                                 nivel__periodo__tipo__id__in=[
                                                                                                     3, 4]).annotate(
                    carrera=F('inscripcion__carrera__nombre'),
                    carreraalias=F('inscripcion__carrera__alias'),
                    carreraid=F('inscripcion__carrera__id'),
                    periodo=F('nivel__periodo__nombre'),
                    periodoid=F('nivel__periodo__id'),
                    cohorte=F('nivel__periodo__cohorte'),
                    fechainicio=F('nivel__periodo__inicio'),
                    fechafin=F('nivel__periodo__fin')
                    ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('carrera', 'cohorte')

                # print(programas_maestria)
                totalrubrosanterior = 0
                totalliquidado = 0
                totalanulado = 0
                totalpagosanterior = 0

                totalsaldosinicial = 0
                totalvencimientosmes = 0
                totalpagosmes = 0
                totalsaldosfinal = 0

                vencimientosmes = 0
                pagosmes = 0
                idcarrera = 0
                carrera = ""
                print("PROGRAMA======COHORTE------SALDO AL " + str(fechafinmesanterior) + "----VENCIMIENTOS MES-----PAGOS DEL MES------SALDO FINAL AL " + str(finmes))
                totalsaldoinicialprog = 0
                totalvencimientomesprog = 0
                totalpagomesprog = 0
                totalsaldofinalprog = 0

                fila = 5

                # for programa in programas_maestria:
                #     print(programa)
                #
                # return

                for programa in programas_maestria:
                    print(programa)
                    if not idcarrera:
                        idcarrera = programa['carreraid']
                        carrera = programa['carrera']

                    if idcarrera != programa['carreraid']:
                        if totalsaldoinicialprog != 0 or totalvencimientomesprog != 0 or totalpagomesprog != 0:
                            # fila += 1
                            hojadestino.write(fila, 0, "TOTAL " + carrera, fuentenormalnegrell)
                            hojadestino.write(fila, 1, "", fuentenormalnegrell)
                            hojadestino.write(fila, 2, "", fuentenormalnegrell)
                            hojadestino.write(fila, 3, "", fuentenormalnegrell)
                            hojadestino.write(fila, 4, "", fuentenormalnegrell)
                            hojadestino.write(fila, 5, totalsaldoinicialprog, fuentemonedaneg)
                            hojadestino.write(fila, 6, totalvencimientomesprog, fuentemonedaneg)
                            hojadestino.write(fila, 7, totalpagomesprog, fuentemonedaneg)
                            hojadestino.write(fila, 8, totalsaldofinalprog, fuentemonedaneg)
                            hojadestino.write(fila, 9, ((totalsaldofinalprog - totalsaldoinicialprog) / totalsaldoinicialprog) if totalsaldoinicialprog > 0 else 0 , fuenteporcentajeneg)

                            fila += 1

                            print("TOTAL PROGRAMA: ", totalsaldoinicialprog, "-", totalvencimientomesprog, "-", totalpagomesprog, "-", totalsaldofinalprog)
                            print("=============================================================")

                        idcarrera = programa['carreraid']
                        carrera = programa['carrera']
                        totalsaldoinicialprog = 0
                        totalvencimientomesprog = 0
                        totalpagomesprog = 0
                        totalsaldofinalprog = 0

                    # print(programa['carrera'] + "-" + programa['carreraalias'] + " " +str(programa['cohorte']) + " COHORTE")

                    totalrubrosanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                                       tipo__subtiporubro=1,
                                                                                       fechavence__lt=iniciomes,
                                                                                       matricula__inscripcion__carrera__id=
                                                                                       programa['carreraid'],
                                                                                       matricula__nivel__periodo__id=
                                                                                       programa['periodoid']
                                                                                       ).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    totalliquidadoanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                                          tipo__subtiporubro=1,
                                                                                          fechavence__lt=iniciomes,
                                                                                          matricula__inscripcion__carrera__id=
                                                                                          programa['carreraid'],
                                                                                          matricula__nivel__periodo__id=
                                                                                          programa['periodoid'],
                                                                                          pago__pagoliquidacion__isnull=False
                                                                                          ).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    totalanuladoanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        status=True,
                        rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
                        rubro__matricula__nivel__periodo__id=programa['periodoid'],
                        rubro__status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__fechavence__lte=finmes,
                        factura__valida=False,
                        factura__status=True
                    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
                        rubro__matricula__nivel__periodo__id=programa['periodoid'],
                        rubro__status=True
                        # rubro__fechavence__lte=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
                        rubro__matricula__nivel__periodo__id=programa['periodoid'],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gte=iniciomes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    vencimientosmes = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                                   tipo__subtiporubro=1,
                                                                                   fechavence__gte=iniciomes,
                                                                                   fechavence__lte=finmes,
                                                                                   matricula__inscripcion__carrera__id=
                                                                                   programa['carreraid'],
                                                                                   matricula__nivel__periodo__id=
                                                                                   programa['periodoid']
                                                                                   ).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    totalvencimientos2 = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
                        rubro__matricula__nivel__periodo__id=programa['periodoid'],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gte=iniciomes,
                        rubro__fechavence__lte=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    # Pagos del mes que corresponden a rubros de meses posteriores
                    totalvencimientos3 = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__gte=iniciomes,
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula__inscripcion__carrera__id=programa['carreraid'],
                        rubro__matricula__nivel__periodo__id=programa['periodoid'],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gt=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    vencimientosmes = (vencimientosmes - totalvencimientos2) + totalvencimientos3

                    pagosmes = Decimal(null_to_decimal(Pago.objects.filter(fecha__gte=iniciomes, fecha__lte=finmes,
                                                                           pagoliquidacion__isnull=True,
                                                                           status=True,
                                                                           rubro__tipo__subtiporubro=1,
                                                                           rubro__matricula__inscripcion__carrera__id=
                                                                           programa['carreraid'],
                                                                           rubro__matricula__nivel__periodo__id=
                                                                           programa['periodoid'],
                                                                           rubro__status=True
                                                                           ).exclude(factura__valida=False).aggregate(
                        pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidadoanterior + totalanuladoanterior)
                    saldoanterior += totalvencimientosposterior

                    saldofinal = (saldoanterior + vencimientosmes) - pagosmes
                    # print(saldoanterior)

                    if saldoanterior == 0 and vencimientosmes == 0 and pagosmes == 0:
                        continue

                    totalsaldosinicial += saldoanterior
                    totalvencimientosmes += vencimientosmes
                    totalpagosmes += pagosmes
                    totalsaldosfinal += saldofinal

                    totalsaldoinicialprog += saldoanterior
                    totalvencimientomesprog += vencimientosmes
                    totalpagomesprog += pagosmes
                    totalsaldofinalprog += saldofinal

                    hojadestino.write(fila, 0, programa['carrera'], fuentenormal)
                    hojadestino.write(fila, 1, programa['carreraalias'], fuentenormalcent)
                    hojadestino.write(fila, 2, programa['cohorte'], fuentenormalcent)

                    hojadestino.write(fila, 3, programa['fechainicio'], fuentefecha)
                    hojadestino.write(fila, 4, programa['fechafin'], fuentefecha)

                    hojadestino.write(fila, 5, saldoanterior, fuentemoneda)
                    hojadestino.write(fila, 6, vencimientosmes, fuentemoneda)
                    print("Pagos del mes: ", pagosmes)
                    hojadestino.write(fila, 7, pagosmes, fuentemoneda)
                    hojadestino.write(fila, 8, saldofinal, fuentemoneda)
                    hojadestino.write(fila, 9, ((saldofinal - saldoanterior) / saldoanterior) if saldoanterior > 0 else 0 , fuenteporcentaje)

                    fila += 1

                    print(programa['carrera'] + "-2222", "-", programa['cohorte'], "-$ ", saldoanterior, "- $ ", vencimientosmes, "- $ ", pagosmes, "- $", saldofinal)

                if totalsaldoinicialprog != 0 or totalvencimientomesprog != 0 or totalpagomesprog != 0:
                    hojadestino.write(fila, 0, "TOTAL " + programa['carrera'], fuentenormalnegrell)
                    hojadestino.write(fila, 1, "", fuentenormalnegrell)
                    hojadestino.write(fila, 2, "", fuentenormalnegrell)
                    hojadestino.write(fila, 3, "", fuentenormalnegrell)
                    hojadestino.write(fila, 4, "", fuentenormalnegrell)
                    hojadestino.write(fila, 5, totalsaldoinicialprog, fuentemonedaneg)
                    hojadestino.write(fila, 6, totalvencimientomesprog, fuentemonedaneg)
                    hojadestino.write(fila, 7, totalpagomesprog, fuentemonedaneg)
                    hojadestino.write(fila, 8, totalsaldofinalprog, fuentemonedaneg)
                    hojadestino.write(fila, 9, ((totalsaldofinalprog - totalsaldoinicialprog) / totalsaldoinicialprog) if totalsaldoinicialprog > 0 else 0 , fuenteporcentajeneg)


                    fila += 1

                hojadestino.write(fila, 0, "TOTAL GENERAL", fuentenormalnegrell)
                hojadestino.write(fila, 1, "", fuentenormalnegrell)
                hojadestino.write(fila, 2, "", fuentenormalnegrell)
                hojadestino.write(fila, 3, "", fuentenormalnegrell)
                hojadestino.write(fila, 4, "", fuentenormalnegrell)
                hojadestino.write(fila, 5, totalsaldosinicial, fuentemonedaneg)
                hojadestino.write(fila, 6, totalvencimientosmes, fuentemonedaneg)
                hojadestino.write(fila, 7, totalpagosmes, fuentemonedaneg)
                hojadestino.write(fila, 8, totalsaldosfinal, fuentemonedaneg)
                hojadestino.write(fila, 9, ((totalsaldosfinal - totalsaldosinicial) / totalsaldosinicial) if totalsaldosinicial > 0 else 0 , fuenteporcentajeneg)

                print("TOTAL GENERAL===================================")
                print(totalsaldosinicial, "-", totalvencimientosmes, "-", totalpagosmes, "-", totalsaldosfinal)


                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
                # return JsonResponse({'result': 'ok', 'archivo': filename})
            except Exception as ex:
                print("error")
                pass

        elif action == 'reporte_edad_cartera_vencida':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                         "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']

                anio_actual = anio
                mes_actual = mes
                ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                primerdia = "1"

                # Fecha inicio de mes
                iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                # Fecha fin de mes
                finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                # Fecha fin de mes anterior
                fechafinmesanterior = iniciomes - relativedelta(days=1)

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
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                fuenteporcentaje = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; ',
                    num_format_str='0.00%')

                fuenteporcentajeneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str='0.00%')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'
                nombre = "R5_EDAD_CARTERA_VENCIDA_" + meses[int(mes_actual) - 1].upper() + "_" + datetime.now().strftime(
                    '%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 14, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 14, 'EDAD DE LA CARTERA VENCIDA DEL MES DE ' + meses[int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

                fila = 4
                fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(fechafinmesanterior.year)
                fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

                hojadestino.row(fila).height_mismatch = True
                hojadestino.row(fila).height = 400
                hojadestino.row(fila + 1).height_mismatch = True
                hojadestino.row(fila + 1).height = 400

                columnas = [
                    (u"PROGRAMAS", 8000),
                    (u"PROG.", 2500),
                    (u"COHORTE", 2500),
                    (u"FECHA PERIODO INICIAL", 3000),
                    (u"FECHA PERIODO FINAL", 3000),
                    (u"ESTUDIANTE", 10000),
                    (u"IDENTIFICACIÓN", 3900),
                    (u"VALOR TOTAL PROGRAMA", 4000),
                    (u"VALOR COBRADO A LA FECHA", 4000)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
                    # hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]

                hojadestino.write_merge(fila, fila, 9, 10, "SALDO VENCIDO AL " + fechafinact, fuentecabecera)
                hojadestino.write(fila + 1, 9, "MONTO", fuentecabecera)
                hojadestino.write(fila + 1, 10, "%", fuentecabecera)

                hojadestino.write_merge(fila, fila, 11, 15, "EDAD DE LA CARTERA VENCIDA", fuentecabecera)
                hojadestino.write(fila + 1, 11, "1 - 30", fuentecabecera)
                hojadestino.col(11).width = 4000
                hojadestino.write(fila + 1, 12, "31 - 60", fuentecabecera)
                hojadestino.col(12).width = 4000
                hojadestino.write(fila + 1, 13, "61 - 90", fuentecabecera)
                hojadestino.col(13).width = 4000
                hojadestino.write(fila + 1, 14, "+ 90", fuentecabecera)
                hojadestino.col(14).width = 4000
                hojadestino.write(fila + 1, 15, "ACCIÓN", fuentecabecera)
                hojadestino.col(14).width = 4000
                hojadestino.write_merge(fila, fila + 1, 16, 16, "SALDO POR VENCER AL " + fechafinact, fuentecabecera)
                hojadestino.col(16).width = 4000

                # periodos = Periodo.objects.values('id').filter(nivel__matricula__rubro__saldo__gt=0, nivel__matricula__rubro__fechavence__lt=datetime.now().date(), tipo__id__in=[3, 4]).distinct().order_by('id')
                # matriculas = Matricula.objects.filter(nivel__periodo__tipo__id__in=[3, 4], inscripcion__persona__cedula='0926476813').order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                # print("Ultimo dia mes anterior: ", fechafinmesanterior)
                # print("Primer dia mes actual: ", iniciomes, " Ultimo día mes actual: ", finmes)

                matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                      # inscripcion__persona__cedula='0925980575'
                                                      # inscripcion__carrera__id=60,
                                                      # nivel__periodo__id__in=[12, 13, 78, 84, 91]
                                                      ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                            'inscripcion__persona__apellido2',
                                                                            'inscripcion__persona__nombres')

                # matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by(
                #     'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                totalmatriculas = matriculas.count()

                # print(totalmatriculas)
                c = 0

                horainicio = datetime.now()

                totalalumnos = 0

                totalsaldoinicial = 0
                totalrubros = 0
                totalpagado = 0
                totalsaldofinal = 0

                fila = 6
                cedula = ''

                totalprograma = 0
                totalcobrado = 0
                totalsaldovencido = 0
                totaledad1 = 0
                totaledad2 = 0
                totaledad3 = 0
                totaledad4 = 0
                totalsaldovencer = 0

                for matricula in matriculas:
                    c += 1
                    print("Procesando ", c, " de ", totalmatriculas)

                    periodo = matricula.nivel.periodo
                    costoprograma = Decimal(null_to_decimal(
                        periodo.periodocarreracosto_set.filter(carrera=matricula.inscripcion.carrera,
                                                               status=True).aggregate(costo=Sum('costo'))[
                            'costo'])).quantize(Decimal('.01'))
                    valordescontado = 0

                    if matricula.matriculanovedad_set.filter(tipo=1).exists():
                        novedad = matricula.matriculanovedad_set.filter(tipo=1)[0]
                        motivo = '%s' % novedad.motivo
                        porcentaje = Decimal(novedad.porcentajedescuento).quantize(Decimal('.01')) if novedad.porcentajedescuento else 0
                        if porcentaje > 0:
                            valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(Decimal('.01'))

                    if matricula.descuentoposgradomatricula_set.filter(status=True, estado=2).exists():
                        descuentoayuda = matricula.descuentoposgradomatricula_set.filter(status=True, estado=2)[0]
                        porcentaje = Decimal(null_to_decimal(descuentoayuda.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.porcentaje, 2))
                        if porcentaje > 0:
                            valordescontado = descuentoayuda.valordescuento
                            # valorrubros = costoprograma - valordescontado
                        else:
                            valordescontado = Decimal(0)
                            # porcentaje = round((valorrubros * 100) / costoprograma, 2)
                            # valorrubros = costoprograma - valordescontado


                    valortotalprograma = costoprograma - valordescontado

                    if matricula.retiradomatricula or matricula.retirado_programa_maestria():
                        print("Retirado", valortotalprograma, " - ", matricula.total_generado_alumno_retirado())
                        print(matricula.inscripcion.persona.cedula)
                        valortotalprograma = matricula.total_generado_alumno_retirado()

                    # SALDO ANTERIOR
                    totalrubrosanterior = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                             tipo__subtiporubro=1,
                                                                                             fechavence__lt=iniciomes
                                                                                             ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                    print("Total rubros anterior:", totalrubrosanterior)

                    totalliquidado = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                        tipo__subtiporubro=1,
                                                                                        fechavence__lt=iniciomes,
                                                                                        pago__pagoliquidacion__isnull=False
                                                                                        ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    print("Total Liquidado ", totalliquidado)

                    totalanulado = Decimal(null_to_decimal(Pago.objects.filter(
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True,
                        rubro__fechavence__lte=finmes,
                        factura__valida=False,
                        factura__status=True
                    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    print("total anulado: ", totalanulado)

                    # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True
                        # rubro__fechavence__lte=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                    print("Total Pagado anterior: ", totalpagosanterior)

                    totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula=matricula,
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gte=iniciomes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidado + totalanulado)
                    saldoanterior += totalvencimientosposterior

                    print("Saldo anterior: ", saldoanterior)

                    if saldoanterior != 0:
                        totalprograma += valortotalprograma
                        totalcobrado += totalpagosanterior
                        totalsaldovencido += saldoanterior

                        valoredad1 = 0
                        valoredad2 = 0
                        valoredad3 = 0
                        valoredad4 = 0

                        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                        hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                        hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(), fuentenormal)
                        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                        hojadestino.write(fila, 7, valortotalprograma, fuentemoneda)
                        hojadestino.write(fila, 8, totalpagosanterior, fuentemoneda)
                        hojadestino.write(fila, 9, saldoanterior, fuentemoneda)

                        porcentajevencido = saldoanterior / valortotalprograma if valortotalprograma > 0 else 0

                        if porcentajevencido < 0:
                            porcentajevencido = 0

                        hojadestino.write(fila, 10, porcentajevencido, fuenteporcentaje)


                        # ===== SALDOS 1-30, 31-60, 61-90, + 90 DIAS
                        fechafincartera = fechafinmesanterior
                        fechainiciocartera = datetime.strptime(str(fechafincartera.year) + '-' + str(fechafincartera.month) + '-' + primerdia, '%Y-%m-%d').date()

                        columna = 11

                        for n in range(1, 4):

                            totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                                    tipo__subtiporubro=1,
                                                                                                    fechavence__gte=fechainiciocartera,
                                                                                                    fechavence__lte=fechafincartera
                                                                                                    ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                            print("Total rubros anterior:", totalrubrosanterior)

                            totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                                       tipo__subtiporubro=1,
                                                                                                       fechavence__gte=fechainiciocartera,
                                                                                                       fechavence__lte=fechafincartera,
                                                                                                       pago__pagoliquidacion__isnull=False
                                                                                                       ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                            print("Total Liquidado ", totalliquidado)

                            totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                                status=True,
                                rubro__matricula=matricula,
                                rubro__status=True,
                                rubro__tipo__subtiporubro=1,
                                rubro__fechavence__gte=fechainiciocartera,
                                rubro__fechavence__lte=fechafincartera,
                                factura__valida=False,
                                factura__status=True
                            ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                            print("total anulado: ", totalanulado)

                            # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                            totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                                fecha__lt=iniciomes,
                                pagoliquidacion__isnull=True,
                                status=True,
                                rubro__tipo__subtiporubro=1,
                                rubro__matricula=matricula,
                                rubro__status=True,
                                rubro__fechavence__gte=fechainiciocartera,
                                rubro__fechavence__lte=fechafincartera
                            ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                            print("Total Pagado anterior: ", totalpagosanterior)
                            saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                            print("Saldo anterior 1-30 días:", saldoanteriorcartera)

                            hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)

                            if n == 1:
                                totaledad1 += saldoanteriorcartera
                                valoredad1 = saldoanteriorcartera
                            elif n == 2:
                                totaledad2 += saldoanteriorcartera
                                valoredad2 = saldoanteriorcartera
                            else:
                                totaledad3 += saldoanteriorcartera
                                valoredad3 = saldoanteriorcartera

                            columna += 1

                            fechafincartera = fechainiciocartera - relativedelta(days=1)
                            fechainiciocartera = datetime.strptime(str(fechafincartera.year) + '-' + str(fechafincartera.month) + '-' + primerdia,'%Y-%m-%d').date()

                        fechainiciocartera = fechafincartera + relativedelta(days=1)
                        print("Fecha inicio de cartera:", fechainiciocartera)
                        totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                                tipo__subtiporubro=1,
                                                                                                fechavence__lt=fechainiciocartera
                                                                                                ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
                        print("Total rubros anterior:", totalrubroscartera)

                        totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                                   tipo__subtiporubro=1,
                                                                                                   fechavence__lt=fechainiciocartera,
                                                                                                   pago__pagoliquidacion__isnull=False
                                                                                                   ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                        print("Total Liquidado ", totalliquidadocartera)

                        totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                            status=True,
                            rubro__tipo__subtiporubro=1,
                            rubro__matricula=matricula,
                            rubro__status=True,
                            rubro__fechavence__lt=fechainiciocartera,
                            factura__valida=False,
                            factura__status=True
                        ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                        print("total anulado: ", totalanuladocartera)

                        # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                        totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                            fecha__lt=iniciomes,
                            pagoliquidacion__isnull=True,
                            status=True,
                            rubro__tipo__subtiporubro=1,
                            rubro__matricula=matricula,
                            rubro__status=True,
                            rubro__fechavence__lt=fechainiciocartera
                        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                        print("Total Pagado anterior: ", totalpagoscartera)

                        # saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                        aux = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                        saldoanteriorcartera = saldoanterior - (valoredad1 + valoredad2 + valoredad3)

                        saldovencer = valortotalprograma - totalpagosanterior - saldoanterior
                        print("Saldo anterior mayor a 90 días:", saldoanteriorcartera)
                        hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)

                        porcvenc = porcentajevencido * 100
                        if porcvenc == 0:
                            accion_coactiva = ""
                        elif porcvenc > 0.01 and porcvenc <= 15:
                            accion_coactiva = "TEXTO"
                        elif porcvenc > 15 and porcvenc < 50:
                            accion_coactiva = "E-MAIL"
                        else:
                            accion_coactiva = "COACTIVA"


                        hojadestino.write(fila, columna + 1, accion_coactiva, fuentenormal)

                        hojadestino.write(fila, columna + 2, saldovencer, fuentemoneda)

                        totaledad4 += saldoanteriorcartera
                        totalsaldovencer += saldovencer

                        fila += 1

                hojadestino.write_merge(fila, fila, 0, 6, "TOTAL GENERAL", fuentenormalnegrell)
                hojadestino.write(fila, 7, totalprograma, fuentemonedaneg)
                hojadestino.write(fila, 8, totalcobrado, fuentemonedaneg)
                hojadestino.write(fila, 9, totalsaldovencido, fuentemonedaneg)

                hojadestino.write(fila, 11, totaledad1, fuentemonedaneg)
                hojadestino.write(fila, 12, totaledad2, fuentemonedaneg)
                hojadestino.write(fila, 13, totaledad3, fuentemonedaneg)
                hojadestino.write(fila, 14, totaledad4, fuentemonedaneg)


                hojadestino.write(fila, 16, totalsaldovencer, fuentemonedaneg)

                fila += 1
                hojadestino.write(fila, 9, 1, fuenteporcentajeneg)
                hojadestino.write(fila, 11, totaledad1 / totalsaldovencido, fuenteporcentajeneg)
                hojadestino.write(fila, 12, totaledad2 / totalsaldovencido, fuenteporcentajeneg)
                hojadestino.write(fila, 13, totaledad3 / totalsaldovencido, fuenteporcentajeneg)
                hojadestino.write(fila, 14, totaledad4 / totalsaldovencido, fuenteporcentajeneg)

                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
                # return JsonResponse({'result': 'ok', 'archivo': filename})
            except Exception as ex:
                print("error")
                pass

        elif action == 'reporte_proyeccion_cobros':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                         "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']

                anio_actual = anio
                mes_actual = mes
                ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                primerdia = "1"

                # Fecha inicio de mes
                iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                # Fecha fin de mes
                finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                # Fecha fin de mes anterior
                fechafinmesanterior = iniciomes - relativedelta(days=1)

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
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                fuenteporcentajeneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str='0.00%')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1,
                                                                                                             10000).__str__() + '.xls'
                nombre = "R6_PROYECCION_COBROS_POSGRADO_" + meses[
                    int(mes_actual) - 1].upper() + "_" + datetime.now().strftime(
                    '%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 14, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 14, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 14, 'PROYECCIÓN DE COBROS POSGRADO', titulo2)
                # hojadestino.write_merge(2, 2, 0, 14, 'EDAD DE LA CARTERA VENCIDA DEL MES DE ' + meses[
                #     int(mes_actual) - 1].upper() + ' DEL ' + anio_actual, titulo2)

                fila = 4
                fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(fechafinmesanterior.year)
                fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

                hojadestino.row(fila).height_mismatch = True
                hojadestino.row(fila).height = 400
                hojadestino.row(fila + 1).height_mismatch = True
                hojadestino.row(fila + 1).height = 400

                columnas = [
                    (u"PROGRAMAS", 8000),
                    (u"PROG.", 2500),
                    (u"COHORTE", 2500),
                    (u"FECHA PERIODO INICIAL", 3000),
                    (u"FECHA PERIODO FINAL", 3000),
                    (u"ESTUDIANTE", 10000),
                    (u"IDENTIFICACIÓN", 3900),
                    (u"VALOR TOTAL PROGRAMA", 4000),
                    (u"VALOR COBRADO A LA FECHA", 4000),
                    # (u"SALDO VENCIDO AL " + fechafinant, 4000),
                    (u"SALDO VENCIDO AL " + fechafinact, 4000),
                    (U"SALDO POR VENCER AL " + fechafinact, 4000)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write_merge(fila, fila + 1, col_num, col_num, columnas[col_num][0], fuentecabecera)
                    # hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]

                hojadestino.write_merge(fila, fila, 11, 14, "PROYECCIÓN DE COBROS", fuentecabecera)
                hojadestino.write(fila + 1, 11, "1 - 30", fuentecabecera)
                hojadestino.col(11).width = 4000
                hojadestino.write(fila + 1, 12, "31 - 60", fuentecabecera)
                hojadestino.col(12).width = 4000
                hojadestino.write(fila + 1, 13, "61 - 90", fuentecabecera)
                hojadestino.col(13).width = 4000
                hojadestino.write(fila + 1, 14, "+ 90", fuentecabecera)
                hojadestino.col(14).width = 4000

                # periodos = Periodo.objects.values('id').filter(nivel__matricula__rubro__saldo__gt=0, nivel__matricula__rubro__fechavence__lt=datetime.now().date(), tipo__id__in=[3, 4]).distinct().order_by('id')
                # matriculas = Matricula.objects.filter(nivel__periodo__tipo__id__in=[3, 4], inscripcion__persona__cedula='0926476813').order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                # print("Ultimo dia mes anterior: ", fechafinmesanterior)
                # print("Primer dia mes actual: ", iniciomes, " Ultimo día mes actual: ", finmes)

                lista_cedulas = ['0940118045', '0928364082', '0704120369', '0925007726', '0909116311', '0925007940','0928541556', '1205907601', '0926477142', '0923070536', '0940358872']

                matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                      # inscripcion__persona__cedula__in=lista_cedulas
                                                      # inscripcion__carrera__id=60,
                                                      # nivel__periodo__id__in=[12, 13, 78, 84, 91],
                                                      ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                            'inscripcion__persona__apellido2',
                                                                            'inscripcion__persona__nombres')

                # matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).distinct().order_by(
                #     'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                totalmatriculas = matriculas.count()

                # print(totalmatriculas)
                c = 0

                horainicio = datetime.now()

                totalalumnos = 0

                totalsaldoinicial = 0
                totalrubros = 0
                totalpagado = 0
                totalsaldofinal = 0

                fila = 6
                cedula = ''

                totalprograma = 0
                totalcobrado = 0
                totalsaldovencido = 0
                totaledad1 = 0
                totaledad2 = 0
                totaledad3 = 0
                totaledad4 = 0
                totalsaldovencer = 0

                for matricula in matriculas:
                    c += 1
                    print("Procesando ", c, " de ", totalmatriculas)

                    periodo = matricula.nivel.periodo

                    costoprograma = Decimal(null_to_decimal(
                        periodo.periodocarreracosto_set.filter(carrera=matricula.inscripcion.carrera,
                                                               status=True).aggregate(costo=Sum('costo'))[
                            'costo'])).quantize(Decimal('.01'))
                    valordescontado = 0

                    if matricula.matriculanovedad_set.filter(tipo=1).exists():
                        novedad = matricula.matriculanovedad_set.filter(tipo=1)[0]
                        motivo = '%s' % novedad.motivo
                        porcentaje = Decimal(novedad.porcentajedescuento).quantize(
                            Decimal('.01')) if novedad.porcentajedescuento else 0
                        if porcentaje > 0:
                            valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(
                                Decimal('.01'))

                    if matricula.descuentoposgradomatricula_set.filter(status=True, estado=2).exists():
                        descuentoayuda = matricula.descuentoposgradomatricula_set.filter(status=True, estado=2)[0]
                        porcentaje = Decimal(null_to_decimal(descuentoayuda.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.porcentaje, 2))
                        if porcentaje > 0:
                            valordescontado = descuentoayuda.valordescuento
                            # valorrubros = costoprograma - valordescontado
                        else:
                            valordescontado = Decimal(0)
                            # porcentaje = round((valorrubros * 100) / costoprograma, 2)
                            # valorrubros = costoprograma - valordescontado


                    valortotalprograma = costoprograma - valordescontado

                    if matricula.retiradomatricula or matricula.retirado_programa_maestria():
                        print("Retirado", valortotalprograma, " - ", matricula.total_generado_alumno_retirado())
                        valortotalprograma = matricula.total_generado_alumno_retirado()

                    # SALDO ANTERIOR
                    totalrubrosanterior = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                             tipo__subtiporubro=1,
                                                                                             fechavence__lte=finmes # iniciomes
                                                                                             # fechavence__lt=iniciomes
                                                                                             ).aggregate(
                        valor=Sum('valortotal'))[
                                                                      'valor'], 2)).quantize(Decimal('.01'))
                    print("Total rubros anterior:", totalrubrosanterior)

                    totalliquidado = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                        tipo__subtiporubro=1,
                                                                                        fechavence__lte=finmes,
                                                                                        # fechavence__lt=iniciomes,
                                                                                        pago__pagoliquidacion__isnull=False
                                                                                        ).aggregate(
                        valor=Sum('valortotal'))[
                                                                 'valor'], 2)).quantize(Decimal('.01'))

                    print("Total Liquidado ", totalliquidado)

                    totalanulado = Decimal(null_to_decimal(Pago.objects.filter(
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True,
                        rubro__fechavence__lte=finmes,
                        factura__valida=False,
                        factura__status=True
                    ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    print("total anulado: ", totalanulado)

                    # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True
                        # rubro__fechavence__lte=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))
                    print("Total Pagado anterior: ", totalpagosanterior)

                    totalpagosalafecha = Decimal(null_to_decimal(Pago.objects.filter(
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula=matricula,
                        rubro__status=True
                        # rubro__fechavence__lte=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))
                    print("Total Pagado a la fecha: ", totalpagosalafecha)

                    totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        # fecha__lt=iniciomes, # este era
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        rubro__matricula=matricula,
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        # rubro__fechavence__gte=iniciomes
                        rubro__fechavence__gt=finmes
                    ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    # saldoanterior = totalrubrosanterior - (totalpagosanterior + totalliquidado + totalanulado)
                    saldoanterior = totalrubrosanterior - (totalpagosalafecha + totalliquidado + totalanulado)
                    saldoanterior += totalvencimientosposterior

                    print("Saldo anterior: ", saldoanterior)

                    saldovencer = valortotalprograma - totalpagosanterior - saldoanterior
                    saldovencer2 = valortotalprograma - totalpagosalafecha - saldoanterior

                    if saldoanterior == 0 and saldovencer == 0 and saldovencer2 == 0:
                        fechainiciocartera1 = finmes + relativedelta(days=1)
                        rubros_por_cobrar = matricula.rubro_set.filter(status=True, tipo__subtiporubro=1, fechavence__gte=fechainiciocartera1, cancelado=False).count()
                        if rubros_por_cobrar > 0:
                            print(matricula.inscripcion.persona.cedula)
                            print("Si tiene rubros por cobrar")

                    
                    if saldoanterior != 0 or saldovencer != 0 or saldovencer2 != 0:
                        totalprograma += valortotalprograma
                        # totalcobrado += totalpagosanterior
                        totalcobrado += totalpagosalafecha
                        totalsaldovencido += saldoanterior

                        saldovencer = valortotalprograma - totalpagosanterior - saldoanterior
                        saldovencer2 = valortotalprograma - totalpagosalafecha - saldoanterior

                        # totalsaldovencer += saldovencer

                        totalsaldovencer += saldovencer2


                        hojadestino.write(fila, 0, matricula.inscripcion.carrera.nombre, fuentenormal)
                        hojadestino.write(fila, 1, matricula.inscripcion.carrera.alias, fuentenormalcent)
                        hojadestino.write(fila, 2, matricula.nivel.periodo.cohorte, fuentenormalcent)
                        hojadestino.write(fila, 3, matricula.nivel.periodo.inicio, fuentefecha)
                        hojadestino.write(fila, 4, matricula.nivel.periodo.fin, fuentefecha)
                        hojadestino.write(fila, 5, matricula.inscripcion.persona.nombre_completo_inverso(),
                                          fuentenormal)
                        hojadestino.write(fila, 6, matricula.inscripcion.persona.identificacion(), fuentenormal)
                        hojadestino.write(fila, 7, valortotalprograma, fuentemoneda)
                        # hojadestino.write(fila, 8, totalpagosanterior, fuentemoneda)
                        hojadestino.write(fila, 8, totalpagosalafecha, fuentemoneda)
                        hojadestino.write(fila, 9, saldoanterior, fuentemoneda)
                        # hojadestino.write(fila, 10, saldovencer, fuentemoneda)
                        hojadestino.write(fila, 10, saldovencer2, fuentemoneda)

                        # ===== SALDOS 1-30, 31-60, 61-90, + 90 DIAS
                        fechainiciocartera = finmes + relativedelta(days=1)
                        # ultimodia = str(fechainiciocartera.year, fechainiciocartera.month[1])

                        ultimodia = str(calendar.monthrange(fechainiciocartera.year, fechainiciocartera.month)[1])

                        fechafincartera = datetime.strptime(
                            str(fechainiciocartera.year) + '-' + str(fechainiciocartera.month) + '-' + ultimodia,
                            '%Y-%m-%d').date()

                        columna = 11

                        saldoanteriorcartera = 0
                        valoredad1 = 0
                        valoredad2 = 0
                        valoredad3 = 0
                        valoredad4 = 0

                        if saldovencer != 0:

                            for n in range(1, 4):

                                # totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                #                                                                         fechavence__gte=fechainiciocartera,
                                #                                                                         fechavence__lte=fechafincartera
                                #                                                                         ).aggregate(
                                #     valor=Sum('valortotal'))[
                                #                                                  'valor'], 2)).quantize(Decimal('.01'))
                                #
                                # print("Total rubros anterior:", totalrubrosanterior)

                                rubros = matricula.rubro_set.filter(status=True, tipo__subtiporubro=1, fechavence__gte=fechainiciocartera, fechavence__lte=fechafincartera)

                                # pagos_rubros_posteriores = Pago.objects.filter(
                                #     fecha__gte=fechainiciocartera,
                                #     fecha__lte=fechafincartera,
                                #     pagoliquidacion__isnull=True,
                                #     status=True,
                                #     rubro__matricula=matricula,
                                #     rubro__status=True,
                                #     rubro__fechavence__gt=finmes
                                # ).exclude(factura__valida=False)

                                total_rubros_mes_cobrar = 0
                                # if rubros or pagos_rubros_posteriores:
                                if rubros:
                                    for rubro in rubros:
                                        matricula = rubro.matricula
                                        # Preguntar si rubro fue pagado en meses anteriores

                                        pagos = Pago.objects.filter(
                                            fecha__lt=fechainiciocartera,
                                            pagoliquidacion__isnull=True,
                                            status=True,
                                            rubro__status=True,
                                            rubro__fechavence__gte=fechainiciocartera,
                                            rubro__fechavence__lte=fechafincartera,
                                            rubro=rubro)

                                        for pago in pagos:
                                            print(pago.fecha, pago.rubro, pago.valortotal)


                                        totalpagadorubro = Decimal(null_to_decimal(Pago.objects.filter(
                                            fecha__lt=fechainiciocartera,
                                            pagoliquidacion__isnull=True,
                                            status=True,
                                            rubro__status=True,
                                            rubro__fechavence__gte=fechainiciocartera,
                                            rubro__fechavence__lte=fechafincartera,
                                            rubro=rubro
                                        ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'],
                                                                                   2)).quantize(
                                            Decimal('.01'))
                                        # totalpagadorubro = 0
                                        valor_neto_rubro = rubro.valortotal - totalpagadorubro
                                        total_rubros_mes_cobrar += valor_neto_rubro

                                    # for pago in pagos_rubros_posteriores:
                                    #     total_rubros_mes_cobrar += pago.valortotal

                                saldoanteriorcartera = total_rubros_mes_cobrar

                                print("Saldo anterior 1-30 días:", saldoanteriorcartera)

                                hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)

                                if n == 1:
                                    totaledad1 += saldoanteriorcartera
                                    valoredad1 = saldoanteriorcartera
                                elif n == 2:
                                    totaledad2 += saldoanteriorcartera
                                    valoredad2 = saldoanteriorcartera
                                else:
                                    totaledad3 += saldoanteriorcartera
                                    valoredad3 = saldoanteriorcartera

                                columna += 1

                                fechainiciocartera = fechafincartera + relativedelta(days=1)
                                # ultimodia = str(fechainiciocartera.year, fechainiciocartera.month[1])

                                ultimodia = str(
                                    calendar.monthrange(fechainiciocartera.year, fechainiciocartera.month)[1])

                                fechafincartera = datetime.strptime(str(fechainiciocartera.year) + '-' + str(
                                    fechainiciocartera.month) + '-' + ultimodia, '%Y-%m-%d').date()

                                # fechafincartera = fechainiciocartera - relativedelta(days=1)
                                # fechainiciocartera = datetime.strptime(str(fechafincartera.year) + '-' + str(fechafincartera.month) + '-' + primerdia, '%Y-%m-%d').date()
                        else:
                            hojadestino.write(fila, columna, 0, fuentemoneda)
                            hojadestino.write(fila, columna + 1, 0, fuentemoneda)
                            hojadestino.write(fila, columna + 2, 0, fuentemoneda)
                            hojadestino.write(fila, columna + 3, 0, fuentemoneda)

                        # fechainiciocartera = fechafincartera + relativedelta(days=1)

                        if saldovencer != 0:
                            fechainiciocartera = fechafincartera + relativedelta(days=1)

                            print("Fecha inicio de cartera:", fechainiciocartera)
                            totalrubroscartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                                                                                                    fechavence__gte=fechainiciocartera
                                                                                                    ).aggregate(
                                valor=Sum('valortotal'))[
                                                                             'valor'], 2)).quantize(Decimal('.01'))
                            print("Total rubros anterior:", totalrubroscartera)

                            # totalliquidadocartera = Decimal(null_to_decimal(matricula.rubro_set.filter(status=True,
                            #                                                                     fechavence__lt=fechainiciocartera,
                            #                                                                     pago__pagoliquidacion__isnull=False
                            #                                                                     ).aggregate(valor=Sum('valortotal'))[
                            #                                              'valor'], 2)).quantize(Decimal('.01'))
                            #
                            # print("Total Liquidado ", totalliquidadocartera)
                            #
                            # totalanuladocartera = Decimal(null_to_decimal(Pago.objects.filter(
                            #     status=True,
                            #     rubro__matricula=matricula,
                            #     rubro__status=True,
                            #     rubro__fechavence__lt=fechainiciocartera,
                            #     factura__valida=False,
                            #     factura__status=True
                            # ).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                            #
                            # print("total anulado: ", totalanuladocartera)
                            #
                            # # PAGADO ANTERIOR ---- REVISAR BIEN ESTA TOMANDO PAGO DE RUBROS DE JULIO, AGOSTO
                            # totalpagoscartera = Decimal(null_to_decimal(Pago.objects.filter(
                            #     fecha__lt=iniciomes,
                            #     pagoliquidacion__isnull=True,
                            #     status=True,
                            #     rubro__matricula=matricula,
                            #     rubro__status=True,
                            #     rubro__fechavence__lt=fechainiciocartera
                            # ).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))
                            # print("Total Pagado anterior: ", totalpagoscartera)
                            # saldoanteriorcartera = totalrubroscartera - (totalpagoscartera + totalliquidadocartera + totalanuladocartera)
                            saldoanteriorcartera = saldovencer - (valoredad1 + valoredad2 + valoredad3)
                            saldoanteriorcartera = saldovencer2 - (valoredad1 + valoredad2 + valoredad3)

                            # saldovencer = valortotalprograma - totalpagosanterior - saldoanterior
                            print("Saldo anterior mayor a 90 días:", saldoanteriorcartera)
                            hojadestino.write(fila, columna, saldoanteriorcartera, fuentemoneda)
                            # hojadestino.write(fila, columna + 1, saldovencer, fuentemoneda)

                            totaledad4 += saldoanteriorcartera
                            # totalsaldovencer += saldovencer

                        fila += 1

                hojadestino.write_merge(fila, fila, 0, 6, "TOTAL GENERAL", fuentenormalnegrell)
                hojadestino.write(fila, 7, totalprograma, fuentemonedaneg)
                hojadestino.write(fila, 8, totalcobrado, fuentemonedaneg)
                hojadestino.write(fila, 9, totalsaldovencido, fuentemonedaneg)
                hojadestino.write(fila, 10, totalsaldovencer, fuentemonedaneg)
                hojadestino.write(fila, 11, totaledad1, fuentemonedaneg)
                hojadestino.write(fila, 12, totaledad2, fuentemonedaneg)
                hojadestino.write(fila, 13, totaledad3, fuentemonedaneg)
                hojadestino.write(fila, 14, totaledad4, fuentemonedaneg)
                # hojadestino.write(fila, 14, totalsaldovencer, fuentemonedaneg)

                fila += 1

                if totalsaldovencer > 0:
                    hojadestino.write(fila, 10, 1, fuenteporcentajeneg)
                    hojadestino.write(fila, 11, totaledad1 / totalsaldovencer, fuenteporcentajeneg)
                    hojadestino.write(fila, 12, totaledad2 / totalsaldovencer, fuenteporcentajeneg)
                    hojadestino.write(fila, 13, totaledad3 / totalsaldovencer, fuenteporcentajeneg)
                    hojadestino.write(fila, 14, totaledad4 / totalsaldovencer, fuenteporcentajeneg)

                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})

                # return JsonResponse({'result': 'ok', 'archivo': filename})
            except Exception as ex:
                print("error")
                pass

        elif action == 'reporte_indice_cartera':
            try:
                meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                         "Octubre", "Noviembre", "Diciembre"]

                anio = request.POST['anio']
                mes = request.POST['mes']


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
                fuentenormalwrapneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; alignment: vert distributed;borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalneg = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalnegrell = easyxf(
                    'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                fuentenormalwrap.alignment.wrap = True
                fuentenormalwrap.font.bold = True

                fuentenormalcent = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right, vert centre',
                    num_format_str=' "$" #,##0.00')
                fuentemonedaneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                fuenteporcentaje = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right, vert centre',
                    num_format_str='0.00%')
                fuenteporcentajeneg = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                    num_format_str='0.00%')
                fuentenormalrelleno = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')


                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False

                output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                libdestino = xlwt.Workbook()
                hojadestino = libdestino.add_sheet("Reporte")

                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=presupuesto_anual_' + random.randint(1, 10000).__str__() + '.xls'
                nombre = "R7_INDICE_CARTERA_VENCIDA_" + anio + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                filename = os.path.join(output_folder, nombre)
                ruta = "media/postgrado/" + nombre

                hojadestino.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                hojadestino.write_merge(1, 1, 0, 15, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', titulo2)
                hojadestino.write_merge(2, 2, 0, 15, 'ÍNDICE DE CARTERA VENCIDA DEL ' + anio, titulo2)

                fila = 4
                # fechafinant = str(fechafinmesanterior.day) + "-" + meses[fechafinmesanterior.month - 1][:3].upper() + "-" + str(fechafinmesanterior.year)
                # fechafinact = str(finmes.day) + "-" + meses[finmes.month - 1][:3].upper() + "-" + str(finmes.year)

                columnas = [
                    (u"", 5000),
                    (u"ENERO", 3200),
                    (u"FEBRERO", 3200),
                    (u"MARZO", 3200),
                    (u"ABRIL", 3200),
                    (u"MAYO", 3200),
                    (u"JUNIO", 3200),
                    (u"JULIO", 3200),
                    (u"AGOSTO", 3200),
                    (u"SEPTIEMBRE", 3200),
                    (u"OCTUBRE", 3200),
                    (u"NOVIEMBRE", 3200),
                    (u"DICIEMBRE", 3200),
                    (u"PROMEDIOS", 3400),
                    (u"TOTAL VENCIMIENTOS PERIODO", 3400),
                    (u"CARTERA AL COBRO PERIODO", 3400)
                ]

                for col_num in range(len(columnas)):
                    hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                    hojadestino.col(col_num).width = columnas[col_num][1]


                hojadestino.write(5, 0, "Saldo vencido inicial del periodo", fuentenormalwrapneg)
                hojadestino.write(6, 0, "Vencimientos del periodo", fuentenormalwrapneg)
                hojadestino.write(7, 0, "Cartera al cobro en el periodo", fuentenormalwrapneg)
                hojadestino.write(8, 0, "Cobros del periodo", fuentenormalwrapneg)
                hojadestino.write(9, 0, "Saldo vencido final del periodo", fuentenormalwrapneg)
                hojadestino.write(10, 0, "% de Recuperación de la cartera al cobro", fuentenormalwrapneg)
                hojadestino.write(11, 0, "Proyección de la cartera vencida (días)", fuentenormalwrapneg)

                for f in range(5, 12):
                    hojadestino.row(f).height_mismatch = True
                    hojadestino.row(f).height = 500


                col = 1
                anio_actual = anio
                total_vencimientos_anio = 0
                total_cobros_anio = 0

                for nmes in range(1, int(mes)+1):

                    mes_actual = str(nmes)
                    ultimodia = str(calendar.monthrange(int(anio_actual), int(mes_actual))[1])
                    primerdia = "1"

                    # Fecha inicio de mes
                    iniciomes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + primerdia, '%Y-%m-%d').date()
                    # Fecha fin de mes
                    finmes = datetime.strptime(anio_actual + '-' + mes_actual + '-' + ultimodia, '%Y-%m-%d').date()
                    # Fecha fin de mes anterior
                    fechafinmesanterior = iniciomes - relativedelta(days=1)

                    # Rubros de meses anteriores
                    totalrubrosanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                                       # matricula__inscripcion__persona__cedula__in=cedulas,
                                                                                       tipo__subtiporubro=1,
                                                                                       fechavence__lt=iniciomes,
                                                                                       matricula__nivel__periodo__tipo__id__in=[
                                                                                           3, 4]
                                                                                       # matricula__inscripcion__carrera__id=carrera,
                                                                                       # matricula__nivel__periodo__id__in=periodos
                                                                                       ).exclude(matricula__nivel__periodo__pk__in=[120, 128]).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    # Liquidado de meses anteriores
                    totalliquidadoanterior = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                                          # matricula__inscripcion__persona__cedula__in=cedulas,
                                                                                          tipo__subtiporubro=1,
                                                                                          fechavence__lt=iniciomes,
                                                                                          matricula__nivel__periodo__tipo__id__in=[
                                                                                              3,
                                                                                              4],
                                                                                          # matricula__inscripcion__carrera__id=carrera,
                                                                                          # matricula__nivel__periodo__id__in=periodos,
                                                                                          pago__pagoliquidacion__isnull=False
                                                                                          ).exclude(matricula__nivel__periodo__pk__in=[120, 128]).aggregate(
                        valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                    # Anulado meses anteriores
                    totalanuladoanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        status=True,
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__lte=finmes,
                        # rubro__fechavence__lt=iniciomes,
                        factura__valida=False,
                        factura__status=True
                    ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(Decimal('.01'))

                    # Pagos de meses anteriores
                    totalpagosanterior = Decimal(null_to_decimal(Pago.objects.filter(
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True
                        # rubro__fechavence__lt=iniciomes
                        # rubro__fechavence__lte=finmes # este es
                    ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    print("Total pagos anterior: ", totalpagosanterior)
                    # Hacer ajustes para calcular bien saldo anterior :D
                    # Pagos del mes que corresponden a rubros de meses posteriores
                    totalvencimientosposterior = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gte=iniciomes
                    ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    # ========================================

                    # Vencimientos del mes: rubros del mes estén pagados o no
                    totalvencimientos = Decimal(null_to_decimal(Rubro.objects.filter(status=True,
                                                                                     tipo__subtiporubro=1,
                                                                                     # matricula__inscripcion__persona__cedula__in=cedulas,
                                                                                     matricula__nivel__periodo__tipo__id__in=[
                                                                                         3, 4],
                                                                                     # matricula__inscripcion__carrera__id=carrera,
                                                                                     # matricula__nivel__periodo__id__in=periodos,
                                                                                     fechavence__gte=iniciomes,
                                                                                     fechavence__lte=finmes).exclude(matricula__nivel__periodo__pk__in=[120, 128]).aggregate(
                        valor=Sum('valortotal'))[
                                                                    'valor'], 2)).quantize(Decimal('.01'))
                    # Rubros del mes y que han sido pagados en meses anteriores
                    totalvencimientos2 = 0
                    totalvencimientos2 = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__lt=iniciomes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gte=iniciomes,
                        rubro__fechavence__lte=finmes
                    ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    # Pagos del mes que corresponden a rubros de meses posteriores
                    totalvencimientos3 = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__gte=iniciomes,
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True,
                        rubro__fechavence__gt=finmes
                    ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    totalvencimientos = (totalvencimientos - totalvencimientos2) + totalvencimientos3

                    # Cobros del mes
                    totalcobros = Decimal(null_to_decimal(Pago.objects.filter(
                        # rubro__matricula__inscripcion__persona__cedula__in=cedulas,
                        fecha__gte=iniciomes,
                        fecha__lte=finmes,
                        pagoliquidacion__isnull=True,
                        status=True,
                        rubro__tipo__subtiporubro=1,
                        rubro__matricula__nivel__periodo__tipo__id__in=[3, 4],
                        # rubro__matricula__inscripcion__carrera__id=carrera,
                        # rubro__matricula__nivel__periodo__id__in=periodos,
                        rubro__status=True
                        # rubro__fechavence__lte=finmes
                    ).exclude(rubro__matricula__nivel__periodo__pk__in=[120, 128]).exclude(factura__valida=False).aggregate(pagos=Sum('valortotal'))['pagos'], 2)).quantize(
                        Decimal('.01'))

                    saldoanterior = totalrubrosanterior - (
                                totalpagosanterior + totalliquidadoanterior + totalanuladoanterior)

                    saldoanterior += totalvencimientosposterior

                    carteracobroperiodo = saldoanterior + totalvencimientos
                    saldovencidofinalperiodo = carteracobroperiodo - totalcobros

                    total_vencimientos_anio += totalvencimientos
                    total_cobros_anio += totalcobros

                    if nmes == 1:
                        saldo_inicial_anio = saldoanterior

                    ultimo_total_cobros = totalcobros

                    print("Saldo vencido inicio periodo: ", saldoanterior)
                    print("Vencimientos del periodo: ", totalvencimientos)
                    print("Cartera al cobro en el periodo: ", carteracobroperiodo)
                    print("Cobros del periodo: ", totalcobros)
                    print("Saldo final de periodo: ", saldovencidofinalperiodo)

                    hojadestino.write(5, col, saldoanterior, fuentemoneda)
                    hojadestino.write(6, col, totalvencimientos, fuentemoneda)
                    hojadestino.write(7, col, carteracobroperiodo, fuentemoneda)
                    hojadestino.write(8, col, totalcobros, fuentemoneda)
                    hojadestino.write(9, col, saldovencidofinalperiodo, fuentemoneda)
                    hojadestino.write(10, col, totalcobros / carteracobroperiodo, fuenteporcentaje)
                    hojadestino.write(11, col, null_to_decimal(saldovencidofinalperiodo / totalcobros * 30, 0), fuentenumeroentero)


                    # hojadestino.write(5, col, finmes, fuentefecha)



                    col += 1

                # diferencia_meses = 12 - int(mes)
                # print(diferencia_meses)

                for n in range(int(mes), 12):
                    hojadestino.write(5, col, "", fuentenormalrelleno)
                    hojadestino.write(6, col, "", fuentenormalrelleno)
                    hojadestino.write(7, col, "", fuentenormalrelleno)
                    hojadestino.write(8, col, "", fuentenormalrelleno)
                    hojadestino.write(9, col, "", fuentenormalrelleno)
                    hojadestino.write(10, col, "", fuentenormalrelleno)
                    hojadestino.write(11, col, "", fuentenormalrelleno)

                    col += 1

                cartera_cobro_periodo = total_vencimientos_anio + saldo_inicial_anio
                promedio_vencimientos = total_vencimientos_anio / int(mes)
                promedio_cobros = total_cobros_anio / int(mes)
                cartera_vencida_periodo = cartera_cobro_periodo - total_cobros_anio

                hojadestino.write(5, 13, "", fuentenormalrelleno)
                hojadestino.write(5, 14, "", fuentenormalrelleno)
                hojadestino.write(5, 15, "", fuentenormalrelleno)

                hojadestino.write(6, 13, promedio_vencimientos, fuentemoneda)
                hojadestino.write(6, 14, total_vencimientos_anio, fuentemoneda)
                hojadestino.write(6, 15, cartera_cobro_periodo, fuentemoneda)

                hojadestino.write(7, 13, "", fuentenormalrelleno)
                hojadestino.write(7, 14, "TOTAL COBROS PERIODO", fuentecabecera)
                hojadestino.write(7, 15, "CARTERA VENCIDA PERIODO", fuentecabecera)

                hojadestino.write(8, 13, promedio_cobros, fuentemoneda)
                hojadestino.write(8, 14, total_cobros_anio, fuentemoneda)
                hojadestino.write(8, 15, cartera_vencida_periodo, fuentemoneda)



                libdestino.save(filename)
                return JsonResponse({'result': 'ok', 'archivo': ruta})
            except Exception as ex:
                print("error")
                pass

        elif action == 'pdfcontratoconsultadeuda':
            try:
                numcontrato = 0
                idins = request.POST['idins']
                registro = Contrato.objects.filter(status=True, inscripcion__id=idins, inscripcion__status=True).last()
                secuenciacp = secuencia_contratopagare(request, datetime.now().year)
                if not registro or not registro.numerocontrato:
                    secuenciacp.secuenciacontrato += 1
                    secuenciacp.save(request)
                    if Contrato.objects.filter(status=True, numerocontrato=secuenciacp.secuenciacontrato).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error al generar el contrato, intente nuevamente"})
                    else:
                        if Contrato.objects.filter(status=True,inscripcion_id=idins).exists():
                            ct = Contrato.objects.filter(inscripcion_id=idins, status=True,).last()
                            ct.numerocontrato = secuenciacp.secuenciacontrato
                            ct.save(request)
                            log(u'Editó número contrato: %s' % (ct), request, "add")
                        else:
                            ct = Contrato(inscripcion_id=idins, numerocontrato=secuenciacp.secuenciacontrato)
                            ct.save(request)
                            log(u'Adicionó numero contrato: %s' % (ct), request, "add")
                        numcontrato = ct.numerocontrato
                else:
                    if Contrato.objects.get(status=True, inscripcion__id=idins, inscripcion__status=True).numerocontrato:
                        numcontrato = Contrato.objects.get(status=True, inscripcion__id=idins, inscripcion__status=True).numerocontrato
                qrresult = contratoconsultadeuda(request.POST['idins'], request.POST['idmat'], numcontrato)
                return JsonResponse({"result": "ok", 'url': qrresult})
            except Exception as ex:
                transaction.set_rollback(True)
                import sys
                print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                print(f'${ex.__str__()}')
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Consulta de alumnos (Consulta de Cartera vencida)'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']
            # action = request.GET['action']

            if action == 'listarubrosmatriculas':
                try:
                    matricularubro = Matricula.objects.select_related().get(pk=request.GET['idmatricula'])
                    numrubros = Rubro.objects.values_list('id', flat=True).filter(matricula=matricularubro, status=True)
                    rubrosnegados = Pago.objects.values_list('rubro_id', flat=True).filter(rubro__in=numrubros, factura__valida=False)
                    listarubros1 = Rubro.objects.filter(persona=matricularubro.inscripcion.persona, matricula__isnull=True, status=True).order_by('id')
                    listarubros2 = Rubro.objects.filter(persona=matricularubro.inscripcion.persona, matricula=matricularubro, status=True).exclude(pk__in=rubrosnegados).order_by('id')
                    listarubros = listarubros1 | listarubros2
                    lista = []
                    nombrespersona = matricularubro.inscripcion.persona.apellido1 + ' ' + matricularubro.inscripcion.persona.apellido2 + ' ' + matricularubro.inscripcion.persona.nombres
                    for rubros in listarubros:
                        datadoc = {}
                        datadoc['idrub'] = rubros.id
                        if rubros.matricula_id:
                            datadoc['matri'] = rubros.matricula_id
                        else:
                            datadoc['matri'] = 0

                        datadoc['epunemi'] = 'S' if rubros.epunemi else 'N'
                        datadoc['tipo'] = rubros.tipo.nombre
                        datadoc['rubro'] = rubros.nombre
                        datadoc['valorrubro'] = rubros.valortotal
                        datadoc['per'] = matricularubro.inscripcion.persona.id
                        datadoc['emite'] = str(rubros.fecha)
                        datadoc['vence'] = str(rubros.fechavence)
                        cancela = '<span class="label label-important">NO</span>'
                        if rubros.cancelado:
                            cancela = '<span class="label label-success">SI</span>'
                        datadoc['cancelado'] = cancela
                        lista.append(datadoc)

                    # Si existen rubros bloqueados no se debe mostrar boton guardar
                    if Rubro.objects.values("id").filter(status=True, matricula=matricularubro, bloqueado=True).exists():
                        puedegrabar = 'NO'
                    else:
                        puedegrabar = 'SI'

                    return JsonResponse({'result': 'ok', 'lista': lista, 'nombrespersona': nombrespersona, 'puedegrabar': puedegrabar})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reportebecas':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_postulantes' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"PROGRAMA", 10000),
                        (u"COHORTE", 10000),
                        (u"TIPO", 10000),
                        (u"NOMBRE DEL MAESTRANTE", 10000),
                        (u"COSTO DEL PROGRAMA", 6000),
                        (u"PORCENTAJE DE DESCUENTO APLICADO", 10000),
                        (u"VALOR DESCONTADO", 6000),
                        (u"COSTO FINAL DEL PROGRAMA", 4000),
                    ]


                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    peri = Periodo.objects.get(pk=request.GET['peri'])
                    listado = MatriculaNovedad.objects.filter(matricula__nivel__periodo=peri, matricula__inscripcion__carrera_id=request.GET['carr'], tipo=1).order_by('matricula__inscripcion__persona__apellido1','matricula__inscripcion__persona__apellido2')
                    unalumno = Matricula.objects.filter(nivel__periodo=peri, inscripcion__carrera_id=request.GET['carr'], matriculanovedad__isnull=True)[0]
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        campo1 = lista.matricula.inscripcion.carrera.nombre
                        if lista.tipodescuento:
                            campo2 = lista.tipodescuento.nombre
                        else:
                            campo2 = ''
                        campo4 = lista.matricula.inscripcion.persona.apellido1 + ' ' + lista.matricula.inscripcion.persona.apellido2 + ' ' + lista.matricula.inscripcion.persona.nombres
                        campo5 = unalumno.total_rubrossinanular()
                        campo6 = lista.porcentajedescuento
                        campo8 = lista.matricula.total_rubrossinanular()
                        campo7 = null_to_decimal((campo5 * campo6)/100, 2)

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, peri.nombre, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporteretirados':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_postulantes' + random.randint(1, 10000).__str__() + '.xls'
                    row_num = 0
                    columns = [
                        (u"PROGRAMA", 10000),
                        (u"COHORTE", 10000),
                        (u"NOMBRE DEL MAESTRANTE", 10000),
                        (u"MODULOS CURSADOS", 7000),
                        (u"TOTAL DE MODULOS DEL PROGRAMA", 7000),
                        (u"COSTO DEL PROGRAMA", 7000),
                        (u"COSTO DEL MODULO", 7000),
                        (u"VALOR POR PAGAR MODULOS RECIBIDOS", 7000),
                        (u"VALOR PAGADO", 7000),
                        (u"SALDO POR PAGAR", 7000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    peri = Periodo.objects.get(pk=request.GET['peri'])
                    listado = Matricula.objects.filter(nivel__periodo=peri, inscripcion__carrera_id=request.GET['carr'], retiradomatricula=True).order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                    # unalumno = Matricula.objects.filter(nivel__periodo=peri, inscripcion__carrera_id=request.GET['carr'], matriculanovedad__isnull=True)[0]

                    # totalasignaturasmalla = AsignaturaMalla.objects.filter(malla__carrera_id=request.GET['carr'],status=True).count()
                    row_num = 0
                    for lista in listado:
                        row_num += 1
                        inscripcionmalla = lista.inscripcion.inscripcionmalla_set.filter(status=True)[0]
                        totalasignaturasmalla = inscripcionmalla.malla.asignaturamalla_set.filter(status=True, opcional=False).count()

                        campo1 = lista.inscripcion.carrera.nombre
                        campo2 = lista.inscripcion.persona.apellido1 + ' ' + lista.inscripcion.persona.apellido2 + ' ' + lista.inscripcion.persona.nombres
                        campo3 = lista.inscripcion.recordacademico_set.filter(status=True).count()
                        campo4 = totalasignaturasmalla
                        campo5 = lista.total_rubrossinanular()
                        campo6 = null_to_decimal(campo5 / campo4, 2)
                        campo7 = campo6 * campo3
                        campo8 = lista.total_pagado_rubrosinanular()
                        campo9 = campo7 - campo8
                        if campo8 >= campo5:
                            campo9 = 0

                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, peri.nombre, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, font_style2)
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_beca_general':
                try:

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')

                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
                    fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_becados_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 7, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', title2)
                    ws.write_merge(2, 2, 0, 7, 'LISTADO GENERAL DE MAESTRANTES BECADOS', title2)

                    row_num = 4
                    columns = [
                        (u"PERIODO", 10000),
                        (u"PROGRAMAS EN EJECUCIÓN", 10000),
                        (u"TIPO DESCUENTO", 6000),
                        (u"NOMBRE DEL MAESTRANTE", 10000),
                        (u"COSTO DEL PROGRAMA", 6000),
                        (u"PORCENTAJE DE DESCUENTO APLICADO", 6000),
                        (u"VALOR DESCONTADO", 6000),
                        (u"COSTO FINAL DEL PROGRAMA", 6000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    lista_periodos_b1 = Periodo.objects.filter(nivel__matricula__matriculanovedad__tipo=1, nivel__matricula__matriculanovedad__status=True).distinct()
                    lista_periodos_b2 = Periodo.objects.filter(nivel__matricula__descuentoposgradomatricula__status=True, nivel__matricula__descuentoposgradomatricula__estado=2).distinct()

                    lista_periodos_b = lista_periodos_b1|lista_periodos_b2
                    lista_periodos_b = lista_periodos_b.order_by('inicio', 'fin')

                    row_num = 4

                    for pb in lista_periodos_b:
                        lista_carreras_b1 = Carrera.objects.filter(inscripcion__matricula__matriculanovedad__tipo=1, inscripcion__matricula__matriculanovedad__status=True, inscripcion__matricula__nivel__periodo=pb).distinct()
                        lista_carreras_b2 = Carrera.objects.filter(inscripcion__matricula__nivel__periodo=pb, inscripcion__matricula__descuentoposgradomatricula__status=True, inscripcion__matricula__descuentoposgradomatricula__estado=2).distinct()

                        lista_carreras_b = lista_carreras_b1 | lista_carreras_b2
                        lista_carreras_b = lista_carreras_b.order_by('nombre')


                        for cb in lista_carreras_b:
                            listado = MatriculaNovedad.objects.filter(matricula__nivel__periodo=pb, matricula__inscripcion__carrera=cb, tipo=1).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres')

                            for lista in listado:
                                row_num += 1
                                programa = lista.matricula.inscripcion.carrera.nombre
                                tipodescuento = lista.tipodescuento.nombre.upper() if lista.tipodescuento else ''
                                alumno = lista.matricula.inscripcion.persona.apellido1 + ' ' + lista.matricula.inscripcion.persona.apellido2 + ' ' + lista.matricula.inscripcion.persona.nombres
                                costoprograma = lista.matricula.costo_programa()
                                porcentaje = Decimal(null_to_decimal(lista.porcentajedescuento,2))
                                valorrubros = lista.matricula.total_generado_alumno()

                                if porcentaje > 0:
                                    valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(Decimal('.01'))
                                    valorrubros = costoprograma - valordescontado
                                else:
                                    valordescontado = Decimal(0)
                                    porcentaje = round((valorrubros * 100) / costoprograma,2)
                                    porcentaje = 100 - porcentaje
                                    valordescontado = round((costoprograma * porcentaje)/100,2)
                                    valorrubros = costoprograma - valordescontado

                                ws.write(row_num, 0, pb.nombre, fuentenormal)
                                ws.write(row_num, 1, programa, fuentenormal)
                                ws.write(row_num, 2, tipodescuento, fuentenormal)
                                ws.write(row_num, 3, alumno, fuentenormal)
                                ws.write(row_num, 4, costoprograma, fuentemoneda)
                                ws.write(row_num, 5, porcentaje, fuentenumero)
                                ws.write(row_num, 6, valordescontado, fuentemoneda)
                                ws.write(row_num, 7, valorrubros, fuentemoneda)

                            # descuentos por lo del covid
                            for cb in DescuentoPosgradoMatricula.objects.filter(status=True, estado=2, matricula__nivel__periodo=pb, matricula__inscripcion__carrera=cb).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2', 'matricula__inscripcion__persona__nombres'):
                                row_num += 1
                                programa = cb.matricula.inscripcion.carrera.nombre
                                tipodescuento = cb.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.descripcion
                                alumno = cb.matricula.inscripcion.persona.apellido1 + ' ' + cb.matricula.inscripcion.persona.apellido2 + ' ' + cb.matricula.inscripcion.persona.nombres
                                costoprograma = cb.matricula.costo_programa()
                                porcentaje = Decimal(null_to_decimal(cb.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.porcentaje, 2))
                                valorrubros = cb.matricula.total_generado_alumno()

                                if porcentaje > 0:
                                    # valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(Decimal('.01'))
                                    valordescontado = cb.valordescuento
                                    valorrubros = costoprograma - valordescontado
                                else:
                                    valordescontado = Decimal(0)
                                    porcentaje = round((valorrubros * 100) / costoprograma, 2)
                                    # porcentaje = 100 - porcentaje
                                    # valordescontado = round((costoprograma * porcentaje) / 100, 2)
                                    valorrubros = costoprograma - valordescontado

                                ws.write(row_num, 0, pb.nombre, fuentenormal)
                                ws.write(row_num, 1, programa, fuentenormal)
                                ws.write(row_num, 2, tipodescuento, fuentenormal)
                                ws.write(row_num, 3, alumno, fuentenormal)
                                ws.write(row_num, 4, costoprograma, fuentemoneda)
                                ws.write(row_num, 5, porcentaje, fuentenumero)
                                ws.write(row_num, 6, valordescontado, fuentemoneda)
                                ws.write(row_num, 7, valorrubros, fuentemoneda)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'carteravencida':
                try:
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
                    title2 = easyxf(
                        'font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalneg = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    fuentenormalnegpie = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                    fuentenormalnegpieder = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25')
                    fuentenormalder = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
                    fuentemonedaneg = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')

                    fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cartera_vencida_' + random.randint(1,10000).__str__() + '.xls'

                    carreraid = int(request.GET['carr'])
                    periodoid = int(request.GET['peri'])
                    fechacorte = datetime.now().date()

                    carrera = Carrera.objects.get(pk=carreraid)
                    periodo = Periodo.objects.get(pk=periodoid)

                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                    ws.write_merge(2, 2, 0, 8, 'CARTERA VENCIDA', title)
                    ws.write_merge(3, 3, 0, 8, carrera.nombre + " - " + periodo.nombre, title2)
                    ws.write_merge(4, 4, 0, 8, "PERIODO INICIO - FIN: " + str(periodo.inicio) + " - " + str(periodo.fin), title2)
                    ws.write_merge(5, 5, 0, 8, "ESTADO DE MAESTRÍA - (" + ("EN EJECUCIÓN" if datetime.now().date() <= periodo.fin else "FINALIZADO") + ")", title2)
                    ws.write_merge(6, 6, 0, 8, "FECHA DEL REPORTE (" +  str(fechacorte)+ ")" , title2)

                    row_num = 8

                    columns = [
                        (u"N°", 1000),
                        (u"PROVINCIA", 4000),
                        (u"CANTÓN", 4000),
                        (u"CÉDULA", 4000),
                        (u"ESTUDIANTE", 10000),
                        (u"N° CUOTAS VENCIDAS", 4000),
                        (u"FECHA 1RA CUOTA VENCIDA", 4000),
                        (u"FECHA ÚLTIMA CUOTA VENCIDA", 4000),
                        (u"DÍAS VENCIMIENTO", 4000),
                        (u"TOTAL PAGADO", 4000),
                        (u"VALOR VENCIDO", 4000),
                        (u"VALOR PENDIENTE", 4000),
                        (u"CATEGORÍA", 4000),
                        (u"RANGO DÍAS", 4000),
                        (u"ESTADO ESTUDIANTE", 4000),
                        (u"FECHA ÚLTIMA CUOTA", 4000),
                        (u"ESTADO FINANCIAMIENTO", 4000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    resumen = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                               1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                               2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                               3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                               4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                               5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                               }

                    secuencia = 0
                    totalvencido = 0
                    totalpendiente = 0
                    totalpagado = 0

                    matriculas = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')#[:2500]
                    for lista in matriculas:
                        row_num += 1
                        secuencia += 1

                        alumno = lista.inscripcion.persona.nombre_completo_inverso()
                        personaalumno = lista.inscripcion.persona
                        rubrosalumno = lista.rubros_maestria()
                        ultimafechavence = ""

                        if personaalumno.cedula == '0502179798':
                            print("here!")

                        if not lista.retirado_programa_maestria():
                            # pagosvencidos = lista.numero_cuotas_vencidas()
                            # valorvencido = Decimal(lista.vencido_a_la_fechamatricula_rubro_maestria()).quantize(Decimal('.01'))

                            rubrosvencidos = lista.rubros_maestria_vencidos(fechacorte)
                            pagosvencidos = len(rubrosvencidos)
                            valorvencido = 0
                            for r in rubrosvencidos:
                                valorvencido += r[2]

                            valorpendiente = Decimal(lista.total_saldo_rubrosinanular_rubro_maestria()).quantize(Decimal('.01'))
                        else:
                            valorvencido = Decimal(lista.total_saldo_alumno_retirado()).quantize(Decimal('.01'))
                            valorpendiente = valorvencido
                            pagosvencidos = 1 if valorvencido > 0 else 0

                        valorpagado = lista.total_pagado_alumno_rubro_maestria()

                        fechavence1 = fechavencerec = ""
                        diasvencidos = 0

                        if valorvencido > 0 and rubrosalumno:
                            # rubrosvencidos = lista.rubros_vencidos()
                            rubrosvencidos = lista.rubros_maestria_vencidos(fechacorte)

                            if rubrosvencidos:
                                # fechavence1 = rubrosvencidos.first().fechavence
                                fechavence1 = rubrosvencidos[0][1]

                                if not lista.retirado_programa_maestria():
                                    # fechavencerec = rubrosvencidos.last().fechavence
                                    fechavencerec = rubrosvencidos[-1][1]
                                else:
                                    fechavencerec = fechavence1
                            else:
                                rubrospagados = lista.rubros_maestria_pagados()
                                fechavence1 = rubrospagados.last().fechavence
                                fechavencerec = fechavence1

                            diasvencidos = (datetime.now().date() - fechavence1).days
                            categoriaantiguedad = ""

                            if diasvencidos <= 30:
                                resumen[1]['estudiantes'] += 1
                                resumen[1]['pagado'] += valorpagado
                                resumen[1]['vencido'] += valorvencido
                                resumen[1]['pendiente'] += valorpendiente
                                categoriaantiguedad = "A"
                                rangodias = "1-30"
                            elif diasvencidos <= 60:
                                resumen[2]['estudiantes'] += 1
                                resumen[2]['pagado'] += valorpagado
                                resumen[2]['vencido'] += valorvencido
                                resumen[2]['pendiente'] += valorpendiente
                                categoriaantiguedad = "B"
                                rangodias = "31-60"
                            elif diasvencidos <= 90:
                                resumen[3]['estudiantes'] += 1
                                resumen[3]['pagado'] += valorpagado
                                resumen[3]['vencido'] += valorvencido
                                resumen[3]['pendiente'] += valorpendiente
                                categoriaantiguedad = "C"
                                rangodias = "61-90"
                            elif diasvencidos <= 180:
                                resumen[4]['estudiantes'] += 1
                                resumen[4]['pagado'] += valorpagado
                                resumen[4]['vencido'] += valorvencido
                                resumen[4]['pendiente'] += valorpendiente
                                categoriaantiguedad = "D"
                                rangodias = "91-180"
                            else:
                                resumen[5]['estudiantes'] += 1
                                resumen[5]['pagado'] += valorpagado
                                resumen[5]['vencido'] += valorvencido
                                resumen[5]['pendiente'] += valorpendiente
                                categoriaantiguedad = "E"
                                rangodias = "181 DÍAS EN ADELANTE"
                        else:
                            resumen[0]['estudiantes'] += 1
                            resumen[0]['pagado'] += valorpagado
                            resumen[0]['vencido'] += valorvencido
                            resumen[0]['pendiente'] += valorpendiente
                            categoriaantiguedad = "VIGENTE"
                            rangodias = ""

                        ws.write(row_num, 0, secuencia, fuentenormalder)
                        ws.write(row_num, 1, personaalumno.provincia.nombre if personaalumno.provincia else '', fuentenormal)
                        ws.write(row_num, 2, personaalumno.canton.nombre if personaalumno.canton else '', fuentenormal)
                        ws.write(row_num, 3, personaalumno.identificacion(), fuentenormal)
                        ws.write(row_num, 4, alumno, fuentenormal)
                        ws.write(row_num, 5, pagosvencidos, fuentenormalder)
                        ws.write(row_num, 6, fechavence1, fuentefecha)
                        ws.write(row_num, 7, fechavencerec, fuentefecha)
                        ws.write(row_num, 8, diasvencidos, fuentenormalder)
                        ws.write(row_num, 9, valorpagado,  fuentemoneda)
                        ws.write(row_num, 10, valorvencido,  fuentemoneda)
                        ws.write(row_num, 11, valorpendiente, fuentemoneda)
                        ws.write(row_num, 12, categoriaantiguedad, fuentenormal)
                        ws.write(row_num, 13, rangodias, fuentenormal)
                        ws.write(row_num, 14, lista.estado_inscripcion_maestria() , fuentenormal)

                        if rubrosalumno:
                            ultimafechavence = rubrosalumno.last().fechavence

                            if lista.tiene_refinanciamiento_deuda_posgrado():
                                estadofinanciamiento = "REFINANCIAMIENTO"
                            elif lista.tiene_coactiva_posgrado():
                                estadofinanciamiento = "COACTIVA"
                            elif datetime.now().date() <= ultimafechavence:
                                estadofinanciamiento = "EN EJECUCIÓN"
                            else:
                                estadofinanciamiento = "FINALIZADA"
                        else:
                            estadofinanciamiento = "NO TIENE RUBROS"

                        ws.write(row_num, 15, ultimafechavence, fuentefecha)
                        ws.write(row_num, 16, estadofinanciamiento, fuentenormal)

                        totalpagado += valorpagado
                        totalvencido += valorvencido
                        totalpendiente += valorpendiente

                    row_num += 1
                    ws.write_merge(row_num, row_num, 0, 8, "TOTALES", fuentenormalnegpie)
                    ws.write(row_num, 9, totalpagado, fuentemonedaneg)
                    ws.write(row_num, 10, totalvencido, fuentemonedaneg)
                    ws.write(row_num, 11, totalpendiente, fuentemonedaneg)

                    row_num += 3
                    ws.write_merge(row_num, row_num, 0, 6, "RESUMEN DE CARTERA VENCIDA", title2)
                    row_num += 1
                    ws.write_merge(row_num, row_num, 0, 1, "PERIODO DE VENCIMIENTO", fuentecabecera)
                    ws.write(row_num, 2, "NRO.ESTUDIANTES", fuentecabecera)
                    ws.write(row_num, 3, "VALOR PAGADO", fuentecabecera)
                    ws.write(row_num, 4, "VALOR CARTERA VENCIDA", fuentecabecera)
                    ws.write(row_num, 5, "VALOR PENDIENTE", fuentecabecera)
                    ws.write(row_num, 6, "ANTIGUEDAD", fuentecabecera)

                    row_num += 1
                    for i in resumen:
                        ws.write_merge(row_num, row_num, 0, 1, resumen[i]['etiqueta'], fuentenormal)
                        ws.write(row_num, 2, resumen[i]['estudiantes'], fuentenormalder)
                        ws.write(row_num, 3, resumen[i]['pagado'], fuentemoneda)
                        ws.write(row_num, 4, resumen[i]['vencido'], fuentemoneda)
                        ws.write(row_num, 5, resumen[i]['pendiente'], fuentemoneda)
                        ws.write(row_num, 6, resumen[i]['antiguedad'], fuentenormalcent)
                        row_num += 1

                    ws.write_merge(row_num, row_num, 0, 1, "TOTAL", fuentenormalnegpie)
                    ws.write(row_num, 2, secuencia, fuentenormalnegpieder)
                    ws.write(row_num, 3, totalpagado, fuentemonedaneg)
                    ws.write(row_num, 4, totalvencido, fuentemonedaneg)
                    ws.write(row_num, 5, totalpendiente, fuentemonedaneg)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass


            elif action == 'reporte_retirado_general':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalder = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')

                    fuentemonedaneg = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                        num_format_str=' "$" #,##0.00')

                    fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    # ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_retirados_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 7, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', title2)
                    ws.write_merge(2, 2, 0, 7, 'LISTADO GENERAL DE MAESTRANTES RETIRADOS', title2)

                    row_num = 4

                    columns = [
                        (u"PERIODO", 10000),
                        (u"PROGRAMAS EN EJECUCIÓN", 10000),
                        (u"NOMBRE DEL MAESTRANTE", 10000),
                        (u"MODULOS CURSADOS", 4000),
                        (u"TOTAL DE MODULOS DEL PROGRAMA", 4000),
                        (u"COSTO DEL PROGRAMA", 4000),
                        (u"DESCUENTO", 4000),
                        (u"NETO DEL PROGRAMA", 4000),
                        (u"COSTO DEL MODULO", 4000),
                        (u"VALOR POR PAGAR MODULOS RECIBIDOS", 4000),
                        (u"VALOR PAGADO", 4000),
                        (u"SALDO POR PAGAR", 4000),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    lista_periodos_r = Periodo.objects.filter(tipo__id__in=[3, 4], nivel__matricula__retiradomatricula=True).order_by('inicio', 'fin').distinct()
                    # lista_periodos_r = Periodo.objects.filter(tipo__id__in=[3, 4], nivel__matricula__materiaasignada__retiramateria=True).order_by('inicio', 'fin').distinct()


                    row_num = 4
                    total_por_pagar = Decimal(0)

                    for pr in lista_periodos_r:
                        lista_carreras_r = Carrera.objects.filter(inscripcion__matricula__retiradomatricula=True, inscripcion__matricula__nivel__periodo=pr).order_by('nombre').distinct()
                        # lista_carreras_r = Carrera.objects.filter(inscripcion__matricula__materiaasignada__retiramateria=True, inscripcion__matricula__nivel__periodo=pr).order_by('nombre').distinct()
                        for cr in lista_carreras_r:
                            # listado = Matricula.objects.filter(nivel__periodo=pr, inscripcion__carrera=cr,
                            #                                    materiaasignada__retiramateria=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2').distinct()

                            listado = Matricula.objects.filter(nivel__periodo=pr, inscripcion__carrera=cr,
                                                               retiradomatricula=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2').distinct()

                            for lista in listado:
                                row_num += 1
                                inscripcionmalla = lista.inscripcion.inscripcionmalla_set.filter(status=True)[0]
                                totalasignaturasmalla = inscripcionmalla.malla.asignaturamalla_set.filter(status=True, opcional=False).count()
                                programa = lista.inscripcion.carrera.nombre
                                alumno = lista.inscripcion.persona.apellido1 + ' ' + lista.inscripcion.persona.apellido2 + ' ' + lista.inscripcion.persona.nombres
                                costoprograma = lista.costo_programa()

                                # Verifico si tiene descuento
                                if lista.matriculanovedad_set.filter(status=True, tipo=1).exists():
                                    novedaddescuento = lista.matriculanovedad_set.filter(status=True, tipo=1)[0]
                                    porcentaje = Decimal(null_to_decimal(novedaddescuento.porcentajedescuento, 2))
                                    valordescontado = Decimal(null_to_decimal((costoprograma * porcentaje) / 100, 2)).quantize(Decimal('.01'))
                                    costoprogramaneto = costoprograma - valordescontado
                                elif lista.descuentoposgradomatricula_set.filter(status=True, estado=2).exists():
                                    descuentoayuda = lista.descuentoposgradomatricula_set.filter(status=True, estado=2)[0]
                                    porcentaje = Decimal(null_to_decimal(descuentoayuda.detalleconfiguraciondescuentoposgrado.configuraciondescuentoposgrado.porcentaje, 2))
                                    valordescontado = descuentoayuda.valordescuento
                                    costoprogramaneto = costoprograma - valordescontado
                                else:
                                    valordescontado = 0
                                    costoprogramaneto = costoprograma

                                #moduloscursados = lista.inscripcion.recordacademico_set.filter(status=True).count()
                                moduloscursados = lista.materiaasignada_set.filter(status=True, retiramateria=False).count()
                                modulosprograma = totalasignaturasmalla
                                costomodulo = round(costoprogramaneto/modulosprograma, 2)
                                montomodulosrecibidos = costomodulo * moduloscursados
                                # montopagosrealizados = lista.total_pagado_alumno()
                                montopagosrealizados = lista.total_pagado_alumno_rubro_maestria()
                                saldopagar = Decimal(null_to_decimal(montomodulosrecibidos, 2)) - montopagosrealizados if montopagosrealizados <= montomodulosrecibidos else Decimal(0)
                                total_por_pagar += saldopagar

                                ws.write(row_num, 0, pr.nombre, fuentenormal)
                                ws.write(row_num, 1, programa, fuentenormal)
                                ws.write(row_num, 2, alumno, fuentenormal)
                                ws.write(row_num, 3, moduloscursados, fuentenormalder)
                                ws.write(row_num, 4, modulosprograma, fuentenormalder)
                                ws.write(row_num, 5, costoprograma, fuentemoneda)
                                ws.write(row_num, 6, valordescontado, fuentemoneda)
                                ws.write(row_num, 7, costoprogramaneto, fuentemoneda)
                                ws.write(row_num, 8, costomodulo, fuentemoneda)
                                ws.write(row_num, 9, montomodulosrecibidos, fuentemoneda)
                                ws.write(row_num, 10, montopagosrealizados, fuentemoneda)
                                ws.write(row_num, 11, saldopagar, fuentemoneda)

                    row_num += 1
                    ws.write(row_num, 11, total_por_pagar, fuentemonedaneg)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_cartera_vencida_general_rubro_version_final_background':
                try:
                    fechacorte = datetime.strptime(request.GET['fechacartera'], '%Y-%m-%d').date()

                    # Guardar la notificación
                    notificacion = Notificacion(
                        cuerpo='Generación de reporte de excel en progreso',
                        titulo='Reporte Excel Cartera Vencida General - Detalle Rubros',
                        destinatario=persona,
                        url='',
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=1),
                        tipo=2,
                        en_proceso=True
                    )
                    notificacion.save(request)

                    reporte_cartera_vencida_general_rubro_version_final_background(request=request, data=data, idnotificacion=notificacion.id, fechacorte=fechacorte).start()

                    return JsonResponse({"result": "ok",
                                         "mensaje": u"El reporte se está generando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    print("error")
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})

            elif action == 'reporte_cartera_vencida_general_rubro_version_final':
                try:
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))
                    nombrearchivo = "CARTERA_VENCIDA_GENERAL_RUBROS_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Crea un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    hojadestino = workbook.add_worksheet("Reporte")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    fceldageneralcent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneralcent"])
                    ftitulo2izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo2izq"])
                    ftitulo3izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo3izq"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])
                    fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                    fceldanegritageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritageneral"])

                    ruta = "media/postgrado/" + nombrearchivo

                    fechacorte = datetime.strptime(request.GET['fechacartera'], '%Y-%m-%d').date()

                    hojadestino.merge_range(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo2izq)
                    hojadestino.merge_range(1, 0, 1, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', ftitulo2izq)
                    hojadestino.merge_range(2, 0, 2, 15, 'CARTERA VENCIDA GENERAL - DETALLE RUBROS', ftitulo2izq)
                    hojadestino.merge_range(3, 0, 3, 15, 'FECHA DE CORTE: ' + str(fechacorte) + '', ftitulo2izq)
                    hojadestino.merge_range(4, 0, 4, 15, 'FECHA DE DESCARGA DEL REPORTE (' + str(datetime.now().date()) + ')', ftitulo2izq)

                    columnas = [
                        (u"N°", 3),
                        (u"PROGRAMA DE MAESTRÍA", 30),
                        (u"COHORTE", 11),
                        (u"PERIODO (INICIO-FIN)", 20),
                        (u"ESTADO DE MAESTRÍA", 15),
                        (u"PROVINCIA", 15),
                        (u"CANTÓN", 15),
                        (u"CÉDULA", 15),
                        (u"ESTUDIANTE", 38),
                        (u"N° CUOTAS VENCIDAS", 15),
                        (u"ID RUBRO", 15),
                        (u"FECHA VENCIMIENTO", 15),
                        (u"DÍAS VENCIMIENTO", 15),
                        (u"TOTAL PAGADO", 15),
                        (u"VALOR VENCIDO", 15),
                        (u"VALOR PENDIENTE", 15),
                        (u"CATEGORÍA", 15),
                        (u"RANGO DÍAS", 15),
                        (u"ESTADO ESTUDIANTE", 15),
                        (u"FECHA ÚLTIMA CUOTA", 15),
                        (u"ESTADO FINANCIAMIENTO", 15)
                    ]

                    fila = 6
                    for col_num in range(len(columnas)):
                        hojadestino.write(fila, col_num, columnas[col_num][0], fcabeceracolumna)
                        hojadestino.set_column(col_num, col_num, columnas[col_num][1])

                    # cedulas = ['1716247307']

                    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                          # inscripcion__persona__cedula__in=cedulas,
                                                          # inscripcion__carrera__id__in=[173],
                                                          # nivel__periodo__id__in=*[143]
                                                          ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                                                                           'inscripcion__persona__apellido2',
                                                                                                                           'inscripcion__persona__nombres')#[:10]
                    totalmatriculas = matriculas.count()

                    secuencia = 0
                    registros = 0
                    totalvencido = 0
                    totalpendiente = 0
                    totalpagado = 0

                    programas = []

                    resumengeneral = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                                      1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                                      2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                                      3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                                      4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                                      5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                                      }

                    for matricula in matriculas:
                        secuencia += 1

                        alumno = matricula.inscripcion.persona.nombre_completo_inverso()
                        personaalumno = matricula.inscripcion.persona
                        rubrosalumno = matricula.rubros_maestria()
                        ultimafechavence = ""

                        # Verifico si el programa y cohorte existen en la lista de resumen
                        existe = False
                        indice = j = 0

                        idprograma = matricula.inscripcion.carrera.id
                        nombreprograma = matricula.inscripcion.carrera.nombre
                        idperiodo = matricula.nivel.periodo.id
                        numerocohorte = matricula.nivel.periodo.cohorte if matricula.nivel.periodo.cohorte else 0
                        fechasperiodo = str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin)
                        estadoprograma = "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO"

                        for datoprograma in programas:
                            if datoprograma[0] == idprograma and datoprograma[1] == idperiodo:
                                # indice = j
                                existe = True
                                break

                            j += 1

                        indice = j

                        if not existe:
                            # Agrego el programa y cohorte a la lista de programas
                            resumen = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                                       1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                                       2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                                       3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                                       4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                                       5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                                       }
                            datoprograma = [idprograma, idperiodo, nombreprograma, numerocohorte, fechasperiodo, estadoprograma, resumen]
                            programas.append(datoprograma)

                        datos = matricula.rubros_maestria_vencidos_detalle_version_final(fechacorte)

                        # No es retirado INICIO
                        if not matricula.retirado_programa_maestria():
                            # Si hay rubros no vencidos: INICIO
                            if datos['rubrosnovencidos']:
                                for rubro_no_vencido in datos['rubrosnovencidos']:
                                    fila += 1

                                    # print(fila)

                                    registros += 1

                                    codigorubro = rubro_no_vencido[0]
                                    valorpagado = rubro_no_vencido[3]
                                    valorpendiente = rubro_no_vencido[4]
                                    valorvencido = rubro_no_vencido[5]
                                    fechavence = rubro_no_vencido[1]
                                    diasvencidos = rubro_no_vencido[6]
                                    pagosvencidos = 1 if valorvencido > 0 else 0

                                    programas[indice][6][0]['estudiantes'] += 1
                                    programas[indice][6][0]['pagado'] += valorpagado
                                    programas[indice][6][0]['vencido'] += valorvencido
                                    programas[indice][6][0]['pendiente'] += valorpendiente

                                    resumengeneral[0]['estudiantes'] += 1
                                    resumengeneral[0]['pagado'] += valorpagado
                                    resumengeneral[0]['vencido'] += valorvencido
                                    resumengeneral[0]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "VIGENTE"
                                    rangodias = ""

                                    hojadestino.write(fila, 0, registros, fceldageneral)
                                    hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                    hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                    hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                                    hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                    hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                    hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                    hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                    hojadestino.write(fila, 8, alumno, fceldageneral)
                                    hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                    hojadestino.write(fila, 10, codigorubro, fceldageneral)
                                    hojadestino.write(fila, 11, fechavence, fceldafecha)
                                    hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                                    hojadestino.write(fila, 13, valorpagado, fceldamoneda)
                                    hojadestino.write(fila, 14, valorvencido, fceldamoneda)
                                    hojadestino.write(fila, 15, valorpendiente, fceldamoneda)
                                    hojadestino.write(fila, 16, categoriaantiguedad, fceldageneral)
                                    hojadestino.write(fila, 17, rangodias, fceldageneral)
                                    hojadestino.write(fila, 18, matricula.estado_inscripcion_maestria(), fceldageneral)

                                    if rubrosalumno:
                                        ultimafechavence = rubrosalumno.last().fechavence

                                        if matricula.tiene_refinanciamiento_deuda_posgrado():
                                            estadofinanciamiento = "REFINANCIAMIENTO"
                                        elif matricula.tiene_coactiva_posgrado():
                                            estadofinanciamiento = "COACTIVA"
                                        elif datetime.now().date() <= ultimafechavence:
                                            estadofinanciamiento = "EN EJECUCIÓN"
                                        else:
                                            estadofinanciamiento = "FINALIZADA"
                                    else:
                                        estadofinanciamiento = "NO TIENE RUBROS"

                                    hojadestino.write(fila, 19, ultimafechavence, fceldafecha)
                                    hojadestino.write(fila, 20, estadofinanciamiento, fceldageneral)

                                    totalpagado += valorpagado
                                    totalvencido += valorvencido
                                    totalpendiente += valorpendiente

                            # Si hay rubros no vencidos: FIN

                            # Si hay rubros vencidos: INICIO
                            if datos['rubrosvencidos']:
                                for rubro_vencido in datos['rubrosvencidos']:
                                    fila += 1

                                    # print(fila)

                                    registros += 1

                                    codigorubro = rubro_vencido[0]
                                    valorpagado = rubro_vencido[3]
                                    valorpendiente = rubro_vencido[4]
                                    valorvencido = rubro_vencido[5]
                                    fechavence = rubro_vencido[1]
                                    diasvencidos = rubro_vencido[6]
                                    pagosvencidos = 1 if valorvencido > 0 else 0

                                    categoriaantiguedad = ""

                                    if diasvencidos <= 30:
                                        programas[indice][6][1]['estudiantes'] += 1
                                        programas[indice][6][1]['pagado'] += valorpagado
                                        programas[indice][6][1]['vencido'] += valorvencido
                                        programas[indice][6][1]['pendiente'] += valorpendiente

                                        resumengeneral[1]['estudiantes'] += 1
                                        resumengeneral[1]['pagado'] += valorpagado
                                        resumengeneral[1]['vencido'] += valorvencido
                                        resumengeneral[1]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "A"
                                        rangodias = "1-30"
                                    elif diasvencidos <= 60:
                                        programas[indice][6][2]['estudiantes'] += 1
                                        programas[indice][6][2]['pagado'] += valorpagado
                                        programas[indice][6][2]['vencido'] += valorvencido
                                        programas[indice][6][2]['pendiente'] += valorpendiente

                                        resumengeneral[2]['estudiantes'] += 1
                                        resumengeneral[2]['pagado'] += valorpagado
                                        resumengeneral[2]['vencido'] += valorvencido
                                        resumengeneral[2]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "B"
                                        rangodias = "31-60"
                                    elif diasvencidos <= 90:
                                        programas[indice][6][3]['estudiantes'] += 1
                                        programas[indice][6][3]['pagado'] += valorpagado
                                        programas[indice][6][3]['vencido'] += valorvencido
                                        programas[indice][6][3]['pendiente'] += valorpendiente

                                        resumengeneral[3]['estudiantes'] += 1
                                        resumengeneral[3]['pagado'] += valorpagado
                                        resumengeneral[3]['vencido'] += valorvencido
                                        resumengeneral[3]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "C"
                                        rangodias = "61-90"
                                    elif diasvencidos <= 180:
                                        programas[indice][6][4]['estudiantes'] += 1
                                        programas[indice][6][4]['pagado'] += valorpagado
                                        programas[indice][6][4]['vencido'] += valorvencido
                                        programas[indice][6][4]['pendiente'] += valorpendiente

                                        resumengeneral[4]['estudiantes'] += 1
                                        resumengeneral[4]['pagado'] += valorpagado
                                        resumengeneral[4]['vencido'] += valorvencido
                                        resumengeneral[4]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "D"
                                        rangodias = "91-180"
                                    else:
                                        programas[indice][6][5]['estudiantes'] += 1
                                        programas[indice][6][5]['pagado'] += valorpagado
                                        programas[indice][6][5]['vencido'] += valorvencido
                                        programas[indice][6][5]['pendiente'] += valorpendiente

                                        resumengeneral[5]['estudiantes'] += 1
                                        resumengeneral[5]['pagado'] += valorpagado
                                        resumengeneral[5]['vencido'] += valorvencido
                                        resumengeneral[5]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "E"
                                        rangodias = "181 DÍAS EN ADELANTE"

                                    hojadestino.write(fila, 0, registros, fceldageneral)
                                    hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                    hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                    hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneral)
                                    hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                    hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                    hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                    hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                    hojadestino.write(fila, 8, alumno, fceldageneral)
                                    hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                    hojadestino.write(fila, 10, codigorubro, fceldageneral)
                                    hojadestino.write(fila, 11, fechavence, fceldafecha)
                                    hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                                    hojadestino.write(fila, 13, valorpagado, fceldamoneda)
                                    hojadestino.write(fila, 14, valorvencido, fceldamoneda)
                                    hojadestino.write(fila, 15, valorpendiente, fceldamoneda)
                                    hojadestino.write(fila, 16, categoriaantiguedad, fceldageneral)
                                    hojadestino.write(fila, 17, rangodias, fceldageneral)
                                    hojadestino.write(fila, 18, matricula.estado_inscripcion_maestria(), fceldageneral)

                                    if rubrosalumno:
                                        ultimafechavence = rubrosalumno.last().fechavence

                                        if matricula.tiene_refinanciamiento_deuda_posgrado():
                                            estadofinanciamiento = "REFINANCIAMIENTO"
                                        elif matricula.tiene_coactiva_posgrado():
                                            estadofinanciamiento = "COACTIVA"
                                        elif datetime.now().date() <= ultimafechavence:
                                            estadofinanciamiento = "EN EJECUCIÓN"
                                        else:
                                            estadofinanciamiento = "FINALIZADA"
                                    else:
                                        estadofinanciamiento = "NO TIENE RUBROS"

                                    hojadestino.write(fila, 19, ultimafechavence, fceldafecha)
                                    hojadestino.write(fila, 20, estadofinanciamiento, fceldageneral)

                                    totalpagado += valorpagado
                                    totalvencido += valorvencido
                                    totalpendiente += valorpendiente

                            # Si hay rubros vencidos: FIN
                        else:
                            registros += 1
                            fila += 1

                            # print(fila)

                            valorpagado = datos['totalpagado']
                            valorpendiente = datos['totalpendiente']
                            valorvencido = datos['totalvencido']
                            fechavence = datos['fechavence']
                            diasvencidos = datos['diasvencimiento']
                            pagosvencidos = 1 if valorvencido > 0 else 0

                            categoriaantiguedad = ""

                            if valorvencido > 0:
                                if diasvencidos <= 30:
                                    programas[indice][6][1]['estudiantes'] += 1
                                    programas[indice][6][1]['pagado'] += valorpagado
                                    programas[indice][6][1]['vencido'] += valorvencido
                                    programas[indice][6][1]['pendiente'] += valorpendiente

                                    resumengeneral[1]['estudiantes'] += 1
                                    resumengeneral[1]['pagado'] += valorpagado
                                    resumengeneral[1]['vencido'] += valorvencido
                                    resumengeneral[1]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "A"
                                    rangodias = "1-30"
                                elif diasvencidos <= 60:
                                    programas[indice][6][2]['estudiantes'] += 1
                                    programas[indice][6][2]['pagado'] += valorpagado
                                    programas[indice][6][2]['vencido'] += valorvencido
                                    programas[indice][6][2]['pendiente'] += valorpendiente

                                    resumengeneral[2]['estudiantes'] += 1
                                    resumengeneral[2]['pagado'] += valorpagado
                                    resumengeneral[2]['vencido'] += valorvencido
                                    resumengeneral[2]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "B"
                                    rangodias = "31-60"
                                elif diasvencidos <= 90:
                                    programas[indice][6][3]['estudiantes'] += 1
                                    programas[indice][6][3]['pagado'] += valorpagado
                                    programas[indice][6][3]['vencido'] += valorvencido
                                    programas[indice][6][3]['pendiente'] += valorpendiente

                                    resumengeneral[3]['estudiantes'] += 1
                                    resumengeneral[3]['pagado'] += valorpagado
                                    resumengeneral[3]['vencido'] += valorvencido
                                    resumengeneral[3]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "C"
                                    rangodias = "61-90"
                                elif diasvencidos <= 180:
                                    programas[indice][6][4]['estudiantes'] += 1
                                    programas[indice][6][4]['pagado'] += valorpagado
                                    programas[indice][6][4]['vencido'] += valorvencido
                                    programas[indice][6][4]['pendiente'] += valorpendiente

                                    resumengeneral[4]['estudiantes'] += 1
                                    resumengeneral[4]['pagado'] += valorpagado
                                    resumengeneral[4]['vencido'] += valorvencido
                                    resumengeneral[4]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "D"
                                    rangodias = "91-180"
                                else:
                                    programas[indice][6][5]['estudiantes'] += 1
                                    programas[indice][6][5]['pagado'] += valorpagado
                                    programas[indice][6][5]['vencido'] += valorvencido
                                    programas[indice][6][5]['pendiente'] += valorpendiente

                                    resumengeneral[5]['estudiantes'] += 1
                                    resumengeneral[5]['pagado'] += valorpagado
                                    resumengeneral[5]['vencido'] += valorvencido
                                    resumengeneral[5]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "E"
                                    rangodias = "181 DÍAS EN ADELANTE"
                            else:
                                programas[indice][6][0]['estudiantes'] += 1
                                programas[indice][6][0]['pagado'] += valorpagado
                                programas[indice][6][0]['vencido'] += valorvencido
                                programas[indice][6][0]['pendiente'] += valorpendiente

                                resumengeneral[0]['estudiantes'] += 1
                                resumengeneral[0]['pagado'] += valorpagado
                                resumengeneral[0]['vencido'] += valorvencido
                                resumengeneral[0]['pendiente'] += valorpendiente

                                categoriaantiguedad = "VIGENTE"
                                rangodias = ""

                            hojadestino.write(fila, 0, registros, fceldageneral)
                            hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                            hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                            hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneral)
                            hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                            hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                            hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                            hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                            hojadestino.write(fila, 8, alumno, fceldageneral)
                            hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                            hojadestino.write(fila, 10, "S/N", fceldageneral)
                            hojadestino.write(fila, 11, fechavence, fceldafecha)
                            hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                            hojadestino.write(fila, 13, valorpagado, fceldamoneda)
                            hojadestino.write(fila, 14, valorvencido, fceldamoneda)
                            hojadestino.write(fila, 15, valorpendiente, fceldamoneda)
                            hojadestino.write(fila, 16, categoriaantiguedad, fceldageneral)
                            hojadestino.write(fila, 17, rangodias, fceldageneral)
                            hojadestino.write(fila, 18, matricula.estado_inscripcion_maestria(), fceldageneral)

                            if rubrosalumno:
                                ultimafechavence = rubrosalumno.last().fechavence

                                if matricula.tiene_refinanciamiento_deuda_posgrado():
                                    estadofinanciamiento = "REFINANCIAMIENTO"
                                elif matricula.tiene_coactiva_posgrado():
                                    estadofinanciamiento = "COACTIVA"
                                elif datetime.now().date() <= ultimafechavence:
                                    estadofinanciamiento = "EN EJECUCIÓN"
                                else:
                                    estadofinanciamiento = "FINALIZADA"
                            else:
                                estadofinanciamiento = "NO TIENE RUBROS"

                            hojadestino.write(fila, 19, ultimafechavence, fceldafecha)
                            hojadestino.write(fila, 20, estadofinanciamiento, fceldageneral)

                            totalpagado += valorpagado
                            totalvencido += valorvencido
                            totalpendiente += valorpendiente

                        # No es retirado FIN

                        print(secuencia, " de ", totalmatriculas)

                    fila += 1
                    hojadestino.merge_range(fila, 0, fila, 12, "TOTALES", fceldanegritageneral)
                    hojadestino.write(fila, 13, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 14, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 15, totalpendiente, fceldamonedapie)



                    fila += 3
                    hojadestino.merge_range(fila, 0, fila, 11, "RESUMEN DE CARTERA VENCIDA GENERAL", ftitulo3izq)

                    fila += 1

                    hojadestino.merge_range(fila, 0, fila, 1, "PERIODO DE VENCIMIENTO", fcabeceracolumna)
                    hojadestino.write(fila, 2, "NRO.ESTUDIANTES", fcabeceracolumna)
                    hojadestino.write(fila, 3, "VALOR PAGADO", fcabeceracolumna)
                    hojadestino.write(fila, 4, "VALOR CARTERA VENCIDA", fcabeceracolumna)
                    hojadestino.write(fila, 5, "VALOR PENDIENTE", fcabeceracolumna)
                    hojadestino.write(fila, 6, "ANTIGUEDAD", fcabeceracolumna)

                    fila += 1
                    for i in resumengeneral:
                        hojadestino.merge_range(fila, 0, fila, 1, resumengeneral[i]['etiqueta'], fceldageneral)
                        hojadestino.write(fila, 2, resumengeneral[i]['estudiantes'], fceldageneral)
                        hojadestino.write(fila, 3, resumengeneral[i]['pagado'], fceldamoneda)
                        hojadestino.write(fila, 4, resumengeneral[i]['vencido'], fceldamoneda)
                        hojadestino.write(fila, 5, resumengeneral[i]['pendiente'], fceldamoneda)
                        hojadestino.write(fila, 6, resumengeneral[i]['antiguedad'], fceldageneralcent)
                        fila += 1

                    hojadestino.merge_range(fila, 0, fila, 1, "TOTAL", fceldanegritageneral)
                    hojadestino.write(fila, 2, registros, fceldanegritageneral)
                    hojadestino.write(fila, 3, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 4, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 5, totalpendiente, fceldamonedapie)


                    fila += 3
                    hojadestino.merge_range(fila, 0, fila, 11, "RESUMEN DE CARTERA VENCIDA POR PROGRAMA DE MAESTRÍA", ftitulo3izq)

                    fila += 1
                    hojadestino.write(fila, 0, "N°", fcabeceracolumna)
                    hojadestino.write(fila, 1, "PROGRAMA", fcabeceracolumna)
                    hojadestino.write(fila, 2, "COHORTE", fcabeceracolumna)
                    hojadestino.write(fila, 3, "PERIODO (INICIO-FIN)", fcabeceracolumna)
                    hojadestino.write(fila, 4, "ESTADO DE MAESTRIA", fcabeceracolumna)
                    hojadestino.write(fila, 5, "PERIODO DE VENCIMIENTO", fcabeceracolumna)
                    hojadestino.write(fila, 6, "NRO.ESTUDIANTES", fcabeceracolumna)
                    hojadestino.write(fila, 7, "VALOR PAGADO", fcabeceracolumna)
                    hojadestino.write(fila, 8, "VALOR CARTERA VENCIDA", fcabeceracolumna)
                    hojadestino.write(fila, 9, "VALOR PENDIENTE", fcabeceracolumna)
                    hojadestino.write(fila, 10, "ANTIGUEDAD", fcabeceracolumna)

                    # Ordeno por programa y cohorte
                    programas = sorted(programas, key=lambda programa: (programa[2], programa[3]))

                    secresumen = 0
                    for datoprograma in programas:
                        fila += 1
                        secresumen += 1
                        hojadestino.merge_range(fila, 0, fila + 5, 0, secresumen, fceldageneralcent)
                        hojadestino.merge_range(fila, 1, fila + 5, 1, datoprograma[2], fceldageneralcent)
                        hojadestino.merge_range(fila, 2, fila + 5, 2, datoprograma[3], fceldageneralcent)
                        hojadestino.merge_range(fila, 3, fila + 5, 3, datoprograma[4], fceldageneralcent)
                        hojadestino.merge_range(fila, 4, fila + 5, 4, datoprograma[5], fceldageneralcent)

                        tot_est_prog = tot_venc_prog = tot_pend_prog = tot_pag_prog = 0

                        resumen = datoprograma[6]
                        for i in resumen:
                            hojadestino.write(fila, 5, resumen[i]['etiqueta'], fceldageneral)
                            hojadestino.write(fila, 6, resumen[i]['estudiantes'], fceldageneral)
                            hojadestino.write(fila, 7, resumen[i]['pagado'], fceldamoneda)
                            hojadestino.write(fila, 8, resumen[i]['vencido'], fceldamoneda)
                            hojadestino.write(fila, 9, resumen[i]['pendiente'], fceldamoneda)
                            hojadestino.write(fila, 10, resumen[i]['antiguedad'], fceldageneralcent)

                            tot_est_prog += resumen[i]['estudiantes']
                            tot_pag_prog += resumen[i]['pagado']
                            tot_venc_prog += resumen[i]['vencido']
                            tot_pend_prog += resumen[i]['pendiente']

                            fila += 1

                        hojadestino.merge_range(fila, 0, fila, 5, "TOTAL " + datoprograma[2] + " COHORTE " + str(datoprograma[3]), fceldanegritageneral)
                        hojadestino.write(fila, 6, tot_est_prog, fceldanegritageneral)
                        hojadestino.write(fila, 7, tot_pag_prog, fceldamonedapie)
                        hojadestino.write(fila, 8, tot_venc_prog, fceldamonedapie)
                        hojadestino.write(fila, 9, tot_pend_prog, fceldamonedapie)

                    fila += 1
                    hojadestino.merge_range(fila, 0, fila, 5, "TOTAL GENERAL", fceldanegritageneral)
                    hojadestino.write(fila, 6, registros, fceldanegritageneral)
                    hojadestino.write(fila, 7, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 8, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 9, totalpendiente, fceldamonedapie)

                    workbook.close()

                    ruta = "media/postgrado/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    print("error")
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})

            elif action == 'reporte_cartera_vencida_general_rubro_por_categoria_version_final':
                try:
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))
                    nombrearchivo = "COACTIVA_POR_CATEGORIA_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Crea un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    hojadestino = workbook.add_worksheet("Detalle Rubros")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    fceldageneralcent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneralcent"])
                    ftitulo2izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo2izq"])
                    ftitulo3izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo3izq"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])
                    fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                    fceldanegritageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritageneral"])

                    ruta = "media/postgrado/" + nombrearchivo

                    fechacorte = datetime.strptime(request.GET['fechacartera'], '%Y-%m-%d').date()
                    categoriadeuda = request.GET['categoria']

                    hojadestino.merge_range(0, 0, 0, 16, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo2izq)
                    hojadestino.merge_range(1, 0, 1, 16, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', ftitulo2izq)
                    hojadestino.merge_range(2, 0, 2, 16, 'COACTIVA POR CATEGORÍA - (CATEGORÍA ' + categoriadeuda + ' HASTA A)', ftitulo2izq)
                    hojadestino.merge_range(3, 0, 3, 16, "FECHA DE CORTE: " + str(fechacorte) + "", ftitulo2izq)
                    hojadestino.merge_range(4, 0, 4, 16, "FECHA DE DESCARGA DEL REPORTE (" + str(datetime.now().date()) + ")", ftitulo2izq)

                    fila = 6

                    columnas = [
                        (u"N°", 3),
                        (u"PROGRAMA DE MAESTRÍA", 30),
                        (u"COHORTE", 11),
                        (u"PERIODO (INICIO-FIN)", 20),
                        (u"ESTADO DE MAESTRÍA", 15),
                        (u"PROVINCIA", 15),
                        (u"CANTÓN", 15),
                        (u"CÉDULA", 15),
                        (u"ESTUDIANTE", 38),
                        (u"N° CUOTAS VENCIDAS", 15),
                        (u"ID RUBRO", 15),
                        (u"FECHA VENCIMIENTO", 15),
                        (u"DÍAS VENCIMIENTO", 15),
                        (u"TOTAL PAGADO", 15),
                        (u"VALOR VENCIDO", 15),
                        (u"VALOR PENDIENTE", 15),
                        (u"CATEGORÍA", 15),
                        (u"RANGO DÍAS", 15),
                        (u"ESTADO ESTUDIANTE", 15),
                        (u"FECHA ÚLTIMA CUOTA", 15),
                        (u"ESTADO FINANCIAMIENTO", 15),
                        (u"PRE-COACTIVA", 15)
                    ]

                    for col_num in range(len(columnas)):
                        hojadestino.write(fila, col_num, columnas[col_num][0], fcabeceracolumna)
                        hojadestino.set_column(col_num, col_num, columnas[col_num][1])

                    cedulas = ['0919322644']

                    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                          # inscripcion__persona__cedula__in=cedulas,
                                                          # inscripcion__carrera__id__in=[173],
                                                          # nivel__periodo__id__in=[143]
                                                          ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                                                                           'inscripcion__persona__apellido2',
                                                                                                                           'inscripcion__persona__nombres')#[:1000]
                    totalmatriculas = matriculas.count()

                    secuencia = 0
                    registros = 0
                    totalvencido = 0
                    totalpendiente = 0
                    totalpagado = 0

                    programas = []
                    resumenpersona = []
                    indicepersona = 0

                    resumengeneral = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                                      1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                                      2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                                      3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                                      4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                                      5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                                      }
                    tx = matriculas.count()
                    for matricula in matriculas:
                        secuencia += 1

                        print("Procesando", secuencia, " de ", tx)
                        print(matricula.inscripcion.persona.cedula)

                        alumno = matricula.inscripcion.persona.nombre_completo_inverso()
                        personaalumno = matricula.inscripcion.persona
                        rubrosalumno = matricula.rubros_maestria()
                        ultimafechavence = ""

                        # Verifico si el programa y cohorte existen en la lista de resumen
                        existe = False
                        indice = j = 0

                        idprograma = matricula.inscripcion.carrera.id
                        nombreprograma = matricula.inscripcion.carrera.nombre
                        idperiodo = matricula.nivel.periodo.id
                        numerocohorte = matricula.nivel.periodo.cohorte if matricula.nivel.periodo.cohorte else 0
                        fechasperiodo = str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin)
                        estadoprograma = "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO"

                        for datoprograma in programas:
                            if datoprograma[0] == idprograma and datoprograma[1] == idperiodo:
                                # indice = j
                                existe = True
                                break

                            j += 1

                        indice = j

                        if not existe:
                            # Agrego el programa y cohorte a la lista de programas
                            resumen = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                                       1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                                       2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                                       3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                                       4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                                       5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                                       }
                            datoprograma = [idprograma, idperiodo, nombreprograma, numerocohorte, fechasperiodo, estadoprograma, resumen]
                            programas.append(datoprograma)

                        # datos = matricula.rubros_maestria_vencidos_detalle_version_final(fechacorte)
                        datos = matricula.rubros_maestria_vencidos_detalle_por_categoria_version_final(fechacorte, categoriadeuda)

                        if datos:
                            # Agrego al alumno a la lista resumenpersona
                            resumenpersona.append([matricula.id,
                                                   personaalumno.identificacion(),
                                                   alumno,
                                                   0,
                                                   0,
                                                   nombreprograma,
                                                   numerocohorte,
                                                   personaalumno.provincia.nombre if personaalumno.provincia else '',
                                                   personaalumno.canton.nombre if personaalumno.canton else '',
                                                   personaalumno.direccion_corta(),
                                                   personaalumno.telefono_conv if personaalumno.telefono_conv else 'NO TIENE',
                                                   personaalumno.telefono,
                                                   personaalumno.email,
                                                   personaalumno.emailinst])

                            # No es retirado INICIO
                            if not matricula.retirado_programa_maestria():
                                # Si hay rubros vencidos: INICIO
                                if datos['rubrosvencidos']:
                                    for rubro_vencido in datos['rubrosvencidos']:
                                        fila += 1

                                        registros += 1

                                        codigorubro = rubro_vencido[0]
                                        valorpagado = rubro_vencido[3]
                                        valorpendiente = rubro_vencido[4]
                                        valorvencido = rubro_vencido[5]
                                        fechavence = rubro_vencido[1]
                                        diasvencidos = rubro_vencido[6]
                                        pagosvencidos = 1 if valorvencido > 0 else 0

                                        # Actualizo valores en ls lista de resumen por persona
                                        resumenpersona[indicepersona][3] += 1
                                        resumenpersona[indicepersona][4] += valorvencido

                                        categoriaantiguedad = ""

                                        if diasvencidos <= 30:
                                            programas[indice][6][1]['estudiantes'] += 1
                                            programas[indice][6][1]['pagado'] += valorpagado
                                            programas[indice][6][1]['vencido'] += valorvencido
                                            programas[indice][6][1]['pendiente'] += valorpendiente

                                            resumengeneral[1]['estudiantes'] += 1
                                            resumengeneral[1]['pagado'] += valorpagado
                                            resumengeneral[1]['vencido'] += valorvencido
                                            resumengeneral[1]['pendiente'] += valorpendiente

                                            categoriaantiguedad = "A"
                                            rangodias = "1-30"
                                        elif diasvencidos <= 60:
                                            programas[indice][6][2]['estudiantes'] += 1
                                            programas[indice][6][2]['pagado'] += valorpagado
                                            programas[indice][6][2]['vencido'] += valorvencido
                                            programas[indice][6][2]['pendiente'] += valorpendiente

                                            resumengeneral[2]['estudiantes'] += 1
                                            resumengeneral[2]['pagado'] += valorpagado
                                            resumengeneral[2]['vencido'] += valorvencido
                                            resumengeneral[2]['pendiente'] += valorpendiente

                                            categoriaantiguedad = "B"
                                            rangodias = "31-60"
                                        elif diasvencidos <= 90:
                                            programas[indice][6][3]['estudiantes'] += 1
                                            programas[indice][6][3]['pagado'] += valorpagado
                                            programas[indice][6][3]['vencido'] += valorvencido
                                            programas[indice][6][3]['pendiente'] += valorpendiente

                                            resumengeneral[3]['estudiantes'] += 1
                                            resumengeneral[3]['pagado'] += valorpagado
                                            resumengeneral[3]['vencido'] += valorvencido
                                            resumengeneral[3]['pendiente'] += valorpendiente

                                            categoriaantiguedad = "C"
                                            rangodias = "61-90"
                                        elif diasvencidos <= 180:
                                            programas[indice][6][4]['estudiantes'] += 1
                                            programas[indice][6][4]['pagado'] += valorpagado
                                            programas[indice][6][4]['vencido'] += valorvencido
                                            programas[indice][6][4]['pendiente'] += valorpendiente

                                            resumengeneral[4]['estudiantes'] += 1
                                            resumengeneral[4]['pagado'] += valorpagado
                                            resumengeneral[4]['vencido'] += valorvencido
                                            resumengeneral[4]['pendiente'] += valorpendiente

                                            categoriaantiguedad = "D"
                                            rangodias = "91-180"
                                        else:
                                            programas[indice][6][5]['estudiantes'] += 1
                                            programas[indice][6][5]['pagado'] += valorpagado
                                            programas[indice][6][5]['vencido'] += valorvencido
                                            programas[indice][6][5]['pendiente'] += valorpendiente

                                            resumengeneral[5]['estudiantes'] += 1
                                            resumengeneral[5]['pagado'] += valorpagado
                                            resumengeneral[5]['vencido'] += valorvencido
                                            resumengeneral[5]['pendiente'] += valorpendiente

                                            categoriaantiguedad = "E"
                                            rangodias = "181 DÍAS EN ADELANTE"

                                        hojadestino.write(fila, 0, registros, fceldageneral)
                                        hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                        hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                        hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                                        hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                        hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                        hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                        hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                        hojadestino.write(fila, 8, alumno, fceldageneral)
                                        hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                        hojadestino.write(fila, 10, codigorubro, fceldageneral)
                                        hojadestino.write(fila, 11, fechavence, fceldafecha)
                                        hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                                        hojadestino.write(fila, 13, valorpagado, fceldamoneda)
                                        hojadestino.write(fila, 14, valorvencido, fceldamoneda)
                                        hojadestino.write(fila, 15, valorpendiente, fceldamoneda)
                                        hojadestino.write(fila, 16, categoriaantiguedad, fceldageneral)
                                        hojadestino.write(fila, 17, rangodias, fceldageneral)
                                        hojadestino.write(fila, 18, matricula.estado_inscripcion_maestria(), fceldageneral)

                                        if rubrosalumno:
                                            ultimafechavence = rubrosalumno.last().fechavence

                                            if matricula.tiene_refinanciamiento_deuda_posgrado():
                                                estadofinanciamiento = "REFINANCIAMIENTO"
                                            elif matricula.tiene_coactiva_posgrado():
                                                estadofinanciamiento = "COACTIVA"
                                            elif datetime.now().date() <= ultimafechavence:
                                                estadofinanciamiento = "EN EJECUCIÓN"
                                            else:
                                                estadofinanciamiento = "FINALIZADA"
                                        else:
                                            estadofinanciamiento = "NO TIENE RUBROS"

                                        hojadestino.write(fila, 19, ultimafechavence, fceldafecha)
                                        hojadestino.write(fila, 20, estadofinanciamiento, fceldageneral)
                                        hojadestino.write(fila, 21, "SI", fceldageneral)

                                        totalpagado += valorpagado
                                        totalvencido += valorvencido
                                        totalpendiente += valorpendiente

                                    indicepersona += 1
                                # Si hay rubros vencidos: FIN
                            else:
                                registros += 1
                                fila += 1

                                valorpagado = datos['totalpagado']
                                valorpendiente = datos['totalpendiente']
                                valorvencido = datos['totalvencido']
                                fechavence = datos['fechavence']
                                diasvencidos = datos['diasvencimiento']
                                pagosvencidos = 1 if valorvencido > 0 else 0

                                categoriaantiguedad = ""

                                if valorvencido > 0:
                                    # Actualizo valores en ls lista de resumen por persona
                                    resumenpersona[indicepersona][3] += 1
                                    resumenpersona[indicepersona][4] += valorvencido

                                    if diasvencidos <= 30:
                                        programas[indice][6][1]['estudiantes'] += 1
                                        programas[indice][6][1]['pagado'] += valorpagado
                                        programas[indice][6][1]['vencido'] += valorvencido
                                        programas[indice][6][1]['pendiente'] += valorpendiente

                                        resumengeneral[1]['estudiantes'] += 1
                                        resumengeneral[1]['pagado'] += valorpagado
                                        resumengeneral[1]['vencido'] += valorvencido
                                        resumengeneral[1]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "A"
                                        rangodias = "1-30"
                                    elif diasvencidos <= 60:
                                        programas[indice][6][2]['estudiantes'] += 1
                                        programas[indice][6][2]['pagado'] += valorpagado
                                        programas[indice][6][2]['vencido'] += valorvencido
                                        programas[indice][6][2]['pendiente'] += valorpendiente

                                        resumengeneral[2]['estudiantes'] += 1
                                        resumengeneral[2]['pagado'] += valorpagado
                                        resumengeneral[2]['vencido'] += valorvencido
                                        resumengeneral[2]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "B"
                                        rangodias = "31-60"
                                    elif diasvencidos <= 90:
                                        programas[indice][6][3]['estudiantes'] += 1
                                        programas[indice][6][3]['pagado'] += valorpagado
                                        programas[indice][6][3]['vencido'] += valorvencido
                                        programas[indice][6][3]['pendiente'] += valorpendiente

                                        resumengeneral[3]['estudiantes'] += 1
                                        resumengeneral[3]['pagado'] += valorpagado
                                        resumengeneral[3]['vencido'] += valorvencido
                                        resumengeneral[3]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "C"
                                        rangodias = "61-90"
                                    elif diasvencidos <= 180:
                                        programas[indice][6][4]['estudiantes'] += 1
                                        programas[indice][6][4]['pagado'] += valorpagado
                                        programas[indice][6][4]['vencido'] += valorvencido
                                        programas[indice][6][4]['pendiente'] += valorpendiente

                                        resumengeneral[4]['estudiantes'] += 1
                                        resumengeneral[4]['pagado'] += valorpagado
                                        resumengeneral[4]['vencido'] += valorvencido
                                        resumengeneral[4]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "D"
                                        rangodias = "91-180"
                                    else:
                                        programas[indice][6][5]['estudiantes'] += 1
                                        programas[indice][6][5]['pagado'] += valorpagado
                                        programas[indice][6][5]['vencido'] += valorvencido
                                        programas[indice][6][5]['pendiente'] += valorpendiente

                                        resumengeneral[5]['estudiantes'] += 1
                                        resumengeneral[5]['pagado'] += valorpagado
                                        resumengeneral[5]['vencido'] += valorvencido
                                        resumengeneral[5]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "E"
                                        rangodias = "181 DÍAS EN ADELANTE"

                                    precoactiva = "SI"
                                    indicepersona += 1
                                else:
                                    programas[indice][6][0]['estudiantes'] += 1
                                    programas[indice][6][0]['pagado'] += valorpagado
                                    programas[indice][6][0]['vencido'] += valorvencido
                                    programas[indice][6][0]['pendiente'] += valorpendiente

                                    resumengeneral[0]['estudiantes'] += 1
                                    resumengeneral[0]['pagado'] += valorpagado
                                    resumengeneral[0]['vencido'] += valorvencido
                                    resumengeneral[0]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "VIGENTE"
                                    rangodias = ""
                                    precoactiva = "NO"

                                hojadestino.write(fila, 0, registros, fceldageneral)
                                hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                                hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                hojadestino.write(fila, 8, alumno, fceldageneral)
                                hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                hojadestino.write(fila, 10, "S/N", fceldageneral)
                                hojadestino.write(fila, 11, fechavence, fceldafecha)
                                hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                                hojadestino.write(fila, 13, valorpagado, fceldamoneda)
                                hojadestino.write(fila, 14, valorvencido, fceldamoneda)
                                hojadestino.write(fila, 15, valorpendiente, fceldamoneda)
                                hojadestino.write(fila, 16, categoriaantiguedad, fceldageneral)
                                hojadestino.write(fila, 17, rangodias, fceldageneral)
                                hojadestino.write(fila, 18, matricula.estado_inscripcion_maestria(), fceldageneral)

                                if rubrosalumno:
                                    ultimafechavence = rubrosalumno.last().fechavence

                                    if matricula.tiene_refinanciamiento_deuda_posgrado():
                                        estadofinanciamiento = "REFINANCIAMIENTO"
                                    elif matricula.tiene_coactiva_posgrado():
                                        estadofinanciamiento = "COACTIVA"
                                    elif datetime.now().date() <= ultimafechavence:
                                        estadofinanciamiento = "EN EJECUCIÓN"
                                    else:
                                        estadofinanciamiento = "FINALIZADA"
                                else:
                                    estadofinanciamiento = "NO TIENE RUBROS"

                                hojadestino.write(fila, 19, ultimafechavence, fceldafecha)
                                hojadestino.write(fila, 20, estadofinanciamiento, fceldageneral)
                                hojadestino.write(fila, 21, precoactiva, fceldageneral)

                                totalpagado += valorpagado
                                totalvencido += valorvencido
                                totalpendiente += valorpendiente

                            # No es retirado FIN

                        print(secuencia, " de ", totalmatriculas)


                    fila += 1
                    hojadestino.merge_range(fila, 0, fila, 12, "TOTALES", fceldanegritageneral)
                    hojadestino.write(fila, 13, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 14, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 15, totalpendiente, fceldamonedapie)

                    fila += 3
                    hojadestino.merge_range(fila, 0, fila, 11, "RESUMEN DE CARTERA VENCIDA GENERAL", ftitulo3izq)

                    fila += 1

                    hojadestino.merge_range(fila, 0, fila, 1, "PERIODO DE VENCIMIENTO", fcabeceracolumna)
                    hojadestino.write(fila, 2, "NRO.ESTUDIANTES", fcabeceracolumna)
                    hojadestino.write(fila, 3, "VALOR PAGADO", fcabeceracolumna)
                    hojadestino.write(fila, 4, "VALOR CARTERA VENCIDA", fcabeceracolumna)
                    hojadestino.write(fila, 5, "VALOR PENDIENTE", fcabeceracolumna)
                    hojadestino.write(fila, 6, "ANTIGUEDAD", fcabeceracolumna)

                    fila += 1
                    for i in resumengeneral:
                        hojadestino.merge_range(fila, 0, fila, 1, resumengeneral[i]['etiqueta'], fceldageneral)
                        hojadestino.write(fila, 2, resumengeneral[i]['estudiantes'], fceldageneral)
                        hojadestino.write(fila, 3, resumengeneral[i]['pagado'], fceldamoneda)
                        hojadestino.write(fila, 4, resumengeneral[i]['vencido'], fceldamoneda)
                        hojadestino.write(fila, 5, resumengeneral[i]['pendiente'], fceldamoneda)
                        hojadestino.write(fila, 6, resumengeneral[i]['antiguedad'], fceldageneralcent)
                        fila += 1

                    hojadestino.merge_range(fila, 0, fila, 1, "TOTAL", fceldanegritageneral)
                    hojadestino.write(fila, 2, registros, fceldanegritageneral)
                    hojadestino.write(fila, 3, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 4, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 5, totalpendiente, fceldamonedapie)

                    fila += 3
                    hojadestino.merge_range(fila, 0, fila, 11, "RESUMEN DE CARTERA VENCIDA POR PROGRAMA DE MAESTRÍA", ftitulo3izq)

                    fila += 1
                    hojadestino.write(fila, 0, "N°", fcabeceracolumna)
                    hojadestino.write(fila, 1, "PROGRAMA", fcabeceracolumna)
                    hojadestino.write(fila, 2, "COHORTE", fcabeceracolumna)
                    hojadestino.write(fila, 3, "PERIODO (INICIO-FIN)", fcabeceracolumna)
                    hojadestino.write(fila, 4, "ESTADO DE MAESTRIA", fcabeceracolumna)
                    hojadestino.write(fila, 5, "PERIODO DE VENCIMIENTO", fcabeceracolumna)
                    hojadestino.write(fila, 6, "NRO.ESTUDIANTES", fcabeceracolumna)
                    hojadestino.write(fila, 7, "VALOR PAGADO", fcabeceracolumna)
                    hojadestino.write(fila, 8, "VALOR CARTERA VENCIDA", fcabeceracolumna)
                    hojadestino.write(fila, 9, "VALOR PENDIENTE", fcabeceracolumna)
                    hojadestino.write(fila, 10, "ANTIGUEDAD", fcabeceracolumna)

                    # Ordeno por programa y cohorte
                    programas = sorted(programas, key=lambda programa: (programa[2], programa[3]))

                    secresumen = 0
                    for datoprograma in programas:
                        fila += 1
                        secresumen += 1
                        hojadestino.merge_range(fila, 0, fila + 5, 0, secresumen, fceldageneralcent)
                        hojadestino.merge_range(fila, 1, fila + 5, 1, datoprograma[2], fceldageneralcent)
                        hojadestino.merge_range(fila, 2, fila + 5, 2, datoprograma[3], fceldageneralcent)
                        hojadestino.merge_range(fila, 3, fila + 5, 3, datoprograma[4], fceldageneralcent)
                        hojadestino.merge_range(fila, 4, fila + 5, 4, datoprograma[5], fceldageneralcent)

                        tot_est_prog = tot_venc_prog = tot_pend_prog = tot_pag_prog = 0

                        resumen = datoprograma[6]
                        for i in resumen:
                            hojadestino.write(fila, 5, resumen[i]['etiqueta'], fceldageneral)
                            hojadestino.write(fila, 6, resumen[i]['estudiantes'], fceldageneral)
                            hojadestino.write(fila, 7, resumen[i]['pagado'], fceldamoneda)
                            hojadestino.write(fila, 8, resumen[i]['vencido'], fceldamoneda)
                            hojadestino.write(fila, 9, resumen[i]['pendiente'], fceldamoneda)
                            hojadestino.write(fila, 10, resumen[i]['antiguedad'], fceldageneralcent)

                            tot_est_prog += resumen[i]['estudiantes']
                            tot_pag_prog += resumen[i]['pagado']
                            tot_venc_prog += resumen[i]['vencido']
                            tot_pend_prog += resumen[i]['pendiente']

                            fila += 1

                        hojadestino.merge_range(fila, 0, fila, 5, "TOTAL " + datoprograma[2] + " COHORTE " + str(datoprograma[3]), fceldanegritageneral)
                        hojadestino.write(fila, 6, tot_est_prog, fceldanegritageneral)
                        hojadestino.write(fila, 7, tot_pag_prog, fceldamonedapie)
                        hojadestino.write(fila, 8, tot_venc_prog, fceldamonedapie)
                        hojadestino.write(fila, 9, tot_pend_prog, fceldamonedapie)

                    fila += 1
                    hojadestino.merge_range(fila, 0, fila, 5, "TOTAL GENERAL", fceldanegritageneral)
                    hojadestino.write(fila, 6, registros, fceldanegritageneral)
                    hojadestino.write(fila, 7, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 8, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 9, totalpendiente, fceldamonedapie)

                    if totalvencido > 0:
                        # Resumen general por Persona
                        hojadestino = workbook.add_worksheet("Resumen Persona")
                        hojadestino.merge_range(0, 0, 0, 16, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo2izq)
                        hojadestino.merge_range(1, 0, 1, 16, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', ftitulo2izq)
                        hojadestino.merge_range(2, 0, 2, 16, 'COACTIVA POR CATEGORÍA - (CATEGORÍA ' + categoriadeuda + ' HASTA A)', ftitulo2izq)
                        hojadestino.merge_range(3, 0, 3, 16, "FECHA DE CORTE: " + str(fechacorte) + "", ftitulo2izq)
                        hojadestino.merge_range(4, 0, 4, 16, "FECHA DE DESCARGA DEL REPORTE (" + str(datetime.now().date()) + ")", ftitulo2izq)

                        fila = 6

                        columnas = [
                            (u"N°", 3),
                            (u"CÉDULA", 15),
                            (u"ESTUDIANTE", 38),
                            (u"N° CUOTAS VENCIDAS", 15),
                            (u"VALOR VENCIDO", 15),
                            (u"PROGRAMA DE MAESTRÍA", 30),
                            (u"COHORTE", 11),
                            (u"PROVINCIA", 15),
                            (u"CANTÓN", 15),
                            (u"DIRECCIÓN", 38),
                            (u"TELÉFONO FIJO", 15),
                            (u"CELULAR", 15),
                            (u"E-MAIL PERSONAL", 15),
                            (u"E-MAIL UNEMI", 15)
                        ]

                        for col_num in range(len(columnas)):
                            hojadestino.write(fila, col_num, columnas[col_num][0], fcabeceracolumna)
                            hojadestino.set_column(col_num, col_num, columnas[col_num][1])

                        numero = 0
                        for datopersona in resumenpersona:
                            fila += 1
                            numero += 1
                            hojadestino.write(fila, 0, numero, fceldageneral)
                            hojadestino.write(fila, 1, datopersona[1], fceldageneral)
                            hojadestino.write(fila, 2, datopersona[2], fceldageneral)
                            hojadestino.write(fila, 3, datopersona[3], fceldageneral)
                            hojadestino.write(fila, 4, datopersona[4], fceldamoneda)
                            hojadestino.write(fila, 5, datopersona[5], fceldageneral)
                            hojadestino.write(fila, 6, datopersona[6], fceldageneralcent)
                            hojadestino.write(fila, 7, datopersona[7], fceldageneral)
                            hojadestino.write(fila, 8, datopersona[8], fceldageneral)
                            hojadestino.write(fila, 9, datopersona[9], fceldageneral)
                            hojadestino.write(fila, 10, datopersona[10], fceldageneral)
                            hojadestino.write(fila, 11, datopersona[11], fceldageneral)
                            hojadestino.write(fila, 12, datopersona[12], fceldageneral)
                            hojadestino.write(fila, 13, datopersona[13], fceldageneral)

                        fila += 1
                        hojadestino.merge_range(fila, 0, fila, 3, "TOTAL GENERAL", fceldanegritageneral)
                        hojadestino.write(fila, 4, totalvencido, fceldamonedapie)

                    workbook.close()

                    ruta = "media/postgrado/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    print("error")
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})

            elif action == 'reporte_cartera_vencida_general_vs_cobros_rubro_version_final_background':
                try:
                    fechacorte = datetime.strptime(request.GET['fechacartera'], '%Y-%m-%d').date()
                    fechapago = datetime.strptime(request.GET['fechacobro'], '%Y-%m-%d').date()

                    # Guardar la notificación
                    notificacion = Notificacion(
                        cuerpo='Generación de reporte de excel en progreso',
                        titulo='Reporte Excel Cartera Vencida General vs Cobros - Detalle Rubros',
                        destinatario=persona,
                        url='',
                        prioridad=1,
                        app_label='SGA',
                        fecha_hora_visible=datetime.now() + timedelta(days=1),
                        tipo=2,
                        en_proceso=True
                    )
                    notificacion.save(request)

                    reporte_cartera_vencida_general_vs_cobros_rubro_version_final_background(request=request, data=data, idnotificacion=notificacion.id, fechacorte=fechacorte, fechapago=fechapago).start()

                    return JsonResponse({"result": "ok",
                                         "mensaje": u"El reporte se está generando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    msg = ex.__str__()
                    transaction.set_rollback(True)
                    print("error")
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})

            elif action == 'reporte_cartera_vencida_general_vs_cobros_rubro_version_final':
                try:
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))
                    nombrearchivo = "CARTERA_VENCIDA_GENERAL_VS_COBRO_RUBROS_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xlsx"

                    # Crea un nuevo archivo de excel y le agrega una hoja
                    workbook = xlsxwriter.Workbook(output_folder + '/' + nombrearchivo)
                    hojadestino = workbook.add_worksheet("Reporte")

                    fcabeceracolumna = workbook.add_format(FORMATOS_CELDAS_EXCEL["cabeceracolumna"])
                    fceldageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneral"])
                    fceldageneralcent = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdageneralcent"])
                    ftitulo2izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo2izq"])
                    ftitulo3izq = workbook.add_format(FORMATOS_CELDAS_EXCEL["titulo3izq"])
                    fceldafecha = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdafecha"])
                    fceldamoneda = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamoneda"])
                    fceldamonedapie = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdamonedapie"])
                    fceldanegritaizq = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritaizq"])
                    fceldanegritageneral = workbook.add_format(FORMATOS_CELDAS_EXCEL["celdanegritageneral"])

                    ruta = "media/postgrado/" + nombrearchivo

                    meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre",
                             "Octubre", "Noviembre", "Diciembre"]

                    fechacorte = datetime.strptime(request.GET['fechacartera'], '%Y-%m-%d').date()
                    fechapago = datetime.strptime(request.GET['fechacobro'], '%Y-%m-%d').date()

                    fechasigdiacorte = fechacorte + relativedelta(days=1)

                    textofechacorte = str(fechacorte.day) + "-" + meses[fechacorte.month - 1][:3].upper() + "-" + str(fechacorte.year)
                    textofechapago = str(fechapago.day) + "-" + meses[fechapago.month - 1][:3].upper() + "-" + str(fechapago.year)
                    textosigdiacorte = str(fechasigdiacorte.day) + "-" + meses[fechasigdiacorte.month - 1][:3].upper() + "-" + str(fechasigdiacorte.year)

                    hojadestino.merge_range(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', ftitulo2izq)
                    hojadestino.merge_range(1, 0, 1, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', ftitulo2izq)
                    hojadestino.merge_range(2, 0, 2, 15, 'CARTERA VENCIDA GENERAL VS COBROS - DETALLES RUBROS', ftitulo2izq)
                    hojadestino.merge_range(3, 0, 3, 15, 'FECHA DE CORTE CARTERA VENCIDA: ' + str(fechacorte) + '', ftitulo2izq)
                    hojadestino.merge_range(4, 0, 4, 15, 'FECHA DE CORTE DE COBROS: ' + str(fechapago), ftitulo2izq)
                    hojadestino.merge_range(5, 0, 5, 15, 'FECHA DE DESCARGA DEL REPORTE (' + str(datetime.now().date()) + ')', ftitulo2izq)

                    fila = 7

                    columnas = [
                        (u"N°", 3),
                        (u"PROGRAMA DE MAESTRÍA", 30),
                        (u"COHORTE", 11),
                        (u"PERIODO (INICIO-FIN)", 20),
                        (u"ESTADO DE MAESTRÍA", 15),
                        (u"PROVINCIA", 15),
                        (u"CANTÓN", 15),
                        (u"CÉDULA", 15),
                        (u"ESTUDIANTE", 38),
                        (u"N° CUOTAS VENCIDAS", 15),
                        (u"ID RUBRO", 15),
                        (u"FECHA VENCIMIENTO", 15),
                        (u"DÍAS VENCIMIENTO", 15),
                        (u"VALOR VENCIDO", 15),
                        (u"CATEGORÍA", 15),
                        (u"RANGO DÍAS", 15),
                        (u"FECHA DE PAGO", 15),
                        (u"VALOR COBRADO", 15),
                        (u"DIAS DE COBRO", 15),
                        (u"TOTAL PAGADO", 15),
                        (u"VALOR PENDIENTE", 15),
                        (u"ESTADO ESTUDIANTE", 15),
                        (u"FECHA ÚLTIMA CUOTA", 15),
                        (u"ESTADO FINANCIAMIENTO", 15)
                    ]

                    for col_num in range(len(columnas)):
                        hojadestino.write(fila, col_num, columnas[col_num][0], fcabeceracolumna)
                        hojadestino.set_column(col_num, col_num, columnas[col_num][1])

                    # cedulas = ['1309336129']

                    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]
                                                          # inscripcion__persona__cedula__in=cedulas,
                                                          # inscripcion__carrera__id__in=[173],
                                                          # nivel__periodo__id__in=[143]
                                                          ).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                                                                           'inscripcion__persona__apellido2',
                                                                                                                           'inscripcion__persona__nombres')#[:10]
                    totalmatriculas = matriculas.count()

                    print("Generación de archivo en proceso...")

                    secuencia = 0
                    registros = 0
                    totalvencido = 0
                    totalpendiente = 0
                    totalcobrocartera = 0
                    totalpagado = 0

                    programas = []

                    SUMANV = SUMAV = 0

                    resumengeneral = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'vencidoencurso': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                                      1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'vencidoencurso': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                                      2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'vencidoencurso': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                                      3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'vencidoencurso': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                                      4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'vencidoencurso': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                                      5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'vencidoencurso': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                                      }

                    for matricula in matriculas:
                        secuencia += 1

                        alumno = matricula.inscripcion.persona.nombre_completo_inverso()
                        personaalumno = matricula.inscripcion.persona
                        rubrosalumno = matricula.rubros_maestria()
                        ultimafechavence = ""

                        # Verifico si el programa y cohorte existen en la lista de resumen
                        existe = False
                        indice = j = 0

                        idprograma = matricula.inscripcion.carrera.id
                        nombreprograma = matricula.inscripcion.carrera.nombre
                        idperiodo = matricula.nivel.periodo.id
                        numerocohorte = matricula.nivel.periodo.cohorte if matricula.nivel.periodo.cohorte else 0
                        fechasperiodo = str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin)
                        estadoprograma = "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO"

                        for datoprograma in programas:
                            if datoprograma[0] == idprograma and datoprograma[1] == idperiodo:
                                # indice = j
                                existe = True
                                break

                            j += 1

                        indice = j

                        if not existe:
                            # Agrego el programa y cohorte a la lista de programas
                            resumen = {0: {'etiqueta': 'CARTERA VIGENTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': ''},
                                       1: {'etiqueta': '1-30 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'A'},
                                       2: {'etiqueta': '31-60 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'B'},
                                       3: {'etiqueta': '61-90 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'C'},
                                       4: {'etiqueta': '91-180 DÍAS', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'D'},
                                       5: {'etiqueta': '181 DÍAS EN ADELANTE', 'estudiantes': 0, 'pagado': Decimal(0), 'vencido': Decimal(0), 'cobroscartera': Decimal(0), 'pendiente': Decimal(0), 'antiguedad': 'E'}
                                       }
                            datoprograma = [idprograma, idperiodo, nombreprograma, numerocohorte, fechasperiodo, estadoprograma, resumen]
                            programas.append(datoprograma)

                        datos = matricula.rubros_maestria_vencidos_vs_pagos_detalle_version_final(fechacorte, fechapago)

                        if not matricula.retirado_programa_maestria():
                            # SIi hay rubros no vencidos
                            if datos['rubrosnovencidos']:
                                for rubro_no_vencido in datos['rubrosnovencidos']:
                                    fila += 1

                                    registros += 1

                                    codigorubro = rubro_no_vencido[0]
                                    valorpagado = rubro_no_vencido[3]
                                    valorpendiente = rubro_no_vencido[4]
                                    valorvencido = 0
                                    valorvencidoencurso = 0
                                    fechavence = rubro_no_vencido[1]
                                    diasvencidos = rubro_no_vencido[6]
                                    pagosvencidos = 1 if valorvencido > 0 or valorvencidoencurso > 0 else 0
                                    fechacobrocartera = rubro_no_vencido[7]
                                    valorcobrocartera = rubro_no_vencido[8]
                                    diascobro = rubro_no_vencido[9]

                                    categoriaantiguedad = ""

                                    programas[indice][6][0]['estudiantes'] += 1
                                    programas[indice][6][0]['pagado'] += valorpagado
                                    programas[indice][6][0]['vencido'] += valorvencido
                                    programas[indice][6][0]['cobroscartera'] += valorcobrocartera
                                    programas[indice][6][0]['pendiente'] += valorpendiente

                                    resumengeneral[0]['estudiantes'] += 1
                                    resumengeneral[0]['pagado'] += valorpagado
                                    resumengeneral[0]['vencido'] += valorvencido

                                    resumengeneral[0]['vencidoencurso'] = 0
                                    resumengeneral[0]['cobroscartera'] += valorcobrocartera
                                    resumengeneral[0]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "VIGENTE"
                                    rangodias = ""

                                    hojadestino.write(fila, 0, registros, fceldageneral)
                                    hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                    hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                    hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                                    hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                    hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                    hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                    hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                    hojadestino.write(fila, 8, alumno, fceldageneral)
                                    hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                    hojadestino.write(fila, 10, codigorubro, fceldageneral)
                                    hojadestino.write(fila, 11, fechavence, fceldafecha)
                                    hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                                    hojadestino.write(fila, 13, valorvencido, fceldamoneda)
                                    hojadestino.write(fila, 14, categoriaantiguedad, fceldageneral)
                                    hojadestino.write(fila, 15, rangodias, fceldageneral)
                                    hojadestino.write(fila, 16, fechacobrocartera, fceldafecha)
                                    hojadestino.write(fila, 17, valorcobrocartera, fceldamoneda)
                                    hojadestino.write(fila, 18, diascobro if valorcobrocartera > 0 else '', fceldageneral)
                                    hojadestino.write(fila, 19, valorpagado, fceldamoneda)
                                    hojadestino.write(fila, 20, valorpendiente, fceldamoneda)
                                    hojadestino.write(fila, 21, matricula.estado_inscripcion_maestria(), fceldageneral)

                                    if rubrosalumno:
                                        ultimafechavence = rubrosalumno.last().fechavence

                                        if matricula.tiene_refinanciamiento_deuda_posgrado():
                                            estadofinanciamiento = "REFINANCIAMIENTO"
                                        elif matricula.tiene_coactiva_posgrado():
                                            estadofinanciamiento = "COACTIVA"
                                        elif datetime.now().date() <= ultimafechavence:
                                            estadofinanciamiento = "EN EJECUCIÓN"
                                        else:
                                            estadofinanciamiento = "FINALIZADA"
                                    else:
                                        estadofinanciamiento = "NO TIENE RUBROS"

                                    hojadestino.write(fila, 22, ultimafechavence, fceldafecha)
                                    hojadestino.write(fila, 23, estadofinanciamiento, fceldageneral)

                                    totalpagado += valorpagado
                                    totalvencido += valorvencido
                                    totalpendiente += valorpendiente
                                    totalcobrocartera += valorcobrocartera

                            # SIi hay rubros no vencidos

                            # Si hay rubros vencidos: INICIO
                            if datos['rubrosvencidos']:
                                for rubro_vencido in datos['rubrosvencidos']:
                                    fila += 1
                                    registros += 1

                                    codigorubro = rubro_vencido[0]
                                    valorpagado = rubro_vencido[3]
                                    valorpendiente = rubro_vencido[4]
                                    valorvencido = rubro_vencido[5] if rubro_vencido[10] == 'NO' else 0
                                    valorvencidoencurso = rubro_vencido[5] if rubro_vencido[10] == 'SI' else 0

                                    fechavence = rubro_vencido[1]
                                    diasvencidos = rubro_vencido[6]
                                    pagosvencidos = 1 if valorvencido > 0 or valorvencidoencurso > 0 else 0
                                    fechacobrocartera = rubro_vencido[7]
                                    valorcobrocartera = rubro_vencido[8]
                                    diascobro = rubro_vencido[9]

                                    categoriaantiguedad = ""

                                    if diasvencidos <= 30:
                                        programas[indice][6][1]['estudiantes'] += 1
                                        programas[indice][6][1]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][1]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][1]['vencido'] += valorvencidoencurso

                                        programas[indice][6][1]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][1]['pendiente'] += valorpendiente

                                        resumengeneral[1]['estudiantes'] += 1
                                        resumengeneral[1]['pagado'] += valorpagado
                                        resumengeneral[1]['vencido'] += valorvencido
                                        resumengeneral[1]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[1]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[1]['pendiente'] += valorpendiente

                                        # print(rubro_vencido[10], valorvencido, valorvencidoencurso)
                                        SUMANV += valorvencido
                                        SUMAV += valorvencidoencurso
                                        # print(resumengeneral[1]['vencidoencurso'])

                                        categoriaantiguedad = "A"
                                        rangodias = "1-30"
                                    elif diasvencidos <= 60:
                                        programas[indice][6][2]['estudiantes'] += 1
                                        programas[indice][6][2]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][2]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][2]['vencido'] += valorvencidoencurso

                                        programas[indice][6][2]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][2]['pendiente'] += valorpendiente

                                        resumengeneral[2]['estudiantes'] += 1
                                        resumengeneral[2]['pagado'] += valorpagado
                                        resumengeneral[2]['vencido'] += valorvencido
                                        resumengeneral[2]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[2]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[2]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "B"
                                        rangodias = "31-60"
                                    elif diasvencidos <= 90:
                                        programas[indice][6][3]['estudiantes'] += 1
                                        programas[indice][6][3]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][3]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][3]['vencido'] += valorvencidoencurso


                                        programas[indice][6][3]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][3]['pendiente'] += valorpendiente

                                        resumengeneral[3]['estudiantes'] += 1
                                        resumengeneral[3]['pagado'] += valorpagado
                                        resumengeneral[3]['vencido'] += valorvencido
                                        resumengeneral[3]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[3]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[3]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "C"
                                        rangodias = "61-90"
                                    elif diasvencidos <= 180:
                                        programas[indice][6][4]['estudiantes'] += 1
                                        programas[indice][6][4]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][4]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][4]['vencido'] += valorvencidoencurso

                                        programas[indice][6][4]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][4]['pendiente'] += valorpendiente

                                        resumengeneral[4]['estudiantes'] += 1
                                        resumengeneral[4]['pagado'] += valorpagado
                                        resumengeneral[4]['vencido'] += valorvencido
                                        resumengeneral[4]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[4]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[4]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "D"
                                        rangodias = "91-180"
                                    else:
                                        programas[indice][6][5]['estudiantes'] += 1
                                        programas[indice][6][5]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][5]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][5]['vencido'] += valorvencidoencurso


                                        programas[indice][6][5]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][5]['pendiente'] += valorpendiente

                                        resumengeneral[5]['estudiantes'] += 1
                                        resumengeneral[5]['pagado'] += valorpagado
                                        resumengeneral[5]['vencido'] += valorvencido
                                        resumengeneral[5]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[5]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[5]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "E"
                                        rangodias = "181 DÍAS EN ADELANTE"

                                    hojadestino.write(fila, 0, registros, fceldageneral)
                                    hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                    hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                    hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                                    hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                    hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                    hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                    hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                    hojadestino.write(fila, 8, alumno, fceldageneral)
                                    hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                    hojadestino.write(fila, 10, codigorubro, fceldageneral)
                                    hojadestino.write(fila, 11, fechavence, fceldafecha)
                                    hojadestino.write(fila, 12, diasvencidos, fceldageneral)

                                    if valorvencido > 0:
                                        hojadestino.write(fila, 13, valorvencido, fceldamoneda)
                                    else:
                                        hojadestino.write(fila, 13, valorvencidoencurso, fceldamoneda)

                                    hojadestino.write(fila, 14, categoriaantiguedad, fceldageneral)
                                    hojadestino.write(fila, 15, rangodias, fceldageneral)
                                    hojadestino.write(fila, 16, fechacobrocartera, fceldafecha)
                                    hojadestino.write(fila, 17, valorcobrocartera, fceldamoneda)
                                    hojadestino.write(fila, 18, diascobro if valorcobrocartera > 0 else '', fceldageneral)
                                    hojadestino.write(fila, 19, valorpagado, fceldamoneda)
                                    hojadestino.write(fila, 20, valorpendiente, fceldamoneda)
                                    hojadestino.write(fila, 21, matricula.estado_inscripcion_maestria(), fceldageneral)

                                    if rubrosalumno:
                                        ultimafechavence = rubrosalumno.last().fechavence

                                        if matricula.tiene_refinanciamiento_deuda_posgrado():
                                            estadofinanciamiento = "REFINANCIAMIENTO"
                                        elif matricula.tiene_coactiva_posgrado():
                                            estadofinanciamiento = "COACTIVA"
                                        elif datetime.now().date() <= ultimafechavence:
                                            estadofinanciamiento = "EN EJECUCIÓN"
                                        else:
                                            estadofinanciamiento = "FINALIZADA"
                                    else:
                                        estadofinanciamiento = "NO TIENE RUBROS"

                                    hojadestino.write(fila, 22, ultimafechavence, fceldafecha)
                                    hojadestino.write(fila, 23, estadofinanciamiento, fceldageneral)

                                    totalpagado += valorpagado

                                    if valorvencido > 0:
                                        totalvencido += valorvencido
                                    else:
                                        totalvencido += valorvencidoencurso

                                    totalpendiente += valorpendiente
                                    totalcobrocartera += valorcobrocartera

                            # Si hay rubros vencidos: FIN

                            # Si hay rubros vencimiento en curso: INICIO
                            if datos['rubrosvencimientocurso']:
                                for rubro_vencido in datos['rubrosvencimientocurso']:
                                    fila += 1
                                    registros += 1

                                    codigorubro = rubro_vencido[0]
                                    valorpagado = rubro_vencido[3]
                                    valorpendiente = rubro_vencido[4]
                                    valorvencido = rubro_vencido[5] if rubro_vencido[10] == 'NO' else 0
                                    valorvencidoencurso = rubro_vencido[5] if rubro_vencido[10] == 'SI' else 0
                                    fechavence = rubro_vencido[1]
                                    diasvencidos = rubro_vencido[6]
                                    pagosvencidos = 1 if valorvencido > 0 or valorvencidoencurso > 0 else 0
                                    fechacobrocartera = rubro_vencido[7]
                                    valorcobrocartera = rubro_vencido[8]
                                    diascobro = rubro_vencido[9]

                                    categoriaantiguedad = ""

                                    if diasvencidos <= 30:
                                        programas[indice][6][1]['estudiantes'] += 1
                                        programas[indice][6][1]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][1]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][1]['vencido'] += valorvencidoencurso

                                        programas[indice][6][1]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][1]['pendiente'] += valorpendiente

                                        resumengeneral[1]['estudiantes'] += 1
                                        resumengeneral[1]['pagado'] += valorpagado
                                        resumengeneral[1]['vencido'] += valorvencido
                                        resumengeneral[1]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[1]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[1]['pendiente'] += valorpendiente

                                        # print(rubro_vencido[10], valorvencido, valorvencidoencurso)
                                        SUMANV += valorvencido
                                        SUMAV += valorvencidoencurso
                                        # print(resumengeneral[1]['vencidoencurso'])

                                        categoriaantiguedad = "A"
                                        rangodias = "1-30"
                                    elif diasvencidos <= 60:
                                        programas[indice][6][2]['estudiantes'] += 1
                                        programas[indice][6][2]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][2]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][2]['vencido'] += valorvencidoencurso

                                        programas[indice][6][2]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][2]['pendiente'] += valorpendiente

                                        resumengeneral[2]['estudiantes'] += 1
                                        resumengeneral[2]['pagado'] += valorpagado
                                        resumengeneral[2]['vencido'] += valorvencido
                                        resumengeneral[2]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[2]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[2]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "B"
                                        rangodias = "31-60"
                                    elif diasvencidos <= 90:
                                        programas[indice][6][3]['estudiantes'] += 1
                                        programas[indice][6][3]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][3]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][3]['vencido'] += valorvencidoencurso

                                        programas[indice][6][3]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][3]['pendiente'] += valorpendiente

                                        resumengeneral[3]['estudiantes'] += 1
                                        resumengeneral[3]['pagado'] += valorpagado
                                        resumengeneral[3]['vencido'] += valorvencido
                                        resumengeneral[3]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[3]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[3]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "C"
                                        rangodias = "61-90"
                                    elif diasvencidos <= 180:
                                        programas[indice][6][4]['estudiantes'] += 1
                                        programas[indice][6][4]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][4]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][4]['vencido'] += valorvencidoencurso

                                        programas[indice][6][4]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][4]['pendiente'] += valorpendiente

                                        resumengeneral[4]['estudiantes'] += 1
                                        resumengeneral[4]['pagado'] += valorpagado
                                        resumengeneral[4]['vencido'] += valorvencido
                                        resumengeneral[4]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[4]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[4]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "D"
                                        rangodias = "91-180"
                                    else:
                                        programas[indice][6][5]['estudiantes'] += 1
                                        programas[indice][6][5]['pagado'] += valorpagado

                                        if valorvencido > 0:
                                            programas[indice][6][5]['vencido'] += valorvencido
                                        else:
                                            programas[indice][6][5]['vencido'] += valorvencidoencurso

                                        programas[indice][6][5]['cobroscartera'] += valorcobrocartera
                                        programas[indice][6][5]['pendiente'] += valorpendiente

                                        resumengeneral[5]['estudiantes'] += 1
                                        resumengeneral[5]['pagado'] += valorpagado
                                        resumengeneral[5]['vencido'] += valorvencido
                                        resumengeneral[5]['vencidoencurso'] += valorvencidoencurso
                                        resumengeneral[5]['cobroscartera'] += valorcobrocartera
                                        resumengeneral[5]['pendiente'] += valorpendiente

                                        categoriaantiguedad = "E"
                                        rangodias = "181 DÍAS EN ADELANTE"

                                    hojadestino.write(fila, 0, registros, fceldageneral)
                                    hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                                    hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                                    hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                                    hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                                    hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                                    hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                                    hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                                    hojadestino.write(fila, 8, alumno, fceldageneral)
                                    hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                                    hojadestino.write(fila, 10, codigorubro, fceldageneral)
                                    hojadestino.write(fila, 11, fechavence, fceldafecha)
                                    hojadestino.write(fila, 12, diasvencidos, fceldageneral)

                                    if valorvencido > 0:
                                        hojadestino.write(fila, 13, valorvencido, fceldamoneda)
                                    else:
                                        hojadestino.write(fila, 13, valorvencidoencurso, fceldamoneda)

                                    hojadestino.write(fila, 14, categoriaantiguedad, fceldageneral)
                                    hojadestino.write(fila, 15, rangodias, fceldageneral)
                                    hojadestino.write(fila, 16, fechacobrocartera, fceldafecha)
                                    hojadestino.write(fila, 17, valorcobrocartera, fceldamoneda)
                                    hojadestino.write(fila, 18, diascobro if valorcobrocartera > 0 else '', fceldageneral)
                                    hojadestino.write(fila, 19, valorpagado, fceldamoneda)
                                    hojadestino.write(fila, 20, valorpendiente, fceldamoneda)
                                    hojadestino.write(fila, 21, matricula.estado_inscripcion_maestria(), fceldageneral)

                                    if rubrosalumno:
                                        ultimafechavence = rubrosalumno.last().fechavence

                                        if matricula.tiene_refinanciamiento_deuda_posgrado():
                                            estadofinanciamiento = "REFINANCIAMIENTO"
                                        elif matricula.tiene_coactiva_posgrado():
                                            estadofinanciamiento = "COACTIVA"
                                        elif datetime.now().date() <= ultimafechavence:
                                            estadofinanciamiento = "EN EJECUCIÓN"
                                        else:
                                            estadofinanciamiento = "FINALIZADA"
                                    else:
                                        estadofinanciamiento = "NO TIENE RUBROS"

                                    hojadestino.write(fila, 22, ultimafechavence, fceldafecha)
                                    hojadestino.write(fila, 23, estadofinanciamiento, fceldageneral)

                                    totalpagado += valorpagado

                                    if valorvencido > 0:
                                        totalvencido += valorvencido
                                    else:
                                        totalvencido += valorvencidoencurso

                                    totalpendiente += valorpendiente
                                    totalcobrocartera += valorcobrocartera

                            # Si hay rubros vencidos: FIN
                        else:
                            # RETIRADO
                            registros += 1
                            fila += 1

                            valorpagado = datos['totalpagado']
                            valorpendiente = datos['totalpendiente']
                            valorvencido = datos['totalvencido']
                            fechavence = datos['fechavence']
                            diasvencidos = datos['diasvencimiento']
                            pagosvencidos = 1 if valorvencido > 0 else 0
                            fechacobrocartera = ""
                            valorcobrocartera = 0
                            diascobro = 0

                            categoriaantiguedad = ""

                            if valorvencido > 0:
                                if diasvencidos <= 30:
                                    programas[indice][6][1]['estudiantes'] += 1
                                    programas[indice][6][1]['pagado'] += valorpagado
                                    programas[indice][6][1]['vencido'] += valorvencido
                                    programas[indice][6][1]['cobroscartera'] += valorcobrocartera
                                    programas[indice][6][1]['pendiente'] += valorpendiente

                                    resumengeneral[1]['estudiantes'] += 1
                                    resumengeneral[1]['pagado'] += valorpagado
                                    resumengeneral[1]['vencido'] += valorvencido
                                    resumengeneral[1]['vencidoencurso'] += 0
                                    resumengeneral[1]['cobroscartera'] += valorcobrocartera
                                    resumengeneral[1]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "A"
                                    rangodias = "1-30"
                                elif diasvencidos <= 60:
                                    programas[indice][6][2]['estudiantes'] += 1
                                    programas[indice][6][2]['pagado'] += valorpagado
                                    programas[indice][6][2]['vencido'] += valorvencido
                                    programas[indice][6][2]['cobroscartera'] += valorcobrocartera
                                    programas[indice][6][2]['pendiente'] += valorpendiente

                                    resumengeneral[2]['estudiantes'] += 1
                                    resumengeneral[2]['pagado'] += valorpagado
                                    resumengeneral[2]['vencido'] += valorvencido
                                    resumengeneral[2]['vencidoencurso'] += 0
                                    resumengeneral[2]['cobroscartera'] += valorcobrocartera
                                    resumengeneral[2]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "B"
                                    rangodias = "31-60"
                                elif diasvencidos <= 90:
                                    programas[indice][6][3]['estudiantes'] += 1
                                    programas[indice][6][3]['pagado'] += valorpagado
                                    programas[indice][6][3]['vencido'] += valorvencido
                                    programas[indice][6][3]['cobroscartera'] += valorcobrocartera
                                    programas[indice][6][3]['pendiente'] += valorpendiente

                                    resumengeneral[3]['estudiantes'] += 1
                                    resumengeneral[3]['pagado'] += valorpagado
                                    resumengeneral[3]['vencido'] += valorvencido
                                    resumengeneral[3]['vencidoencurso'] += 0
                                    resumengeneral[3]['cobroscartera'] += valorcobrocartera
                                    resumengeneral[3]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "C"
                                    rangodias = "61-90"
                                elif diasvencidos <= 180:
                                    programas[indice][6][4]['estudiantes'] += 1
                                    programas[indice][6][4]['pagado'] += valorpagado
                                    programas[indice][6][4]['vencido'] += valorvencido
                                    programas[indice][6][4]['cobroscartera'] += valorcobrocartera
                                    programas[indice][6][4]['pendiente'] += valorpendiente

                                    resumengeneral[4]['estudiantes'] += 1
                                    resumengeneral[4]['pagado'] += valorpagado
                                    resumengeneral[4]['vencido'] += valorvencido
                                    resumengeneral[4]['vencidoencurso'] += 0
                                    resumengeneral[4]['cobroscartera'] += valorcobrocartera
                                    resumengeneral[4]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "D"
                                    rangodias = "91-180"
                                else:
                                    programas[indice][6][5]['estudiantes'] += 1
                                    programas[indice][6][5]['pagado'] += valorpagado
                                    programas[indice][6][5]['vencido'] += valorvencido
                                    programas[indice][6][5]['cobroscartera'] += valorcobrocartera
                                    programas[indice][6][5]['pendiente'] += valorpendiente

                                    resumengeneral[5]['estudiantes'] += 1
                                    resumengeneral[5]['pagado'] += valorpagado
                                    resumengeneral[5]['vencido'] += valorvencido
                                    resumengeneral[5]['vencidoencurso'] += 0
                                    resumengeneral[5]['cobroscartera'] += valorcobrocartera
                                    resumengeneral[5]['pendiente'] += valorpendiente

                                    categoriaantiguedad = "E"
                                    rangodias = "181 DÍAS EN ADELANTE"
                            else:
                                programas[indice][6][0]['estudiantes'] += 1
                                programas[indice][6][0]['pagado'] += valorpagado
                                programas[indice][6][0]['vencido'] += valorvencido
                                programas[indice][6][0]['cobroscartera'] += valorcobrocartera
                                programas[indice][6][0]['pendiente'] += valorpendiente

                                resumengeneral[0]['estudiantes'] += 1
                                resumengeneral[0]['pagado'] += valorpagado
                                resumengeneral[0]['vencido'] += valorvencido
                                resumengeneral[0]['vencidoencurso'] += 0
                                resumengeneral[0]['cobroscartera'] += valorcobrocartera
                                resumengeneral[0]['pendiente'] += valorpendiente

                                categoriaantiguedad = "VIGENTE"
                                rangodias = ""

                            hojadestino.write(fila, 0, registros, fceldageneral)
                            hojadestino.write(fila, 1, nombreprograma, fceldageneral)
                            hojadestino.write(fila, 2, numerocohorte, fceldageneralcent)
                            hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fceldageneralcent)
                            hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fceldageneral)
                            hojadestino.write(fila, 5, personaalumno.provincia.nombre if personaalumno.provincia else '', fceldageneral)
                            hojadestino.write(fila, 6, personaalumno.canton.nombre if personaalumno.canton else '', fceldageneral)
                            hojadestino.write(fila, 7, personaalumno.identificacion(), fceldageneral)
                            hojadestino.write(fila, 8, alumno, fceldageneral)
                            hojadestino.write(fila, 9, pagosvencidos, fceldageneral)
                            hojadestino.write(fila, 10, "S/N", fceldageneral)
                            hojadestino.write(fila, 11, fechavence, fceldafecha)
                            hojadestino.write(fila, 12, diasvencidos, fceldageneral)
                            hojadestino.write(fila, 13, valorvencido, fceldamoneda)
                            hojadestino.write(fila, 14, categoriaantiguedad, fceldageneral)
                            hojadestino.write(fila, 15, rangodias, fceldageneral)
                            hojadestino.write(fila, 16, fechacobrocartera, fceldafecha)
                            hojadestino.write(fila, 17, valorcobrocartera, fceldamoneda)
                            hojadestino.write(fila, 18, diascobro if valorcobrocartera > 0 else '', fceldageneral)
                            hojadestino.write(fila, 19, valorpagado, fceldamoneda)
                            hojadestino.write(fila, 20, valorpendiente, fceldamoneda)
                            hojadestino.write(fila, 21, matricula.estado_inscripcion_maestria(), fceldageneral)

                            if rubrosalumno:
                                ultimafechavence = rubrosalumno.last().fechavence

                                if matricula.tiene_refinanciamiento_deuda_posgrado():
                                    estadofinanciamiento = "REFINANCIAMIENTO"
                                elif matricula.tiene_coactiva_posgrado():
                                    estadofinanciamiento = "COACTIVA"
                                elif datetime.now().date() <= ultimafechavence:
                                    estadofinanciamiento = "EN EJECUCIÓN"
                                else:
                                    estadofinanciamiento = "FINALIZADA"
                            else:
                                estadofinanciamiento = "NO TIENE RUBROS"

                            hojadestino.write(fila, 22, ultimafechavence, fceldafecha)
                            hojadestino.write(fila, 23, estadofinanciamiento, fceldageneral)

                            totalpagado += valorpagado
                            totalvencido += valorvencido
                            totalpendiente += valorpendiente
                            totalcobrocartera += valorcobrocartera

                        print(secuencia, " de ", totalmatriculas)

                    fila += 1
                    hojadestino.merge_range(fila, 0, fila, 12, "TOTALES", fceldanegritageneral)
                    hojadestino.write(fila, 13, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 17, totalcobrocartera, fceldamonedapie)
                    hojadestino.write(fila, 19, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 20, totalpendiente, fceldamonedapie)

                    fila += 3
                    hojadestino.merge_range(fila, 0, fila, 11, "RESUMEN DE CARTERA VENCIDA GENERAL", ftitulo3izq)

                    fila += 1

                    hojadestino.merge_range(fila, 0, fila, 1, "PERIODO DE VENCIMIENTO", fcabeceracolumna)
                    hojadestino.write(fila, 2, "NRO.ESTUDIANTES", fcabeceracolumna)
                    hojadestino.write(fila, 3, "VALOR PAGADO", fcabeceracolumna)
                    hojadestino.write(fila, 4, "VALOR CARTERA VENCIDA AL " + textofechacorte, fcabeceracolumna)
                    hojadestino.write(fila, 5, "VALOR CARTERA VENCIDA DEL " + textosigdiacorte + " AL " + textofechapago , fcabeceracolumna)
                    hojadestino.write(fila, 6, "COBROS CARTERA AL " + textofechapago, fcabeceracolumna)
                    hojadestino.write(fila, 7, "VALOR CARTERA VENCIDA AL " + textofechapago, fcabeceracolumna)
                    hojadestino.write(fila, 8, "VALOR PENDIENTE", fcabeceracolumna)
                    hojadestino.write(fila, 9, "ANTIGUEDAD", fcabeceracolumna)

                    fila += 1
                    totalvencidoresgen = totalvencidoencurso = totalsaldofinal = 0

                    for i in resumengeneral:
                        hojadestino.merge_range(fila, 0, fila, 1, resumengeneral[i]['etiqueta'], fceldageneral)
                        hojadestino.write(fila, 2, resumengeneral[i]['estudiantes'], fceldageneral)
                        hojadestino.write(fila, 3, resumengeneral[i]['pagado'], fceldamoneda)
                        hojadestino.write(fila, 4, resumengeneral[i]['vencido'], fceldamoneda)
                        hojadestino.write(fila, 5, resumengeneral[i]['vencidoencurso'], fceldamoneda)
                        hojadestino.write(fila, 6, resumengeneral[i]['cobroscartera'], fceldamoneda)

                        totalvencidoresgen += resumengeneral[i]['vencido']
                        totalvencidoencurso += resumengeneral[i]['vencidoencurso']

                        saldofinal = (resumengeneral[i]['vencido'] + resumengeneral[i]['vencidoencurso']) - resumengeneral[i]['cobroscartera']
                        totalsaldofinal += saldofinal

                        hojadestino.write(fila, 7, saldofinal, fceldamoneda)

                        hojadestino.write(fila, 8, resumengeneral[i]['pendiente'], fceldamoneda)
                        hojadestino.write(fila, 9, resumengeneral[i]['antiguedad'], fceldageneralcent)
                        fila += 1

                    hojadestino.merge_range(fila, 0, fila, 1, "TOTAL", fceldanegritageneral)
                    hojadestino.write(fila, 2, registros, fceldanegritageneral)
                    hojadestino.write(fila, 3, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 4, totalvencidoresgen, fceldamonedapie)
                    hojadestino.write(fila, 5, totalvencidoencurso, fceldamonedapie)
                    hojadestino.write(fila, 6, totalcobrocartera, fceldamonedapie)
                    hojadestino.write(fila, 7, totalsaldofinal, fceldamonedapie)
                    hojadestino.write(fila, 8, totalpendiente, fceldamonedapie)

                    fila += 3
                    hojadestino.merge_range(fila, 0, fila, 11, "RESUMEN DE CARTERA VENCIDA POR PROGRAMA DE MAESTRÍA", ftitulo3izq)

                    fila += 1
                    hojadestino.write(fila, 0, "N°", fcabeceracolumna)
                    hojadestino.write(fila, 1, "PROGRAMA", fcabeceracolumna)
                    hojadestino.write(fila, 2, "COHORTE", fcabeceracolumna)
                    hojadestino.write(fila, 3, "PERIODO (INICIO-FIN)", fcabeceracolumna)
                    hojadestino.write(fila, 4, "ESTADO DE MAESTRIA", fcabeceracolumna)
                    hojadestino.write(fila, 5, "PERIODO DE VENCIMIENTO", fcabeceracolumna)
                    hojadestino.write(fila, 6, "NRO.ESTUDIANTES", fcabeceracolumna)
                    hojadestino.write(fila, 7, "VALOR PAGADO", fcabeceracolumna)
                    hojadestino.write(fila, 8, "VALOR CARTERA VENCIDA", fcabeceracolumna)
                    hojadestino.write(fila, 9, "COBROS CARTERA A FECHA DE CORTE", fcabeceracolumna)
                    hojadestino.write(fila, 10, "VALOR PENDIENTE", fcabeceracolumna)
                    hojadestino.write(fila, 11, "ANTIGUEDAD", fcabeceracolumna)

                    # Ordeno por programa y cohorte
                    programas = sorted(programas, key=lambda programa: (programa[2], programa[3]))

                    secresumen = 0
                    for datoprograma in programas:
                        fila += 1
                        secresumen += 1
                        hojadestino.merge_range(fila, 0, fila + 5, 0, secresumen, fceldageneralcent)
                        hojadestino.merge_range(fila, 1, fila + 5, 1, datoprograma[2], fceldageneralcent)
                        hojadestino.merge_range(fila, 2, fila + 5, 2, datoprograma[3], fceldageneralcent)
                        hojadestino.merge_range(fila, 3, fila + 5, 3, datoprograma[4], fceldageneralcent)
                        hojadestino.merge_range(fila, 4, fila + 5, 4, datoprograma[5], fceldageneralcent)

                        tot_est_prog = tot_venc_prog = tot_pend_prog = tot_pag_prog = tot_cobrocart_prog = 0

                        resumen = datoprograma[6]
                        for i in resumen:
                            hojadestino.write(fila, 5, resumen[i]['etiqueta'], fceldageneral)
                            hojadestino.write(fila, 6, resumen[i]['estudiantes'], fceldageneral)
                            hojadestino.write(fila, 7, resumen[i]['pagado'], fceldamoneda)
                            hojadestino.write(fila, 8, resumen[i]['vencido'], fceldamoneda)
                            hojadestino.write(fila, 9, resumen[i]['cobroscartera'], fceldamoneda)
                            hojadestino.write(fila, 10, resumen[i]['pendiente'], fceldamoneda)
                            hojadestino.write(fila, 11, resumen[i]['antiguedad'], fceldageneralcent)

                            tot_est_prog += resumen[i]['estudiantes']
                            tot_pag_prog += resumen[i]['pagado']
                            tot_venc_prog += resumen[i]['vencido']
                            tot_pend_prog += resumen[i]['pendiente']
                            tot_cobrocart_prog += resumen[i]['cobroscartera']

                            fila += 1

                        hojadestino.merge_range(fila, 0, fila, 5, "TOTAL " + datoprograma[2] + " COHORTE " + str(datoprograma[3]), fceldanegritageneral)
                        hojadestino.write(fila, 6, tot_est_prog, fceldanegritageneral)
                        hojadestino.write(fila, 7, tot_pag_prog, fceldamonedapie)
                        hojadestino.write(fila, 8, tot_venc_prog, fceldamonedapie)
                        hojadestino.write(fila, 9, tot_cobrocart_prog, fceldamonedapie)
                        hojadestino.write(fila, 10, tot_pend_prog, fceldamonedapie)

                    fila += 1
                    hojadestino.merge_range(fila, 0, fila, 5, "TOTAL GENERAL", fceldanegritageneral)
                    hojadestino.write(fila, 6, registros, fceldanegritageneral)
                    hojadestino.write(fila, 7, totalpagado, fceldamonedapie)
                    hojadestino.write(fila, 8, totalvencido, fceldamonedapie)
                    hojadestino.write(fila, 9, totalcobrocartera, fceldamonedapie)
                    hojadestino.write(fila, 10, totalpendiente, fceldamonedapie)

                    workbook.close()

                    ruta = "media/postgrado/" + nombrearchivo
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    msg = ex.__str__()
                    print("error")
                    return JsonResponse({"result": "bad", "mensaje": u"Error al generar el reporte. [%s]" % msg})

            elif action == 'reporte_retirados_acp':
                try:
                    matriculas = Matricula.objects.filter(status=True, retiradomatricula=True, nivel__periodo__tipo__id__in=[3, 4]).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')

                    if not matriculas:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": "No existen registros de maestrantes retirados", "showSwal": "True", "swalType": "warning"})

                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
                    titulo2 = easyxf(
                        'font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalder = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    fuentenormalwrap = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: vert centre, horiz centre')
                    fuentenormalneg = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalnegrell = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')
                    fuentenormalnegpie = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; pattern: pattern solid, fore_colour gray25')

                    fuentenormalnegpieder = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25')

                    fuentenormalwrap.alignment.wrap = True
                    fuentenormalcent = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentemonedaneg = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
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

                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))

                    libdestino = xlwt.Workbook()
                    hojadestino = libdestino.add_sheet("Reporte")

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=retirados_acp' + random.randint(1, 10000).__str__() + '.xls'
                    nombre = "MAESTRANTES_RETIRADOS_ACP_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                    filename = os.path.join(output_folder, nombre)
                    ruta = "media/postgrado/" + nombre

                    hojadestino.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    hojadestino.write_merge(1, 1, 0, 15, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', titulo)
                    hojadestino.write_merge(2, 2, 0, 15, 'MAESTRANTES RETIRADOS - ACTUALIZAR COMPROMISO DE PAGO', titulo)
                    hojadestino.write_merge(3, 3, 0, 15, "FECHA DE DESCARGA DEL REPORTE (" + str(datetime.now().date()) + ")", titulo2)

                    fila = 5

                    columnas = [
                        (u"N°", 1000),
                        (u"PROGRAMA DE MAESTRÍA", 7000),
                        (u"COHORTE", 3000),
                        (u"PERIODO (INICIO-FIN)", 5500),
                        (u"ESTADO DE MAESTRÍA", 4000),
                        (u"CÉDULA", 4000),
                        (u"ESTUDIANTE", 10000),
                        (u"TOTAL GENERADO RETIRADO", 4000),
                        (u"TOTAL RUBROS EXISTENTES", 4000)
                    ]

                    for col_num in range(len(columnas)):
                        hojadestino.write(fila, col_num, columnas[col_num][0], fuentecabecera)
                        hojadestino.col(col_num).width = columnas[col_num][1]

                    totalmatriculas = matriculas.count()

                    secuencia = 0

                    for matricula in matriculas:
                        totalgeneradoretirado = matricula.total_generado_alumno_retirado()
                        totalrubros = matricula.total_generado_alumno()

                        if totalgeneradoretirado != totalrubros:
                            secuencia += 1
                            fila += 1

                            alumno = matricula.inscripcion.persona.nombre_completo_inverso()
                            personaalumno = matricula.inscripcion.persona
                            rubrosalumno = matricula.rubros_maestria()
                            nombreprograma = matricula.inscripcion.carrera.nombre
                            numerocohorte = matricula.nivel.periodo.cohorte if matricula.nivel.periodo.cohorte else 0
                            fechasperiodo = str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin)

                            hojadestino.write(fila, 0, secuencia, fuentenormalder)
                            hojadestino.write(fila, 1, nombreprograma, fuentenormal)
                            hojadestino.write(fila, 2, numerocohorte, fuentenormalcent)
                            hojadestino.write(fila, 3, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), fuentenormalcent)
                            hojadestino.write(fila, 4, "EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO", fuentenormal)
                            hojadestino.write(fila, 5, personaalumno.identificacion(), fuentenormal)
                            hojadestino.write(fila, 6, alumno, fuentenormal)
                            hojadestino.write(fila, 7, matricula.total_generado_alumno_retirado(), fuentemoneda)
                            hojadestino.write(fila, 8, matricula.total_generado_alumno(), fuentemoneda)

                    libdestino.save(filename)
                    return JsonResponse({'result': 'ok', 'archivo': ruta})
                except Exception as ex:
                    print("error")
                    pass

            elif action == 'reporte_cobranzas_general':
                try:
                    __author__ = 'Unemi'

                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 220; alignment: vert distributed, horiz left')
                    title2 = easyxf('font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')

                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalneg = easyxf('font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalder = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',num_format_str=' "$" #,##0.00')
                    fuentemonedaneg = easyxf('font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',num_format_str=' "$" #,##0.00')

                    fuenteporcentaje = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='0%')
                    fuenteporcentajeneg = easyxf('font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25', num_format_str='0%')

                    fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',num_format_str='#,##0.00')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Cobranzas')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=cobranzas_maestrias_' + random.randint(1, 10000).__str__() + '.xls'

                    anio_actual = datetime.now().year
                    mes_actual = datetime.now().month
                    nca_titulo = mes_actual * 3

                    nmeses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

                    ws.write_merge(0, 0, 0, 3 + nca_titulo, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 3 + nca_titulo, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                    ws.write_merge(2, 2, 0, 3 + nca_titulo, 'RESUMEN COBRANZAS MAESTRÍAS AÑO '+ str(anio_actual), title)

                    row_num = 5

                    #5, 6, 0, 0 FILA INICIO, FILA FIN, COLUMNA INICIO, COLUMNA FIN
                    ws.write_merge(5, 6, 0, 0, u'PERIODO', fuentecabecera)
                    ws.write_merge(5, 6, 1, 1, u'PROGRAMAS EN EJECUCIÓN', fuentecabecera)
                    ws.write_merge(5, 6, 2, 2, u'TOTAL ALUMNOS', fuentecabecera)
                    ws.write_merge(5, 6, 3, 3, u'ESTADO', fuentecabecera)

                    col_num = 4
                    row_num = 6
                    for mes in range(1, mes_actual + 1):
                        ws.write_merge(row_num - 1, row_num - 1, col_num, col_num + 2, nmeses[mes - 1].upper(), fuentecabecera)
                        ws.write(row_num, col_num, "META", fuentecabecera)
                        ws.write(row_num, col_num + 1, "RECAUDADO", fuentecabecera)
                        ws.write(row_num, col_num + 2, "% EJECUCIÓN", fuentecabecera)
                        col_num += 3

                    total_columnas = col_num

                    row_num += 1

                    periodos = Periodo.objects.values('id').filter(nivel__matricula__rubro__saldo__gt=0, nivel__matricula__rubro__fechavence__lt=datetime.now().date(), tipo__id__in=[3, 4]).distinct().order_by('id')

                    for pmaestria in periodos:
                        periodomaestria = Periodo.objects.get(pk=pmaestria['id'])

                        programas = Carrera.objects.values('id').filter(inscripcion__matricula__rubro__saldo__gt=0,
                                                                        inscripcion__matricula__rubro__fechavence__lt=datetime.now().date(),
                                                                        inscripcion__matricula__nivel__periodo__id=periodomaestria.id,
                                                                        inscripcion__matricula__nivel__periodo__tipo__id__in=[
                                                                            3, 4]).distinct().order_by('nombre')

                        for programa in programas:
                            col_num = 0

                            programamaestria = Carrera.objects.get(pk=programa['id'])

                            totalmatriculados = Matricula.objects.values('id').filter(nivel__periodo__id=periodomaestria.id, inscripcion__carrera__id=programamaestria.id).distinct().count()
                            totalcobrar_anio_anterior = Decimal(null_to_decimal(
                                Rubro.objects.filter(matricula__nivel__periodo__id=periodomaestria.id,
                                                     matricula__inscripcion__carrera__id=programamaestria.id,
                                                     fechavence__year__lt=anio_actual,
                                                     status=True
                                                     ).aggregate(
                                    valor=Sum('valortotal'))['valor'], 2)).quantize(
                                Decimal('.01'))

                            pagos_anio_anterior = Decimal(null_to_decimal(
                                Pago.objects.values_list('valortotal').filter(fecha__year__lt=anio_actual,
                                                                              pagoliquidacion__isnull=True,
                                                                              rubro__fechavence__year__lt=anio_actual,
                                                                              rubro__matricula__nivel__periodo__id=periodomaestria.id,
                                                                              rubro__matricula__inscripcion__carrera__id=programamaestria.id,
                                                                              status=True, rubro__status=True
                                                                              ).exclude(
                                    factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(
                                Decimal('.01'))

                            vencido_anterior = totalcobrar_anio_anterior - pagos_anio_anterior

                            ws.write(row_num, col_num, periodomaestria.nombre, fuentenormal)
                            ws.write(row_num, col_num + 1, programamaestria.nombre, fuentenormal)
                            ws.write(row_num, col_num + 2, totalmatriculados, fuentenormalder)
                            ws.write(row_num, col_num + 3, "ABIERTO" if periodomaestria.activo else "CERRADO", fuentenormal)

                            col_num = 4

                            for mes in range(1, mes_actual + 1):
                                valorcuotasmes = Decimal(null_to_decimal(
                                    Rubro.objects.filter(matricula__nivel__periodo__id=periodomaestria.id,
                                                         matricula__inscripcion__carrera__id=programamaestria.id,
                                                         fechavence__year=anio_actual, fechavence__month=mes,
                                                         status=True
                                                         ).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(
                                    Decimal('.01'))

                                pagadomes = Decimal(null_to_decimal(
                                    Pago.objects.values_list('valortotal').filter(fecha__year=anio_actual, fecha__month=mes,
                                                                                  pagoliquidacion__isnull=True,
                                                                                  rubro__matricula__nivel__periodo__id=periodomaestria.id,
                                                                                  rubro__matricula__inscripcion__carrera__id=programamaestria.id,
                                                                                  status=True,
                                                                                  rubro__status=True).exclude(
                                        factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'],
                                    2)).quantize(Decimal('.01'))


                                valorcobrarmes = vencido_anterior + valorcuotasmes
                                vencidomes = valorcobrarmes - pagadomes
                                # porcentaje = round((pagadomes / valorcobrarmes) * 100, 0) if valorcobrarmes > 0 else 0
                                porcentaje = pagadomes / valorcobrarmes if valorcobrarmes > 0 else 0

                                ws.write(row_num, col_num, valorcobrarmes, fuentemoneda)
                                ws.write(row_num, col_num + 1, pagadomes, fuentemoneda)
                                ws.write(row_num, col_num + 2, porcentaje, fuenteporcentaje)

                                vencido_anterior = vencidomes

                                col_num += 3

                            row_num += 1

                    cascii = 69
                    letcol = ''
                    x = 1
                    for ncol in range(4, col_num):
                        if cascii > 90:
                            cascii = 65
                            letcol = 'A'

                        celda = letcol + chr(cascii)

                        ri = celda + "8"
                        rf = celda + str(row_num)

                        if x % 3 != 0:
                            formula = 'SUM(' + ri + ":" + rf + ')'
                            ws.write(row_num, ncol, xlwt.Formula(formula), fuentemonedaneg)
                        else:
                            formula = 'AVERAGE(' + ri + ":" + rf + ')'
                            ws.write(row_num, ncol, xlwt.Formula(formula), fuenteporcentajeneg)

                        cascii += 1
                        x += 1

                    # ws.write(row_num, 4, xlwt.Formula('SUM(E8:E'+str(row_num)+')'), fuentemonedaneg)

                    row_num += 2
                    for col_num in range(total_columnas):
                        if col_num <= 1:
                            ws.col(col_num).width = 9000
                        elif col_num <= 3:
                            ws.col(col_num).width = 4000
                        else:
                            ws.col(col_num).width = 4000

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadomaestrantes':
                try:
                    __author__ = 'Unemi'

                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
                    title2 = easyxf(
                        'font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')

                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalneg = easyxf(
                        'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalder = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str=' "$" #,##0.00')
                    fuentemonedaneg = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                        num_format_str=' "$" #,##0.00')

                    fuentenumero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right', num_format_str='#,##0.00')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Listado')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_maestrantes_' + random.randint(1,10000).__str__() + '.xls'

                    carreraid = int(request.GET['carr'])
                    periodoid = int(request.GET['peri'])

                    carrera = Carrera.objects.get(pk=carreraid)
                    periodo = Periodo.objects.get(pk=periodoid)

                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                    ws.write_merge(2, 2, 0, 8, 'DEUDAS DE ESTUDIANTES', title)
                    ws.write_merge(3, 3, 0, 8, carrera.nombre + " - " + periodo.nombre, title2)

                    row_num = 5

                    columns = [
                        (u"N°", 700),
                        (u"ESTUDIANTE", 8300),
                        (u"TOTAL GENERADO", 3500),
                        (u"TOTAL PAGADO", 3500),
                        (u"TOTAL VENCIDO", 3500),
                        (u"TOTAL PENDIENTE", 3500),
                        (u"TOTAL RUBROS ADICIONALES", 3500),
                        (u"FECHA ÚLTIMA CUOTA", 3500),
                        (u"COMP.VENC.", 2500)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'

                    secuencia = 0
                    totalgenerado = Decimal(0)
                    totalpagado = Decimal(0)
                    totalvencido = Decimal(0)
                    totalpendiente = Decimal(0)
                    totaladicional = Decimal(0)
                    matriculas = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                    for lista in matriculas:
                        row_num += 1
                        secuencia += 1

                        alumno = lista.inscripcion.persona.apellido1 + ' ' + lista.inscripcion.persona.apellido2 + ' ' + lista.inscripcion.persona.nombres

                        valorpagado = lista.total_pagado_alumno_rubro_maestria()
                        valoradicionales = lista.total_rubro_adicional_alumno()

                        if not lista.retirado_programa_maestria():
                            valorgenerado = lista.total_generado_alumno_solo_rubros_maestria()
                            valorvencido = lista.vencido_a_la_fechamatricula_rubro_maestria()
                            valorpendiente = lista.total_saldo_rubrosinanular_rubro_maestria()
                        else:
                            valorgenerado = lista.total_generado_alumno_retirado()
                            valorvencido = lista.total_saldo_alumno_retirado()
                            valorpendiente = valorvencido

                        ws.write(row_num, 0, secuencia, fuentenormalder)
                        ws.write(row_num, 1, alumno, fuentenormal)
                        ws.write(row_num, 2, valorgenerado,  fuentemoneda)
                        ws.write(row_num, 3, valorpagado, fuentemoneda)
                        ws.write(row_num, 4, valorvencido, fuentemoneda)
                        ws.write(row_num, 5, valorpendiente, fuentemoneda)
                        ws.write(row_num, 6, valoradicionales, fuentemoneda)

                        if lista.rubro_set.filter(status=True).exists():
                            ultimacuota = lista.rubro_set.filter(status=True).order_by('-fechavence')[0]
                            if valorpendiente > 0:
                                vencido = "SI" if datetime.now().date() > ultimacuota.fechavence else "NO"
                            else:
                                vencido = "NO"
                            ws.write(row_num, 7, ultimacuota.fechavence, fuentefecha)
                            ws.write(row_num, 8, vencido, fuentenormal)
                        else:
                            ws.write(row_num, 7, "", fuentenormal)
                            ws.write(row_num, 8, "", fuentenormal)

                        totalgenerado += Decimal(valorgenerado)
                        totalpagado += Decimal(valorpagado)
                        totalvencido += Decimal(valorvencido)
                        totalpendiente += Decimal(valorpendiente)
                        totaladicional += Decimal(valoradicionales)

                    row_num += 1
                    ws.write_merge(row_num, row_num, 0, 1, "TOTALES", fuentenormalneg)
                    ws.write(row_num, 2, totalgenerado, fuentemonedaneg)
                    ws.write(row_num, 3, totalpagado, fuentemonedaneg)
                    ws.write(row_num, 4, totalvencido, fuentemonedaneg)
                    ws.write(row_num, 5, totalpendiente, fuentemonedaneg)
                    ws.write(row_num, 6, totaladicional, fuentemonedaneg)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'reporte_general':
                try:
                    __author__ = 'Unemi'
                    output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'postgrado'))
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    style1 = easyxf(num_format_str='DD/mm/YYYY')
                    # style2 = easyxf(num_format_str='HH:mm')
                    style2 = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentecabecerader = easyxf(
                        'font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    fuentenormalder = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    title3 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre; borders: top thin')

                    #fuentenormal = easyxf(
                    #    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')

                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')

                    fuentemonedaneg = easyxf(
                        'font: name Verdana, bold on, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                        num_format_str=' "$" #,##0.00')

                    fuentenumero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')

                    wb = Workbook(encoding='utf-8')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=presupuesto_general_' + random.randint(1,
                                                                                                                   10000).__str__() + '.xls'
                    # nombre = "PROYECCIONANULA_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
                    # filename = os.path.join(output_folder, nombre)
                    # ruta = "media/postgrado/" + nombre
                    ws = wb.add_sheet('TOTAL_GENERAL')
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', title2)
                    ws.write_merge(2, 2, 0, 8, 'PROYECCION DEL PRESUPUESTO GENERAL ', title2)
                    ws.write_merge(4, 4, 0, 1, u'INGRESOS', fuentecabecera)
                    ws.write_merge(5, 5, 0, 0, u'PERIODO', fuentecabecera)
                    ws.col(0).width = 10000
                    ws.write_merge(5, 5, 1, 1, u'PROGRAMAS EN EJECUCIÓN', fuentecabecera)
                    ws.col(1).width = 10000
                    row_num = 6

                    valor_total = 0
                    ingreso_neto_total = 0
                    valor_pagado_total = 0
                    nnumfilas = 2

                    listadoperiodos = Periodo.objects.filter(tipo__id__in=[3, 4], status=True).distinct().order_by('id')


                    # listadoanios = Pago.objects.dates('factura__fecha', 'year').filter(
                    #     (Q(factura__valida=True) | Q(factura__isnull=False)),
                    #     rubro__matricula__nivel__periodo_id__in=listadoperiodos.values_list('id'), status=True,
                    #     rubro__status=True)

                    listadoanios = Rubro.objects.dates('fechavence','year').filter(matricula__nivel__periodo_id__in=listadoperiodos.values_list('id'), status=True).distinct()

                    for lisfilas in listadoanios:
                        ws.write_merge(4, 4, nnumfilas, nnumfilas + 1, str(lisfilas.strftime('%Y')), fuentecabecera)
                        ws.write_merge(5, 5, nnumfilas, nnumfilas, u'TOTAL PROYECTADO', fuentecabecera)
                        ws.write_merge(5, 5, nnumfilas + 1, nnumfilas + 1, u'TOTAL PAGADO', fuentecabecera)
                        ws.col(nnumfilas).width = 5000
                        ws.col(nnumfilas+1).width = 5000
                        nnumfilas += 2
                    ws.write_merge(4, 4, nnumfilas, nnumfilas + 5, u'TOTALES GENERALES', fuentecabecera)
                    ws.write_merge(5, 5, nnumfilas, nnumfilas, u'PROYECTADO', fuentecabecera)
                    ws.col(nnumfilas).width = 5000

                    ws.write_merge(5, 5, nnumfilas+1, nnumfilas+1, u'RETIRADOS', fuentecabecera)
                    ws.col(nnumfilas + 1).width = 5000


                    ws.write_merge(5, 5, nnumfilas+2, nnumfilas+2, u'NETO PROYECTADO', fuentecabecera)
                    ws.col(nnumfilas + 2).width = 5000

                    ws.write_merge(5, 5, nnumfilas + 3, nnumfilas + 3, u'PAGADO', fuentecabecera)
                    ws.col(nnumfilas  + 3).width = 5000
                    ws.write_merge(5, 5, nnumfilas + 4, nnumfilas + 4, u'VENCIDO', fuentecabecera)
                    ws.col(nnumfilas + 4).width = 5000
                    ws.write_merge(5, 5, nnumfilas + 5, nnumfilas + 5, u'PENDIENTE', fuentecabecera)
                    ws.col(nnumfilas + 5).width = 5000

                    matriz1 = []
                    matriz2 = []
                    for p in listadoperiodos:
                        for carrera in Carrera.objects.filter(inscripcion__matricula__nivel__periodo=p,
                                                              inscripcion__matricula__nivel__periodo__tipo__id__in=[3,4]).distinct().order_by('nombre'):
                            ws.write_merge(row_num, row_num, 0, 0, p.nombre, fuentenormal)
                            ws.write_merge(row_num, row_num, 1, 1, carrera.nombre, fuentenormal)
                            nnumfilas = 2

                            sumatotalproyectado = 0
                            sumatotalpagado = 0
                            sumatotalvencido = 0

                            pagos = Pago.objects.filter(pagoliquidacion__isnull=True,
                                                        rubro__matricula__nivel__periodo=p,
                                                        rubro__matricula__inscripcion__carrera=carrera,
                                                        status=True,
                                                        rubro__status=True
                                                        ).exclude(factura__valida=False).order_by('fecha')

                            pagos = pagos.annotate(anio=ExtractYear('fecha')).values_list('anio').annotate(tpagado=Sum('valortotal'))

                            for lisfilas in listadoanios:
                                # Total generado rubros
                                totalproyectado = Decimal(null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                                                                                               matricula__inscripcion__carrera=carrera,
                                                                                               status=True,
                                                                                               fechavence__year=str(lisfilas.strftime('%Y'))).aggregate(valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))
                                # Total anulado rubros
                                totalanulado = Decimal(null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                                           rubro__matricula__inscripcion__carrera=carrera,
                                                                                           status=True,
                                                                                           rubro__status=True,
                                                                                           rubro__fechavence__year=str(lisfilas.strftime('%Y')),
                                                                                           factura__valida=False,
                                                                                           factura__status=True).aggregate(valor=Sum('valortotal'))['valor'],2)).quantize(Decimal('.01'))

                                # Total liquidado rubros
                                totalliquidado = Decimal(null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                                             rubro__matricula__inscripcion__carrera=carrera,
                                                                                             status=True,
                                                                                             rubro__status=True,
                                                                                             rubro__fechavence__year=str(lisfilas.strftime('%Y')),
                                                                                             pagoliquidacion__isnull=False,
                                                                                             pagoliquidacion__status=True).aggregate(valor=Sum('valortotal'))['valor'],2)).quantize(Decimal('.01'))

                                totalpagado = 0

                                aniofila = 0

                                for rp in pagos:
                                    if rp[0] == int(str(lisfilas.strftime('%Y'))):
                                        totalpagado += Decimal(rp[1])
                                        aniofila = rp[0]
                                    elif aniofila != 0 and aniofila != rp[0]:
                                        break


                                # Total vencido rubros
                                totalvencido = Decimal(null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                                                                                            matricula__inscripcion__carrera=carrera,
                                                                                            matricula__retiradomatricula=False,
                                                                                            status=True,
                                                                                            fechavence__year=str(lisfilas.strftime('%Y')),
                                                                                            fechavence__lt=datetime.now().date()).aggregate(valor=Sum('saldo'))['valor'], 2)).quantize(Decimal('.01'))


                                totalproyectado = totalproyectado - (totalanulado + totalliquidado)


                                ws.write_merge(row_num, row_num, nnumfilas, nnumfilas, totalproyectado, fuentemoneda)
                                ws.write_merge(row_num, row_num, nnumfilas + 1, nnumfilas + 1, totalpagado, fuentemoneda)

                                matriz1.append([nnumfilas, totalpagado])
                                matriz2.append([nnumfilas + 1, totalproyectado])
                                sumatotalpagado += totalpagado
                                sumatotalproyectado += totalproyectado
                                sumatotalvencido += totalvencido

                                nnumfilas += 2


                            # Total generado rubros de no retirados
                            totalproyectadonoret = Decimal(
                                null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=p,
                                                                     matricula__inscripcion__carrera=carrera,

                                                                     matricula__retiradomatricula=False,

                                                                     status=True,
                                                                     ).aggregate(
                                    valor=Sum('valor'))['valor'], 2)).quantize(Decimal('.01'))

                            # Total anulado rubros de no retirados
                            totalanuladonoret = Decimal(
                                null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                    rubro__matricula__inscripcion__carrera=carrera,

                                                                    rubro__matricula__retiradomatricula=False,

                                                                    status=True,
                                                                    rubro__status=True,
                                                                    factura__valida=False,
                                                                    factura__status=True).aggregate(
                                    valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                            # Total liquidado rubros de no retirados
                            totalliquidadonoret = Decimal(
                                null_to_decimal(Pago.objects.filter(rubro__matricula__nivel__periodo=p,
                                                                    rubro__matricula__inscripcion__carrera=carrera,

                                                                    rubro__matricula__retiradomatricula=False,

                                                                    status=True,
                                                                    rubro__status=True,
                                                                    pagoliquidacion__isnull=False,
                                                                    pagoliquidacion__status=True).aggregate(
                                    valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                            # Total generado alumnos retirados
                            totalproyectadoretirados = 0
                            totalsaldoretirados = 0

                            retirados = Matricula.objects.filter(nivel__periodo=p,
                                                                 inscripcion__carrera=carrera,
                                                                 retiradomatricula=True).distinct().order_by(
                                'inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                            if retirados:
                                for ar in retirados:

                                    montoretirado = ar.total_generado_alumno_retirado()
                                    montosaldo = ar.total_saldo_alumno_retirado()
                                    totalproyectadoretirados += montoretirado
                                    totalsaldoretirados += montosaldo


                            sumatotalvencido += totalsaldoretirados
                            sumatotalnetoproyectado = (totalproyectadonoret - (totalliquidadonoret + totalanuladonoret)) + totalproyectadoretirados


                            ws.write_merge(row_num, row_num, nnumfilas, nnumfilas, sumatotalproyectado,
                                           fuentemonedaneg)

                            ws.write_merge(row_num, row_num, nnumfilas+1, nnumfilas+1, (sumatotalproyectado - sumatotalnetoproyectado),
                                           fuentemonedaneg)

                            ws.write_merge(row_num, row_num, nnumfilas+2, nnumfilas+2, sumatotalnetoproyectado,
                                           fuentemonedaneg)

                            ws.write_merge(row_num, row_num, nnumfilas + 3, nnumfilas + 3, sumatotalpagado,
                                           fuentemonedaneg)
                            ws.write_merge(row_num, row_num, nnumfilas + 4, nnumfilas + 4, sumatotalvencido,
                                           fuentemonedaneg)

                            # IMSM
                            ###sumatotalpendiente = sumatotalproyectado - sumatotalpagado
                            sumatotalpendiente = sumatotalnetoproyectado - sumatotalpagado
                            ws.write_merge(row_num, row_num, nnumfilas + 5, nnumfilas + 5, sumatotalpendiente, fuentemonedaneg)
                            # IMSM

                            row_num += 1

                    ws.write_merge(row_num, row_num, 0, 1, u'TOTAL', fuentecabecera)
                    ws.write_merge(row_num + 1, row_num + 1, 0, 1, u'NO ADMITIDOS', fuentecabecera)
                    ws.write_merge(row_num + 2, row_num + 2, 0, 1, u'TOTAL DE INGRESOS', fuentecabecera)
                    nnumfilas = 2
                    codigo_rubro = TipoOtroRubro.objects.values_list('id', flat=True).filter(tiporubro=1, status=True)
                    for lisfilas in listadoanios:
                        valornoadmitidos = 0
                        valornoadmitidos = Decimal(null_to_decimal(Rubro.objects.filter(pago__factura__fecha__year=str(lisfilas.strftime('%Y')), pago__factura__valida=True, status=True, matricula__isnull=True, tipo__in=codigo_rubro).aggregate(valor=Sum('pago__subtotal0'))['valor'], 2)).quantize(Decimal('.01'))
                        sumafilas = 0
                        sumafilas2 = 0
                        for lismatriz in matriz1:
                            if lismatriz[0] == nnumfilas:
                                sumafilas += lismatriz[1]
                        for lismatriz2 in matriz2:
                            if lismatriz2[0] == nnumfilas + 1:
                                sumafilas2 += lismatriz2[1]
                        ws.write_merge(row_num, row_num, nnumfilas, nnumfilas, sumafilas2, fuentemonedaneg)
                        ws.write_merge(row_num, row_num, nnumfilas + 1, nnumfilas + 1, sumafilas, fuentemonedaneg)
                        ws.write_merge(row_num + 1, row_num + 1, nnumfilas + 1, nnumfilas + 1, valornoadmitidos, fuentemonedaneg)
                        ws.write_merge(row_num + 2, row_num + 2, nnumfilas + 1, nnumfilas + 1, sumafilas + valornoadmitidos, fuentemonedaneg)
                        nnumfilas += 2
                    # ws.write(row_num, 2, Formula("SUM(C2:C" + str(row_num) + ")"), font_style)
                    wb.save(response)
                    return response
                    # return JsonResponse({'result': 'ok'})

                except Exception as ex:
                    print(ex)
                    pass

            elif action == 'reporte':
                try:
                    DESCUENTA_MORA = variable_valor('DESCUENTA_MORA')
                    DESCUENTA_BECA = variable_valor('DESCUENTA_BECA')
                    DESCUENTA_RETIRADO = variable_valor('DESCUENTA_RETIRADO')
                    periodoid = int(request.GET['periodo'])
                    carreraid = int(request.GET['carrera'])
                    carrera = Carrera.objects.get(pk=carreraid)
                    periodo = Periodo.objects.get(pk=periodoid)
                    inscripciones = Inscripcion.objects.filter(status=True, matricula__nivel__periodo__id=periodoid, carrera__id=carreraid)

                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    title2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    style1 = easyxf(num_format_str='DD/mm/YYYY')
                    # style2 = easyxf(num_format_str='HH:mm')
                    style2 = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz centre')
                    stylel = easyxf('borders: left thin, right thin, top thin, bottom thin; alignment: horiz left')
                    styler = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    fuentecabecera = easyxf('font: name Times New Roman, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Times New Roman, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    title3 = easyxf('font: name Times New Roman, color-index black, bold on , height 200; alignment: horiz centre; borders: top thin')
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('INGRESOS')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=presupuesto_general_' + random.randint(1,10000).__str__() + '.xls'
                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE INVESTIGACIÓN Y POSGRADO', title2)
                    ws.write_merge(2, 2, 0, 8, carrera.nombre, title2)
                    ws.write_merge(3, 3, 0, 8, periodo.nombre, title2)

                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')

                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')

                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')

                    fuentemonedaneg = easyxf(
                        'font: name Verdana, bold on, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
                        num_format_str=' "$" #,##0.00')

                    ws.write_merge(4, 5, 0, 0, u'N', fuentecabecera)
                    ws.write_merge(4, 5, 1, 1, u'NÓMINA', fuentecabecera)
                    ws.write_merge(4, 5, 2, 2, u'CÉDULA', fuentecabecera)
                    ws.write_merge(4, 5, 3, 3, u'PROCEDENCIA', fuentecabecera)
                    ws.write_merge(4, 5, 4, 4, u'NUMEROS TELEFÓNICOS', fuentecabecera)
                    ws.write_merge(4, 5, 5, 5, u'CORREO ELECTRÓNICO ', fuentecabecera)
                    ws.write_merge(4, 5, 6, 6, u'# CUOTAS', fuentecabecera)
                    ws.write_merge(4, 5, 7, 7, u'CUOTAS PAGADAS', fuentecabecera)
                    ws.write_merge(4, 5, 8, 8, u'VALOR MAESTRIA', fuentecabecera)

                    ws.write_merge(4, 5, 9, 9, u'VALOR RETIRO', fuentecabecera)
                    ws.write_merge(4, 5, 10, 10, u'VALOR MAESTRIA NETO ', fuentecabecera)


                    pagos = Pago.objects.filter(rubro__matricula__inscripcion__in=inscripciones, status=True, rubro__tipocuota=3)
                    rubros = Rubro.objects.filter(matricula__inscripcion__in=inscripciones, status=True)
                    # if pagos:
                    if rubros:
                        fechamenorrubro = rubros.order_by('fechavence')[0].fechavence
                        fechamayorrubro = rubros.order_by('-fechavence')[0].fechavence

                        fechamenorpago = pagos.order_by('fecha')[0].fecha
                        fechamayorpago = pagos.order_by('-fecha')[0].fecha

                        if fechamenorrubro < fechamenorpago:
                            fechamenor = fechamenorrubro
                        else:
                            fechamenor = fechamenorpago

                        if fechamayorrubro > fechamayorpago:
                            fechamayor = fechamayorrubro
                        else:
                            fechamayor = fechamayorpago

                        aniomenor = fechamenor.year
                        mesmenor = fechamenor.month
                        aniomayor = fechamayor.year
                        mesmayor = fechamayor.month
                        rangomes = 12 - mesmenor
                        rangoanio = aniomayor - aniomenor

                        fila = 9

                        fila = 11
                        # proyeccion
                        a1 = 0
                        while aniomenor <= aniomayor:
                            ws.write_merge(5, 5, fila, fila, str(aniomenor), fuentecabecera)
                            fila += 1
                            aniomenor += 1
                            a1 += 1
                        if a1 > 0:
                            a1 -= 1

                        ###ws.write_merge(4, 4, 9, 9+a1, u"PROYECCIONES", fuentecabecera)

                        ws.write_merge(4, 4, 11, 11+a1, u"PROYECCIONES", fuentecabecera)


                        aniomenor = fechamenor.year
                        aniomayor = fechamayor.year
                        while aniomenor <= aniomayor:
                            filaanio = fila
                            mesdesde = 12 - rangomes
                            ws.write_merge(5, 5, fila, fila, u"ADMISIÓN", fuentecabecera)
                            fila += 1
                            ws.write_merge(5, 5, fila, fila, u"MATRICULA", fuentecabecera)
                            fila += 1
                            a = 0
                            while mesdesde <= 12:
                                a += 1
                                ws.write_merge(5, 5, fila, fila, u"CUOTA MES "+str(mesdesde), fuentecabecera)
                                if mesdesde == mesmayor and aniomenor == aniomayor:
                                    mesdesde = 13
                                mesdesde += 1
                                fila += 1
                                rangomes = 11
                                # fila  += 1
                            ws.write_merge(4, 4, filaanio, filaanio + a + 1, str(aniomenor), fuentecabecera)
                            ws.write_merge(4, 5, fila, fila, u"TOTAL DE INGRESOS "+str(aniomenor), fuentecabecera)
                            fila += 1
                            aniomenor += 1
                        ws.write_merge(4, 5, fila, fila, u"TOTAL DE INGRESOS", fuentecabecera)
                        fila += 1
                        ws.write_merge(4, 5, fila, fila, u'SALDO POR PAGAR', fuentecabecera)
                        columns = [
                            (u"", 2000),
                            (u"", 7500),
                            (u"", 4000),
                            (u"", 4000),
                            (u"", 4000),
                            (u"", 4000),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                        ]
                        row_num = 6
                        n = 1
                        for r in inscripciones:
                            matricula = r.matricula_periodo(periodo)
                            campo1 = str(n)
                            campo2 = r.persona.nombre_completo_inverso()
                            campo3 = r.persona.cedula
                            campo4 = r.persona.canton.nombre
                            campo5 = r.persona.telefonos()
                            campo6 = r.persona.emails()
                            campo7 = ""
                            campo8 = ""
                            campo11 = ""
                            if matricula:
                                # Total generado rubros
                                rubro = Rubro.objects.filter(matricula=matricula, status=True).aggregate(totalrubros=Count('valor'), sumarubros=Sum('valor'))
                                totrubgen = rubro['totalrubros'] if rubro['totalrubros'] else 0
                                sumrubgen = Decimal(rubro['sumarubros']).quantize(Decimal('.01')) if rubro['sumarubros'] else Decimal(0)

                                # Total anulado rubros
                                rubro = Pago.objects.filter(rubro__matricula=matricula, status=True, rubro__status=True, factura__valida=False, factura__status=True).aggregate(totalrubros=Count('valortotal'), sumarubros=Sum('valortotal'))
                                totrubanu = rubro['totalrubros'] if rubro['totalrubros'] else 0
                                sumrubanu = Decimal(rubro['sumarubros']).quantize(Decimal('.01')) if rubro['sumarubros'] else Decimal(0)

                                # Total liquidado rubros
                                rubro = Pago.objects.filter(rubro__matricula=matricula, status=True, rubro__status=True, pagoliquidacion__isnull=False, pagoliquidacion__status=True).aggregate(totalrubros=Count('valortotal'), sumarubros=Sum('valortotal'))
                                totrubliq = rubro['totalrubros'] if rubro['totalrubros'] else 0
                                sumrubliq = Decimal(rubro['sumarubros']).quantize(Decimal('.01')) if rubro['sumarubros'] else Decimal(0)

                                totalrubrogenerado = totrubgen - (totrubanu + totrubliq)
                                sumarubrogenerado = sumrubgen - (sumrubanu + sumrubliq)

                                trn = totalrubrogenerado

                                # Total pagos
                                pagos = Pago.objects.values_list('valortotal').filter(pagoliquidacion__isnull=True, rubro__matricula=matricula, status=True, rubro__status=True).exclude(factura__valida=False).aggregate(valor=Count('valortotal'))['valor']

                                totalrubrospagados = pagos

                                montoretiroalumno = Decimal(0)
                                netoproyectado = sumarubrogenerado

                                if matricula.retiradomatricula:
                                    netoproyectado = matricula.total_generado_alumno_retirado()
                                    montoretiroalumno = sumarubrogenerado - netoproyectado


                            ws.write(row_num, 0, campo1, style2)
                            ws.write(row_num, 1, campo2, fuentenormal)
                            ws.write(row_num, 2, campo3, fuentenormal)
                            ws.write(row_num, 3, campo4, fuentenormal)
                            ws.write(row_num, 4, campo5, fuentenormal)
                            ws.write(row_num, 5, campo6, fuentenormal)
                            ws.write(row_num, 6, trn, styler)
                            ws.write(row_num, 7, totalrubrospagados, styler)


                            ws.write(row_num, 9, montoretiroalumno, fuentemoneda)
                            ws.write(row_num, 10, netoproyectado, fuentemonedaneg)

                            aniomenor = fechamenor.year
                            mesmenor = fechamenor.month
                            aniomayor = fechamayor.year
                            mesmayor = fechamayor.month
                            rangomes = 12 - mesmenor
                            rangoanio = aniomayor - aniomenor


                            fila = 9

                            fila = 11
                            # proyeccion
                            while aniomenor <= aniomayor:
                                # Total rubros generados
                                rubroa = Rubro.objects.filter(matricula=matricula, status=True, fechavence__year=aniomenor).aggregate(totalrubros=Count('valor'), sumarubros=Sum('valor'))
                                sumrubgena = Decimal(rubroa['sumarubros']).quantize(Decimal('.01')) if rubroa['sumarubros'] else Decimal(0)

                                # Total rubros anulados
                                rubroa = Pago.objects.filter(rubro__matricula=matricula, rubro__fechavence__year=aniomenor, status=True, rubro__status=True, factura__valida=False, factura__status=True).aggregate(totalrubros=Count('valortotal'), sumarubros=Sum('valortotal'))
                                sumrubanua = Decimal(rubroa['sumarubros']).quantize(Decimal('.01')) if rubroa['sumarubros'] else Decimal(0)

                                # Total rubros liquidados
                                rubroa = Pago.objects.filter(rubro__matricula=matricula, rubro__fechavence__year=aniomenor, status=True, rubro__status=True, pagoliquidacion__isnull=False, pagoliquidacion__status=True).aggregate(totalrubros=Count('valortotal'), sumarubros=Sum('valortotal'))
                                sumrubliqa = Decimal(rubroa['sumarubros']).quantize(Decimal('.01')) if rubroa['sumarubros'] else Decimal(0)

                                sumarubrogeneradoa = sumrubgena - (sumrubanua + sumrubliqa)

                                ws.write_merge(row_num, row_num, fila, fila, sumarubrogeneradoa, fuentemoneda)
                                fila += 1
                                aniomenor += 1
                            aniomenor = fechamenor.year
                            aniomayor = fechamayor.year
                            valor_total_anio = Decimal(0).quantize(Decimal('.01'))


                            while aniomenor <= aniomayor:
                                mesdesde = 12 - rangomes
                                valor_total_mes = Decimal(0).quantize(Decimal('.01'))

                                campo9 = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(rubro__matricula=matricula, rubro__status=True, status=True, fecha__year=aniomenor, rubro__tipocuota=1).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                                campo10 = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(rubro__matricula=matricula, rubro__status=True, status=True, fecha__year=aniomenor, rubro__tipocuota=2).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))

                                ws.write_merge(row_num, row_num, fila, fila, campo9, fuentemoneda)
                                valor_total_mes += campo9
                                fila += 1
                                ws.write_merge(row_num, row_num, fila, fila, campo10, fuentemoneda)
                                valor_total_mes += campo10
                                fila += 1


                                while mesdesde <= 12:
                                    rubros = r.persona.rubro_set.filter(status=True, matricula=matricula)

                                    # Pagos
                                    pagosa = Decimal(null_to_decimal(Pago.objects.values_list('valortotal').filter(pagoliquidacion__isnull=True, rubro__matricula=matricula, status=True, rubro__status=True, rubro__id__in=rubros, fecha__year=aniomenor, fecha__month=mesdesde, rubro__tipocuota=3).exclude(factura__valida=False).aggregate(valor=Sum('valortotal'))['valor'],2)).quantize(Decimal('.01'))

                                    totalrubrospagadosa = pagosa
                                    valor = totalrubrospagadosa
                                    valor_total_mes += totalrubrospagadosa

                                    ws.write_merge(row_num, row_num, fila, fila, valor if valor > 0.00 else "", fuentemoneda)
                                    if mesdesde == mesmayor and aniomenor == aniomayor:
                                        mesdesde = 13
                                    mesdesde += 1
                                    fila += 1
                                    rangomes = 11


                                valor_total_anio += valor_total_mes
                                ws.write_merge(row_num, row_num, fila, fila, valor_total_mes, fuentemoneda)
                                fila += 1
                                aniomenor += 1
                            ws.write_merge(row_num, row_num, fila, fila, valor_total_anio, fuentemoneda)
                            fila += 1

                            ###ws.write_merge(row_num, row_num, fila, fila, sumarubrogenerado-Decimal(valor_total_anio), fuentemoneda)

                            ws.write_merge(row_num, row_num, fila, fila, netoproyectado-(Decimal(valor_total_anio)), fuentemonedaneg)

                            ws.write(row_num, 8, sumarubrogenerado, fuentemoneda)

                            row_num += 1
                            n += 1


                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style2)
                            ws.col(col_num).width = columns[col_num][1]

                    # HOJA DE PRESUPUESTO
                    ws = wb.add_sheet('PRESUPUESTO')
                    pagos = Pago.objects.filter(rubro__matricula__inscripcion__in=inscripciones, status=True, rubro__tipocuota=3)
                    rubros = Rubro.objects.filter(matricula__inscripcion__in=inscripciones, status=True)
                    row_num = 0
                    # if pagos:
                    if rubros:
                        fechamenorrubro = rubros.order_by('fechavence')[0].fechavence
                        fechamayorrubro = rubros.order_by('-fechavence')[0].fechavence

                        fechamenorpago = pagos.order_by('fecha')[0].fecha
                        fechamayorpago = pagos.order_by('-fecha')[0].fecha

                        if fechamenorrubro < fechamenorpago:
                            fechamenor = fechamenorrubro
                        else:
                            fechamenor = fechamenorpago

                        if fechamayorrubro > fechamayorpago:
                            fechamayor = fechamayorrubro
                        else:
                            fechamayor = fechamayorpago

                        aniomenor = fechamenor.year
                        mesmenor = fechamenor.month
                        aniomayor = fechamayor.year
                        mesmayor = fechamayor.month
                        rangomes = 12 - mesmenor
                        rangoanio = aniomayor - aniomenor
                        ws.write_merge(row_num, row_num, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 3, 'INSTITUTO DE POSTGRADO Y EDUCACION CONTINUA', title2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 3, carrera.nombre, title2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 3, periodo.nombre, title2)
                        row_num += 1
                        while aniomenor <= aniomayor:
                            cantidadpersonaltotal = Rubro.objects.values_list('matricula__inscripcion__persona__id', flat=True).filter(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, fechavence__year=aniomenor, status=True).distinct().count()


                            valorsaldototal = null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, fechavence__year=aniomenor, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)



                            personaladministrativo = Rubro.objects.values_list('matricula__inscripcion__persona__id', flat=True).filter(matricula__inscripcion__persona__administrativo__isnull=False,  matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, fechavence__year=aniomenor, status=True)
                            cantidadpersonaladministrativo = personaladministrativo.distinct().count()
                            valorsaldoadministrativo = null_to_decimal(Rubro.objects.filter(matricula__inscripcion__persona__administrativo__isnull=False,  matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, fechavence__year=aniomenor, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)

                            personalestudiante = Rubro.objects.values_list('matricula__inscripcion__persona__id', flat=True).filter(matricula__inscripcion__isnull=False, matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, fechavence__year=aniomenor, status=True).exclude(persona__id__in=personaladministrativo)
                            cantidadpersonalestudiante = personalestudiante.distinct().count()
                            valorsaldoestudiante = null_to_decimal(Rubro.objects.filter(matricula__inscripcion__isnull=False,  matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, fechavence__year=aniomenor, status=True).exclude(persona__id__in=personaladministrativo).aggregate(valor=Sum('saldo'))['valor'], 2)

                            cantidadpersonalparticular = cantidadpersonaltotal - cantidadpersonaladministrativo - cantidadpersonalestudiante
                            valorsaldoparticular = valorsaldototal - valorsaldoadministrativo - valorsaldoestudiante

                            mora = Decimal((valorsaldototal*DESCUENTA_MORA)/100).quantize(Decimal('.01'))
                            beca = Decimal((valorsaldototal*DESCUENTA_BECA)/100).quantize(Decimal('.01'))
                            retirado = Decimal((valorsaldototal*DESCUENTA_RETIRADO)/100).quantize(Decimal('.01'))
                            descuentos = mora+beca+retirado
                            ws.write_merge(row_num, row_num, 0, 3, 'PRESUPUESTO GENERAL' + str(aniomenor), title2)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'INGRESO BRUTO', font_style)
                            ws.write_merge(row_num, row_num, 3, 3, str(valorsaldototal), font_style)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'INGRESO NETO', font_style)
                            ws.write_merge(row_num, row_num, 3, 3, str(Decimal(valorsaldototal).quantize(Decimal('.01'))-descuentos), font_style)
                            row_num += 2
                            ws.write_merge(row_num, row_num, 1, 1, 'ALUMNOS', font_style)
                            ws.write_merge(row_num, row_num, 2, 2, 'VALOR', font_style)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'ESTUDIATES PARTICULARES', font_style)
                            ws.write_merge(row_num, row_num, 1, 1, str(cantidadpersonalparticular), font_style2)
                            ws.write_merge(row_num, row_num, 2, 2, str(valorsaldoparticular), font_style2)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'ESTUDIANTES UNEMI', font_style)
                            ws.write_merge(row_num, row_num, 1, 1, str(cantidadpersonalestudiante), font_style2)
                            ws.write_merge(row_num, row_num, 2, 2, str(valorsaldoestudiante), font_style2)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'ESTUDIANTES ADMINISTRATIVO', font_style)
                            ws.write_merge(row_num, row_num, 1, 1, str(cantidadpersonaladministrativo), font_style2)
                            ws.write_merge(row_num, row_num, 2, 2, str(valorsaldoadministrativo), font_style2)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'BECAS', font_style)
                            ws.write_merge(row_num, row_num, 2, 2, str(beca), font_style2)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'RETIRADOS', font_style)
                            ws.write_merge(row_num, row_num, 2, 2, str(retirado), font_style2)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'MORA', font_style)
                            ws.write_merge(row_num, row_num, 2, 2, str(mora), font_style2)
                            row_num += 2
                            ws.write_merge(row_num, row_num, 0, 0, 'COSTOS', font_style)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'HONORARIOS PROFESIONALES (INCLUYE IVA)', font_style)
                            row_num += 1
                            ws.write_merge(row_num, row_num, 0, 0, 'PAC (INCLUYE IVA)', font_style)
                            row_num += 1

                            row_num += 5

                            aniomenor += 1
                        columns = [
                            (u"", 8500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500)]
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style2)
                            ws.col(col_num).width = columns[col_num][1]

                    # HOJA DE PRESUPUESTO GENERAL
                    ws = wb.add_sheet('PRESUPUESTOGENERAL')
                    pagos = Pago.objects.filter(rubro__matricula__inscripcion__in=inscripciones, status=True, rubro__tipocuota=3)
                    rubros = Rubro.objects.filter(matricula__inscripcion__in=inscripciones, status=True)
                    row_num = 0
                    # if pagos:
                    if rubros:
                        ws.write_merge(row_num, row_num, 0, 3, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 3, 'INSTITUTO DE POSTGRADO Y EDUCACION CONTINUA', title2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 3, carrera.nombre, title2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 3, periodo.nombre, title2)
                        row_num += 1
                        cantidadpersonaltotal = Rubro.objects.values_list('matricula__inscripcion__persona__id', flat=True).filter(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True).distinct().count()
                        valorsaldototal = null_to_decimal(Rubro.objects.filter(matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)

                        personaladministrativo = Rubro.objects.values_list('matricula__inscripcion__persona__id', flat=True).filter(matricula__inscripcion__persona__administrativo__isnull=False,  matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True)
                        cantidadpersonaladministrativo = personaladministrativo.distinct().count()
                        valorsaldoadministrativo = null_to_decimal(Rubro.objects.filter(matricula__inscripcion__persona__administrativo__isnull=False,  matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True).aggregate(valor=Sum('saldo'))['valor'], 2)

                        personalestudiante = Rubro.objects.values_list('matricula__inscripcion__persona__id', flat=True).filter(matricula__inscripcion__isnull=False, matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True).exclude(persona__id__in=personaladministrativo)
                        cantidadpersonalestudiante = personalestudiante.distinct().count()
                        valorsaldoestudiante = null_to_decimal(Rubro.objects.filter(matricula__inscripcion__isnull=False,  matricula__nivel__periodo=periodo, matricula__inscripcion__carrera=carrera, status=True).exclude(persona__id__in=personaladministrativo).aggregate(valor=Sum('saldo'))['valor'], 2)

                        cantidadpersonalparticular = cantidadpersonaltotal - cantidadpersonaladministrativo - cantidadpersonalestudiante
                        valorsaldoparticular = valorsaldototal - valorsaldoadministrativo - valorsaldoestudiante

                        mora = Decimal((valorsaldototal*DESCUENTA_MORA)/100).quantize(Decimal('.01'))
                        beca = Decimal((valorsaldototal*DESCUENTA_BECA)/100).quantize(Decimal('.01'))
                        retirado = Decimal((valorsaldototal*DESCUENTA_RETIRADO)/100).quantize(Decimal('.01'))
                        descuentos = mora+beca+retirado
                        ws.write_merge(row_num, row_num, 0, 3, 'PRESUPUESTO GENERAL ANUAL', title2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'INGRESO BRUTO', font_style)
                        ws.write_merge(row_num, row_num, 3, 3, str(valorsaldototal), font_style)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'INGRESO NETO', font_style)
                        ws.write_merge(row_num, row_num, 3, 3, str(Decimal(valorsaldototal).quantize(Decimal('.01'))-descuentos), font_style)
                        row_num += 2
                        ws.write_merge(row_num, row_num, 1, 1, 'ALUMNOS', font_style)
                        ws.write_merge(row_num, row_num, 2, 2, 'VALOR', font_style)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'ESTUDIATES PARTICULARES', font_style)
                        ws.write_merge(row_num, row_num, 1, 1, str(cantidadpersonalparticular), font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, str(valorsaldoparticular), font_style2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'ESTUDIANTES UNEMI', font_style)
                        ws.write_merge(row_num, row_num, 1, 1, str(cantidadpersonalestudiante), font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, str(valorsaldoestudiante), font_style2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'ESTUDIANTES ADMINISTRATIVO', font_style)
                        ws.write_merge(row_num, row_num, 1, 1, str(cantidadpersonaladministrativo), font_style2)
                        ws.write_merge(row_num, row_num, 2, 2, str(valorsaldoadministrativo), font_style2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'BECAS', font_style)
                        ws.write_merge(row_num, row_num, 2, 2, str(beca), font_style2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'RETIRADOS', font_style)
                        ws.write_merge(row_num, row_num, 2, 2, str(retirado), font_style2)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'MORA', font_style)
                        ws.write_merge(row_num, row_num, 2, 2, str(mora), font_style2)
                        row_num += 2
                        ws.write_merge(row_num, row_num, 0, 0, 'COSTOS', font_style)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'HONORARIOS PROFESIONALES (INCLUYE IVA)', font_style)
                        row_num += 1
                        ws.write_merge(row_num, row_num, 0, 0, 'PAC (INCLUYE IVA)', font_style)
                        row_num += 1

                        columns = [
                            (u"", 8500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500),
                            (u"", 3500)]
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style2)
                            ws.col(col_num).width = columns[col_num][1]
                    wb.save(response)
                    return response
                except Exception as ex:
                    print("Error...")
                    pass

            elif action == 'reportenotificado':
                try:
                    data['fechadescarga'] = datetime.now()
                    # tiempo_dias = timedelta(90)
                    # before = now-tiempo_dias
                    # deuda = []
                    carreraid = request.GET['carrera']
                    periodoid = request.GET['periodo']
                    data['carrerarp'] = carrera = Carrera.objects.get(pk=carreraid)
                    data['periodorp'] = periodo = Periodo.objects.get(pk=periodoid)
                    data['matriculas'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1','inscripcion__persona__apellido2')
                    # for m in matricula:
                    #     notificacion = DetNotificacionDeuda.objects.filter(inscripcion=m, fechanoti__range=[before, now]).all()
                    #     deuda.append(notificacion)
                    # data['notifi'] = deuda
                    return conviert_html_to_pdf('rec_consultaalumnos/pdfnotificados.html',{'pagesize': 'A4', 'data': data,})
                except Exception as ex:
                    pass

            elif action == 'reportenotificado2':
                try:
                    logunemiurl = 'https://sga.unemi.edu.ec/static/images/LOGO-UNEMI-2020.png'
                    logunemi = io.BytesIO(urlopen(logunemiurl).read())
                    carreraid = request.GET['carrera']
                    periodoid = request.GET['periodo']
                    data['carrerarp'] = carrera = Carrera.objects.get(pk=carreraid)
                    data['periodorp'] = periodo = Periodo.objects.get(pk=periodoid)
                    data['matriculas'] = matricula = Matricula.objects.filter(nivel__periodo=periodo, inscripcion__carrera=carrera).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')


                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('reporte_')
                    ws.set_column(1, 20)
                    ws.set_row(13, 20)

                    formatoceldaleft = workbook.add_format({'font_size': 6, 'border': 1, 'text_wrap': True, 'align': 'left'})
                    formatoceldacenter = workbook.add_format({'font_size': 11, 'border': 1, 'text_wrap': True, 'align': 'center', 'valign': 'vcenter'})
                    formatotitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 12, 'border': 1, 'text_wrap': True, 'font_color': 'blue'})
                    formatosubtitulo = workbook.add_format(
                        {'align': 'center', 'valign': 'vcenter', 'bold': 1, 'font_size': 10, 'border': 1, 'text_wrap': True})
                    formatotitulo1 = workbook.add_format({'text_wrap': True, 'align': 'right', 'font_color': 'blue', 'font_size': 12})
                    formatotitulo2 = workbook.add_format({'text_wrap': True, 'align': 'left', 'font_size': 12})
                    formatoceldasinborde = workbook.add_format({'text_wrap': True, 'bold': True, 'align': 'center', 'font_size': 6})
                    formatoceldatitulo = workbook.add_format({'font_size': 11,'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'fg_color': '#A9BCD6'})
                    formatoceldagrist = workbook.add_format({'font_size': 10, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    formatoceldagris = workbook.add_format({'font_size': 6, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'text_wrap': True, 'fg_color': '#B6BFC0'})
                    ws.merge_range('A1:E6', '', formatotitulo)
                    ws.insert_image('A1', logunemiurl, {'x_scale': 0.31, 'y_scale': 0.31, 'image_data': logunemi})
                    ws.merge_range('F1:N3', 'REPORTE DE NOTIFICACION DE DEUDA', formatotitulo)
                    ws.merge_range('F4:N6',str(carrera),formatosubtitulo)

                    ws.merge_range('A8:B9', 'Cédula', formatoceldatitulo)
                    ws.merge_range('C8:F9', 'Nombre', formatoceldatitulo)
                    ws.merge_range('G8:I9', 'Veces Notificado', formatoceldatitulo)
                    ws.merge_range('J8:N9', 'Fechas de Notificación', formatoceldatitulo)

                    i = 9
                    val = 0
                    for ma in matricula:
                        noti = ""
                        notificaciones = DetNotificacionDeuda.objects.filter(inscripcion=ma).all()
                        if notificaciones.count()>0:
                            val = notificaciones.count() - 1
                            ws.merge_range('A%s:B%s'%(i+1,i+1+val), str(ma.inscripcion.persona.cedula), formatoceldacenter)
                            ws.merge_range('C%s:F%s'%(i+1,i+1+val), str(ma.inscripcion.persona), formatoceldacenter)
                            ws.merge_range('G%s:I%s'%(i+1,i+1+val), str(notificaciones.count()), formatoceldacenter)
                            for n in notificaciones:
                                ws.merge_range(i, 9, i, 13, str("{} {} $ {}".format(str(n.fechanoti),str(n.horanoti),str(n.valordeuda))),formatoceldacenter)
                                i += 1
                        else:
                            ws.merge_range(i,0,i,1,str(ma.inscripcion.persona.cedula),formatoceldacenter)
                            ws.merge_range(i, 2, i, 5, str(ma.inscripcion.persona), formatoceldacenter)
                            ws.merge_range(i, 6, i, 8, str(notificaciones.count()), formatoceldacenter)
                            ws.merge_range(i,9,i,13,str('-'),formatoceldacenter)
                            i+=1


                    workbook.close()
                    output.seek(0)
                    filename = 'reporte' + random.randint(1, 10000).__str__() + '.xlsx'
                    response = HttpResponse(output, content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename

                    return response
                except Exception as ex:
                    pass


            elif action == 'ver_epunemi':
                try:
                    data['title'] = u'Rubros que recudará EPUNEMI'
                    data['matricula'] = matricula = Matricula.objects.select_related().get(pk=request.GET['idmatricula'])
                    data['rubros'] = Rubro.objects.filter(matricula=matricula, status=True, cancelado=False).order_by('fechavence')
                    return render(request, "niveles/ver_epunemi.html", data)
                except Exception as ex:
                    pass

            elif action == 'reporte_detallado_docentes':
                try:
                    __author__ = 'Unemi'

                    title = easyxf('font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormalder = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Docentes')

                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_docentes_maestria' + random.randint(1, 10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    ws.write_merge(1, 1, 0, 6, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
                    ws.write_merge(2, 2, 0, 6, 'LISTADO DE DOCENTES DE LAS MAESTRIAS', title)

                    row_num = 5

                    columns = [
                        (u"N°", 700),
                        (u"PERIODO", 8300),
                        (u"COHORTE", 3500),
                        (u"CARRERA", 8300),
                        (u"IDENTIFICACION", 3500),
                        (u"DOCENTE", 8300),
                        (u"ASIGNATURA", 9300),
                        (u"PARALELO", 8300),
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]
                    secuencia = 0
                    prfesores = ProfesorMateria.objects.select_related().filter(materia__nivel__periodo__tipo_id__in=[3, 4], status=True, activo=True).distinct().order_by('materia__nivel__periodo', 'materia__asignaturamalla__malla__carrera', 'profesor')
                    for lista in prfesores:
                        row_num += 1
                        secuencia += 1
                        identificacion = lista.profesor.persona.identificacion()
                        periodo = lista.materia.nivel.periodo
                        ws.write(row_num, 0, secuencia, fuentenormalder)
                        ws.write(row_num, 1, u'%s' % periodo.nombre, fuentenormal)
                        ws.write(row_num, 2, u'%s' % periodo.cohorte, fuentenormal)
                        ws.write(row_num, 3, u'%s' % lista.materia.asignaturamalla.malla.carrera, fuentenormal)
                        ws.write(row_num, 4, u'%s' % identificacion, fuentenormal)
                        ws.write(row_num, 5, u'%s' % lista.profesor, fuentenormal)
                        ws.write(row_num, 6, u'%s' % lista.materia.asignaturamalla.asignatura, fuentenormal)
                        ws.write(row_num, 7, u'%s' % lista.materia.paralelo, fuentenormal)
                    row_num += 1

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'configuracionvalores':
                try:
                    data['title'] = u'Gestión configuración de costo de maestria'
                    search = None
                    ids = None
                    periodocarreracosto = PeriodoCarreraCosto.objects.filter(status=True)
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        periodocarreracosto = periodocarreracosto.filter(Q(carrera__nombre__icontains=search) |
                                                                         Q(periodo__nombre__icontains=search))
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        periodocarreracosto = periodocarreracosto.filter(id=ids)
                    paging = MiPaginador(periodocarreracosto, 20)
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
                    data['periodocarreracosto'] = page.object_list
                    return render(request, "rec_consultaalumnos/configuracionvalores.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadopostulacionesmaestrias':
                try:
                    data['title'] = u'Listado de programas'
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        periodosadmision = MaestriasAdmision.objects.filter(descripcion__icontains=search, status=True).distinct()
                    else:
                        periodosadmision = MaestriasAdmision.objects.filter(status=True).distinct().order_by('id')
                    paging = MiPaginador(periodosadmision, 25)
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
                    data['periodosadmision'] = page.object_list
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    return render(request, "rec_consultaalumnos/listadopostulacionesmaestrias.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportematriculadosmaestrias':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listadomatriculados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 55)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 40)
                    ws.set_column(4, 4, 25)
                    ws.set_column(5, 5, 25)
                    ws.set_column(6, 6, 25)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 45)
                    ws.set_column(9, 9, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    ws.merge_range('A1:J1', "REPORTE DE MATRICULADOS", formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'PROGRAMA DE MAESTRÍA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'PERIODO(INICIO - FIN)', formatoceldacab)
                    ws.write(1, 4, 'ESTADO DE MAESTRÍA', formatoceldacab)
                    ws.write(1, 5, 'PROVINCIA', formatoceldacab)
                    ws.write(1, 6, 'CANTÓN', formatoceldacab)
                    ws.write(1, 7, 'CÉDULA', formatoceldacab)
                    ws.write(1, 8, 'ESTUDIANTE', formatoceldacab)
                    ws.write(1, 9, 'ESTADO ESTUDIANTE', formatoceldacab)

                    matriculas = Matricula.objects.filter(status=True, nivel__periodo__tipo__id__in=[3, 4]).exclude(nivel__periodo__pk__in=[120, 128]).distinct().order_by('inscripcion__persona__apellido1',
                                                                                                                           'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    filas_recorridas = 3
                    cont = 1

                    for matricula in matriculas:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(matricula.inscripcion.carrera.nombre), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(matricula.nivel.periodo.cohorte if matricula.nivel.periodo.cohorte else 0), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(matricula.nivel.periodo.inicio) + " a " + str(matricula.nivel.periodo.fin), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str("EN EJECUCIÓN" if datetime.now().date() <= matricula.nivel.periodo.fin else "FINALIZADO"), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(matricula.inscripcion.persona.provincia), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(matricula.inscripcion.persona.canton), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(matricula.inscripcion.persona.cedula), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(matricula.inscripcion.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(matricula.estado_inscripcion_maestria()), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_matriculados_maestrias.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportematriculadosmaestrias_cantidades':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listadomatriculados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 55)
                    ws.set_column(2, 2, 35)
                    ws.set_column(3, 3, 20)
                    ws.set_column(4, 4, 40)
                    ws.set_column(5, 5, 25)
                    ws.set_column(6, 6, 20)
                    ws.set_column(7, 7, 20)
                    ws.set_column(8, 8, 20)
                    ws.set_column(9, 9, 20)
                    ws.set_column(10, 10, 20)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)
                    ws.set_column(13, 13, 20)
                    ws.set_column(14, 14, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    ws.merge_range('A1:O1', "REPORTE DE MATRICULADOS", formatotitulo_filtros)
                    ws.write(1, 0, 'N°', formatoceldacab)
                    ws.write(1, 1, 'PROGRAMA DE MAESTRÍA', formatoceldacab)
                    ws.write(1, 2, 'COHORTE', formatoceldacab)
                    ws.write(1, 3, 'Nº COHORTE', formatoceldacab)
                    ws.write(1, 4, 'PERIODO(INICIO - FIN)', formatoceldacab)
                    ws.write(1, 5, 'ESTADO DE MAESTRÍA', formatoceldacab)
                    ws.write(1, 6, 'ESTUDIANTES MATRICULADOS', formatoceldacab)
                    ws.write(1, 7, 'RETIRADOS', formatoceldacab)
                    ws.write(1, 8, 'EN CURSO', formatoceldacab)
                    ws.write(1, 9, 'CUMPLIMIENTO MALLA', formatoceldacab)
                    ws.write(1, 10, 'TITULACIÓN/PROYECTO', formatoceldacab)
                    ws.write(1, 11, 'TITULACIÓN/COMPLEXIVO', formatoceldacab)
                    ws.write(1, 12, 'EGRESADOS TITULACIÓN/PROYECTO', formatoceldacab)
                    ws.write(1, 13, 'EGRESADOS TITULACIÓN/COMPLEXIVO', formatoceldacab)
                    ws.write(1, 14, 'GRADUADOS', formatoceldacab)

                    cohortes = CohorteMaestria.objects.filter(status=True)

                    filas_recorridas = 3
                    cont = 1

                    for cohorte in cohortes:

                        # Matriculados
                        matriculados = Matricula.objects.filter(status=True, inscripcion__inscripcioncohorte__cohortes__id=cohorte.id,
                                                                    nivel__periodo__tipo__id__in=[3, 4]).exclude(nivel__periodo__pk__in=[120, 128]).distinct()
                        #Retirados, En curso, En titulacion
                        retirados = malla_cumplida = graduados = en_titulacion = vigentes = complexivo =  egre_titu = egre_comple = 0

                        if matriculados.count() > 0:
                            matri = matriculados[0]

                            for matriculado in matriculados:
                                # Si está retirado
                                if matriculado.retirado_programa_maestria():
                                    retirados += 1
                                # Si en la inscripción tiene estado graduado
                                elif matriculado.inscripcion.graduado():
                                    graduados += 1
                                # Si tiene asignado tema de titulación
                                elif matriculado.tematitulacionposgradomatricula_set.filter(status=True).exists():
                                    if matriculado.tematitulacionposgradomatricula_set.filter(status=True, mecanismotitulacionposgrado__id=15).exists():
                                        # Obtengo el tema de titulación más reciente
                                        tematitulacion = matriculado.tematitulacionposgradomatricula_set.filter(status=True, mecanismotitulacionposgrado__id=15).order_by('-id')[0]
                                        # Si pasó por estados de aprobación
                                        if tematitulacion.estado_aprobacion():
                                            # Si el tema fue aprobado
                                            if tematitulacion.estado_aprobacion().estado == 2:
                                                if tematitulacion.calificacion >= 70 and tematitulacion.actacerrada == True:
                                                    egre_comple += 1
                                                else:
                                                    complexivo += 1
                                            else:
                                                if matriculado.malla_culminada():
                                                    malla_cumplida += 1
                                                else:
                                                    vigentes += 1
                                        else:
                                            if matriculado.malla_culminada():
                                                malla_cumplida += 1
                                            else:
                                                vigentes += 1
                                    else:
                                        # Obtengo el tema de titulación más reciente
                                        tematitulacion = matriculado.tematitulacionposgradomatricula_set.filter(status=True).order_by('-id')[0]
                                        # Si pasó por estados de aprobación
                                        if tematitulacion.estado_aprobacion():
                                            # Si el tema fue aprobado
                                            if tematitulacion.estado_aprobacion().estado == 2:
                                                # Si existen registros de tutorías
                                                if tematitulacion.tutoriastematitulacionposgradoprofesor_set.filter(status=True).exists():
                                                    if tematitulacion.calificacion >= 70 and tematitulacion.actacerrada == True:
                                                        egre_titu += 1
                                                    else:
                                                        en_titulacion += 1
                                                else:
                                                     if matriculado.malla_culminada():
                                                        malla_cumplida += 1
                                                     else:
                                                        vigentes += 1
                                            else:
                                                if matriculado.malla_culminada():
                                                    malla_cumplida += 1
                                                else:
                                                    vigentes += 1
                                        else:
                                            if matriculado.malla_culminada():
                                                malla_cumplida += 1
                                            else:
                                                vigentes += 1
                                elif matriculado.malla_culminada():
                                    malla_cumplida += 1
                                else:
                                    vigentes += 1

                            ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                            ws.write('B%s' % filas_recorridas, str(cohorte.maestriaadmision.carrera.nombre), formatoceldaleft)
                            ws.write('C%s' % filas_recorridas, str(cohorte.descripcion), formatoceldaleft)
                            ws.write('D%s' % filas_recorridas, str(matri.nivel.periodo.cohorte if matri.nivel.periodo.cohorte else 0), formatoceldaleft)
                            ws.write('E%s' % filas_recorridas, str(matri.nivel.periodo.inicio) + " a " + str(matri.nivel.periodo.fin), formatoceldaleft)
                            ws.write('F%s' % filas_recorridas, str("EN EJECUCIÓN" if datetime.now().date() <= matri.nivel.periodo.fin else "FINALIZADO"), formatoceldaleft)
                            ws.write('G%s' % filas_recorridas, str(matriculados.count()), formatoceldaleft)
                            ws.write('H%s' % filas_recorridas, str(retirados), formatoceldaleft)
                            ws.write('I%s' % filas_recorridas, str(vigentes), formatoceldaleft)
                            ws.write('J%s' % filas_recorridas, str(malla_cumplida), formatoceldaleft)
                            ws.write('K%s' % filas_recorridas, str(en_titulacion), formatoceldaleft)
                            ws.write('L%s' % filas_recorridas, str(complexivo), formatoceldaleft)
                            ws.write('M%s' % filas_recorridas, str(egre_titu), formatoceldaleft)
                            ws.write('N%s' % filas_recorridas, str(egre_comple), formatoceldaleft)
                            ws.write('O%s' % filas_recorridas, str(graduados), formatoceldaleft)

                            filas_recorridas += 1
                            cont += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'Reporte_matriculados_maestrias.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadorubros':
                try:
                    data['title'] = u'Rubros'
                    search = None
                    ids = None
                    rubros = TipoOtroRubro.objects.filter(tiporubro=1, status=True)

                    if 'id' in request.GET:
                        ids = int(request.GET['id'])
                        rubros = rubros.filter(instructor_id=int(request.GET['id']))
                    if 's' in request.GET:
                        search = request.GET['s']
                        rubros = rubros.filter(nombre__icontains=search)

                    paging = MiPaginador(rubros, 20)
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
                    data['ids'] = ids if ids else ""
                    data['search'] = search if search else ""
                    data['rubros'] = page.object_list

                    return render(request, "rec_consultaalumnos/listadorubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'addrubros':
                try:
                    data['title'] = u'Nuevo Rubro'
                    data['form'] = TipoOtroRubroIpecRubForm()
                    return render(request, "rec_consultaalumnos/addrubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'editrubros':
                try:
                    data['title'] = u'Modificación Rubro'
                    data['tipootrorubro'] = tipootrorubro = TipoOtroRubro.objects.get(pk=request.GET['id'])
                    form = TipoOtroRubroIpecRubForm(initial={'nombre': tipootrorubro.nombre,
                                                          'partida': tipootrorubro.partida,
                                                          'unidad_organizacional': tipootrorubro.unidad_organizacional,
                                                          'programa': tipootrorubro.programa,
                                                          'tipo': tipootrorubro.tiporubro})
                    data['form'] = form
                    return render(request, "rec_consultaalumnos/editrubros.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadocohortes':
                try:
                    data['title'] = u'Listado de Cohortes'
                    data['maestriaadmision'] = maestriaadmision = MaestriasAdmision.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['listadocohortes'] = maestriaadmision.cohortemaestria_set.filter(status=True).order_by('id')
                    return render(request, "rec_consultaalumnos/listamaestrias.html", data)
                except Exception as ex:
                    pass

            if action == 'configurarcohorte':
                try:
                    data['title'] = u'Editar Cohorte'
                    persona = data['persona']
                    if persona.profesor():
                        data['personasesion'] = persona.profesor()
                    else:
                        data['personasesion'] = persona
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=int(encrypt(request.GET['idcohorte'])))
                    if cohorte.coordinador_id in [None, '', 0]:
                        data['idcoordinador'] = idcoordinador = 0
                    else:
                        if cohorte.coordinador.profesor():
                            data['idcoordinador'] = idcoordinador = cohorte.coordinador.profesor().id
                        else:
                            data['idcoordinador'] = idcoordinador = 0
                    if cohorte.tiporubro_id in [None, '', 0]:
                        data['idtipootrorubro'] = idtipootrorubro = 0
                    else:
                        data['idtipootrorubro'] = idtipootrorubro = cohorte.tiporubro_id
                    form = ConfiCohorteMaestriaForm(initial={'tienecostomatricula': cohorte.tienecostomatricula,
                                                             'valormatricula': cohorte.valormatricula,
                                                             'tipootrorubro': idtipootrorubro,
                                                             'costomaestria': cohorte.valorprograma,
                                                             'valorprogramacertificado': cohorte.valorprogramacertificado,
                                                             'fechavencerubro': cohorte.fechavencerubro,
                                                             'fechainiordinaria': cohorte.fechainiordinaria,
                                                             'fechafinordinaria': cohorte.fechafinordinaria,
                                                             'fechainiextraordinaria': cohorte.fechainiextraordinaria,
                                                             'fechafinextraordinaria': cohorte.fechafinextraordinaria,
                                                             'tienecostomaestria': cohorte.tienecostototal,
                                                             'presupuestobeca': cohorte.presupuestobeca})
                    data['form'] = form

                    data['editarpresupuesto'] = cohorte.puede_editar_prespuestobecas()
                    data['presupuestoutilizado'] = cohorte.valor_utilizado_presupuestobecas()

                    return render(request, "rec_consultaalumnos/configurarcohorte.html", data)
                except Exception as ex:
                    pass

            elif action == 'configurarfinanciamientocohorte':
                try:
                    data['title'] = u'Configuración financiamiento de Cohorte'
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=int(encrypt(request.GET['idcohorte'])))
                    search = None
                    ids = None
                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        info = cohorte.configfinanciamientocohorte_set.filter(descripcion__icontains=search,status=True).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        info = cohorte.configfinanciamientocohorte_set.filter(id=ids,status=True)
                    else:
                        info = cohorte.configfinanciamientocohorte_set.filter(status=True)
                    paging = MiPaginador(info, 30)
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
                    data['infofinanciera'] = page.object_list
                    return render(request, "rec_consultaalumnos/configfinanciamientocohorte.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfinanciamientocohorte':
                try:
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=request.GET['idcohorte'])
                    carrera = cohorte.maestriaadmision.carrera
                    instauracion = None
                    if carrera:
                        instauracion = carrera.programapac_set.last()
                    if instauracion:
                        infopac = instauracion.infraestructuraequipamientoinformacionpac_set.last()
                        if infopac:
                            form = ConfigFinanciamientoCohorteForm(initial={'valormatricula': infopac.valormatricula,
                                                                         'valorarancel': infopac.valorarancel,
                                                                         'valortotalprograma': infopac.valortotalprograma,
                                                                         'porcentajeminpagomatricula': infopac.porcentajeminpagomatricula,
                                                                         'maxnumcuota': infopac.maxnumcuota})
                        else:
                            form = ConfigFinanciamientoCohorteForm()
                    else:
                        form = ConfigFinanciamientoCohorteForm()
                    data['form2'] = form
                    template = get_template("rec_consultaalumnos/modal/modalfinanciamientocohorte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'editfinanciamientocohorte':
                try:
                    data['id'] = request.GET['id']
                    data['filtro'] = filtro = ConfigFinanciamientoCohorte.objects.get(pk=request.GET['id'])
                    data['form2'] = ConfigFinanciamientoCohorteForm(model_to_dict(filtro))
                    template = get_template("rec_consultaalumnos/modal/modalfinanciamientocohorte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'duplicarfinanciamientocohorte':
                try:
                    data['id'] = request.GET['id']
                    data['cohorte'] = cohorte = CohorteMaestria.objects.get(pk=request.GET['id'])
                    data['filtro'] = filtro = ConfigFinanciamientoCohorte.objects.filter(status=True, cohorte__maestriaadmision=cohorte.maestriaadmision).distinct('cohorte_id').order_by('cohorte_id').exclude(cohorte=cohorte)
                    template = get_template("rec_consultaalumnos/modal/duplicarfinanciamientocohorte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'listadocontratopagare':
                try:
                    data['title'] = u'Contratos y pagarés'
                    search = None
                    ids = None
                    info = Contrato.objects.filter(status=True)

                    if 's' in request.GET:
                        search = request.GET['s']
                    if search:
                        info = Contrato.objects.filter(Q(inscripcion__inscripcionaspirante__persona__nombres__icontains=search)|
                                                       Q(inscripcion__inscripcionaspirante__persona__apellido1__icontains=search)|
                                                       Q(inscripcion__inscripcionaspirante__persona__apellido2__icontains=search)|
                                                       Q(inscripcion__cohortes__descripcion__icontains=search)|
                                                       Q(inscripcion__cohortes__maestriaadmision__descripcion__icontains=search)|
                                                       Q(inscripcion__cohortes__maestriaadmision__carrera__nombre__icontains=search)|
                                                       Q(formapago__descripcion__icontains=search), status=True).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        info = Contrato.objects.filter(id=ids)

                    paging = MiPaginador(info, 20)
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
                    data['ids'] = ids if ids else ""
                    data['search'] = search if search else ""
                    data['registros'] = page.object_list

                    return render(request, "rec_consultaalumnos/listadocontratopagare.html", data)
                except Exception as ex:
                    pass

            if action == 'tablaamortizacion':
                try:
                    data['title'] = u'Tabla de amortización'
                    data['cohorte'] = contrato = Contrato.objects.get(status=True, inscripcion_id=int(request.GET['id']))
                    data['tablaamortizacion'] = tablaamortizacion = contrato.tablaamortizacion_set.filter(status=True)
                    data['aspirante'] = contrato.inscripcion
                    total = 0
                    for valor in tablaamortizacion:
                        total = total + valor.valor
                    data['total'] = total
                    template = get_template("rec_consultaalumnos/modal/tablaamortizacion.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'addvalormaestria':
                try:
                    data['title'] = u'Adicionar valor maestria'
                    data['form'] = ValorMaestriaForm()
                    return render(request, "rec_consultaalumnos/addvalormaestria.html", data)
                except Exception as ex:
                    pass

            elif action == 'editvalormaestria':
                try:
                    data['title'] = u'Editar valor maestria'
                    data['periodocarreracosto'] = periodocarreracosto = PeriodoCarreraCosto.objects.get(pk=request.GET['id'])
                    initial = model_to_dict(periodocarreracosto)
                    form = ValorMaestriaForm(initial=initial)
                    data['form'] = form
                    return render(request, "rec_consultaalumnos/editvalormaestria.html", data)
                except Exception as ex:
                    pass

            elif action == 'deletevalormaestria':
                try:
                    data['title'] = u'Borrar valor maestria'
                    data['periodocarreracosto'] = PeriodoCarreraCosto.objects.get(pk=request.GET['id'])
                    return render(request, "rec_consultaalumnos/deletevalormaestria.html", data)
                except Exception as ex:
                    pass

            if action == 'addmatriculadonovigente':
                try:
                    if not request.GET['id']:
                        return JsonResponse({"result": False, "mensaje": "No existe periodo seleccionado."}, safe=False)
                    codigoperiodo = Periodo.objects.get(pk=request.GET['id'])
                    if not Periodo.objects.filter(pk=request.GET['id'], nombre__icontains='NO VIGENTE', tipo_id__in=[3,4]):
                        return JsonResponse({"result": False, "mensaje": "Esta opción es solo para periodo NO VIGENTES."}, safe=False)
                    if not Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=7,periodo=codigoperiodo, status=True).exists():
                        return JsonResponse({"result": True, "mensaje": "No existe niveles creado en el periodo."}, safe=False)
                    data['id'] = request.GET['id']
                    data['form2'] = InscripcionesMaestriasForm()
                    template = get_template("rec_consultaalumnos/modal/inscripcionmaestria.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'buscarpersonamaestria':
                try:
                    q = request.GET['q'].upper().strip()
                    s = q.split(" ")
                    if len(s) == 1:
                        per = Inscripcion.objects.filter((Q(persona__nombres__icontains=q) | Q(persona__apellido1__icontains=q) | Q(persona__cedula__icontains=q) | Q(persona__apellido2__icontains=q) | Q(persona__cedula__contains=q)), Q(status=True)).filter(carrera__niveltitulacion_id=4, status=True).distinct()[:15]
                    elif len(s) == 2:
                        per = Inscripcion.objects.filter((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) | (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) | (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1]))).filter(carrera__niveltitulacion_id=4, status=True).distinct()[:15]
                    else:
                        per = Inscripcion.objects.filter((Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(persona__apellido2__contains=s[2])) | (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2]))).filter(carrera__niveltitulacion_id=4, status=True).distinct()[:15]

                    data = {"result": "ok", "results": [{"id": x.id, "name": "{} - {}".format(x.persona.cedula, x.persona.nombre_completo() + ' -> ' + x.carrera.nombre)} for x in per]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'calculo':
                try:
                    data['title'] = u'Cálculo descuento Posgrado'
                    data['matricula'] = DescuentoPosgradoMatricula.objects.get(pk=request.GET['idmatricula'])
                    data['tipo'] = request.GET['tipo']
                    return render(request, "rec_consultaalumnos/calculo.html", data)
                except Exception as ex:
                    pass

            elif action == 'validardocumentocompromiso':
                try:
                    data['title'] = u'Legalizar Contrato de Maestría'
                    data['idm'] = int(encrypt(request.GET['idm']))
                    persona = data['persona']

                    matricula = Matricula.objects.get(pk=encrypt(request.GET['idm']))

                    data['compromisopago'] = compromisopago = matricula.compromisopagoposgrado_set.filter(status=True, vigente=True, tipo=1)[0]

                    primerdocumento = {}
                    primerdocumento['descripcion'] = 'Tabla de amortización'
                    primerdocumento['url'] = compromisopago.archivocompromiso.url
                    data['primerdocumento'] = primerdocumento

                    documentos = []
                    documentos.append(['CP', 'Tabla de amortización', compromisopago.archivocompromiso.url, compromisopago.get_estadocompromiso_display(), compromisopago.estadocompromiso, 0, compromisopago.observacioncompromiso])
                    documentos.append(['CM', 'Contrato de Maestría', compromisopago.archivocontrato.url, compromisopago.get_estadocontrato_display(), compromisopago.estadocontrato, 0, compromisopago.observacioncontrato])
                    documentos.append(['PG', 'Pagaré', compromisopago.archivopagare.url, compromisopago.get_estadopagare_display(), compromisopago.estadopagare, 0, compromisopago.observacionpagare])

                    # Consulto los documentos personales del alumnos: cedula y papeleta de votación
                    documentospersonales = matricula.inscripcion.persona.documentos_personales()
                    if documentospersonales:
                        # El primer valor es el indice de la pestaña
                        documentos.append(['CC', 'Cédula de ciudadanía', documentospersonales.cedula.url, documentospersonales.get_estadocedula_display(), documentospersonales.estadocedula, 0, documentospersonales.observacioncedula])
                        documentos.append(['PV', 'Papeleta de votación', documentospersonales.papeleta.url, documentospersonales.get_estadopapeleta_display(), documentospersonales.estadopapeleta, 0, documentospersonales.observacionpapeleta])

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
                        es_revisor_inicial = compromisopago.personarevisa == persona
                        # if compromisopago.personarevisa != persona and compromisopago.estado.valor != 3:
                        #     return JsonResponse({"result": "bad", "mensaje": "Los documentos del compromiso de pago está siendo revisada por %s." % (compromisopago.personarevisa.nombre_completo_inverso())})
                    else:
                        # Actualizo el compromiso de pago
                        es_revisor_inicial = True
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

                    if es_revisor_inicial is False:
                        data['permite_modificar'] = False

                    template = get_template("rec_consultaalumnos/validardocumento.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    pass

            elif action == 'rubrosadicionales':
                try:
                    matricula = Matricula.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['matricula'] = matricula
                    data['rubrosadicionales'] = rubrosadicionales = matricula.rubros_adicionales_posgrado()
                    data['totalrubros'] = x = rubrosadicionales.values_list('valor').aggregate(totalrubros=Sum('valor'))['totalrubros']
                    template = get_template("rec_consultaalumnos/rubrosadicionales.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_carreras_ofer':
                try:
                    hoy = datetime.now().date()
                    lista = []
                    idmatriculados = Rubro.objects.values_list('matricula_id').filter(fechavence__lt=hoy, matricula__isnull=False,
                                                                                        tipo__tiporubro=1, cancelado=False, status=True, tipo__subtiporubro=1).distinct()

                    matriculados = Matricula.objects.filter(status=True, id__in=idmatriculados).order_by('-fecha')

                    carreras = Carrera.objects.filter(status=True, id__in=matriculados.values_list('inscripcion__carrera__id', flat=True).order_by('inscripcion__carrera__id').distinct())

                    for carrera in carreras:
                        if not buscar_dicc(lista, 'id', carrera.id):
                            lista.append({'id': carrera.id, 'nombre': carrera.nombre + ' - '})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'reportecarteravencida':
                try:
                    __author__ = 'Unemi'

                    hoy = datetime.now().date()
                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('cartera_vencida')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 35)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 30)
                    ws.set_column(6, 6, 15)
                    ws.set_column(7, 7, 40)
                    ws.set_column(8, 8, 20)
                    ws.set_column(9, 9, 40)
                    ws.set_column(10, 10, 15)
                    ws.set_column(11, 11, 20)
                    ws.set_column(12, 12, 20)
                    ws.set_column(13, 13, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    carrera = 0
                    desde = hasta = ''

                    if 'carrera' in request.GET:
                        carrera = request.GET['carrera']

                    if 'desde' in request.GET:
                        desde = request.GET['desde']
                    if 'hasta' in request.GET:
                        hasta = request.GET['hasta']

                    ws.merge_range('A1:N1', 'Reporte de carteera vencida (Detalle deudor)', formatotitulo_filtros)
                    if desde and hasta:
                        ws.merge_range('A2:N2', 'Desde el ' + desde + ' Hasta el ' + hasta, formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Deudor', formatoceldacab)
                    ws.write(2, 2, 'Cédula', formatoceldacab)
                    ws.write(2, 3, 'Teléfono', formatoceldacab)
                    ws.write(2, 4, 'Teléfono conv', formatoceldacab)
                    ws.write(2, 5, 'Correo personal', formatoceldacab)
                    ws.write(2, 6, 'Fecha de nacimiento', formatoceldacab)
                    ws.write(2, 7, 'Dirección', formatoceldacab)
                    ws.write(2, 8, 'Ciudad de residencia', formatoceldacab)
                    ws.write(2, 9, 'Programa de maestría que adeuda', formatoceldacab)
                    ws.write(2, 10, 'Monto total vencido', formatoceldacab)
                    ws.write(2, 11, 'Número de cuenta bancaria', formatoceldacab)
                    ws.write(2, 12, 'Tipo de cuenta bancaria', formatoceldacab)
                    ws.write(2, 13, 'Nombre del banco registrado', formatoceldacab)

                    filtro = Q(status=True)
                    if carrera != "":
                        if eval(request.GET['carrera'])[0] != "0":
                            filtro = filtro & Q(inscripcion__carrera__in=eval(request.GET['carrera']))

                    if desde and hasta:
                        idmatriculados = Rubro.objects.values_list('matricula_id').filter(fechavence__lt=hoy, matricula__isnull=False, fechavence__range=(desde, hasta),
                                                                                        tipo__tiporubro=1, cancelado=False, status=True, tipo__subtiporubro=1).distinct()
                    elif desde:
                        idmatriculados = Rubro.objects.values_list('matricula_id').filter(fechavence__lt=hoy, matricula__isnull=False, fechavence__gte=desde,
                                                                                        tipo__tiporubro=1, cancelado=False, status=True, tipo__subtiporubro=1).distinct()
                    elif hasta:
                        idmatriculados = Rubro.objects.values_list('matricula_id').filter(fechavence__lt=hoy, matricula__isnull=False, fechavence__lte=hasta,
                                                                                        tipo__tiporubro=1, cancelado=False, status=True, tipo__subtiporubro=1).distinct()
                    else:
                        idmatriculados = Rubro.objects.values_list('matricula_id').filter(fechavence__lt=hoy, matricula__isnull=False,
                                                                                        tipo__tiporubro=1, cancelado=False, status=True, tipo__subtiporubro=1).distinct()

                    matriculados = Matricula.objects.filter(filtro & Q(id__in=idmatriculados)).order_by('-fecha')

                    filas_recorridas = 4
                    cont = 1

                    for matriculado in matriculados:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(matriculado.inscripcion.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(matriculado.inscripcion.persona.identificacion()), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(matriculado.inscripcion.persona.telefono if matriculado.inscripcion.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(matriculado.inscripcion.persona.telefono_conv if matriculado.inscripcion.persona.telefono_conv else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(matriculado.inscripcion.persona.email if matriculado.inscripcion.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(matriculado.inscripcion.persona.nacimiento), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(matriculado.inscripcion.persona.direccion if matriculado.inscripcion.persona.direccion else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(matriculado.inscripcion.persona.canton.nombre if matriculado.inscripcion.persona.canton else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(matriculado.inscripcion.carrera.nombre), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, matriculado.vencido_a_la_fechamatricula_rubro_maestria(), decimalformat)
                        ws.write('L%s' % filas_recorridas, str(matriculado.inscripcion.persona.cuentasbancarias()[0].numero if matriculado.inscripcion.persona.cuentasbancarias() else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(matriculado.inscripcion.persona.cuentasbancarias()[0].tipocuentabanco.nombre if matriculado.inscripcion.persona.cuentasbancarias() else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str(matriculado.inscripcion.persona.cuentasbancarias()[0].banco.nombre if matriculado.inscripcion.persona.cuentasbancarias() else 'NO REGISTRA'), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Cartera_vencida_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['periodos'] = Periodo.objects.filter(tipo_id__in=[3, 4])
                if 'id' in request.GET:
                    data['id'] = request.GET['id']
                data['anio'] = anio = datetime.now().year
                data['fecha'] = datetime.now().date()
                data['form2'] = MatriculaNovedadForm
                data['aniosreporte'] = [a for a in range(2021, anio + 1)]
                data['mesesreporte'] = MESES_CHOICES

                cnunemi = connections['sga_select'].cursor()
                sql = """
                        SELECT distinct
ca.nombre AS programa,per.nombre AS cohorte,per.inicio as inicio, per.fin as fin
FROM sga_persona AS pe
INNER JOIN sga_inscripcion AS ins
ON pe.id=ins.persona_id
INNER JOIN sga_carrera AS ca
ON ins.carrera_id=ca.id
INNER JOIN sga_matricula AS mat
ON mat.inscripcion_id=ins.id
INNER JOIN sga_nivel AS ni
ON mat.nivel_id=ni.id
INNER JOIN sga_periodo AS per
ON ni.periodo_id=per.id
INNER JOIN sga_tipoperiodo AS tper
ON per.tipo_id=tper.id
WHERE mat."status"=true
  AND per.tipo_id IN (3, 4) AND per.id NOT IN (120, 128)
  AND per.id NOT IN (SELECT pcc.periodo_id FROM sga_periodocarreracosto AS pcc)
  AND per.nombre NOT ILIKE '%TITULAC%'
ORDER BY per.inicio,per.fin;
                    """
                cnunemi.execute(sql)
                programassincosto = cnunemi.fetchall()
                cnunemi.close()

                data['programassincosto'] = programassincosto

                return render(request, "rec_consultaalumnos/view.html", data)
            except Exception as ex:
                pass


def categoria_antiguedad_cartera(dias):
    pass
