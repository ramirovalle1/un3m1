# -*- coding: UTF-8 -*-
import xlrd
import xlwt
import json
from itertools import chain
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q, Max
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template
from decorators import secure_module
from helpdesk.forms import HdPlanAprobacionForm
from helpdesk.models import HdPlanAprobacion, HdAprobarSolicitud
from sagest.forms import PermisoInstitucionalDetalleForm, PermisoInstitucionalAdicionarForm, \
    KardexVacacionesForm, KardexVacacionesDetalleForm, KardexVacacionesIndividualForm, PermisoInstitucionalFechaForm, \
    InformesPermisoForm
from sagest.models import PermisoInstitucional, PermisoAprobacion, PermisoInstitucionalDetalle, TipoPermiso, \
    DistributivoPersona, TipoPermisoDetalle, RegimenLaboral, IngresoPersonal, KardexVacacionesDetalle, Departamento
from sagest.th_marcadas import calculando_marcadas
from settings import EMAIL_DOMAIN, PUESTO_ACTIVO_ID, ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, generar_nombre, convertir_fecha, null_to_numeric, variable_valor
from datetime import datetime,timedelta
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, Archivo


# @login_required(redirect_field_name='ret', login_url='/loginsagest')
# @secure_module
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona']=persona = request.session['persona']
    usuario = request.user
    if not Departamento.objects.filter(responsable=persona).exists():
        return HttpResponseRedirect('/?info=Usted no es reponsable de un departamento.')
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'addaprobacion':
            try:
                permiso = HdPlanAprobacion.objects.get(pk=request.POST['id'])
                aprobar = HdAprobarSolicitud(plan=permiso,
                                             fechaaprobacion=datetime.now().date(),
                                             observacion=request.POST['obse'],
                                             aprueba=persona,
                                             estadosolicitud=int(request.POST['esta']))
                aprobar.save(request)
                permiso.estadoaprobacion = int(request.POST['esta'])
                permiso.save()
                log(u'Aprobar solicitud(VA): %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addaprobacion_rechazar':
            try:
                permiso = HdPlanAprobacion.objects.get(pk=request.POST['id'])
                aprobar = HdAprobarSolicitud(plan=permiso,
                                            fechaaprobacion=datetime.now().date(),
                                            observacion=request.POST['obse'],
                                            aprueba=persona,
                                            estadosolicitud=int(request.POST['esta']))
                aprobar.save(request)
                permiso.estadoaprobacion=5
                permiso.save(request)
                # aprobar.mail_notificar_talento_humano(request.session['nombresistema'])

                log(u'Rechazar solicitud(TH): %s' % aprobar, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})





        elif action == 'reportepermisosrechazadopdf':
            try:
                listado = []
                fechainicio = datetime.strptime(request.POST['ini'], "%d-%m-%Y").date()
                fechafin = datetime.strptime(request.POST['fin'], "%d-%m-%Y").date()
                if fechafin >= datetime.now().date():
                    fechafin = datetime.now().date() + timedelta(days=-1)
                iddepartamentos_sinordenar = PermisoInstitucional.objects.values_list('unidadorganica_id').filter(fechasolicitud__range=(fechainicio, fechafin)).distinct('unidadorganica_id').order_by('unidadorganica_id')
                iddepartamentos = Departamento.objects.values_list('id').filter(pk__in=iddepartamentos_sinordenar).order_by('nombre')
                for iddepartamento in iddepartamentos:
                    departamento = Departamento.objects.get(pk=iddepartamento[0])
                    pendiente = PermisoInstitucional.objects.values('id').filter(estadosolicitud=1, unidadorganica_id=iddepartamento[0], fechasolicitud__range=(fechainicio, fechafin)).count()
                    solicitada = PermisoInstitucional.objects.values('id').filter(unidadorganica_id=iddepartamento[0], fechasolicitud__range=(fechainicio, fechafin)).count()
                    contaraprobadodirector = 0
                    contaraprobadouath = 0
                    permisoaprobados = PermisoInstitucional.objects.filter((Q(estadosolicitud=3) | Q(estadosolicitud=4)), unidadorganica_id=iddepartamento[0], fechasolicitud__range=(fechainicio, fechafin))
                    for permisoaprobado in permisoaprobados:
                        if permisoaprobado.contar_aprobados() == 1:
                            contaraprobadodirector += 1
                        else:
                            contaraprobadodirector += 1
                            contaraprobadouath += 1
                    listado.append([departamento.nombre, solicitada, pendiente, contaraprobadodirector, contaraprobadouath])
                return conviert_html_to_pdf('th_permiso_institucional/reportepermisosaprobado.html',{
                    'pagesize': 'A4',
                    'listado': listado,
                    'hoy': datetime.now(),
                    'fechainicio': fechainicio,
                    'fechafin': fechafin})
            except Exception as ex:
                pass


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verdetalle':
                try:
                    data = {}
                    detalle = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = detalle
                    data['detallesolicitud'] = detalle.hdaprobarsolicitud_set.all()
                    data['aprobadores'] = detalle.hdaprobarsolicitud_set.all()
                    template = get_template("helpdesk_solicitud/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'xlsaprobarpermiso':
                try:
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_aprobarpermiso.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 1000
                    ws.col(1).width = 6000
                    ws.col(2).width = 3000
                    ws.col(3).width = 3000
                    ws.col(4).width = 3000
                    ws.col(5).width = 8000
                    ws.col(6).width = 8000
                    ws.col(7).width = 3000
                    ws.col(8).width = 3000
                    ws.col(9).width = 15000
                    ws.col(10).width = 2000
                    ws.col(11).width = 15000
                    ws.col(12).width = 2000
                    ws.col(20).width = 5000

                    ws.write(0, 0, 'N.')
                    ws.write(0, 1, 'CODIGO')
                    ws.write(0, 2, 'FECHA')
                    ws.write(0, 3, 'FECHA INICIO')
                    ws.write(0, 4, 'FECHA FIN')
                    ws.write(0, 5, 'HORA INICIO')
                    ws.write(0, 6, 'HORA FIN')
                    ws.write(0, 7, 'DIAS')
                    ws.write(0, 8, 'HORAS')
                    ws.write(0, 9, 'ESTADO')
                    ws.write(0, 10, 'CEDULA')
                    ws.write(0, 11, 'SOLICITANTE')
                    ws.write(0, 12, 'DEPARTAMENTO')
                    ws.write(0, 13, 'TIPO SOLICIDUTD')
                    ws.write(0, 14, 'TIPO PERMISO')
                    ws.write(0, 15, 'DETALLE PERMISO')
                    ws.write(0, 16, 'DESCUENTO VACACIONES')
                    ws.write(0, 17, 'MOTIVO')
                    ws.write(0, 18, 'SOPORTE')
                    ws.write(0, 19, 'USUARIO')
                    ws.write(0, 20, 'CASA SALUD')

                    a = 0
                    date_format = xlwt.XFStyle()
                    fechainicio = request.GET['fechainicio']
                    fechafinal = request.GET['fechafinal']
                    date_format.num_format_str = 'yyyy/mm/dd'
                    plantillas = PermisoInstitucional.objects.filter(fechasolicitud__gte=fechainicio, fechasolicitud__lte=fechafinal).order_by('estadosolicitud', '-fechasolicitud')
                    archivos = ''
                    for per in plantillas:
                        nompersona = ''
                        if PermisoAprobacion.objects.filter(permisoinstitucional=per).exists():
                            aprobadores = PermisoAprobacion.objects.filter(permisoinstitucional=per)
                            if aprobadores.values('id').count() > 1:
                                apro = PermisoAprobacion.objects.filter(permisoinstitucional=per).order_by('-id')[0]
                                nompersona = u"%s" % apro.aprueba
                        listafini = []
                        listaffin = []
                        listahini = []
                        listahfin = []
                        diastotales = ''
                        horastotales = ''
                        permisosdetalles = PermisoInstitucionalDetalle.objects.filter(permisoinstitucional=per)
                        for perdetalles in permisosdetalles:
                            if permisosdetalles.values('id').count() > 1:
                                listafini.append(('%s-' % perdetalles.fechainicio))
                                listaffin.append(('%s-' % perdetalles.fechafin))
                                listahini.append(('%s-' % perdetalles.horainicio))
                                listahfin.append(('%s-' % perdetalles.horafin))
                            else:
                                cursor = connection.cursor()
                                cursor.execute("select CAST((fechafin-fechainicio)AS text) as dias,CAST((horafin-horainicio)AS text) as horas from sagest_PermisoInstitucionalDetalle where id="+str(perdetalles.id))
                                results = cursor.fetchall()
                                diastotales = 0;
                                for r in results:
                                    if r[0] == '0':
                                        diastotales = r[0]
                                    else:
                                        diastotales = int(r[0])+1
                                    horastotales = r[1]
                                fini = perdetalles.fechainicio
                                ffin = perdetalles.fechafin

                                listahini.append(str(perdetalles.horainicio))
                                listahfin.append(str(perdetalles.horafin))
                        a += 1
                        ws.write(a, 0, a)
                        ws.write(a, 1, per.codificacion())
                        ws.write(a, 2, per.fechasolicitud, date_format)
                        if permisosdetalles.values('id').count() == 1:
                            ws.write(a, 3, fini, date_format)
                            ws.write(a, 4, ffin, date_format)
                            ws.write(a, 5, listahini)
                            ws.write(a, 6, listahfin)
                        else:
                            ws.write(a, 3, '%s' % listafini)
                            ws.write(a, 4, '%s' % listaffin)
                            ws.write(a, 5, '%s' % listahini)
                            ws.write(a, 6, '%s' % listahfin)
                        ws.write(a, 7, diastotales)
                        ws.write(a, 8, horastotales)
                        ws.write(a, 9, per.get_estadosolicitud_display())
                        ws.write(a, 10, per.solicita.cedula)
                        ws.write(a, 11, u"%s" % per.solicita.nombre_completo())
                        ws.write(a, 12, u"%s" % per.unidadorganica.nombre)
                        ws.write(a, 13, per.get_tiposolicitud_display().upper())
                        if per.tipopermiso:
                            ws.write(a, 14, u"%s" % per.tipopermiso.descripcion)
                        else:
                            ws.write(a, 14, '')
                        if per.tipopermisodetalle:
                            ws.write(a, 15, u"%s" % per.tipopermisodetalle.descripcion)
                        else:
                            ws.write(a, 15, '')
                        if per.descuentovacaciones:
                            ws.write(a, 16, 'SI')
                        else:
                            ws.write(a, 16, 'NO')
                        ws.write(a, 17, u"%s" % per.motivo)
                        if per.archivo:
                            archivos = 'SI'
                        else:
                            archivos = 'NO'
                        ws.write(a, 18, archivos)
                        ws.write(a, 19, nompersona)
                        ws.write(a, 20, str(per.casasalud.descripcion) if per.casasalud else "")
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'detalle':
                try:
                    data = {}

                    validacion = int(request.GET['validacion'])
                    data['permisos_salud_ocupa'] = permisos_salud_ocupa = True if request.user.has_perm('sagest.ver_permisos_salud_ocupa') and not request.user.is_superuser else False
                    detalle = HdPlanAprobacion.objects.get(pk=int(request.GET['id']))
                    data['solicitud'] = detalle
                    data['detallesolicitud'] =detallepermiso= detalle.hdaprobarsolicitud_set.all()
                    data['aprobador'] = persona
                    # data['th'] = 0 if permisos_salud_ocupa else 1
                    data['fecha'] = datetime.now().date()
                    data['aprobadores'] = detalle.hdaprobarsolicitud_set.all()


                    template = get_template("helpdesk_solicitud/detalle_aprobar.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})



            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Aprobar Solicitud.'
                search = None
                excluir = []
                permisos_salud_ocupa = False

                ids = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        plantillas = HdPlanAprobacion.objects.filter(Q(solicita__nombres__icontains=search) |
                                                                         Q(solicita__apellido1__icontains=search) |
                                                                         Q(solicita__apellido2__icontains=search) |
                                                                         Q(solicita__cedula__icontains=search) |
                                                                         Q(solicita__pasaporte__icontains=search)).distinct().order_by('-fecharegistro')
                    else:
                        plantillas = HdPlanAprobacion.objects.filter(Q(solicita__apellido1__icontains=ss[0]) & Q(solicita__apellido2__icontains=ss[1])).distinct().order_by('-fechasolicitud')
                else:
                    # if permisos_salud_ocupa:
                        plantillas = HdPlanAprobacion.objects.all().order_by('estadoaprobacion', '-fecharegistro')
                        plantillas = list(chain(plantillas.filter(estadoaprobacion__in=[2,5]).order_by('estadoaprobacion'), plantillas.exclude(estadoaprobacion__in=[1,2,5]).order_by('estadoaprobacion')))
                    # else:
                    #     plantillas = PermisoInstitucional.objects.filter(estadosolicitud__gte=2).exclude(tipopermiso__in=excluir).order_by('estadosolicitud', '-fechasolicitud')
                paging = MiPaginador(plantillas, 20)
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
                data['solicitudv'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                data['permisos_salud_ocupa'] = permisos_salud_ocupa
                return render(request, 'helpdesk_solicitud/aprobar_v.html', data)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})





