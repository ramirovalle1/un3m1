# -*- coding: UTF-8 -*-
import csv
import random
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from django.forms import model_to_dict
from django.contrib import messages

from xlwt import *
from decorators import secure_module
from sagest.forms import PeriodoRolForm, ArchivoPeriodoRolForm, TipoRolForm, SunovedadPeriodoRolForm
from sagest.models import PeriodoRol, NovedadPeriodoRol, DetallePeriodoRol, RubroRol, RolPago, TipoRol, DetalleSubnovedadPeriodoRol, SubnovedadPeriodoRol
from settings import EMAIL_DOMAIN, SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log
from sga.models import MONTH_CHOICES, Persona
from sga.templatetags.sga_extras import encrypt


def rango_anios():
    if PeriodoRol.objects.exists():
        inicio = datetime.now().year
        fin = PeriodoRol.objects.order_by('anio')[0].anio
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@transaction.atomic()
def view(request):
    data = {}
    anio_actual = datetime.now().year
    mes_actual = datetime.now().month
    adduserdata(request, data)
    persona = request.session['persona']
    usuario = request.user
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'add':
            try:
                form = PeriodoRolForm(request.POST, request.FILES)
                if form.is_valid():
                    registro = PeriodoRol(mes=form.cleaned_data['mes'],
                                          anio=form.cleaned_data['anio'],
                                          tiporol=form.cleaned_data['tiporol'],
                                          descripcion=form.cleaned_data['descripcion'],
                                          estado=1)
                    registro.save(request)
                    log(u'Registro Nuevo de Periodo Rol: %s' % registro, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'edit':
            try:
                form = PeriodoRolForm(request.POST, request.FILES)
                if form.is_valid():
                    registro = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                    registro.descripcion = form.cleaned_data['descripcion']
                    registro.save(request)
                    log(u'Actualizo Periodo Rol: %s' % registro, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        if action == 'novedades':
            try:
                periodorol = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                form = ArchivoPeriodoRolForm(request.POST, request.FILES)
                if form.is_valid():
                    ficheros = request.FILES.getlist('myfile')
                    if ficheros:
                        periodorol.novedadperiodorol_set.all().delete()
                        for archivo in ficheros:
                            nombre = archivo._name.split('.')[0]
                            if not RubroRol.objects.filter(id=int(nombre), status=True).exists():
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"No existe rubro %s asociado." % nombre})
                            # if periodorol.novedadperiodorol_set.filter(codigo=nombre).exists():
                            #     periodorolanterior=periodorol.novedadperiodorol_set.filter(codigo=nombre)[0]
                            #     periodorolanterior.delete()
                            novedades = NovedadPeriodoRol(archivo=archivo,
                                                          codigo=nombre,
                                                          periodo=periodorol)
                            novedades.save(request)
                    periodorol.estado = 2
                    periodorol.save(request)
                    log(u'Novedades Periodo Rol: %s' % periodorol, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        if action == 'delete':
            try:
                registro = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                registro.status = False
                registro.save(request)
                if DetalleSubnovedadPeriodoRol.objects.filter(status=True, detalleperiodorol__periodo=registro).exists():
                    subnovedades = DetalleSubnovedadPeriodoRol.objects.filter(status=True, detalleperiodorol__periodo=registro)
                    for subnovedad in subnovedades:
                        subnovedad.status=False
                        subnovedad.save(request)
                log(u'Elimino Periodo Rol: %s' % registro, request, "del")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'cerrarrol':
            try:
                registro = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                registro.estado = 5
                registro.save(request)
                log(u'Proceso Periodo Rol: %s' % registro, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al cerrar el Rol."})

        # Subnovedades
        if action == 'subnovedades':
            try:
                periodorol = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                rubrorol = RubroRol.objects.get(pk=request.POST['rubrorol'], status=True)
                form = ArchivoPeriodoRolForm(request.POST, request.FILES)
                if form.is_valid():
                    ficheros = request.FILES.getlist('myfile')
                    if ficheros:
                        # periodorol.novedadperiodorol_set.all().delete()
                        for archivo in ficheros:
                            # OJO
                            # DetallePeriodoRol.objects.filter(periodo=periodorol).delete()
                            subnovedad = SubnovedadPeriodoRol(archivo=archivo,
                                                              periodo=periodorol)
                            subnovedad.save(request)
                            datareader = csv.reader(open(subnovedad.archivo.file.name, "rU", encoding='iso-8859-1'), delimiter=';')
                            linea = 1
                            for cols in datareader:
                                a = linea
                                if linea >= 2:
                                    if Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(
                                            perfilusuario__profesor__isnull=False)), cedula__icontains=cols[0].strip()).exists():
                                        personarol = Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(
                                                                                    perfilusuario__profesor__isnull=False)),
                                                                            cedula__icontains=cols[0].strip())[0]
                                    elif Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(
                                            perfilusuario__profesor__isnull=False)), pasaporte__icontains=cols[0].strip()).exists():
                                        personarol = Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(
                                                                                    perfilusuario__profesor__isnull=False)),
                                                                            pasaporte__icontains=cols[0].strip())[0]
                                    else:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad",
                                                             "mensaje": u"Error numero de identificacion. %s no existe" % cols[0].strip()})
                                    if DetallePeriodoRol.objects.filter(periodo=periodorol, persona=personarol, rubro=rubrorol, status=True).exists():
                                        detalleperiodorol = DetallePeriodoRol.objects.get(periodo=periodorol, persona=personarol, rubro=rubrorol, status=True)
                                    else:
                                        transaction.set_rollback(True)
                                        return JsonResponse({"result": "bad", "mensaje": u"Error. En el periodo %s, la persona %s no posee el rubro %s." %
                                                                                         (periodorol, cols[0].strip(), rubrorol)})
                                    detallesubnovedad = DetalleSubnovedadPeriodoRol(
                                                                detalleperiodorol = detalleperiodorol,
                                                                descripcion=cols[1].strip(),
                                                                valor=float(cols[2].strip().replace(',', '.')))
                                    detallesubnovedad.save(request)
                                linea += 1
                        log(u'Registró subnovedades del Periodo Rol: %s' % periodorol, request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No ha seleccionado el archivo"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                messages.error(request, str(ex))
                return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

        if action == 'verificarnovedades':
            try:
                periodorol = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                DetallePeriodoRol.objects.filter(periodo=periodorol).delete()
                for novedad in NovedadPeriodoRol.objects.filter(periodo=periodorol):
                    a = 2000
                    rubro = RubroRol.objects.get(pk=int(novedad.codigo), status=True)
                    a = 2001
                    datareader = csv.reader(open(novedad.archivo.file.name, "rU", encoding='iso-8859-1'), delimiter=';')
                    a = 2002
                    linea = 1
                    a = 2003
                    for cols in datareader:
                        a = 2004
                        a = linea
                        if linea >= 2:
                            if Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)), cedula__icontains=cols[4].strip()).exists():
                                personarol = Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)), cedula__icontains=cols[4].strip())[0]
                            elif Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)), pasaporte__icontains=cols[4].strip()).exists():
                                personarol = Persona.objects.filter((Q(perfilusuario__administrativo__isnull=False) | Q(perfilusuario__profesor__isnull=False)), pasaporte__icontains=cols[4].strip())[0]
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Error numero de identificacion. %s no existe" % cols[4].strip()})
                            detalle = DetallePeriodoRol(periodo=periodorol,
                                                        persona=personarol,
                                                        rubro=rubro,
                                                        valor=float(cols[7].strip().replace(',', '.')))
                            detalle.save(request)
                        linea += 1

                periodorol.estado = 3
                periodorol.save(request)
                log(u'Verifico Novedades del Periodo Rol: %s' % periodorol, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al verificar los datos. %s" % ex.__str__()})

        if action == 'procesarnovedades':
            try:
                periodorol = PeriodoRol.objects.get(pk=request.POST['id'], status=True)
                periodorol.rolpago_set.all().delete()
                for detalle in periodorol.detalleperiodorol_set.all():
                    if periodorol.rolpago_set.filter(persona=detalle.persona).exists():
                        rolpersona = periodorol.rolpago_set.filter(persona=detalle.persona)[0]
                    else:
                        if detalle.persona.todas_mis_plantillas().exists():
                            plantilla = detalle.persona.todas_mis_plantillas()[0]
                            if not plantilla:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": "bad", "mensaje": u"Error Persona el estado %s en rubro %s." % (detalle.persona, detalle.rubro_id)})
                            denominacionpuesto = plantilla.denominacionpuesto
                            unidadorganica = plantilla.unidadorganica
                            grado = plantilla.grado
                        else:
                            denominacionpuesto = None
                            unidadorganica = None
                            grado = 0

                        rolpersona = RolPago(periodo=periodorol,
                                             persona=detalle.persona,
                                             denominacionpuesto=denominacionpuesto,
                                             unidadorganica=unidadorganica,
                                             grado=grado)
                        rolpersona.save(request)
                    if detalle.rubro.tiporubro == 1:
                        rolpersona.valoringreso += detalle.valor
                    elif detalle.rubro.tiporubro == 2:
                        rolpersona.valoregreso += detalle.valor
                    else:
                        rolpersona.valorinformativo += detalle.valor
                    rolpersona.save(request)
                periodorol.estado = 4
                periodorol.save(request)
                log(u'Proceso el Rol: %s' % periodorol, request, "edit")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al verificar los datos."})

        if action == 'detallerol':
            try:
                data['detallerol'] = registro = RolPago.objects.get(pk=int(request.POST['id']), status=True)
                data['detalleinformativo'] = registro.detallerolinformativo()
                data['detalleingreso'] = registro.detallerolingreso()
                data['detalleegreso'] = registro.detallerolegreso()
                template = get_template("th_nomina/detallerol.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        #Mantenimiento de Tipo de Rol
        if action == 'addtiporol':
            try:
                form = TipoRolForm(request.POST, request.FILES)
                registro = TipoRol()
                if form.is_valid():
                    if not TipoRol.objects.filter(descripcion=request.POST['descripcion'].upper(),status=True).exists():
                        registro.descripcion=form.cleaned_data['descripcion']
                        registro.save(request)
                        log(u'Adicionar Tipo Rol: %s' % registro, request, "addtiporol")
                        return JsonResponse({"result": False}, safe=False)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La descripcion ingresada ya existe."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al adiccionar los datos."})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al adicionar los datos."})

        if action == 'edittiporol':
            try:
                form = TipoRolForm(request.POST)
                tipo=TipoRol.objects.get(pk=int(encrypt(request.POST['id'])))
                if form.is_valid():
                    if not TipoRol.objects.filter(descripcion=request.POST['descripcion'].upper(), status=True).exclude(id=tipo.pk).exists():
                        tipo.descripcion=form.cleaned_data['descripcion']
                        tipo.save(request)
                        log(u'Edito Tipo Rol: %s' % tipo, request, "edittiporol")
                        return JsonResponse({"result":False}, safe=False)
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La descripcion ingresada ya existe."})
                else:
                    raise NameError('Error')
            except Exception as ex:
                msg =str(ex)
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. Detalle: %s" % (msg)})

        if action == 'deletetiporol':
            try:
                registro = TipoRol.objects.get(pk=request.POST['id'])
                if not registro.esta_en_periodorol():
                    registro = TipoRol.objects.get(pk=request.POST['id'])
                    registro.status = False
                    registro.save(request)
                    log(u'Elimino Tipo de Rol: %s' % registro, request, "deletetiporol")
                    return JsonResponse({"result": "ok"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"No se puede eliminar el registro por que ya se encuentra utilizado."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nomina'
                    data['form'] = PeriodoRolForm(initial={'anio': anio_actual})
                    return render(request, "th_nomina/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Modificación Periodo Rol'
                    data['actividad'] = actividad = PeriodoRol.objects.get(pk=request.GET['id'], status=True)
                    form = PeriodoRolForm(initial={'mes': actividad.mes,
                                                   'anio': actividad.anio,
                                                   'tiporol': actividad.tiporol,
                                                   'descripcion': actividad.descripcion})
                    form.editar()
                    data['form'] = form
                    return render(request, "th_nomina/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'novedades':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Novedades Periodo Rol'
                    data['actividad'] = actividad = PeriodoRol.objects.get(pk=request.GET['id'], status=True)
                    form = ArchivoPeriodoRolForm(initial={'mes': actividad.mes,
                                                          'anio': actividad.anio,
                                                          'tiporol': actividad.tiporol,
                                                          'descripcion': actividad.descripcion})
                    form.acciones()
                    data['form'] = form
                    return render(request, "th_nomina/novedades.html", data)
                except Exception as ex:
                    pass

            # Subnovedades
            if action == 'subnovedades':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Subnovedades Periodo Rol'
                    data['actividad'] = actividad = PeriodoRol.objects.get(pk=request.GET['id'], status=True)
                    form = SunovedadPeriodoRolForm(initial={'mes': actividad.mes,
                                                          'anio': actividad.anio,
                                                          'tiporol': actividad.tiporol,
                                                          'descripcion': actividad.descripcion
                                                          })
                    form.acciones()
                    data['form'] = form
                    return render(request, "th_nomina/subnovedades.html", data)
                except Exception as ex:
                    pass

            if action == 'consultar':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Consultar Periodo Rol'
                    periodorol = PeriodoRol.objects.get(pk=request.GET['idp'])
                    data['periodorol'] = periodorol
                    data['registro'] = registro = RolPago.objects.filter(periodo=periodorol)
                    data['reporte_0'] = obtener_reporte('rol_pago')
                    return render(request, "th_nomina/consultar.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Eliminar Periodo Rol'
                    data['actividade'] = PeriodoRol.objects.get(pk=request.GET['id'])
                    return render(request, 'th_nomina/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'verificarnovedades':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Verificar Novedades Periodo Rol'
                    data['actividade'] = PeriodoRol.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'th_nomina/verificar.html', data)
                except Exception as ex:
                    pass

            if action == 'procesarnovedades':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Procesar Novedades Periodo Rol'
                    data['actividad'] = PeriodoRol.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'th_nomina/procesarnovedades.html', data)
                except Exception as ex:
                    pass

            if action == 'cerrarrol':
                try:
                    # puede_realizar_accion(request, 'sagest.puede_modificar_periodo')
                    data['title'] = u'Aprobar Rol Pago'
                    data['actividad'] = PeriodoRol.objects.get(pk=request.GET['id'], status=True)
                    return render(request, 'th_nomina/cerrarrol.html', data)
                except Exception as ex:
                    pass

            if action == 'descargar':
                try:
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    ws.write_merge(0, 0, 0, 7, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=empleados_' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"NRO DE IDENTIFICACION", 6000),
                        (u"APELLIDOS Y NOMBRES", 6000),
                        (u"FECHA INGRESO A INSTITUCION", 6000),
                        (u"FECHA DE NACIMIENTO", 6000),
                        (u"SEXO", 6000),
                        (u"DISCAPACIDAD", 6000),
                        (u"TIPO DE DISCAPACIDAD", 6000),
                        (u"PORCENTAJE DISCAPACIDAD", 12000),
                        (u"CARNET DEL CONADIS", 12000),
                        (u"INSTRUCCIÓN FORMAL", 6000),
                        (u"TITULO ACADEMICO", 6000),
                        (u"INDICE BIOMETRICO", 6000),
                        (u"ETNIA", 6000),
                        (u"TIPO SANGRE", 6000),
                        (u"EMAIL PERSONAL", 6000),
                        (u"EMAIL INSTITUCIONAL", 6000),
                        (u"DIRECCION DOMICILIARIA", 6000),
                        (u"PAIS ORIGEN", 6000),
                        (u"PROVINCIA", 6000),
                        (u"CANTON", 6000),
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    # lista_json = []
                    # data = {}
                    sql = "select p.cedula as numero_identificacion, (p.apellido1|| ' ' ||p.apellido2|| ' ' ||p.nombres) as apellidos_nombre, ad.fechaingreso as fecha_ingreso_institucion, p.nacimiento, " \
                          " (case p.sexo_id when 1 then 'FEMENINO' else 'MASCULINO' end) as sexo , (case pi.tienediscapacidad when 'true' then 'SI' else 'NO' end) as tiene_discapacidad, " \
                          " COALESCE((select di.nombre from sga_discapacidad di where di.id=pi.tipodiscapacidad_id),'') as discapacidad, pi.porcientodiscapacidad as porcentaje_discapacidad, " \
                          " pi.carnetdiscapacidad as carnet_conadis, " \
                          " COALESCE((select nt1.nombre from sga_titulacion t1, sga_titulo ti1, sga_niveltitulacion nt1 where t1.persona_id=p.id and t1.principal=true and t1.titulo_id=ti1.id and nt1.id=ti1.nivel_id),'') as instriccion_formal, " \
                          " COALESCE((select ti1.nombre from sga_titulacion t1, sga_titulo ti1 where t1.persona_id=p.id and t1.principal=true and t1.titulo_id=ti1.id),'') as titulo_academico, " \
                          " p.identificacioninstitucion as indice_biometrico, " \
                          " COALESCE((select r1.nombre from sga_raza r1 where r1.id=pi.raza_id),'') as etnia, " \
                          " COALESCE((select ts1.sangre from sga_tiposangre ts1 where ts1.id=p.sangre_id),'') as tipo_sangre,p.email as email_personal, " \
                          " p.emailinst as email_institucional,(p.direccion||' '||p.direccion2) as direccion_domiciliaria, " \
                          " (select pa1.nombre from sga_pais pa1 where pa1.id=p.paisnacimiento_id) as pais_origen, " \
                          " (select pr1.nombre from sga_provincia pr1 where pr1.id=p.provincia_id) as provincia, " \
                          " (select ca1.nombre from sga_canton ca1 where ca1.id=p.canton_id) as canton " \
                          " from sga_persona p, auth_user usua, sagest_distributivopersona d , sga_administrativo ad, sga_perfilinscripcion pi " \
                          " where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and usua.id=p.usuario_id and ad.persona_id=p.id and d.regimenlaboral_id in (1,4) and pi.persona_id=p.id " \
                          " union " \
                          " select p.cedula as numero_identificacion, (p.apellido1|| ' ' ||p.apellido2|| ' ' ||p.nombres) as apellidos_nombre, pr.fechaingreso as fecha_ingreso_institucion, p.nacimiento, " \
                          " (case p.sexo_id when 1 then 'FEMENINO' else 'MASCULINO' end) as sexo , (case pi.tienediscapacidad when 'true' then 'SI' else 'NO' end) as tiene_discapacidad, " \
                          " COALESCE((select di.nombre from sga_discapacidad di where di.id=pi.tipodiscapacidad_id),'') as discapacidad, pi.porcientodiscapacidad as porcentaje_discapacidad, " \
                          " pi.carnetdiscapacidad as carnet_conadis, " \
                          " COALESCE((select nt1.nombre from sga_titulacion t1, sga_titulo ti1, sga_niveltitulacion nt1 where t1.persona_id=p.id and t1.principal=true and t1.titulo_id=ti1.id and nt1.id=ti1.nivel_id),'') as instriccion_formal, " \
                          " COALESCE((select ti1.nombre from sga_titulacion t1, sga_titulo ti1 where t1.persona_id=p.id and t1.principal=true and t1.titulo_id=ti1.id),'') as titulo_academico, " \
                          " p.identificacioninstitucion as indice_biometrico, " \
                          " COALESCE((select r1.nombre from sga_raza r1 where r1.id=pi.raza_id),'') as etnia, " \
                          " COALESCE((select ts1.sangre from sga_tiposangre ts1 where ts1.id=p.sangre_id),'') as tipo_sangre,p.email as email_personal, " \
                          " p.emailinst as email_institucional,(p.direccion||' '||p.direccion2) as direccion_domiciliaria, " \
                          " (select pa1.nombre from sga_pais pa1 where pa1.id=p.paisnacimiento_id) as pais_origen, " \
                          " (select pr1.nombre from sga_provincia pr1 where pr1.id=p.provincia_id) as provincia, " \
                          " (select ca1.nombre from sga_canton ca1 where ca1.id=p.canton_id) as canton " \
                          " from sga_persona p, auth_user usua, sagest_distributivopersona d , sga_profesor pr, sga_perfilinscripcion pi " \
                          " where p.id=d.persona_id and d.status=true and d.estadopuesto_id=1 and usua.id=p.usuario_id and pr.persona_id=p.id and d.regimenlaboral_id in (2) " \
                          " and pi.persona_id=p.id order by apellidos_nombre; "


                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0
                        campo1 = r[0]
                        campo2 = r[1]
                        campo3 = r[2]
                        campo4 = r[3]
                        campo5 = r[4]
                        campo6 = r[5]
                        campo7 = r[6]
                        campo8 = r[7]
                        campo9 = r[8]
                        campo10 = r[9]
                        campo11 = r[10]
                        campo12 = r[11]
                        campo13 = r[12]
                        campo14 = r[13]
                        campo15 = r[14]
                        campo16 = r[15]
                        campo17 = r[16]
                        campo18 = r[17]
                        campo19 = r[18]
                        campo20 = r[19]
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, style1)
                        ws.write(row_num, 3, campo4, style1)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, campo9, font_style2)
                        ws.write(row_num, 9, campo10, font_style2)
                        ws.write(row_num, 10, campo11, font_style2)
                        ws.write(row_num, 11, campo12, font_style2)
                        ws.write(row_num, 12, campo13, font_style2)
                        ws.write(row_num, 13, campo14, font_style2)
                        ws.write(row_num, 14, campo15, font_style2)
                        ws.write(row_num, 15, campo16, font_style2)
                        ws.write(row_num, 16, campo17, font_style2)
                        ws.write(row_num, 17, campo18, font_style2)
                        ws.write(row_num, 18, campo19, font_style2)
                        ws.write(row_num, 19, campo20, font_style2)
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            # Tipo Rol
            if action == 'tiposrol':
                data['title'] = u'Tipo Rol'
                search = None
                tipos = TipoRol.objects.filter(status=True)
                if 's' in request.GET:
                    search = request.GET['s']
                    tipos = tipos.filter(  Q(descripcion__icontains=search))

                paging = MiPaginador(tipos, 20)
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
                data['tipos'] = page.object_list
                data['email_domain'] = EMAIL_DOMAIN
                return render(request, 'th_nomina/tiporol.html', data)

            if action == 'addtiporol':
                try:
                    data['title'] = u'Adiccionar Tipo Rol'
                    data['form2'] = TipoRolForm()
                    data['action'] = action
                    template = get_template("th_nomina/modal/modal_tipo_rol.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al adicionar los datos."})

            if action == 'edittiporol':
                try:
                    data['title'] = u'Editar Modalidad'
                    data['tipo'] = tipo = TipoRol.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['id'] = int(encrypt(request.GET['id']))
                    data['form2'] = TipoRolForm(initial=model_to_dict(tipo))
                    data['action'] = action
                    template = get_template("th_nomina/modal/modal_tipo_rol.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al editar los datos."})

            if action == 'deletetiporol':
                try:
                    data['title'] = u'Eliminar Tipo Rol '
                    data['tipo'] = TipoRol.objects.get(pk=encrypt(request.GET['id']))
                    data['action'] = action
                    return render(request, 'th_nomina/deletetiporol.html', data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Nomina'
            search = None
            ids = None
            data['anios'] = anios = rango_anios()
            request.session['messelect'] = mes_actual
            if 'mes' in request.GET:
                request.session['messelect'] = mes_actual = int(request.GET['mes'])
            if 'anio' in request.GET:
                request.session['anioperiodorol'] = int(request.GET['anio'])
            if 'anioperiodorol' not in request.session:
                request.session['anioperiodorol'] = anios[0]
            data['anioselect'] = anioselect = request.session['anioperiodorol']
            data['messelect'] = mes_actual

            if 's' in request.GET:
                search = request.GET['s']
            if search:
                plantillas = PeriodoRol.objects.filter(Q(descripcion__icontains=search) | Q(tiporol__descripcion__icontains=search), anio=anioselect, status=True, mes=mes_actual).order_by('estado', 'anio', '-mes', 'descripcion').distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                plantillas = PeriodoRol.objects.filter(id=ids, anio=anioselect, status=True, mes=mes_actual).order_by('estado', 'anio', '-mes', 'descripcion').distinct()
            else:
                plantillas = PeriodoRol.objects.filter(anio=anioselect, status=True, mes=mes_actual).order_by('estado', 'anio', '-mes', 'descripcion').distinct()
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
            data['actividades'] = page.object_list
            data['email_domain'] = EMAIL_DOMAIN
            data['meses'] = MONTH_CHOICES
            return render(request, 'th_nomina/view.html', data)