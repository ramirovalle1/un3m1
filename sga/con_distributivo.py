# -*- coding: latin-1 -*-
import json
from datetime import datetime
from django.db import transaction, connection
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
import xlwt
from decorators import secure_module, last_access
from sga.commonviews import adduserdata, obtener_reporte
from sga.forms import ProfesorTipoForm
from sga.funciones import  MiPaginador, log
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import PracticasPreprofesionalesInscripcion, Profesor, Periodo, Coordinacion, \
    ProfesorDistributivoHoras, Clase, Sesion, ClaseActividadEstado, DetalleDistributivo, ClaseActividad


@login_required(redirect_field_name='ret', login_url='/loginsagest')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex

    persona = request.session['persona']
    coordinacion = []
    periodo = request.session['periodo']
    if persona.es_profesor():
        coordinacion = persona.profesor().coordinacion

    if request.method == 'POST':
        action = request.POST['action']
        if action == 'horarioactividadespdf':
            try:
                data = {}
                data['title'] = u'Horarios de las Actividades del Profesor'
                profesor = Profesor.objects.get(pk=int(request.POST['profesorid']))
                data['profesor'] = profesor
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'], [6, 'Sabado'], [7, 'Domingo']]
                hoy = datetime.now().date()
                data['misclases'] = clases = Clase.objects.filter(activo=True, fin__gte=hoy, materia__profesormateria__profesor=profesor, materia__profesormateria__principal=True).order_by('inicio')
                data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                idper=int(request.POST['periodoid'])
                data['periodo'] = Periodo.objects.get(pk=idper)
                return conviert_html_to_pdf(
                    'pro_horarios/actividades_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass
        if action == 'edittipo':
            try:
                codigo = request.POST['id']
                cod = codigo.split('_')
                profesor = Profesor.objects.get(pk=cod[0])
                distributivo = ProfesorDistributivoHoras.objects.get(periodo_id=cod[1], profesor=profesor)
                f = ProfesorTipoForm(request.POST)
                persona = profesor.persona
                if f.is_valid():
                    distributivo.nivelcategoria = f.cleaned_data['tipo']
                    distributivo.nivelescalafon = f.cleaned_data['escalafon']
                    distributivo.categoria = f.cleaned_data['categoria']
                    distributivo.dedicacion = f.cleaned_data['dedicacion']
                    distributivo.coordinacion = f.cleaned_data['coordinacion']
                    distributivo.carrera = f.cleaned_data['carrera']
                    distributivo.save(request)
                    log(u'Edito tipo en profesor distributivo horas: %s [%s]' % (distributivo, distributivo.id),request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addactividad':
            try:
                periodo = request.session['periodo']
                actividad = ClaseActividad(detalledistributivo_id=request.POST['idactividad'],
                                           tipodistributivo=request.POST['tipoactividad'],
                                           turno_id=request.POST['idturno'],
                                           dia=request.POST['iddia'],
                                           inicio=periodo.inicio,
                                           fin=periodo.fin,
                                           estadosolicitud=1)
                actividad.save(request)
                tipo = actividad.tipodistributivo
                if tipo == '1':
                    tipodes = 'DOCENCIA'
                    des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if tipo == '2':
                    tipodes = 'INVESTIGACION'
                    des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                if tipo == '3':
                    tipodes = 'GESTION'
                    des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                log(u'Adicionó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(actividad.turno),str(actividad.dia)),request, "add")
                return JsonResponse({"result": "ok", "codiactividad": actividad.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})
        elif action == 'delactividad':
            try:
                actividad = ClaseActividad.objects.get(pk=request.POST['id'])
                idactividad = actividad.id
                tipo = actividad.tipodistributivo
                if tipo == 1:
                    des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if tipo == 2:
                    des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                if tipo == 3:
                    des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                turno = actividad.turno_id
                dia = actividad.dia
                return JsonResponse({"result": "ok", 'idactividad': idactividad, 'turno': turno, 'dia': dia, 'des': des})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
        elif action == 'eliminaractividad':
            try:
                actividad = ClaseActividad.objects.get(pk=request.POST['idactividad'])
                nomturno = actividad.turno
                nomdia = actividad.dia
                if actividad.tipodistributivo == 1:
                    tipodes = 'DOCENCIA'
                    des = actividad.detalledistributivo.criteriodocenciaperiodo.criterio.nombre
                if actividad.tipodistributivo == 2:
                    tipodes = 'INVESTIGACION'
                    des = actividad.detalledistributivo.criterioinvestigacionperiodo.criterio.nombre
                if actividad.tipodistributivo == 3:
                    tipodes = 'GESTION'
                    des = actividad.detalledistributivo.criteriogestionperiodo.criterio.nombre
                actividad.delete()
                log(u'Eliminó horario de actividad: %s - %s  turno: %s dia: %s' % (des, tipodes, str(nomturno),str(nomdia)), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data = {}
        adduserdata(request, data)
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'totalactividadesdocentes':
                try:
                    periodo = request.GET['periodo']
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 1000
                    ws.col(1).width = 3000
                    ws.col(2).width = 10000
                    ws.col(3).width = 4000
                    ws.col(4).width = 10000
                    ws.col(5).width = 0
                    ws.col(6).width = 6000
                    ws.col(7).width = 2000
                    ws.col(8).width = 6000
                    ws.col(9).width = 6000
                    ws.write(0, 0, 'N.')
                    ws.write(0, 1, 'CRITERIO')
                    ws.write(0, 2, 'FACULTAD')
                    ws.write(0, 3, 'CEDULA')
                    ws.write(0, 4, 'APELLIDOS Y NOMBRES')
                    ws.write(0, 5, 'USUARIO')
                    ws.write(0, 6, 'ACTIVIDAD')
                    ws.write(0, 7, 'HORAS')
                    ws.write(0, 8, 'DEDICACION')
                    ws.write(0, 9, u'TIPO')
                    ws.write(0, 10, u'CATEGORIZACIÓN')
                    ws.write(0, 11, u'ESCALAFÓN')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente," \
                                      "cri.nombre as actividad,detdis.horas,us.username, td.nombre as dedicacion, " \
                                      "(select tipodoc.nombre from sga_profesortipo tipodoc where tipodoc.id=dis.nivelcategoria_id) as tipo, " \
                                      "(select categ.nombre from sga_categorizaciondocente categ where categ.id=dis.categoria_id) as categoria, " \
                                      "(select escalafon.nombre from sga_nivelescalafondocente escalafon where escalafon.id=dis.nivelescalafon_id) as escalafon,per.cedula " \
                                      "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                                      "sga_tiempodedicaciondocente td, " \
                                      "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                      "where dis.profesor_id=pro.id " \
                                      "and td.id=dis.dedicacion_id " \
                                      "and pro.persona_id=per.id  " \
                                      "and per.usuario_id=us.id " \
                                      "and dis.coordinacion_id=coor.id " \
                                      "and dis.id=detdis.distributivo_id " \
                                      "and detdis.criteriodocenciaperiodo_id=critd.id " \
                                      "and critd.criterio_id=cri.id " \
                                      "and detdis.criteriodocenciaperiodo_id is not null " \
                                      "and dis.periodo_id='" + periodo + "' " \
                                                                         "union all " \
                                                                         "select 'Investigacion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente, " \
                                                                         "cri.nombre as actividad,detdis.horas,us.username , td.nombre as dedicacion, " \
                                                                         "(select tipodoc.nombre from sga_profesortipo tipodoc where tipodoc.id=dis.nivelcategoria_id) as tipo, " \
                                                                         "(select categ.nombre from sga_categorizaciondocente categ where categ.id=dis.categoria_id) as categoria, " \
                                                                         "(select escalafon.nombre from sga_nivelescalafondocente escalafon where escalafon.id=dis.nivelescalafon_id) as escalafon,per.cedula " \
                                                                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                                         "sga_tiempodedicaciondocente td, " \
                                                                         "sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                         "where dis.profesor_id=pro.id  " \
                                                                         "and td.id=dis.dedicacion_id " \
                                                                         "and pro.persona_id=per.id " \
                                                                         "and per.usuario_id=us.id " \
                                                                         "and dis.coordinacion_id=coor.id " \
                                                                         "and dis.id=detdis.distributivo_id " \
                                                                         "and detdis.criterioinvestigacionperiodo_id=critd.id " \
                                                                         "and critd.criterio_id=cri.id " \
                                                                         "and detdis.criterioinvestigacionperiodo_id is not null " \
                                                                         "and dis.periodo_id='" + periodo + "' " \
                                                                                                            "union all " \
                                                                                                            "select 'Gestion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente, " \
                                                                                                            "cri.nombre as actividad,detdis.horas,us.username , td.nombre as dedicacion, " \
                                                                                                            "(select tipodoc.nombre from sga_profesortipo tipodoc where tipodoc.id=dis.nivelcategoria_id) as tipo, " \
                                                                                                            "(select categ.nombre from sga_categorizaciondocente categ where categ.id=dis.categoria_id) as categoria, " \
                                                                                                            "(select escalafon.nombre from sga_nivelescalafondocente escalafon where escalafon.id=dis.nivelescalafon_id) as escalafon,per.cedula " \
                                                                                                            "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                                                                            "sga_tiempodedicaciondocente td, " \
                                                                                                            "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                                                            "where dis.profesor_id=pro.id " \
                                                                                                            "and td.id=dis.dedicacion_id  " \
                                                                                                            "and pro.persona_id=per.id " \
                                                                                                            "and per.usuario_id=us.id " \
                                                                                                            "and dis.coordinacion_id=coor.id " \
                                                                                                            "and dis.id=detdis.distributivo_id " \
                                                                                                            "and detdis.criteriogestionperiodo_id=critd.id " \
                                                                                                            "and critd.criterio_id=cri.id " \
                                                                                                            "and detdis.criteriogestionperiodo_id is not null " \
                                                                                                            "and dis.periodo_id='" + periodo + "';"
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a)
                        ws.write(a, 1, per[0])
                        ws.write(a, 2, per[1])
                        ws.write(a, 3, per[12])
                        ws.write(a, 4, per[2] + ' ' + per[3] + ' ' + per[4])
                        ws.write(a, 5, per[7])
                        ws.write(a, 6, per[5])
                        ws.write(a, 7, per[6])
                        ws.write(a, 8, per[8])
                        ws.write(a, 9, per[9])
                        ws.write(a, 10, per[10])
                        ws.write(a, 11, per[11])
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'totalactividadesdocentesmaterias':
                try:
                    periodo = request.GET['periodo']
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_actividaddocente.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.col(0).width = 10000
                    ws.col(1).width = 4000
                    ws.col(2).width = 4000
                    ws.col(3).width = 2000
                    ws.col(4).width = 6000
                    ws.col(5).width = 6000
                    ws.col(6).width = 2000
                    ws.col(7).width = 10000
                    ws.col(8).width = 3000
                    ws.col(9).width = 3000
                    ws.col(10).width = 6000
                    ws.col(11).width = 6000
                    ws.col(12).width = 4000
                    ws.col(13).width = 6000
                    ws.col(14).width = 4000
                    ws.col(15).width = 10000
                    ws.col(16).width = 10000
                    ws.write(0, 0, 'CARRERA')
                    ws.write(0, 1, 'SECCION')
                    ws.write(0, 2, 'NIVEL')
                    ws.write(0, 3, 'PARALELO')
                    ws.write(0, 4, 'MATRICULADOS')
                    ws.write(0, 5, 'ACTIVIDADES/MATERIAS')
                    ws.write(0, 6, 'HORAS')
                    ws.write(0, 7, 'APELLIDOS Y NOMBRES')
                    ws.write(0, 8, 'CRITERIO')
                    ws.write(0, 9, 'CEDULA')
                    ws.write(0, 10, 'CORREO INSTITUCIONAL')
                    ws.write(0, 11, u'CATEGORIZACIÓN')
                    ws.write(0, 12, 'DEDICACION')
                    ws.write(0, 13, u'TIPO')
                    ws.write(0, 14, u'ESCALAFON')
                    ws.write(0, 15, 'FACULTAD')
                    ws.write(0, 16, 'TIPO PROFESOR')
                    ws.write(0, 17, 'TITULO MASTER')
                    ws.write(0, 18, 'TITULO PHD')
                    a = 0
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listaestudiante = "select 'Docencia' as criterio,coor.nombre as facultad,per.apellido1, per.apellido2 , per.nombres as docente," \
                                      "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username, td.nombre as dedicacion," \
                                      "(select categ.nombre from sga_categorizaciondocente categ where categ.id=dis.categoria_id) as categoria,null,per.cedula,per.emailinst,us.username," \
                                      "null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre),',') " \
                                      "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id " \
                                      "and tit.nivel_id=4 and tit.grado_id in(2, 5) and tc.verificado=true) as master ," \
                                      "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                      "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd, " \
                                      "(select tipodoc.nombre from sga_profesortipo tipodoc where tipodoc.id=dis.nivelcategoria_id) as tipo, " \
                                      "(select escalafon.nombre from sga_nivelescalafondocente escalafon where escalafon.id=dis.nivelescalafon_id) as escalafon,0 as insmatriculados  " \
                                      "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                                      "sga_tiempodedicaciondocente td, " \
                                      "sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                      "where dis.profesor_id=pro.id " \
                                      "and td.id=dis.dedicacion_id " \
                                      "and pro.persona_id=per.id  " \
                                      "and per.usuario_id=us.id " \
                                      "and pro.coordinacion_id=coor.id " \
                                      "and dis.id=detdis.distributivo_id " \
                                      "and detdis.criteriodocenciaperiodo_id=critd.id " \
                                      "and critd.criterio_id=cri.id " \
                                      "and detdis.criteriodocenciaperiodo_id is not null " \
                                      "and dis.periodo_id='" + periodo + "' and cri.id not in (15,16,17,18) " \
                                                                         "union all " \
                                                                         "select 'Investigacion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2, per.nombres as docente, " \
                                                                         "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username , td.nombre as dedicacion," \
                                                                         "(select categ.nombre from sga_categorizaciondocente categ where categ.id=dis.categoria_id) as categoria," \
                                                                         "null,per.cedula,per.emailinst,us.username,null as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre),',') " \
                                                                         "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id " \
                                                                         "and tit.nivel_id=4 and tit.grado_id in(2, 5) and tc.verificado=true) as master ," \
                                                                         "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                                                         "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd, " \
                                                                         "(select tipodoc.nombre from sga_profesortipo tipodoc where tipodoc.id=dis.nivelcategoria_id) as tipo, " \
                                                                         "(select escalafon.nombre from sga_nivelescalafondocente escalafon where escalafon.id=dis.nivelescalafon_id) as escalafon,0 as insmatriculados  " \
                                                                         "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                                         "sga_tiempodedicaciondocente td, " \
                                                                         "sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                         "where dis.profesor_id=pro.id  " \
                                                                         "and td.id=dis.dedicacion_id " \
                                                                         "and pro.persona_id=per.id " \
                                                                         "and per.usuario_id=us.id " \
                                                                         "and pro.coordinacion_id=coor.id " \
                                                                         "and dis.id=detdis.distributivo_id " \
                                                                         "and detdis.criterioinvestigacionperiodo_id=critd.id " \
                                                                         "and critd.criterio_id=cri.id " \
                                                                         "and detdis.criterioinvestigacionperiodo_id is not null " \
                                                                         "and dis.periodo_id='" + periodo + "' " \
                                                                                                            "union all " \
                                                                                                            "select 'Gestion' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente, " \
                                                                                                            "null,null as nivel,null, cri.nombre as actividad,detdis.horas,us.username , td.nombre as dedicacion," \
                                                                                                            "(select categ.nombre from sga_categorizaciondocente categ where categ.id=dis.categoria_id) as categoria,null," \
                                                                                                            "per.cedula,per.emailinst,us.username,null as tipoprofesor ,(SELECT array_to_string(array_agg(tit.nombre),',') " \
                                                                                                            "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id " \
                                                                                                            "and tit.nivel_id=4 and tit.grado_id in(2, 5) and tc.verificado=true) as master ," \
                                                                                                            "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit " \
                                                                                                            "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd, " \
                                                                                                            "(select tipodoc.nombre from sga_profesortipo tipodoc where tipodoc.id=dis.nivelcategoria_id) as tipo, " \
                                                                                                            "(select escalafon.nombre from sga_nivelescalafondocente escalafon where escalafon.id=dis.nivelescalafon_id) as escalafon,0 as insmatriculados  " \
                                                                                                            "from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                                                                            "sga_tiempodedicaciondocente td, " \
                                                                                                            "sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor,auth_user us " \
                                                                                                            "where dis.profesor_id=pro.id " \
                                                                                                            "and td.id=dis.dedicacion_id  " \
                                                                                                            "and pro.persona_id=per.id " \
                                                                                                            "and per.usuario_id=us.id " \
                                                                                                            "and pro.coordinacion_id=coor.id " \
                                                                                                            "and dis.id=detdis.distributivo_id " \
                                                                                                            "and detdis.criteriogestionperiodo_id=critd.id " \
                                                                                                            "and critd.criterio_id=cri.id " \
                                                                                                            "and detdis.criteriogestionperiodo_id is not null " \
                                                                                                            "and dis.periodo_id='" + periodo + "' " \
                                                                                                                                               "union all " \
                                                                                                                                               "select 'Materias' as criterio,coor.nombre as facultad,per.apellido1 , per.apellido2 , per.nombres as docente,  " \
                                                                                                                                               "mat.paralelo,nmalla.nombre as nivel,carr.nombre || ' ' || carr.mencion  as carreras, asig.nombre as actividad,mat.horassemanales,us.username ,  " \
                                                                                                                                               "(select td.nombre from sga_tiempodedicaciondocente td, sga_profesordistributivohoras dis " \
                                                                                                                                               "where td.id=dis.dedicacion_id and dis.profesor_id=pro.id and dis.periodo_id='" + periodo + "' ) as dedicacion," \
                                                                                                                                               "(select cat.nombre from sga_categorizaciondocente cat, sga_profesordistributivohoras dis " \
                                                                                                                                               "where cat.id=dis.categoria_id and dis.profesor_id=pro.id and dis.periodo_id='" + periodo + "' ) as categoria,ses.nombre as sesion, " \
                                                                                                                                               "per.cedula,per.emailinst,us.username,tipro.nombre as tipoprofesor,(SELECT array_to_string(array_agg(tit.nombre),',')  " \
                                                                                                                                               "FROM sga_titulacion tc ,sga_titulo tit where tc.titulo_id=tit.id and tc.persona_id=per.id  " \
                                                                                                                                               "and tit.nivel_id=4 and tit.grado_id in(2, 5) and tc.verificado=true) as master , " \
                                                                                                                                               "(SELECT array_to_string(array_agg(tit.nombre),',') FROM sga_titulacion tc ,sga_titulo tit  " \
                                                                                                                                               "where tc.titulo_id=tit.id and tc.persona_id=per.id and tit.nivel_id=4 and tit.grado_id=1 and tc.verificado=true) as phd," \
                                                                                                                                               "(select tipodoc.nombre from sga_profesortipo tipodoc,sga_profesordistributivohoras dis " \
                                                                                                                                               " where tipodoc.id=dis.nivelcategoria_id and dis.profesor_id=pro.id and dis.periodo_id='" + periodo + "' ) as tipo, " \
                                                                                                                                             " (select escalafon.nombre from sga_nivelescalafondocente escalafon,sga_profesordistributivohoras dis  " \
                                                                                                                                             " where escalafon.id=dis.nivelescalafon_id and dis.profesor_id=pro.id and dis.periodo_id='" + periodo + "') as escalafon,(select count(matasig.matricula_id) from sga_materiaasignada matasig,sga_matricula matri where matasig.matricula_id=matri.id and matasig.materia_id= mat.id and matri.estado_matricula in (2,3) and matasig.status=True and matri.status=True and matasig.id not in (select materiaasignada_id from sga_materiaasignadaretiro)) as insmatriculados  " \
                                                                                                                                             "from sga_profesormateria pmat,sga_materia mat,sga_nivel niv,sga_profesor pro,sga_persona per,  " \
                                                                                                                                             "sga_asignaturamalla asimalla,sga_malla malla,sga_carrera carr,sga_asignatura asig,  " \
                                                                                                                                             "sga_nivelmalla nmalla,auth_user us,sga_coordinacion_carrera corcar,sga_coordinacion coor,  " \
                                                                                                                                             "sga_sesion ses, sga_tipoprofesor tipro  " \
                                                                                                                                             "where pmat.profesor_id=pro.id  " \
                                                                                                                                             "and pro.persona_id=per.id   " \
                                                                                                                                             "and per.usuario_id=us.id  " \
                                                                                                                                             "and pmat.materia_id=mat.id  " \
                                                                                                                                             "and mat.nivel_id=niv.id and niv.sesion_id=ses.id " \
                                                                                                                                             "and mat.asignaturamalla_id=asimalla.id  " \
                                                                                                                                             "and asimalla.malla_id=malla.id  " \
                                                                                                                                             "and malla.carrera_id=carr.id  " \
                                                                                                                                             "and corcar.carrera_id=carr.id  " \
                                                                                                                                             "and corcar.coordinacion_id=coor.id  " \
                                                                                                                                             "and asimalla.asignatura_id=asig.id and asimalla.nivelmalla_id=nmalla.id and pmat.tipoprofesor_id=tipro.id  " \
                                                                                                                                             "and niv.periodo_id='" + periodo + "' ";
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, per[7])
                        ws.write(a, 1, per[13])
                        ws.write(a, 2, per[6])
                        ws.write(a, 3, per[5])
                        ws.write(a, 4, per[22])
                        ws.write(a, 5, per[8])
                        ws.write(a, 6, per[9])
                        ws.write(a, 7, per[2] + ' ' + per[3] + ' ' + per[4])
                        ws.write(a, 8, per[0])
                        ws.write(a, 9, per[14])
                        ws.write(a, 10, per[16] + '@unemi.edu.ec')
                        ws.write(a, 11, per[12])
                        ws.write(a, 12, per[11])
                        ws.write(a, 13, per[20])
                        ws.write(a, 14, per[21])
                        ws.write(a, 15, per[1])
                        ws.write(a, 16, per[17])
                        ws.write(a, 17, per[18])
                        ws.write(a, 18, per[19])
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'formaciondocentesactivos':
                try:
                    periodo = request.GET['periodo']
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_docentes activos.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
                    ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
                    ws.col(0).width = 1000
                    ws.col(1).width = 3000
                    ws.col(2).width = 10000
                    ws.col(3).width = 5000
                    ws.col(4).width = 4000
                    ws.col(5).width = 10000
                    ws.col(6).width = 4000
                    ws.col(7).width = 10000
                    ws.col(8).width = 10000
                    ws.col(9).width = 6000
                    ws.write(4, 0, 'N.')
                    ws.write(4, 1, 'CEDULA')
                    ws.write(4, 2, 'NOMBRES')
                    ws.write(4, 3, 'SEXO')
                    ws.write(4, 4, 'FECHATITULO')
                    ws.write(4, 5, 'TITULO')
                    ws.write(4, 6, 'NIVEL')
                    ws.write(4, 7, 'GRADOTITULO')
                    ws.write(4, 8, 'INSTITUCION')
                    ws.write(4, 9, 'VERIFICADO')
                    a = 4
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    listadocentes = "select distinct p.cedula,p.apellido1,p.apellido2,p.nombres, " \
                                    "d.regimenlaboral_id,ti.fechaobtencion,tit.nombre as titulo,nti.nombre as nivel, " \
                                    "gti.nombre as gradotitulo, sup.nombre as institucion,ti.verificado,sex.nombre as sexo  " \
                                    "from sagest_distributivopersona d right join  sga_persona p on p.id=d.persona_id " \
                                    "left join sga_sexo sex on p.sexo_id=sex.id left join sga_titulacion ti on ti.persona_id=p.id " \
                                    "left join sga_titulo tit on tit.id=ti.titulo_id " \
                                    "left join sga_niveltitulacion nti on nti.id=tit.nivel_id " \
                                    "left join sga_gradotitulacion gti on gti.id=tit.grado_id " \
                                    "left join sga_institucioneducacionsuperior sup on sup.id = ti.institucion_id " \
                                    "where  d.regimenlaboral_id =2 " \
                                    "and p.cedula IS NOT NULL " \
                                    "order by p.apellido1,p.apellido2,p.nombres"
                    cursor.execute(listadocentes)
                    results = cursor.fetchall()
                    for per in results:
                        a += 1
                        ws.write(a, 0, a - 4)
                        ws.write(a, 1, per[0])
                        ws.write(a, 2, per[1] + ' ' + per[2] + ' ' + per[3])
                        ws.write(a, 3, per[11])
                        ws.write(a, 4, per[5], date_format)
                        ws.write(a, 5, per[6])
                        ws.write(a, 6, per[7])
                        ws.write(a, 7, per[8])
                        ws.write(a, 8, per[9])
                        ws.write(a, 9, per[10])
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar Practicas PreProfesionales'
                    data['campo'] = PracticasPreprofesionalesInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "alu_practicaspreprofesionalesinscripcion/delete.html", data)
                except:
                    pass

            if action == 'asistencia':
                try:
                    data['title'] = u'Eliminar Practicas PreProfesionales'
                    data['campo'] = 'hghgg'
                    return render(request, "con_distributivo/asistenciaseg.html", data)
                except:
                    pass

            if action == 'edittipos':
                try:
                    data['title'] = u'Editar Tipos'
                    data['idc'] = int(request.GET['idc'])
                    data['periodolectivo'] = int(request.GET['periodolectivo'])
                    data['profesor'] = profesor = Profesor.objects.get(pk=int(request.GET['profesor']))
                    distributivo = ProfesorDistributivoHoras.objects.get(periodo_id=int(request.GET['periodolectivo']), profesor=profesor)
                    form = ProfesorTipoForm(initial={'tipo': distributivo.nivelcategoria,
                                                     'escalafon': distributivo.nivelescalafon,
                                                     'categoria': distributivo.categoria,
                                                     'dedicacion': distributivo.dedicacion,
                                                     'coordinacion': distributivo.coordinacion,
                                                     'carrera': distributivo.carrera
                                                     })
                    form.editar(distributivo.coordinacion.id)
                    data['form'] = form
                    return render(request, "con_distributivo/edittipo.html", data)
                except:
                    pass

            elif action == 'confighorarioprof':
                data['title'] = u'Horarios de las Actividades del Profesor'
                data['idprof'] = idprof = request.GET['idprof']
                data['idper'] =  request.GET['idper']
                data['idc'] =  request.GET['idc']
                data['profesor'] =profesor= Profesor.objects.get(pk=idprof)
                data['semana'] = [[1, 'Lunes'], [2, 'Martes'], [3, 'Miercoles'], [4, 'Jueves'], [5, 'Viernes'],
                                  [6, 'Sabado'], [7, 'Domingo']]
                hoy = datetime.now().date()
                data['mostrar'] = 0
                if ClaseActividadEstado.objects.values('id').filter(profesor=profesor, periodo=periodo, status=True).exists():
                    data['mostrar'] = 1
                    data['detalleestados'] = estadoactividad = ClaseActividadEstado.objects.filter(profesor=profesor,
                                                                                                   periodo=periodo,
                                                                                                   status=True)
                    data['estadoactividad'] = estadoactividad.all().order_by('-id')[0]
                # data['materiasnoprogramadas'] = ProfesorMateria.objects.filter(profesor=profesor, hasta__gt=hoy, activo=True, principal=True).exclude(materia__clase__id__isnull=False)
                data['misclases'] = clases = Clase.objects.filter(materia__nivel__periodo__visible=True, activo=True,
                                                                  fin__gte=hoy,
                                                                  materia__profesormateria__profesor=profesor,
                                                                  materia__profesormateria__principal=True).order_by(
                    'inicio')
                data['sesiones'] = Sesion.objects.filter(pk__in=[1, 4, 5], status=True).distinct()
                # data['sesiones'] = Sesion.objects.filter(turno__clase__in=clases).distinct()
                data['periodo'] = request.session['periodo']
                if not request.session['periodo'].visible:
                    return HttpResponseRedirect("/?info=Periodo Inactivo.")
                return render(request, "con_distributivo/horarios_actividades.html", data)

            elif action == 'listactividades':
                try:
                    data['idprof'] = idprof = request.GET['idprof']
                    data['profesor'] = profesor = Profesor.objects.get(pk=idprof)
                    actidocencia = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                      distributivo__periodo=periodo,
                                                                      criteriodocenciaperiodo_id__isnull=False).exclude(criteriodocenciaperiodo__criterio_id__in=['15','16','17','18','20','21','27','28','19'])
                    actiinvestigacion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                           distributivo__periodo=periodo,
                                                                           criterioinvestigacionperiodo_id__isnull=False)
                    actigestion = DetalleDistributivo.objects.filter(distributivo__profesor=profesor,
                                                                     distributivo__periodo=periodo,
                                                                     criteriogestionperiodo_id__isnull=False)
                    data['actividades'] = actidocencia | actiinvestigacion | actigestion
                    return render(request, "con_distributivo/actividadesdocentes.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            idc = None
            llenardocentes = []
            if 'idper' in request.GET:
                data['periodolectivo'] = periodolectivo = Periodo.objects.get(pk=request.GET['idper'])
            else:
                data['periodolectivo'] = periodolectivo = Periodo.objects.all().order_by("-id")[0]
            data['periodos'] = Periodo.objects.all()
            data['coordinaciones'] = coordinaciones = Coordinacion.objects.all()
            if 'idc' in request.GET:
                data['idc'] = idc = int(request.GET['idc'])
            else:
                coor = coordinaciones[0]
                data['idc'] =idc= coor.id
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                if len(ss) == 2:
                    if idc:
                        data['distributivos'] = profesores = ProfesorDistributivoHoras.objects.filter(coordinacion_id=idc,periodo_id=periodolectivo).filter(Q(profesor__persona__apellido1__icontains=ss[0]) |
                                                                                                                                                        Q(profesor__persona__apellido2__icontains=ss[1])).distinct().order_by('profesor__persona__apellido1').exclude(horasdocencia=0, horasgestion=0, horasinvestigacion=0)
                else:
                    if idc:
                        data['distributivos'] = profesores = ProfesorDistributivoHoras.objects.filter(periodo_id=periodolectivo).filter(Q(profesor__persona__apellido1__icontains=search) |
                                                                                                                                        Q(profesor__persona__apellido2__icontains=search)).distinct().order_by('profesor__persona__apellido1').exclude(horasdocencia=0, horasgestion=0, horasinvestigacion=0)
            else:
                if idc:
                    data['distributivos'] = profesores = ProfesorDistributivoHoras.objects.filter(coordinacion_id=idc, periodo=periodolectivo).order_by('-profesor__persona__usuario__is_active', 'profesor').exclude(horasdocencia=0, horasgestion=0, horasinvestigacion=0)
            paging = MiPaginador(profesores, 25)
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
            data['idc'] = idc if idc else ""
            data['reporte_1'] = obtener_reporte('hoja_vida_sagest')
            data['reporte_2'] = obtener_reporte('actividades_horas_docente_facu')
            data['reporte_3'] = obtener_reporte('actividades_horas_docente_facu_profesor')
            data['title'] = u'Distributivo Docente'
            return render(request, "con_distributivo/view.html", data)
