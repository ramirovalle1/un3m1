# -*- coding: latin-1 -*-
from decimal import Decimal
import random
import xlwt
from xlwt import *
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection, connections
from django.db.models import Count
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import easyxf, XFStyle
from django.db.models.functions import ExtractYear
from decorators import secure_module, last_access
from sagest.models import datetime
from sga.commonviews import adduserdata
from sga.models import Carrera, Periodo, Inscripcion, Graduado, ProfesorMateria


def rango_anios():
    if Periodo.objects.exists():
        inicio = datetime.now().year
        fin = Periodo.objects.order_by('inicio')[0].inicio.year
        return range(inicio, fin - 1, -1)
    return [datetime.now().date().year]


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    carreras_admision1 = ''
    for c in Carrera.objects.filter(coordinacion__id=9):
        carreras_admision1 = carreras_admision1 +  str(c.id)+","
    carreras_admision1=carreras_admision1[0: len(str(carreras_admision1)) - 1]

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'produccionacademica':
            try:
                data['title'] = "PRODUCCIÓN ACADÉMICA"
                idanio = request.POST['idanio']
                idperiodo = request.POST['idperiodo']
                idcarrera = request.POST['idcarrera']
                cursor = connections['sga_select'].cursor()
                # variable numero de profesores
                sqlprofesor = "select tabla.cedula, tabla.nombre from " \
                              " (select distinct per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                              " sga_tiempodedicaciondocente td, sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                              " sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma " \
                              " where dis.profesor_id=pro.id and pm.principal=true and td.id=dis.dedicacion_id and pro.persona_id=per.id  and dis.coordinacion_id=coor.id " \
                              " and dis.id=detdis.distributivo_id and detdis.criteriodocenciaperiodo_id=critd.id and critd.criterio_id=cri.id " \
                              " and detdis.criteriodocenciaperiodo_id is not null and dis.periodo_id=pe.id and pm.status=true and m.id=pm.materia_id and m.status=true " \
                              " and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and pe.id=n.periodo_id and pe.status=true " \
                              " and n.status=true and n.periodo_id=dis.periodo_id and pm.profesor_id=dis.profesor_id and ma.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id="+ idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and ma.carrera_id="+ idcarrera
                sqlprofesor = sqlprofesor + " union " \
                                            " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                            " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                            " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                            " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                            " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                            " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                            " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                            " and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id="+ idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and addc.carrera_id="+ idcarrera
                sqlprofesor = sqlprofesor + " union " \
                                            " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                            " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                            " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                            " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                            " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                            " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                            " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                            " and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                sqlprofesor = sqlprofesor + ") as tabla order by tabla.nombre"
                cursor.execute(sqlprofesor)
                nprofesores = 0
                profesores_cursor = cursor.fetchall()
                for per in profesores_cursor:
                    nprofesores += 1
                data['nprofesores'] = nprofesores
                data['profesores_cursor'] = profesores_cursor
                # variable sjr
                sqlsjr = "select distinct pa.articulo_id,ai.sjr from sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma, sga_periodo p, sga_participantesarticulos pa, sga_articuloinvestigacion ai, sga_articulosbaseindexada ab, sga_baseindexadainvestigacion bi " \
                         " where pm.status=true and pm.principal=true and m.id=pm.materia_id and m.status=true and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and p.id=n.periodo_id and p.status=true and n.status=true and pa.profesor_id=pm.profesor_id and pa.status=true and ai.id=pa.articulo_id and ai.status=true and ai.id=ab.articulo_id and ab.status=true and " \
                         " ma.carrera_id not in ("+ str(carreras_admision1) +") and p.tipo_id=2 and bi.id=ab.baseindexada_id and bi.status=true and bi.tipo=2 and ai.sjr!='' and ai.sjr!='0' and ai.fechapublicacion BETWEEN p.inicio and p.fin "
                if idanio != '0':
                    sqlsjr = sqlsjr + " and extract(year from p.inicio)=" + idanio
                if idperiodo != '0':
                    sqlsjr = sqlsjr + " and n.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlsjr = sqlsjr + " and ma.carrera_id=" + idcarrera
                cursor.execute(sqlsjr)
                sjracumulado = 0
                sjrcontar = 0
                for sjr in cursor.fetchall():
                    sjracumulado = sjracumulado + (1+(Decimal(3.61).quantize(Decimal('.0001'))*Decimal(sjr[1]).quantize(Decimal('.0001'))))
                    sjrcontar += 1
                try:
                    sjrindicador = sjracumulado / nprofesores
                except ZeroDivisionError:
                    sjrindicador = 0
                data['sjracumulado'] = sjracumulado
                data['sjrcontar'] = sjrcontar
                data['sjrindicador'] = sjrindicador
                # variable sjr no tienen
                sqlsjr = "select distinct ai.nombre from sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma, sga_periodo p, sga_participantesarticulos pa, sga_articuloinvestigacion ai, sga_articulosbaseindexada ab, sga_baseindexadainvestigacion bi " \
                         " where pm.status=true and pm.principal=true and m.id=pm.materia_id and m.status=true and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and p.id=n.periodo_id and p.status=true and n.status=true and pa.profesor_id=pm.profesor_id and pa.status=true and ai.id=pa.articulo_id and ai.status=true and ai.id=ab.articulo_id and ab.status=true and " \
                         " ma.carrera_id not in ("+ str(carreras_admision1) +") and p.tipo_id=2 and ai.fechapublicacion BETWEEN p.inicio and p.fin and bi.id=ab.baseindexada_id and bi.status=true and bi.tipo=2 and not (ai.sjr!='' and ai.sjr!='0')"
                if idanio != '0':
                    sqlsjr = sqlsjr + " and extract(year from p.inicio)=" + idanio
                if idperiodo != '0':
                    sqlsjr = sqlsjr + " and n.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlsjr = sqlsjr + " and ma.carrera_id=" + idcarrera
                cursor.execute(sqlsjr)
                sjrnotiene_cursor = cursor.fetchall()
                sjrnotiene = 0
                for sjr in sjrnotiene_cursor:
                    sjrnotiene += 1
                data['sjrnotiene'] = sjrnotiene
                data['sjrnotiene_cursor'] = sjrnotiene_cursor

                # articulos sin base
                sqlsinbase = "select distinct ai.nombre from sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma, sga_periodo p, sga_participantesarticulos pa, sga_articuloinvestigacion ai " \
                             " where pm.status=true and pm.principal=true and m.id=pm.materia_id and m.status=true and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and p.id=n.periodo_id and p.status=true and " \
                             " ma.carrera_id not in ("+ str(carreras_admision1) +") and p.tipo_id=2 and  n.status=true and pa.profesor_id=pm.profesor_id and pa.status=true and ai.id=pa.articulo_id and ai.status=true and ai.fechapublicacion BETWEEN p.inicio and p.fin "
                if idanio != '0':
                    sqlsinbase = sqlsinbase + " and extract(year from p.inicio)=" + idanio
                if idperiodo != '0':
                    sqlsinbase = sqlsinbase + " and n.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlsinbase = sqlsinbase + " and ma.carrera_id=" + idcarrera
                sqlsinbase = sqlsinbase + " and ai.id not in (select bi.articulo_id from sga_articulosbaseindexada bi where bi.status=true and bi.articulo_id=ai.id)"

                cursor.execute(sqlsinbase)
                sjrnobase = 0
                sjrnobase_cursor = cursor.fetchall()
                for sjr in sjrnobase_cursor:
                    sjrnobase += 1
                data['sjrnobase'] = sjrnobase
                data['sjrnobase_cursor'] = sjrnobase_cursor

                data['anio'] = idanio
                data['periodo'] = None
                if idperiodo != '0':
                    data['periodo'] = Periodo.objects.filter(pk=int(idperiodo))[0]
                data['carrera'] = None
                if idcarrera != '0':
                    data['carrera'] = Carrera.objects.filter(pk=int(idcarrera))[0]

                template = get_template("adm_indicadores/produccionacademica.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Datos en la Carrera no existe."})

        if action == 'formacionposgrado':
            try:
                data['title'] = "AFINIDAD FORMACIÓN POSGRADO"
                idanio = request.POST['idanio']
                idperiodo = request.POST['idperiodo']
                idcarrera = request.POST['idcarrera']
                cursor = connections['sga_select'].cursor()
                # variable asignaturas con profesores con titulo de phd
                sql = "select ca.nombre, am.nivelmalla_id , a.nombre from sga_profesormateria pm, sga_materia m, sga_asignatura a, sga_profesor p, sga_titulacion t, sga_asignaturamalla am, " \
                      " sga_malla ma, sga_carrera ca, sga_titulo ti, sga_nivel n, sga_periodo pe where pm.status=true and pm.afinidad=true and pm.principal=true and pm.materia_id=m.id and m.status=true " \
                      " and a.id=m.asignatura_id and a.status=true and p.id=pm.profesor_id and p.status=true and p.persona_id=t.persona_id and t.status=true " \
                      " and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and ca.id=ma.carrera_id and ca.status=true" \
                      " and ti.id=t.titulo_id and ti.status=true and n.id=m.nivel_id and n.status=true and n.periodo_id=pe.id and pe.status=true and ti.grado_id in (1,4) "
                if idanio != '0':
                    sql = sql + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sql = sql + " and pe.id="+ idperiodo
                if idcarrera != '0':
                    sql = sql + " and ca.id="+ idcarrera
                sql = sql + "GROUP BY ca.nombre, am.nivelmalla_id , a.nombre order by ca.nombre, am.nivelmalla_id , a.nombre"
                cursor.execute(sql)
                nasignaturaphd = 0
                asignaturaphd_cursor = cursor.fetchall()
                for per in asignaturaphd_cursor:
                    nasignaturaphd += 1
                data['nasignaturaphd'] = nasignaturaphd
                data['asignaturaphd_cursor'] = asignaturaphd_cursor

                # variable asignaturas con profesores con titulo de msc o especialidad
                sql = "select ca.nombre, am.nivelmalla_id , a.nombre from sga_profesormateria pm, sga_materia m, sga_asignatura a, sga_profesor p, sga_titulacion t, sga_asignaturamalla am, " \
                      " sga_malla ma, sga_carrera ca, sga_titulo ti, sga_nivel n, sga_periodo pe where pm.status=true and pm.afinidad=true and pm.principal=true and pm.materia_id=m.id and m.status=true " \
                      " and a.id=m.asignatura_id and a.status=true and p.id=pm.profesor_id and p.status=true and p.persona_id=t.persona_id and t.status=true " \
                      " and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and ca.id=ma.carrera_id and ca.status=true" \
                      " and ti.id=t.titulo_id and ti.status=true and n.id=m.nivel_id and n.status=true and n.periodo_id=pe.id and pe.status=true and ti.grado_id in (2,5)"
                if idanio != '0':
                    sql = sql + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sql = sql + " and pe.id="+ idperiodo
                if idcarrera != '0':
                    sql = sql + " and ca.id="+ idcarrera
                sql = sql + "GROUP BY ca.nombre, am.nivelmalla_id , a.nombre order by ca.nombre, am.nivelmalla_id , a.nombre"
                cursor.execute(sql)
                nasignaturamsc = 0
                asignaturamsc_cursor = cursor.fetchall()
                for per in asignaturamsc_cursor:
                    nasignaturamsc += 1
                data['nasignaturamsc'] = nasignaturamsc
                data['asignaturamsc_cursor'] = asignaturamsc_cursor

                # variable asignaturas todas
                sql = "select ca.nombre, am.nivelmalla_id, a.nombre from sga_profesormateria pm, sga_materia m, sga_asignatura a, sga_profesor p, sga_asignaturamalla am, sga_malla ma, sga_carrera ca, sga_nivel n, sga_periodo pe " \
                      " where pm.status=true and pm.principal=true and pm.materia_id=m.id and m.status=true and a.id=m.asignatura_id and a.status=true and " \
                      " p.id=pm.profesor_id and p.status=true and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and ca.id=ma.carrera_id " \
                      " and ca.status=true and n.id=m.nivel_id and n.status=true and n.periodo_id=pe.id and pe.status=true"
                if idanio != '0':
                    sql = sql + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sql = sql + " and pe.id="+ idperiodo
                if idcarrera != '0':
                    sql = sql + " and ca.id="+ idcarrera
                cursor.execute(sql)
                nasignatura = 0
                asignatura_cursor = cursor.fetchall()
                for per in asignatura_cursor:
                    nasignatura += 1
                data['nasignatura'] = nasignatura
                data['asignatura_cursor'] = asignatura_cursor

                data['anio'] = idanio
                data['periodo'] = None
                if idperiodo != '0':
                    data['periodo'] = Periodo.objects.filter(pk=int(idperiodo))[0]
                data['carrera'] = None
                if idcarrera != '0':
                    data['carrera'] = Carrera.objects.filter(pk=int(idcarrera))[0]
                try:
                    indicador = (( ((Decimal(1.5).quantize(Decimal('.0001'))) * (Decimal(nasignaturaphd).quantize(Decimal('.0001')))) + (Decimal(nasignaturamsc).quantize(Decimal('.0001'))) ) / (Decimal(nasignatura).quantize(Decimal('.0001'))))
                except:
                    indicador = 0
                data['indicador'] = indicador

                template = get_template("adm_indicadores/formacionposgrado.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Datos en la Carrera no existe."})

        if action == 'titularidad':
            try:
                data['title'] = "TITULARIDAD"
                idanio = request.POST['idanio']
                idperiodo = request.POST['idperiodo']
                idcarrera = request.POST['idcarrera']
                cursor = connections['sga_select'].cursor()
                # variable numero de profesores todos
                sqlprofesor = "select tabla.cedula, tabla.nombre from " \
                              " (select distinct per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                              " sga_tiempodedicaciondocente td, sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                              " sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma " \
                              " where dis.profesor_id=pro.id and pm.principal=true and td.id=dis.dedicacion_id and pro.persona_id=per.id  and dis.coordinacion_id=coor.id " \
                              " and dis.id=detdis.distributivo_id and detdis.criteriodocenciaperiodo_id=critd.id and critd.criterio_id=cri.id " \
                              " and detdis.criteriodocenciaperiodo_id is not null and dis.periodo_id=pe.id and pm.status=true and m.id=pm.materia_id and m.status=true " \
                              " and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and pe.id=n.periodo_id and pe.status=true " \
                              " and n.status=true and n.periodo_id=dis.periodo_id and pm.profesor_id=dis.profesor_id and ma.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id="+ idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and ma.carrera_id="+ idcarrera
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)="+ idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id="+ idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id="+ idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo

                sqlprofesor = sqlprofesor + ") as tabla order by tabla.nombre"
                cursor.execute(sqlprofesor)
                nprofesores = 0
                profesores_cursor = cursor.fetchall()
                for per in profesores_cursor:
                    nprofesores += 1
                data['nprofesores'] = nprofesores
                data['profesores_cursor'] = profesores_cursor

                # variable numero de profesores titulares
                sqlprofesortitular = "select tabla.cedula, tabla.nombre from " \
                                     " (select distinct per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                     " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                                     " sga_tiempodedicaciondocente td, sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                     " sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma " \
                                     " where dis.profesor_id=pro.id and pm.principal=true and td.id=dis.dedicacion_id and pro.persona_id=per.id  and dis.coordinacion_id=coor.id " \
                                     " and dis.id=detdis.distributivo_id and detdis.criteriodocenciaperiodo_id=critd.id and critd.criterio_id=cri.id " \
                                     " and detdis.criteriodocenciaperiodo_id is not null and dis.periodo_id=pe.id and pm.status=true and m.id=pm.materia_id and m.status=true " \
                                     " and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and pe.id=n.periodo_id and pe.status=true " \
                                     " and n.status=true and dis.nivelcategoria_id=1  and n.periodo_id=dis.periodo_id and pm.profesor_id=dis.profesor_id and ma.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesortitular = sqlprofesortitular + " and extract(year from pe.inicio)="+ idanio
                if idperiodo != '0':
                    sqlprofesortitular = sqlprofesortitular + " and dis.periodo_id="+ idperiodo
                if idcarrera != '0':
                    sqlprofesortitular = sqlprofesortitular + " and ma.carrera_id="+ idcarrera
                sqlprofesortitular = sqlprofesortitular + " union "
                if idcarrera != '0':
                    sqlprofesortitular = sqlprofesortitular + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                              " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                              " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                              " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                              " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                              " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                              " and dis.nivelcategoria_id=1  and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesortitular = sqlprofesortitular + " and extract(year from pe.inicio)="+ idanio
                    if idperiodo != '0':
                        sqlprofesortitular = sqlprofesortitular + " and dis.periodo_id="+ idperiodo
                    if idcarrera != '0':
                        sqlprofesortitular = sqlprofesortitular + " and addc.carrera_id="+ idcarrera
                else:
                    sqlprofesortitular = sqlprofesortitular + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                              " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                              " sga_actividaddetalledistributivo add " \
                                                              " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                              " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                              " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                              " and dis.nivelcategoria_id=1  and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesortitular = sqlprofesortitular + " and extract(year from pe.inicio)="+ idanio
                    if idperiodo != '0':
                        sqlprofesortitular = sqlprofesortitular + " and dis.periodo_id="+ idperiodo
                sqlprofesortitular = sqlprofesortitular + " union "
                if idcarrera != '0':
                    sqlprofesortitular = sqlprofesortitular +" select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                             " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                             " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                             " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                             " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                             " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                             " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                             " and dis.nivelcategoria_id=1 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesortitular = sqlprofesortitular + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesortitular = sqlprofesortitular + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesortitular = sqlprofesortitular + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesortitular = sqlprofesortitular +" select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                             " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                             " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                             " sga_actividaddetalledistributivo add " \
                                                             " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                             " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                             " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                             " and dis.nivelcategoria_id=1 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesortitular = sqlprofesortitular + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesortitular = sqlprofesortitular + " and dis.periodo_id=" + idperiodo

                sqlprofesortitular = sqlprofesortitular + ") as tabla order by tabla.nombre"
                cursor.execute(sqlprofesortitular)
                nprofesorestitular = 0
                profesorestitular_cursor = cursor.fetchall()
                for per in profesorestitular_cursor:
                    nprofesorestitular += 1
                data['nprofesorestitular'] = nprofesorestitular
                data['profesorestitular_cursor'] = profesorestitular_cursor

                data['anio'] = idanio
                data['periodo'] = None
                if idperiodo != '0':
                    data['periodo'] = Periodo.objects.filter(pk=int(idperiodo))[0]
                data['carrera'] = None
                if idcarrera != '0':
                    data['carrera'] = Carrera.objects.filter(pk=int(idcarrera))[0]

                try:
                    sjrindicador = (Decimal(nprofesorestitular).quantize(Decimal('.0001')) / Decimal(nprofesores).quantize(Decimal('.0001')))*100
                except:
                    sjrindicador = 0
                data['sjrindicador'] = sjrindicador

                template = get_template("adm_indicadores/titularidad1.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'estudianteprofesor':
            try:
                data['title'] = "ESTUDIANTES POR PROFESOR"
                idanio = request.POST['idanio']
                idperiodo = request.POST['idperiodo']
                idcarrera = request.POST['idcarrera']
                cursor = connections['sga_select'].cursor()
                # variable numero de profesores tiempo completo
                sqlprofesor = "select tabla.cedula, tabla.nombre from " \
                              " (select distinct per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                              " sga_tiempodedicaciondocente td, sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                              " sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma " \
                              " where dis.profesor_id=pro.id and pm.principal=true and td.id=dis.dedicacion_id and pro.persona_id=per.id  and dis.coordinacion_id=coor.id " \
                              " and dis.id=detdis.distributivo_id and detdis.criteriodocenciaperiodo_id=critd.id and critd.criterio_id=cri.id " \
                              " and detdis.criteriodocenciaperiodo_id is not null and dis.periodo_id=pe.id and pm.status=true and m.id=pm.materia_id and m.status=true " \
                              " and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and pe.id=n.periodo_id and pe.status=true " \
                              " and dis.dedicacion_id=1 and n.status=true and n.periodo_id=dis.periodo_id and pm.profesor_id=dis.profesor_id and ma.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and ma.carrera_id=" + idcarrera
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=1 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=1 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=1 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=1 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo

                sqlprofesor = sqlprofesor + ") as tabla order by tabla.nombre"
                cursor.execute(sqlprofesor)
                nprofesorestiempocompleto = 0
                profesorestiempocompleto_cursor = cursor.fetchall()
                for per in profesorestiempocompleto_cursor:
                    nprofesorestiempocompleto += 1
                data['nprofesorestiempocompleto'] = nprofesorestiempocompleto
                data['profesorestiempocompleto_cursor'] = profesorestiempocompleto_cursor

                # variable numero de profesores medio tiempo
                sqlprofesor = "select tabla.cedula, tabla.nombre from " \
                              " (select distinct per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                              " sga_tiempodedicaciondocente td, sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                              " sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma " \
                              " where dis.profesor_id=pro.id and pm.principal=true and td.id=dis.dedicacion_id and pro.persona_id=per.id  and dis.coordinacion_id=coor.id " \
                              " and dis.id=detdis.distributivo_id and detdis.criteriodocenciaperiodo_id=critd.id and critd.criterio_id=cri.id " \
                              " and detdis.criteriodocenciaperiodo_id is not null and dis.periodo_id=pe.id and pm.status=true and m.id=pm.materia_id and m.status=true " \
                              " and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and pe.id=n.periodo_id and pe.status=true " \
                              " and dis.dedicacion_id=2 and n.status=true and n.periodo_id=dis.periodo_id and pm.profesor_id=dis.profesor_id and ma.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and ma.carrera_id=" + idcarrera
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=2 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=2 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=2 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=2 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo

                sqlprofesor = sqlprofesor + ") as tabla order by tabla.nombre"
                cursor.execute(sqlprofesor)
                nprofesoresmediotiempo = 0
                profesoresmediotiempo_cursor = cursor.fetchall()
                for per in profesoresmediotiempo_cursor:
                    nprofesoresmediotiempo += 1
                data['nprofesoresmediotiempo'] = nprofesoresmediotiempo
                data['profesoresmediotiempo_cursor'] = profesoresmediotiempo_cursor



                # variable numero de profesores tiempo parcial
                sqlprofesor = "select tabla.cedula, tabla.nombre from " \
                              " (select distinct per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                              " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriodocenciaperiodo critd, " \
                              " sga_tiempodedicaciondocente td, sga_criteriodocencia cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                              " sga_profesormateria pm, sga_materia m, sga_nivel n, sga_asignaturamalla am, sga_malla ma " \
                              " where dis.profesor_id=pro.id and pm.principal=true and td.id=dis.dedicacion_id and pro.persona_id=per.id  and dis.coordinacion_id=coor.id " \
                              " and dis.id=detdis.distributivo_id and detdis.criteriodocenciaperiodo_id=critd.id and critd.criterio_id=cri.id " \
                              " and detdis.criteriodocenciaperiodo_id is not null and dis.periodo_id=pe.id and pm.status=true and m.id=pm.materia_id and m.status=true " \
                              " and n.id=m.nivel_id and am.id=m.asignaturamalla_id and am.status=true and ma.id=am.malla_id and ma.status=true and pe.id=n.periodo_id and pe.status=true " \
                              " and dis.dedicacion_id=3 and n.status=true and n.periodo_id=dis.periodo_id and pm.profesor_id=dis.profesor_id and ma.carrera_id not in ("+ str(carreras_admision1) +") "
                if idanio != '0':
                    sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                if idperiodo != '0':
                    sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " and ma.carrera_id=" + idcarrera
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=3 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criterioinvestigacionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criterioinvestigacion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criterioinvestigacionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criterioinvestigacionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=3 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                sqlprofesor = sqlprofesor + " union "
                if idcarrera != '0':
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add, sga_actividaddetalledistributivocarrera addc " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=3 and add.criterio_id=detdis.id and add.status=true and addc.status=true and addc.actividaddetalle_id=add.id and addc.carrera_id not in ("+ str(carreras_admision1) +") "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo
                    if idcarrera != '0':
                        sqlprofesor = sqlprofesor + " and addc.carrera_id=" + idcarrera
                else:
                    sqlprofesor = sqlprofesor + " select per.cedula, per.apellido1||' '||per.apellido2||' '||per.nombres as nombre " \
                                                " from sga_profesordistributivohoras dis,sga_detalledistributivo detdis,sga_criteriogestionperiodo critd, " \
                                                " sga_tiempodedicaciondocente td, sga_criteriogestion cri, sga_profesor pro,sga_persona per, sga_coordinacion coor, sga_periodo pe, " \
                                                " sga_actividaddetalledistributivo add " \
                                                " where dis.profesor_id=pro.id and td.id=dis.dedicacion_id and pro.persona_id=per.id and dis.coordinacion_id=coor.id " \
                                                " and dis.id=detdis.distributivo_id and detdis.criteriogestionperiodo_id=critd.id and critd.criterio_id=cri.id  " \
                                                " and detdis.criteriogestionperiodo_id is not null and dis.periodo_id=pe.id " \
                                                " and dis.dedicacion_id=3 and add.criterio_id=detdis.id and add.status=true and coor.id not in (9) "
                    if idanio != '0':
                        sqlprofesor = sqlprofesor + " and extract(year from pe.inicio)=" + idanio
                    if idperiodo != '0':
                        sqlprofesor = sqlprofesor + " and dis.periodo_id=" + idperiodo

                sqlprofesor = sqlprofesor + ") as tabla order by tabla.nombre"

                cursor.execute(sqlprofesor)
                nprofesorestiempoparcial = 0
                profesorestiempoparcial_cursor = cursor.fetchall()
                for per in profesorestiempoparcial_cursor:
                    nprofesorestiempoparcial += 1
                data['nprofesorestiempoparcial'] = nprofesorestiempoparcial
                data['profesorestiempoparcial_cursor'] = profesorestiempoparcial_cursor

                # cantidad de estudiantes
                sql = "SELECT count(DISTINCT sga_inscripcion.id) " \
                      " FROM sga_inscripcion sga_inscripcion RIGHT OUTER JOIN sga_matricula sga_matricula ON sga_inscripcion.id = sga_matricula.inscripcion_id " \
                      " LEFT OUTER JOIN sga_persona sga_persona ON sga_inscripcion.persona_id = sga_persona.id " \
                      " LEFT OUTER JOIN sga_carrera sga_carrera ON sga_inscripcion.carrera_id = sga_carrera.id " \
                      " LEFT OUTER JOIN sga_nivelmalla sga_nivelmalla ON sga_matricula.nivelmalla_id = sga_nivelmalla.id " \
                      " LEFT OUTER JOIN sga_nivel sga_nivel ON sga_matricula.nivel_id = sga_nivel.id " \
                      " LEFT OUTER JOIN sga_periodo sga_periodo ON sga_nivel.periodo_id = sga_periodo.id " \
                      " LEFT OUTER JOIN sga_nivellibrecoordinacion sga_nivellibrecoordinacion ON sga_nivel.id = sga_nivellibrecoordinacion.nivel_id " \
                      " LEFT OUTER JOIN sga_coordinacion sga_coordinacion ON sga_nivellibrecoordinacion.coordinacion_id = sga_coordinacion.id " \
                      " WHERE sga_coordinacion.id not in (9) and sga_matricula.estado_matricula in (2,3) "
                if idanio != '0':
                    sql = sql + " and extract(year from sga_periodo.inicio)=" + idanio
                if idperiodo != '0':
                    sql = sql + " and sga_periodo.id=" + idperiodo
                if idcarrera != '0':
                    sql = sql + " and sga_carrera.id=" + idcarrera
                sql = sql + " and sga_matricula.id not in (select ret.matricula_id from sga_retiromatricula ret) and sga_matricula.id not in(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                            " from sga_matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, sga_asignatura asi, sga_periodo p1, sga_asignaturamalla am1, sga_malla m1  where mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                            " and ma.materia_id=mate.id and mate.asignatura_id=asi.id and p1.id=n.periodo_id and p1.status=true and am1.id=mate.asignaturamalla_id and am1.status=true and m1.id=am1.malla_id and m1.status=true "
                if idanio != '0':
                    sql = sql + " and extract(year from p1.inicio)=" + idanio
                if idperiodo != '0':
                    sql = sql + " and p1.id=" + idperiodo
                if idcarrera != '0':
                    sql = sql + " and m1.id=" + idcarrera
                sql = sql + " and asi.modulo=True group by mat.id) as ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                            " from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, sga_materia mate, sga_asignatura asi, sga_periodo p1, sga_asignaturamalla am1, sga_malla m1 where mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                            " and ma.materia_id=mate.id and mate.asignatura_id=asi.id and p1.id=n.periodo_id and p1.status=true and am1.id=mate.asignaturamalla_id and am1.status=true and m1.id=am1.malla_id and m1.status=true "
                if idanio != '0':
                    sql = sql + " and extract(year from p1.inicio)=" + idanio
                if idperiodo != '0':
                    sql = sql + " and p1.id=" + idperiodo
                if idcarrera != '0':
                    sql = sql + " and m1.id=" + idcarrera
                sql = sql + " group by mat.id) as mo where ma.id=mo.id and ma.numero=mo.numero)"
                cursor.execute(sql)
                results = cursor.fetchall()
                cantidad = 0
                for per in results:
                    cantidad = per[0]
                data['nalumnos'] = cantidad

                data['anio'] = idanio
                data['periodo'] = None
                if idperiodo != '0':
                    data['periodo'] = Periodo.objects.filter(pk=int(idperiodo))[0]
                data['carrera'] = None
                if idcarrera != '0':
                    data['carrera'] = Carrera.objects.filter(pk=int(idcarrera))[0]
                try:
                    sjrindicador = (Decimal(cantidad).quantize(Decimal('.0001')) / (    Decimal(nprofesorestiempocompleto).quantize(Decimal('.0001')) + ((Decimal(0.5).quantize(Decimal('.0001'))) * (Decimal(nprofesoresmediotiempo).quantize(Decimal('.0001')))) + ((Decimal(0.25).quantize(Decimal('.0001'))) * (Decimal(nprofesorestiempoparcial).quantize(Decimal('.0001'))))      ))
                except:
                    sjrindicador = 0
                data['sjrindicador'] = sjrindicador

                template = get_template("adm_indicadores/estudianteprofesor.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Indicadores'
        if 'action' in request.GET:
            action = request.GET['action']



            if action == 'ingresarproduccionacademica':
                try:
                    data['title'] = u'Producción Académica'

                    data['anios'] = anios = rango_anios()
                    anioselect = anios[0]
                    data['anioselect'] = anioselect
                    cursor = connections['sga_select'].cursor()
                    sqlperiodo = "select id, nombre,extract(year from inicio) from sga_periodo where status=true and tipo_id=2 and extract(year from inicio)=" + str(anioselect) + " order by inicio"
                    cursor.execute(sqlperiodo)
                    data['periodos'] = cursor.fetchall()
                    data['carreras'] = Carrera.objects.filter(status=True).order_by('nombre').exclude(nombre__icontains='ADMISI')

                    return render(request, "adm_indicadores/ingresarproduccionacademica.html", data)
                except Exception as ex:
                    pass

            if action == 'ingresartitularidad':
                try:
                    data['title'] = u'Titularidad'

                    data['anios'] = anios = rango_anios()
                    anioselect = anios[0]
                    data['anioselect'] = anioselect
                    cursor = connections['sga_select'].cursor()
                    sqlperiodo = "select id, nombre,extract(year from inicio) from sga_periodo where status=true and tipo_id=2 and extract(year from inicio)=" + str(anioselect) + " order by inicio"
                    cursor.execute(sqlperiodo)
                    data['periodos'] = cursor.fetchall()
                    data['carreras'] = Carrera.objects.filter(status=True).order_by('nombre').exclude(nombre__icontains='ADMISI')

                    return render(request, "adm_indicadores/ingresartitularidad.html", data)
                except Exception as ex:
                    pass

            if action == 'ingresarestudianteprofesor':
                try:
                    data['title'] = u'Estuduante por Profesor'

                    data['anios'] = anios = rango_anios()
                    anioselect = anios[0]
                    data['anioselect'] = anioselect
                    cursor = connections['sga_select'].cursor()
                    sqlperiodo = "select id, nombre,extract(year from inicio) from sga_periodo where status=true and tipo_id=2 and extract(year from inicio)=" + str(anioselect) + " order by inicio"
                    cursor.execute(sqlperiodo)
                    data['periodos'] = cursor.fetchall()
                    data['carreras'] = Carrera.objects.filter(status=True).order_by('nombre').exclude(nombre__icontains='ADMISI')

                    return render(request, "adm_indicadores/ingresarestudianteprofesor.html", data)
                except Exception as ex:
                    pass

            if action == 'ingresarformacionposgrado':
                try:
                    data['title'] = u'Afinidad Formación Posgrado'

                    data['anios'] = anios = rango_anios()
                    # anioselect = anios[0]
                    anioselect = request.GET['anio'] if 'anio' in request.GET else anios[0]
                    data['anioselect'] = int(anioselect)
                    # cursor = connections['sga_select'].cursor()
                    # sqlperiodo = "select id, nombre,extract(year from inicio) from sga_periodo where status=true and tipo_id=2 and extract(year from inicio)=" + str(anioselect) + " order by inicio"
                    # cursor.execute(sqlperiodo)
                    # data['periodos'] = cursor.fetchall()
                    probase = ProfesorMateria.objects.filter(status=True, principal=True, materia__nivel__periodo__inicio__year=anioselect)
                    periodos = probase.values_list('materia__nivel__periodo_id', flat=True).distinct()
                    carreras = probase.values_list('materia__asignaturamalla__malla__carrera_id', flat=True).distinct()
                    data['periodos'] = Periodo.objects.filter(status=True, tipo_id=2, id__in=periodos)
                    data['carreras'] = Carrera.objects.filter(status=True, id__in=carreras).order_by('nombre').exclude(nombre__icontains='ADMISI')

                    return render(request, "adm_indicadores/ingresarformacionposgrado.html", data)
                except Exception as ex:
                    pass

            if action == 'tasagraduacion':
                try:
                    data['title'] = u'Tasa de graduación'
                    data['carreras'] = Carrera.objects.filter(status=True).exclude(coordinacion__carrera__coordinacion__id__in=[9])
                    data['listaanios'] = Inscripcion.objects.filter(fechainicioprimernivel__isnull=False, status=True).annotate(Year=ExtractYear('fechainicioprimernivel')).values_list('Year', flat=True).order_by('Year').distinct()
                    data['mostrar'] = 0
                    return render(request, "adm_indicadores/tasagraduacion.html", data)
                except Exception as ex:
                    pass

            if action == 'descargarexcel':
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
                    # ws.write_merge(0, 0, 0, 10, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=Graduados' + random.randint(
                        1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CEDULA", 4000),
                        (u"ESTUDIANTE", 8000),
                        (u"SEXO", 4000),
                        (u"INICIO PRIMER NIVEL", 4000),
                        (u"ETNIA", 4000),
                        (u"DISCAPACIDAD", 5000),
                        (u"GRADUADO", 2500),
                        (u"GRUPO SOCIOECONOMICO", 6000),
                        (u"LGTBI", 2500),
                        (u"CREDO", 6000),
                        (u"PREFERENCIA POLITICA", 6000),
                    ]

                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy-mm-dd'
                    date_formatreverse = xlwt.XFStyle()
                    date_formatreverse.num_format_str = 'dd/mm/yyyy'
                    anioinicio = int(request.GET['anioinicio'])
                    aniofin = int(request.GET['aniofin'])
                    listaporperiodos = Inscripcion.objects.select_related().filter(fechainicioprimernivel__year=anioinicio, fechainicioprimernivel__isnull=False, status=True)
                    graduados = Graduado.objects.select_related().filter(fechagraduado__year__gte=anioinicio, fechagraduado__year__lte=aniofin, inscripcion__in=listaporperiodos)
                    row_num = 1
                    i = 0
                    for listado in listaporperiodos:
                        if graduados.filter(inscripcion__id=listado.id).exists():
                            estudiantegraduado = 'SI'
                        else:
                            estudiantegraduado = 'NO'
                        if listado.persona.lgtbi:
                            preferenciagenero = 'SI'
                        else:
                            preferenciagenero = 'NO'
                        if listado.persona.credo:
                            credo = listado.persona.credo.nombre
                        else:
                            credo = 'NINGUNO'
                        if listado.persona.preferenciapolitica:
                            preferenciapolitica = listado.persona.preferenciapolitica.nombre
                        else:
                            preferenciapolitica = 'NINGUNO'
                        if listado.persona.sexo:
                            sexo = listado.persona.sexo.nombre
                        else:
                            sexo = ''
                        if listado.persona.mi_perfil().raza:
                            raza = listado.persona.mi_perfil().raza.nombre
                        else:
                            raza = ''
                        if listado.persona.mi_perfil().tipodiscapacidad:
                            discapacidad = listado.persona.mi_perfil().tipodiscapacidad.nombre
                        else:
                            discapacidad = 'SIN DISCAPACIDAD'
                        if listado.persona.mi_ficha().grupoeconomico:
                            gruposocioeconomico = listado.persona.mi_ficha().grupoeconomico.nombre
                        else:
                            gruposocioeconomico = 'FICHA SIN LLENAR'

                        i += 1
                        # ws.write(row_num, 0, i, font_style2)
                        ws.write(row_num, 0, listado.persona.cedula, font_style2)
                        ws.write(row_num, 1, listado.persona.apellido1 + ' ' + listado.persona.apellido2 + ' ' + listado.persona.nombres, font_style2)
                        ws.write(row_num, 2, sexo, font_style2)
                        ws.write(row_num, 3, listado.fechainicioprimernivel, date_format)
                        ws.write(row_num, 4, raza, font_style2)
                        ws.write(row_num, 5, discapacidad, font_style2)
                        ws.write(row_num, 6, estudiantegraduado, font_style2)
                        ws.write(row_num, 7, gruposocioeconomico, font_style2)
                        ws.write(row_num, 8, preferenciagenero, font_style2)
                        ws.write(row_num, 9, credo, font_style2)
                        ws.write(row_num, 10, preferenciapolitica, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'generagrafica':
                try:
                    import time
                    data['title'] = u'Tasa de graduación'
                    data['idcarrera'] = idcarrera = int(request.GET['carr'])
                    data['carreras'] = carrera = Carrera.objects.filter(status=True).exclude(coordinacion__carrera__coordinacion__id__in=[9])
                    data['anioinicio'] = anioinicio = int(request.GET['anioinicio'])
                    data['aniofin'] = aniofin = int(request.GET['aniofin'])
                    if idcarrera == 0:
                        listado = Inscripcion.objects.select_related().filter(fechainicioprimernivel__isnull=False, status=True)
                    else:
                        listado = Inscripcion.objects.select_related().filter(carrera__id=idcarrera, fechainicioprimernivel__isnull=False, status=True)
                    data['listaanios'] = listado.annotate(Year=ExtractYear('fechainicioprimernivel')).values_list('Year', flat=True).order_by('Year').distinct()
                    listaporperiodos = listado.filter(fechainicioprimernivel__year=anioinicio)
                    data['totalmuestra'] = listaporperiodos.count()
                    # INICIO PARA SACAR PORCENTAJE GRADUADOS
                    graduados = Graduado.objects.filter(fechagraduado__year__gte=anioinicio, fechagraduado__year__lte=aniofin, inscripcion__in= listaporperiodos)
                    porcentajegraduados = (graduados.count() * 100) / listaporperiodos.count()
                    porcentajeingresos = ((listaporperiodos.count() - graduados.count()) * 100) / listaporperiodos.count()
                    data['totalingresaron'] = totalingresaron = listaporperiodos.count() - graduados.count()
                    data['totalgraduados'] = graduados.count()
                    data['porcentajegraduados'] = round(porcentajegraduados,2)
                    data['porcentajeingresos'] = round(porcentajeingresos,2)
                    # listadoingresaron = listaporperiodos.filter(status=True).exclude(pk__in=graduados.values_list('inscripcion_id'))
                    # FIN PORCENTAJE GRADUADOS
                    # INICIO PARA SACAR PORCENTAJE GRADUADOS POR AÑO
                    listagradxanio = []

                    if idcarrera == 0:
                        data['anios'] = anios = Graduado.objects.filter(status=True, fechagraduado__year__gte=anioinicio, fechagraduado__year__lte=aniofin).annotate(Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by('Year').distinct()
                    else:
                        data['anios'] = anios = Graduado.objects.filter(inscripcion__carrera__id=idcarrera, status=True, fechagraduado__year__gte=anioinicio, fechagraduado__year__lte=aniofin).annotate(Year=ExtractYear('fechagraduado')).values_list('Year', flat=True).order_by('Year').distinct()
                    for a in anios:
                        if idcarrera == 0:
                            graduadoscant = Graduado.objects.values_list("id", flat=True).filter(status=True, fechagraduado__year__gte=a, fechagraduado__year__lte=a).count()
                        else:
                            graduadoscant = Graduado.objects.values_list("id", flat=True).filter(inscripcion__carrera__id=idcarrera, status=True, fechagraduado__year__gte=a, fechagraduado__year__lte=a).count()
                        listagradxanio.append([a, graduadoscant])
                    data['totalgradxanio'] = listagradxanio
                    # FIN PORCENTAJE GRADUADOS POR AÑO
                    # INICIO PARA SACAR PORCENTAJE POR SEXO
                    totalingresaronhombres = listaporperiodos.filter(persona__sexo__id=2).count()
                    totalingresaronmujeres = listaporperiodos.filter(persona__sexo__id=1).count()
                    totalgraduadoshombres = graduados.filter(inscripcion__persona__sexo__id=2).count()
                    totalgraduadosmujeres = graduados.filter(inscripcion__persona__sexo__id=1).count()
                    porcingresaronhombres = (totalingresaronhombres * 100) / totalingresaron
                    porctotalingresaronmujeres = (totalingresaronmujeres * 100) / totalingresaron
                    data['totalingresaronhombres'] = round(totalingresaronhombres,2)
                    data['totalingresaronmujeres'] = round(totalingresaronmujeres,2)
                    data['porcingresaronhombres'] = round(porcingresaronhombres,2)
                    data['porctotalingresaronmujeres'] = round(porctotalingresaronmujeres,2)
                    data['totalgraduadoshombres'] = totalgraduadoshombres
                    data['totalgraduadosmujeres'] = totalgraduadosmujeres
                    if totalingresaronhombres>0:
                        data['tasagraduadoshombres'] = int(round(((totalgraduadoshombres * 100) / totalingresaronhombres), 0))
                    else:
                        data['tasagraduadoshombres'] =0
                    if totalingresaronmujeres>0:
                        data['tasagraduadosmujeres'] = int(round(((totalgraduadosmujeres * 100) / totalingresaronmujeres), 0))
                    else:
                        data['tasagraduadosmujeres'] =0
                    # FIN PORCENTAJE SEXO
                    # INICIO PARA SACAR PORCENTAJE POR PREFERENCIA GENERO
                    totalingresaronhombresgenero = listaporperiodos.filter(persona__sexo__id=2, persona__lgtbi=False).count()
                    totalingresaronmujeresgenero = listaporperiodos.filter(persona__sexo__id=1, persona__lgtbi=False).count()
                    totalingresaronlgtbi = listaporperiodos.filter(persona__lgtbi=True).count()
                    totalgraduadoshombresgenero = graduados.filter(inscripcion__persona__sexo__id=2, inscripcion__persona__lgtbi=False, status=True).count()
                    totalgraduadosmujeresgenero = graduados.filter(inscripcion__persona__sexo__id=1, inscripcion__persona__lgtbi=False, status=True).count()
                    totalgraduadoslgtbigenero = graduados.filter(inscripcion__persona__lgtbi=True, status=True).count()
                    if totalingresaron>0:
                        porcingresaronhombresgenero = (totalingresaronhombresgenero * 100) / totalingresaron
                        porctotalingresaronmujeresgenero = (totalingresaronmujeresgenero * 100) / totalingresaron
                        porctotalingresaronlgtbigenero = (totalingresaronlgtbi * 100) / totalingresaron
                    else:
                        porcingresaronhombresgenero = 0
                        porctotalingresaronmujeresgenero = 0
                        porctotalingresaronlgtbigenero = 0
                    data['totalingresaronhombresgenero'] = round(totalingresaronhombresgenero, 2)
                    data['totalingresaronmujeresgenero'] = round(totalingresaronmujeresgenero, 2)
                    data['totalingresaronlgtbi'] = round(totalingresaronlgtbi, 2)
                    data['porcingresaronhombresgenero'] = round(porcingresaronhombresgenero, 2)
                    data['porctotalingresaronmujeresgenero'] = round(porctotalingresaronmujeresgenero, 2)
                    data['porctotalingresaronlgtbigenero'] = round(porctotalingresaronlgtbigenero, 2)
                    data['totalgraduadoshombresgenero'] = totalgraduadoshombresgenero
                    data['totalgraduadosmujeresgenero'] = totalgraduadosmujeresgenero
                    data['totalgraduadoslgtbigenero'] = totalgraduadoslgtbigenero
                    if totalingresaronhombresgenero>0:
                        data['tasagraduadoshombresgenero'] = int(round(((totalgraduadoshombresgenero * 100) / totalingresaronhombresgenero), 0))
                    else:
                        data['tasagraduadoshombresgenero'] =0
                    if totalingresaronmujeresgenero>0:
                        data['tasagraduadosmujeresgenero'] = int(round(((totalgraduadosmujeresgenero * 100) / totalingresaronmujeresgenero), 0))
                    else:
                        data['tasagraduadosmujeresgenero'] =0
                    if totalingresaronlgtbi>0:
                        data['tasagraduadoslgtbigenero'] = int(round(((totalgraduadoslgtbigenero * 100) / totalingresaronlgtbi), 0))
                    else:
                        data['tasagraduadoslgtbigenero'] =0
                    # FIN PORCENTAJE PREFERENCIA GENERO
                    # INICIO PARA SACAR PORCENTAJE POR RAZA
                    totalesporraza = []
                    listadoraza = listaporperiodos.values_list('persona__perfilinscripcion__raza__id', 'persona__perfilinscripcion__raza__nombre').filter(persona__perfilinscripcion__raza__isnull=False).distinct().annotate(prom=Count('persona__perfilinscripcion__raza__id')).order_by('persona__perfilinscripcion__raza__id')
                    for raza in listadoraza:
                        porrazagraduados = graduados.filter(inscripcion__persona__perfilinscripcion__raza__id=raza[0]).distinct().annotate(prom=Count('inscripcion__persona__perfilinscripcion__raza__id')).order_by('inscripcion__persona__perfilinscripcion__raza__id')
                        promedioraza = int(round(((porrazagraduados.count() * 100) / raza[2]),0))
                        totalesporraza.append([raza[1], round(((raza[2] * 100) / listaporperiodos.count()),2), raza[2], promedioraza, porrazagraduados.count()])
                    data['listadoetnia'] = totalesporraza
                    # FIN PORCENTAJE RAZA
                    # INICIO PARA SACAR PORCENTAJE POR DISCAPACIDAD
                    totalespordiscapacidad = []
                    listadodiscapacidad = listaporperiodos.values_list('persona__perfilinscripcion__tipodiscapacidad__id','persona__perfilinscripcion__tipodiscapacidad__nombre').filter(persona__perfilinscripcion__tipodiscapacidad__isnull=False).distinct().annotate(prom=Count('persona__perfilinscripcion__tipodiscapacidad__id')).order_by('persona__perfilinscripcion__tipodiscapacidad__id')
                    listadosindiscapacidad = listaporperiodos.filter(persona__perfilinscripcion__tipodiscapacidad__isnull=True).distinct().annotate(prom=Count('persona__perfilinscripcion__tipodiscapacidad__id')).order_by('persona__perfilinscripcion__tipodiscapacidad__id')
                    for discapacidad in listadodiscapacidad:
                        pordiscapacidadgraduados = graduados.filter(inscripcion__persona__perfilinscripcion__tipodiscapacidad__id=discapacidad[0]).distinct().annotate(prom=Count('inscripcion__persona__perfilinscripcion__tipodiscapacidad__id')).order_by('inscripcion__persona__perfilinscripcion__tipodiscapacidad__id')
                        promediodiscapacidad = int(round(((pordiscapacidadgraduados.count() * 100) / discapacidad[2]), 0))
                        totalespordiscapacidad.append([discapacidad[1], round(((discapacidad[2] * 100) / listaporperiodos.count()), 2), discapacidad[2], promediodiscapacidad, pordiscapacidadgraduados.count()])
                    pordiscapacidadgraduados = graduados.filter(inscripcion__persona__perfilinscripcion__tipodiscapacidad__isnull=True).distinct().annotate(prom=Count('inscripcion__persona__perfilinscripcion__tipodiscapacidad__id')).order_by('inscripcion__persona__perfilinscripcion__tipodiscapacidad__id')
                    promediodiscapacidad = int(round(((pordiscapacidadgraduados.count() * 100) / listadosindiscapacidad.count()), 0))
                    totalespordiscapacidad.append(['SIN DISCAPACIDAD', round(((listadosindiscapacidad.count() * 100) / listaporperiodos.count()), 2),listadosindiscapacidad.count(), promediodiscapacidad, pordiscapacidadgraduados.count()])
                    data['listadodiscapacidad'] = totalespordiscapacidad
                    # FIN PORCENTAJE DISCAPACIDAD
                    # INICIO PARA SACAR PORCENTAJE POR GRUPO SOCIOECONOMICO
                    totalessocioeconomico = []
                    listadosocioeconomico = listaporperiodos.values_list('persona__fichasocioeconomicainec__grupoeconomico__id','persona__fichasocioeconomicainec__grupoeconomico__nombre').filter(persona__fichasocioeconomicainec__grupoeconomico__isnull=False).distinct().annotate(prom=Count('persona__fichasocioeconomicainec__grupoeconomico__id')).order_by('persona__fichasocioeconomicainec__grupoeconomico__id')
                    for socioeconomico in listadosocioeconomico:
                        porsocioeconomicograduados = graduados.filter(inscripcion__persona__fichasocioeconomicainec__grupoeconomico__id=socioeconomico[0]).distinct().annotate(prom=Count('inscripcion__persona__fichasocioeconomicainec__grupoeconomico__id')).order_by('inscripcion__persona__fichasocioeconomicainec__grupoeconomico__id')
                        promsocioeconomico = int(round(((porsocioeconomicograduados.count() * 100) / socioeconomico[2]), 0))
                        totalessocioeconomico.append([socioeconomico[1], round(((socioeconomico[2] * 100) / listaporperiodos.count()), 2),socioeconomico[2], promsocioeconomico, porsocioeconomicograduados.count()])
                    data['listadosocioeconomico'] = totalessocioeconomico
                    # FIN PORCENTAJE DISCAPACIDAD
                    # INICIO PARA SACAR PORCENTAJE POR CREDO
                    totalesporcredo = []
                    listadocredo = listaporperiodos.values_list('persona__credo__id','persona__credo__nombre').filter(persona__credo__isnull=False).distinct().annotate(prom=Count('persona__credo__id')).order_by('persona__credo__id')
                    for credo in listadocredo:
                        porcredograduados = graduados.filter(inscripcion__persona__credo__id=credo[0]).distinct().annotate(prom=Count('inscripcion__persona__credo__id')).order_by('inscripcion__persona__credo__id')
                        promediocredo = int(round(((porcredograduados.count() * 100) / credo[2]), 0))
                        totalesporcredo.append([credo[1], round(((credo[2] * 100) / listaporperiodos.count()), 2), credo[2], promediocredo, porcredograduados.count()])
                    data['listadocredo'] = totalesporcredo
                    # FIN PORCENTAJE CREDO
                    # INICIO PARA SACAR PORCENTAJE POR PREFERENCIA POLÍTICA
                    totalesporpreferenciapolitica = []
                    listadopreferenciapolitica = listaporperiodos.values_list('persona__preferenciapolitica__id', 'persona__preferenciapolitica__nombre').filter(persona__preferenciapolitica__isnull=False).distinct().annotate(prom=Count('persona__preferenciapolitica__id')).order_by('persona__preferenciapolitica__id')
                    for preferenciapolitica in listadopreferenciapolitica:
                        porpreferenciapoliticagraduados = graduados.filter(inscripcion__persona__preferenciapolitica__id=preferenciapolitica[0]).distinct().annotate(prom=Count('inscripcion__persona__preferenciapolitica__id')).order_by('inscripcion__persona__preferenciapolitica__id')
                        promediopreferenciapolitica = int(round(((porpreferenciapoliticagraduados.count() * 100) / preferenciapolitica[2]), 0))
                        totalesporpreferenciapolitica.append([preferenciapolitica[1], round(((preferenciapolitica[2] * 100) / listaporperiodos.count()), 2), preferenciapolitica[2], promediopreferenciapolitica, porpreferenciapoliticagraduados.count()])
                    data['listadopreferenciapolitica'] = totalesporpreferenciapolitica
                    # FIN PORCENTAJE PREFERENCIA POLÍTICA
                    data['mostrar'] = 1
                    return render(request, "adm_indicadores/tasagraduacion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:

            return render(request, "adm_indicadores/view.html", data)
