import os
import sys
import time
from datetime import datetime, timedelta, date

#from Tools.scripts.pindent import start

from settings import DEBUG
from sga.templatetags.sga_extras import encrypt

SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from sga.models import Persona, Materia
from sagest.models import Rubro
from django.db import transaction, connection, IntegrityError
#new
MY_PRIFIX_MOODLE = 'mooc_'
start = datetime.strptime(f"{datetime.now().date()} {datetime.now().hour}:{datetime.now().minute}", '%Y-%m-%d %H:%M')
fcreacion = int(time.mktime(start.timetuple()))
# @transaction.atomic()


def CrearTareasMoodle(tareaid, persona):
    from sga.models import TareaSilaboSemanal
    from django.db import connections
    from sga.funciones import null_to_numeric
    tarea = TareaSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1,2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'

    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            cursor = None
            conexion = None
            coordinacion_id = materia.coordinacion().id
            if materia.coordinacion():
                if coordinacion_id == 9:
                    conexion = connections['db_moodle_virtual']
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                else:
                    conexion = connections['aulagradob']
            else:
                conexion = connections['moodle_db']

            cursor = conexion.cursor()
            # sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 3)
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, tarea.actividad.categoriamoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = """
                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>
                    <p>%s</p>

                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Instrucciones:</h3></p>
                    <p>%s</p>

                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Recomendaciones:</h3></p>
                    <p>%s</p>
            """ % (tarea.objetivo, tarea.instruccion, tarea.recomendacion)
            if tarea.rubrica:
                if tarea.rubrica or tarea.archivorubrica:
                    archivorubrica = ""
                    if tarea.archivorubrica:
                        namea = tarea.archivorubrica.name.split("/")[-1]
                        archivorubrica = """
                            <div class="fileuploadsubmission"> 
                            <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>   
                            </div>
                        """ % (tarea.archivorubrica.url, namea)
                    intro = """%s
                        <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Rúbrica:</h3></p>
                        <p>%s</p>
                        %s
                        <p> </p>
                        """ % (intro, tarea.rubrica, archivorubrica)

            if tarea.archivotareasilabo:
                archivotareasilabo = ""
                if tarea.archivotareasilabo:
                    namea = tarea.archivotareasilabo.name.split("/")[-1]
                    archivotareasilabo = """
                        <div class="fileuploadsubmission"> 
                        <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>   
                        </div><br>
                    """ % (tarea.archivotareasilabo.url, namea)
                intro = """%s
                        <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Archivos Adicionales</h3></p>
                        %s                    
                        """ % (intro, archivotareasilabo)
            # intro = intro.replace("'", "")
            intro = intro.replace("'", "''")
            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = int(time.mktime(tarea.fechadesde.date().timetuple()))
            fechahasta = datetime(tarea.fechahasta.date().year, tarea.fechahasta.date().month, tarea.fechahasta.date().day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            if tarea.idtareamoodle > 0:
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and id='%s'""" % (cursoid, tarea.idtareamoodle)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if not buscar:
                    tarea.idtareamoodle = 0
            if tarea.idtareamoodle <= 0:
                sql = """
                        INSERT INTO mooc_assign (name, timemodified, course, intro, introformat, alwaysshowdescription, submissiondrafts, requiresubmissionstatement, sendnotifications, sendlatenotifications,
                                         sendstudentnotifications, duedate, cutoffdate, gradingduedate, allowsubmissionsfromdate, grade, completionsubmit, teamsubmission, requireallteammemberssubmit, blindmarking,
                                         hidegrader, attemptreopenmethod, maxattempts, preventsubmissionnotingroup, markingworkflow, markingallocation) 
                            VALUES('%s', '%s', '%s', '%s', '5', '1', '0', '0', '0', '0',
                                '1', '%s', '%s', '0', '%s', '%s', '1', '0', '0', '0',
                                    '0', 'none', '-1', '0', '0', '0')""" % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, cursoid, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0)
                cursor.execute(sql)

                sql = """select id from mooc_assign WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section) 
                        VALUES('%s', '1', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '0', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, instance, fecha, section)
                cursor.execute(sql)

                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()

                if not buscar:
                    sql2 = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                    cursor.execute(sql2)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_event (modulename,courseid,groupid,userid,instance,type,description,name,eventtype,timestart,timesort,format,timemodified) 
                        VALUES('assign', '%s', '0', '%s','%s', '1','%s','%s','due', '%s','%s','1','%s') 
                """ % (cursoid, persona.idusermoodle, instance, intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,
                        grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,
                        needsupdate,weightoverride,timecreated,timemodified,hidden) 
                        VALUES('%s', '%s', '%s', 'mod','assign','%s', '0', NULL, '', NULL, '%s', '%s', '0', NULL, NULL, '0', '1', '0', '0', '0', '8', '0',
                        NULL, '0', '0', '0', '0','%s','%s', '0') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, fecha)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid='%s' and iteminstance='%s' """ % (cursoid, categoryid, instance)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                gradeitemid = buscar[0][0]

                sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                categoryidraiz = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '%s', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '1', '%s', NULL, '%s') 
                """ % (cursoid, categoryidraiz, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, instanceid, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'onlinetext', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxfilesubmissions', '20') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxsubmissionsizebytes', '0') """ % instance
                cursor.execute(sql)

                if tarea.todos:
                    sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', '*') """ % instance
                    cursor.execute(sql)
                else:
                    sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', 'document,spreadsheet,presentation') """ % instance
                    cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s','assignfeedback','comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'comments', 'commentinline', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'editpdf', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'offline', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'file', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grading_areas (contextid,component,areaname,activemethod) VALUES('%s', 'mod_assign', 'submissions', NULL) """ % contextid
                cursor.execute(sql)

                sql = """INSERT INTO mooc_block_recent_activity (action,timecreated,courseid,cmid,userid) VALUES('0', '%s', '%s', '%s', '%s') """ % (fecha, cursoid, instanceid, persona.idusermoodle)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                tarea.idtareamoodle = instanceid
                tarea.estado_id = 4
                tarea.save()

            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = tarea.idtareamoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """
                        update mooc_assign 
                        set name='%s', 
                        timemodified='%s', 
                        intro='%s', 
                        duedate='%s', 
                        cutoffdate='%s', 
                        allowsubmissionsfromdate='%s', 
                        grade='%s'
                        where id='%s'
                        """ % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0, instance)
                cursor.execute(sql)

                sql = """UPDATE mooc_event 
                SET description='%s',
                name='%s',
                timestart='%s',
                timesort='%s',
                timemodified='%s'
                WHERE instance='%s' and courseid='%s' 
                """ % (intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha, instance, cursoid)
                cursor.execute(sql)

                if tarea.todos:
                    sql = """UPDATE mooc_assign_plugin_config SET value = '*' WHERE assignment = %s and name = 'filetypeslist'""" % (instance)
                    cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """update mooc_grade_items 
                        set categoryid='%s',
                        itemname='%s',
                        gradetype='%s',
                        grademax='%s',
                        timemodified='%s'
                        where courseid='%s' and iteminstance='%s'
                """ % (categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, cursoid, instance)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if tarea.calificar:
                # YA CREADA LA TAREA SE PROCEDE A INSERTAR LA RUBRICA
                if tarea.rubricamoodle:
                    rubrica = tarea.rubricamoodle
                    # PROCEDEMOS A BUSCAR LA AREA
                    sql = """select id from mooc_grading_areas where contextid='%s' """ % (contextid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    areaid = buscar[0][0]

                    # VERIFICACION SI EXISTEN DATOS PARA BORRARLOS Y LUEGO INSERTAR DE NUEVO
                    sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    grading_definitions = 0
                    if buscar:
                        grading_definitions = buscar[0][0]
                        for c in rubrica.items():
                            orden = c.orden

                            # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                            sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                            cursor.execute(sql)
                            buscar = cursor.fetchall()
                            if buscar:
                                gradingform_rubric_criteria = buscar[0][0]

                                sql = """DELETE FROM mooc_gradingform_rubric_levels WHERE criterionid = %s """ % (gradingform_rubric_criteria)
                                cursor.execute(sql)

                        sql = """DELETE FROM mooc_gradingform_rubric_criteria WHERE definitionid = %s """ % (grading_definitions)
                        cursor.execute(sql)

                        sql = """DELETE FROM mooc_grading_definitions WHERE id = %s """ % (grading_definitions)
                        cursor.execute(sql)
                        grading_definitions = 0

                    # FIN DE ELIMINACION
                    if grading_definitions == 0:
                        sql = """INSERT INTO mooc_grading_definitions
                                (areaid,method,timecreated,usercreated,timemodified,usermodified,status,descriptionformat,options,name)
                                VALUES(%s,'rubric',%s,%s,%s,%s,'20','1',
                                '{"sortlevelsasc":"1","lockzeropoints":"1","alwaysshowdefinition":"1","showdescriptionteacher":"1","showdescriptionstudent":"1","showscoreteacher":"1","showscorestudent":"1","enableremarks":"1","showremarksstudent":"1"}','%s')""" % (areaid, fecha, persona.idusermoodle, fecha, persona.idusermoodle, rubrica.nombre)
                        cursor.execute(sql)

                        # PROCEDEMOS A BUSCAR GRADING_DEFINITIONS
                        sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        grading_definitions = buscar[0][0]

                        # INSERTAR LOS CRITERIOS
                        for c in rubrica.items():
                            item = c.item
                            item = item.replace("'", "")
                            orden = c.orden
                            sql = """INSERT INTO mooc_gradingform_rubric_criteria (definitionid,descriptionformat,sortorder,description)
                                     VALUES(%s,'0',%s,'%s')""" % (grading_definitions, orden, item)
                            cursor.execute(sql)

                            # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                            sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                            cursor.execute(sql)
                            buscar = cursor.fetchall()
                            gradingform_rubric_criteria = buscar[0][0]

                            for d in c.detalle():
                                descripcion = d.descripcion.replace("'", "")
                                orden1 = d.orden
                                valor = d.valor

                                sql = """INSERT INTO mooc_gradingform_rubric_levels (criterionid, definitionformat, score, definition)
                                VALUES(%s,'0',%s,'%s')""" % (gradingform_rubric_criteria, valor, descripcion)
                                cursor.execute(sql)

                        sql = """UPDATE mooc_grading_areas set activemethod='rubric' where contextid=%s""" % (contextid)
                        cursor.execute(sql)
            if tarea.idtareamoodle > 0:
                tarea.estado_id = 4
                tarea.save()
            return True, u"Tarea migrada a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearTareasTEMoodle(tareaid, persona):
    from sga.models import TareaSilaboSemanal
    from django.db import connections, transaction
    from sga.funciones import null_to_numeric
    tarea = TareaSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'

    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"

    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            cursor = None
            conexion = None
            if materia.coordinacion():
                if coordinacion_id == 9:
                    conexion = connections['db_moodle_virtual']
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                else:
                    conexion = connections['aulagradob']
            else:
                conexion = connections['moodle_db']

            cursor = conexion.cursor()
            # sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 3)
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, tarea.actividad.categoriamoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = """
                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>
                    <p>%s</p>

                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Instrucciones:</h3></p>
                    <p>%s</p>

                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Recomendaciones:</h3></p>
                    <p>%s</p>
            """ % (tarea.objetivo, tarea.instruccion, tarea.recomendacion)
            if tarea.rubrica:
                if tarea.rubrica or tarea.archivorubrica:
                    archivorubrica = ""
                    if tarea.archivorubrica:
                        namea = tarea.archivorubrica.name.split("/")[-1]
                        archivorubrica = """
                            <div class="fileuploadsubmission"> 
                            <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>   
                            </div>
                        """ % (tarea.archivorubrica.url, namea)
                    intro = """%s
                        <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Rúbrica:</h3></p>
                        <p>%s</p>
                        %s
                        <p> </p>
                        """ % (intro, tarea.rubrica, archivorubrica)

            if tarea.archivotareasilabo:
                archivotareasilabo = ""
                if tarea.archivotareasilabo:
                    namea = tarea.archivotareasilabo.name.split("/")[-1]
                    archivotareasilabo = """
                        <div class="fileuploadsubmission"> 
                        <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>   
                        </div><br>
                    """ % (tarea.archivotareasilabo.url, namea)
                intro = """%s
                        <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Archivos Adicionales</h3></p>
                        %s                    
                        """ % (intro, archivotareasilabo)
            # intro = intro.replace("'", "")
            intro = intro.replace("'", "''")
            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = int(time.mktime(tarea.fechadesde.date().timetuple()))
            fechahasta = datetime(tarea.fechahasta.date().year, tarea.fechahasta.date().month, tarea.fechahasta.date().day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            if tarea.idtareamoodle > 0:
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and id='%s'""" % (cursoid, tarea.idtareamoodle)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if not buscar:
                    tarea.idtareamoodle = 0
            if tarea.idtareamoodle <= 0:
                sql = """
                        INSERT INTO mooc_assign (name, timemodified, course, intro, introformat, alwaysshowdescription, submissiondrafts, requiresubmissionstatement, sendnotifications, sendlatenotifications,
                                         sendstudentnotifications, duedate, cutoffdate, gradingduedate, allowsubmissionsfromdate, grade, completionsubmit, teamsubmission, requireallteammemberssubmit, blindmarking,
                                         hidegrader, attemptreopenmethod, maxattempts, preventsubmissionnotingroup, markingworkflow, markingallocation) 
                            VALUES('%s', '%s', '%s', '%s', '5', '1', '0', '0', '0', '0',
                                '1', '%s', '%s', '0', '%s', '%s', '1', '0', '0', '0',
                                    '0', 'none', '-1', '0', '0', '0')""" % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, cursoid, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0)
                cursor.execute(sql)

                sql = """select id from mooc_assign WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section) 
                        VALUES('%s', '1', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '0', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, instance, fecha, section)
                cursor.execute(sql)

                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_event (modulename,courseid,groupid,userid,instance,type,description,name,eventtype,timestart,timesort,format,timemodified) 
                        VALUES('assign', '%s', '0', '%s','%s', '1','%s','%s','due', '%s','%s','1','%s') 
                """ % (cursoid, persona.idusermoodle, instance, intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,
                        grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,
                        needsupdate,weightoverride,timecreated,timemodified,hidden) 
                        VALUES('%s', '%s', '%s', 'mod','assign','%s', '0', NULL, '', NULL, '%s', '%s', '0', NULL, NULL, '0', '1', '0', '0', '0', '8', '0',
                        NULL, '0', '0', '0', '0','%s','%s', '0') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, fecha)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid='%s' and iteminstance='%s' """ % (cursoid, categoryid, instance)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                gradeitemid = buscar[0][0]

                sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                categoryidraiz = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '%s', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '1', '%s', NULL, '%s') 
                """ % (cursoid, categoryidraiz, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, instanceid, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'onlinetext', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxfilesubmissions', '20') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxsubmissionsizebytes', '0') """ % instance
                cursor.execute(sql)

                if tarea.todos:
                    sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', '*') """ % instance
                    cursor.execute(sql)
                else:
                    sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', 'document,spreadsheet,presentation') """ % instance
                    cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s','assignfeedback','comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'comments', 'commentinline', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'editpdf', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'offline', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'file', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grading_areas (contextid,component,areaname,activemethod) VALUES('%s', 'mod_assign', 'submissions', NULL) """ % contextid
                cursor.execute(sql)

                sql = """INSERT INTO mooc_block_recent_activity (action,timecreated,courseid,cmid,userid) VALUES('0', '%s', '%s', '%s', '%s') """ % (fecha, cursoid, instanceid, persona.idusermoodle)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                tarea.idtareamoodle = instanceid
                tarea.estado_id = 4
                tarea.save()

            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = tarea.idtareamoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """
                        update mooc_assign 
                        set name='%s', 
                        timemodified='%s', 
                        intro='%s', 
                        duedate='%s', 
                        cutoffdate='%s', 
                        allowsubmissionsfromdate='%s', 
                        grade='%s'
                        where id='%s'
                        """ % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0, instance)
                cursor.execute(sql)

                sql = """UPDATE mooc_event 
                SET description='%s',
                name='%s',
                timestart='%s',
                timesort='%s',
                timemodified='%s'
                WHERE instance='%s' and courseid='%s' 
                """ % (intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha, instance, cursoid)
                cursor.execute(sql)

                if tarea.todos:
                    sql = """UPDATE mooc_assign_plugin_config SET value = '*' WHERE assignment = %s and name = 'filetypeslist'""" % (instance)
                    cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """update mooc_grade_items 
                        set categoryid='%s',
                        itemname='%s',
                        gradetype='%s',
                        grademax='%s',
                        timemodified='%s'
                        where courseid='%s' and iteminstance='%s'
                """ % (categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, cursoid, instance)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if tarea.calificar:
                # YA CREADA LA TAREA SE PROCEDE A INSERTAR LA RUBRICA
                if tarea.rubricamoodle:
                    rubrica = tarea.rubricamoodle
                    # PROCEDEMOS A BUSCAR LA AREA
                    sql = """select id from mooc_grading_areas where contextid='%s' """ % (contextid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    areaid = buscar[0][0]

                    # VERIFICACION SI EXISTEN DATOS PARA BORRARLOS Y LUEGO INSERTAR DE NUEVO
                    sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    grading_definitions = 0
                    if buscar:
                        grading_definitions = buscar[0][0]
                        for c in rubrica.items():
                            orden = c.orden

                            # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                            sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                            cursor.execute(sql)
                            buscar = cursor.fetchall()
                            if buscar:
                                gradingform_rubric_criteria = buscar[0][0]

                                sql = """DELETE FROM mooc_gradingform_rubric_levels WHERE criterionid = %s """ % (gradingform_rubric_criteria)
                                cursor.execute(sql)

                        sql = """DELETE FROM mooc_gradingform_rubric_criteria WHERE definitionid = %s """ % (grading_definitions)
                        cursor.execute(sql)

                        sql = """DELETE FROM mooc_grading_definitions WHERE id = %s """ % (grading_definitions)
                        cursor.execute(sql)
                        grading_definitions = 0

                    # FIN DE ELIMINACION
                    if grading_definitions == 0:
                        sql = """INSERT INTO mooc_grading_definitions
                                (areaid,method,timecreated,usercreated,timemodified,usermodified,status,descriptionformat,options,name)
                                VALUES(%s,'rubric',%s,%s,%s,%s,'20','1',
                                '{"sortlevelsasc":"1","lockzeropoints":"1","alwaysshowdefinition":"1","showdescriptionteacher":"1","showdescriptionstudent":"1","showscoreteacher":"1","showscorestudent":"1","enableremarks":"1","showremarksstudent":"1"}','%s')""" % (areaid, fecha, persona.idusermoodle, fecha, persona.idusermoodle, rubrica.nombre)
                        cursor.execute(sql)

                        # PROCEDEMOS A BUSCAR GRADING_DEFINITIONS
                        sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        grading_definitions = buscar[0][0]

                        # INSERTAR LOS CRITERIOS
                        for c in rubrica.items():
                            item = c.item
                            item = item.replace("'", "")
                            orden = c.orden
                            sql = """INSERT INTO mooc_gradingform_rubric_criteria (definitionid,descriptionformat,sortorder,description)
                                     VALUES(%s,'0',%s,'%s')""" % (grading_definitions, orden, item)
                            cursor.execute(sql)

                            # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                            sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                            cursor.execute(sql)
                            buscar = cursor.fetchall()
                            gradingform_rubric_criteria = buscar[0][0]

                            for d in c.detalle():
                                descripcion = d.descripcion.replace("'", "")
                                orden1 = d.orden
                                valor = d.valor

                                sql = """INSERT INTO mooc_gradingform_rubric_levels (criterionid, definitionformat, score, definition)
                                VALUES(%s,'0',%s,'%s')""" % (gradingform_rubric_criteria, valor, descripcion)
                                cursor.execute(sql)

                        sql = """UPDATE mooc_grading_areas set activemethod='rubric' where contextid=%s""" % (contextid)
                        cursor.execute(sql)
            if tarea.idtareamoodle > 0:
                tarea.estado_id = 4
                tarea.save()
            return True, u"Tarea migrada a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearPracticasTareasMoodle(tareaid, persona):
    from sga.models import TareaPracticaSilaboSemanal
    from inno.models import FormatoPlanificacionRecurso
    from django.db import connections, transaction
    from sga.funciones import null_to_numeric
    tarea = TareaPracticaSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            conexion = None
            if materia.coordinacion():
                if coordinacion_id == 9:
                    conexion = connections['db_moodle_virtual']
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                else:
                    conexion = connections['aulagradob']
            else:
                conexion = connections['moodle_db']
            cursor = conexion.cursor()
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            section_mooc = 0 if coordinacion_id == 7 else 11
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, section_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = ""
            # intro = """
            #         <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>
            #         <p>%s</p>
            #
            #         <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Instrucciones:</h3></p>
            #         <p>%s</p>
            #
            #         <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Recomendaciones:</h3></p>
            #         <p>%s</p>
            # """ % (tarea.objetivo, tarea.instruccion, tarea.recomendacion)
            detalletareapractica = ""
            if tarea.rubrica:
                # archivorubrica = ""
                # if tarea.archivorubrica:
                #     namea = tarea.archivorubrica.name.split("/")[-1]
                #     archivorubrica = """
                #         <div class="fileuploadsubmission"><img class="icon icon" alt='%s' title='%s' src="https://aulagrado.unemi.edu.ec/theme/image.php/remui/core/1590691061/f/pdf">
                #         <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>
                #         </div>
                #     """ % (namea, namea, tarea.archivorubrica.url, namea)
                intro = """%s
                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Rúbrica:</h3></p>
                    <p>%s</p>
                    <p> </p>
                    """ % (intro, tarea.rubrica)

            if tarea.archivotareapracticasilabo:
                archivotareapracticasilabo, botonformatoestudiante = "", ""
                if tarea.archivotareapracticasilabo:
                    namea = tarea.archivotareapracticasilabo.name.split("/")[-1]
                    if aluformato := FormatoPlanificacionRecurso.objects.filter(id=3, status=True, activo=True).first():
                        if aluformato.archivo:
                            botonformatoestudiante = f"""<a target="_blank" href="https://sga.unemi.edu.ec{aluformato.archivo.url}">{aluformato.descripcion.upper()}</a>"""
                    archivotareapracticasilabo = f"""
                        <div class="fileuploadsubmission">
                            <a target="_blank" href="https://sga.unemi.edu.ec{tarea.archivotareapracticasilabo.url}">{namea}</a>
                            <br>
                            {botonformatoestudiante}
                        </div><br>
                    """
                if tarea.detalle:
                    detalletareapractica = """
                                        <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Detalle:</h3></p>   
                                        <div>%s</div><br>
                                        """ % (tarea.detalle)
                intro = """%s
                        <p>%s</p>
                        %s
                        <p> </p>                    
                        """ % (intro, archivotareapracticasilabo, detalletareapractica)
            # intro = intro.replace("'", "")
            intro = intro.replace("'", "''")

            # if tarea.archivotareasilabo:
            #     archivotareasilabo = ""
            #     if tarea.archivotareasilabo:
            #         namea = tarea.archivotareasilabo.name.split("/")[-1]
            #         archivotareasilabo = """
            #             <div class="fileuploadsubmission"><img class="icon icon" alt='%s' title='%s' src="https://aulagrado.unemi.edu.ec/theme/image.php/remui/core/1590691061/f/pdf">
            #             <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>
            #             </div><br>
            #         """ % (namea, namea, tarea.archivotareasilabo.url, namea)
            #     intro = """%s
            #             <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Archivos Adicionales</h3></p>
            #             %s
            #             """ % (intro, archivotareasilabo)
            #
            # intro = intro.replace("'", "")
            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = int(time.mktime(tarea.fechadesde.date().timetuple()))
            fechahasta = datetime(tarea.fechahasta.date().year, tarea.fechahasta.date().month, tarea.fechahasta.date().day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            if tarea.idtareapracticamoodle > 0:
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and id='%s'""" % (cursoid, tarea.idtareapracticamoodle)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if not buscar:
                    tarea.idtareapracticamoodle = 0
            if tarea.idtareapracticamoodle <= 0:
                sql = """
                        INSERT INTO mooc_assign (name, timemodified, course, intro, introformat, alwaysshowdescription, submissiondrafts, requiresubmissionstatement, sendnotifications, sendlatenotifications,
                                         sendstudentnotifications, duedate, cutoffdate, gradingduedate, allowsubmissionsfromdate, grade, completionsubmit, teamsubmission, requireallteammemberssubmit, blindmarking,
                                         hidegrader, attemptreopenmethod, maxattempts, preventsubmissionnotingroup, markingworkflow, markingallocation) 
                            VALUES('%s', '%s', '%s', '%s', '5', '1', '0', '0', '0', '0',
                                '1', '%s', '%s', '0', '%s', '%s', '1', '0', '0', '0',
                                    '0', 'none', '-1', '0', '0', '0')""" % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, cursoid, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA TAREA CREADA
                sql = """select id from mooc_assign WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section) 
                        VALUES('%s', '1', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '0', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_event (modulename,courseid,groupid,userid,instance,type,description,name,eventtype,timestart,timesort,format,timemodified) 
                        VALUES('assign', '%s', '0', '%s','%s', '1','%s','%s','due', '%s','%s','1','%s') 
                """ % (cursoid, persona.idusermoodle, instance, intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,
                        grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,
                        needsupdate,weightoverride,timecreated,timemodified,hidden) 
                        VALUES('%s', '%s', '%s', 'mod','assign','%s', '0', NULL, '', NULL, '%s', '%s', '0', NULL, NULL, '0', '1', '0', '0', '0', '8', '0',
                        NULL, '0', '0', '0', '0','%s','%s', '0') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, fecha)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR GRADE ITEM ID
                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid='%s' and iteminstance='%s' """ % (cursoid, categoryid, instance)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                gradeitemid = buscar[0][0]

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES raiz
                sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                categoryidraiz = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '%s', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '1', '%s', NULL, '%s') 
                """ % (cursoid, categoryidraiz, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, instanceid, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'onlinetext', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxfilesubmissions', '20') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxsubmissionsizebytes', '0') """ % instance
                cursor.execute(sql)

                if tarea.todos:
                    sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', '*') """ % instance
                    cursor.execute(sql)
                else:
                    sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', 'document,spreadsheet,presentation') """ % instance
                    cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s','assignfeedback','comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'comments', 'commentinline', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'editpdf', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'offline', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'file', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grading_areas (contextid,component,areaname,activemethod) VALUES('%s', 'mod_assign', 'submissions', NULL) """ % contextid
                cursor.execute(sql)

                sql = """INSERT INTO mooc_block_recent_activity (action,timecreated,courseid,cmid,userid) VALUES('0', '%s', '%s', '%s', '%s') """ % (fecha, cursoid, instanceid, persona.idusermoodle)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                tarea.idtareapracticamoodle = instanceid
                tarea.estado_id = 4
                tarea.save()

            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = tarea.idtareapracticamoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """
                        update mooc_assign 
                        set name='%s', 
                        timemodified='%s', 
                        intro='%s', 
                        duedate='%s', 
                        cutoffdate='%s', 
                        allowsubmissionsfromdate='%s', 
                        grade='%s'
                        where id='%s'
                        """ % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0, instance)
                cursor.execute(sql)

                sql = """UPDATE mooc_event 
                SET description='%s',
                name='%s',
                timestart='%s',
                timesort='%s',
                timemodified='%s'
                WHERE instance='%s' and courseid='%s' 
                """ % (intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha, instance, cursoid)
                cursor.execute(sql)

                if tarea.todos:
                    sql = """UPDATE mooc_assign_plugin_config SET value = '*' WHERE assignment = %s and name = 'filetypeslist'""" % (instance)
                    cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """update mooc_grade_items 
                        set categoryid='%s',
                        itemname='%s',
                        gradetype='%s',
                        grademax='%s',
                        timemodified='%s'
                        where courseid='%s' and iteminstance='%s'
                """ % (categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, cursoid, instance)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if tarea.calificar:
                # YA CREADA LA TAREA SE PROCEDE A INSERTAR LA RUBRICA
                if tarea.rubricamoodle:
                    rubrica = tarea.rubricamoodle
                    # PROCEDEMOS A BUSCAR LA AREA
                    sql = """select id from mooc_grading_areas where contextid='%s' """ % (contextid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    areaid = buscar[0][0]

                    # VERIFICACION SI EXISTEN DATOS PARA BORRARLOS Y LUEGO INSERTAR DE NUEVO
                    sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    grading_definitions = 0
                    if buscar:
                        grading_definitions = buscar[0][0]
                    #     for c in rubrica.items():
                    #         orden = c.orden
                    #
                    #         # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                    #         sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                    #         cursor.execute(sql)
                    #         buscar = cursor.fetchall()
                    #         gradingform_rubric_criteria = buscar[0][0]
                    #
                    #         sql = """DELETE FROM mooc_gradingform_rubric_levels WHERE criterionid = %s """ % (gradingform_rubric_criteria)
                    #         cursor.execute(sql)
                    #
                    #     sql = """DELETE FROM mooc_gradingform_rubric_criteria WHERE definitionid = %s """ % (grading_definitions)
                    #     cursor.execute(sql)
                    #
                    #     sql = """DELETE FROM mooc_grading_definitions WHERE id = %s """ % (grading_definitions)
                    #     cursor.execute(sql)

                    # FIN DE ELIMINACION

                    if grading_definitions == 0:
                        sql = """INSERT INTO mooc_grading_definitions
                                (areaid,method,timecreated,usercreated,timemodified,usermodified,status,descriptionformat,options,name)
                                VALUES(%s,'rubric',%s,%s,%s,%s,'20','1',
                                '{"sortlevelsasc":"1","lockzeropoints":"1","alwaysshowdefinition":"1","showdescriptionteacher":"1","showdescriptionstudent":"1","showscoreteacher":"1","showscorestudent":"1","enableremarks":"1","showremarksstudent":"1"}','%s')""" % (areaid, fecha, persona.idusermoodle, fecha, persona.idusermoodle, rubrica.nombre)
                        cursor.execute(sql)

                        # PROCEDEMOS A BUSCAR GRADING_DEFINITIONS
                        sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        grading_definitions = buscar[0][0]

                        # INSERTAR LOS CRITERIOS
                        for c in rubrica.items():
                            item = c.item
                            item = item.replace("'", "")
                            orden = c.orden
                            sql = """INSERT INTO mooc_gradingform_rubric_criteria (definitionid,descriptionformat,sortorder,description)
                                     VALUES(%s,'0',%s,'%s')""" % (grading_definitions, orden, item)
                            # sql = f"INSERT INTO mooc_gradingform_rubric_criteria (definitionid,descriptionformat,sortorder,description) VALUES({grading_definitions},'0',{orden},'{item}')"
                            cursor.execute(sql)

                            # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                            sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                            cursor.execute(sql)
                            buscar = cursor.fetchall()
                            gradingform_rubric_criteria = buscar[0][0]

                            for d in c.detalle():
                                descripcion = d.descripcion.replace("'", "")
                                orden1 = d.orden
                                valor = d.valor

                                sql = """INSERT INTO mooc_gradingform_rubric_levels (criterionid, definitionformat, score, definition)
                                VALUES(%s,'0',%s,'%s')""" % (gradingform_rubric_criteria, valor, descripcion)
                                cursor.execute(sql)

                        sql = """UPDATE mooc_grading_areas set activemethod='rubric' where contextid=%s""" % (contextid)
                        cursor.execute(sql)
            if tarea.idtareapracticamoodle > 0:
                tarea.estado_id = 4
                tarea.save()

            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearTestMoodle(tareaid, persona):
    from sga.models import TestSilaboSemanal
    from django.db import connections

    tarea = TestSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    if DEBUG:
        tarea.idtestmoodle = 0
        tarea.estado_id = 4
        tarea.save()
        return True, u"Recurso migrado a Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            cursor = None
            conexion = None
            if materia.coordinacion():
                if coordinacion_id == 9:
                    # cursor = connections['db_moodle_virtual'].cursor()
                    conexion = connections['db_moodle_virtual']
                    idmodulo = 17
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                    idmodulo = 17
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodulo = 17
                else:
                    conexion = connections['aulagradob']
                    idmodulo = 18
            else:
                # cursor = connections['moodle_db'].cursor()
                conexion = connections['moodle_db']
                idmodulo = 17

            seccion_mooc = 0 if coordinacion_id == 7 else 4
            cursor = conexion.cursor()
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, seccion_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = ""
            horadesde = 0
            minutodesde = 0
            horahasta = 23
            minutohasta = 59
            if tarea.horadesde:
                horadesde = tarea.horadesde.hour
                minutodesde = tarea.horadesde.minute

            if tarea.horahasta:
                horahasta = tarea.horahasta.hour
                minutohasta = tarea.horahasta.minute

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = datetime(tarea.fechadesde.date().year, tarea.fechadesde.date().month,
                                  tarea.fechadesde.date().day, horadesde, minutodesde)
            fechadesde = int(time.mktime(fechadesde.timetuple()))
            fechahasta = datetime(tarea.fechahasta.date().year, tarea.fechahasta.date().month,
                                  tarea.fechahasta.date().day, horahasta, minutohasta)
            fechahasta = int(time.mktime(fechahasta.timetuple()))
            limitetiempo = tarea.tiempoduracion * 60
            introduccion = u"<p>%s <br> %s</p>" % (tarea.instruccion, tarea.recomendacion)
            notamaxima = 0
            if tarea.calificar:
                notamaxima = tarea.detallemodelo.notamaxima

            if tarea.navegacion == 1:
                navegacion = 'free'
            else:
                navegacion = 'sequential'

            if tarea.idtestmoodle == 0:
                introduccion = introduccion.replace("'", "''")
                sql = """INSERT INTO mooc_quiz (name,timeopen,timeclose,timelimit,overduehandling,graceperiod,grade,attempts,grademethod,questionsperpage,navmethod,shuffleanswers,preferredbehaviour,canredoquestions,attemptonlast,showuserpicture,decimalpoints,questiondecimalpoints,showblocks,subnet,delay1,delay2,browsersecurity,allowofflineattempts,completionattemptsexhausted,course,intro,introformat,timemodified,password,reviewattempt,reviewcorrectness,reviewmarks,reviewspecificfeedback,reviewgeneralfeedback,reviewrightanswer,reviewoverallfeedback) VALUES('%s','%s','%s','%s','autosubmit','0','%s','%s','1','1','%s','1','deferredfeedback','0','0','0','2','-1','0','','0','0','-','0','0','%s','%s','5','%s','','65552','16','16','16','16','0','16') """ % (
                tarea.nombretest, fechadesde, fechahasta, limitetiempo, notamaxima, tarea.vecesintento, navegacion, cursoid, introduccion, fecha)
                cursor.execute(sql)

                sql = """select id from mooc_quiz WHERE course=%s AND name='%s' and timemodified='%s' """ % (
                    cursoid, tarea.nombretest, fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course,module,instance,visible,visibleold,visibleoncoursepage,idnumber,groupmode,groupingid,completion,completiongradeitemnumber,completionview,completionexpected,availability,showdescription,added) VALUES('%s','%s','%s','1','1','1','','0','0','2','0','0','0',NULL,'1','%s') """ % (
                        cursoid,idmodulo, instanceid, fecha)
                cursor.execute(sql)


                sql = """select id from mooc_course_modules WHERE course=%s AND module=%s and instance='%s' """ % (
                        cursoid,idmodulo,instanceid)

                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_quiz_sections (quizid,firstslot,heading,shufflequestions) VALUES('%s','1','','0')""" % (instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (course_modules)
                cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (
                    course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (
                    pathcontext, depthcontext, course_modules)
                cursor.execute(sql)

                sql = """DELETE FROM mooc_quiz_feedback WHERE quizid = '%s'""" % (instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_quiz_feedback (quizid,feedbacktext,feedbacktextformat,mingrade,maxgrade) VALUES ('%s','','1','0','11')""" % (instanceid)
                cursor.execute(sql)

                descripcion = u"<div class=""no-overflow""><p>%s <br> %s</p></div>" % (
                    tarea.instruccion, tarea.recomendacion)
                name1 = u"%s abre" % (tarea.nombretest)

                descripcion = descripcion.replace("'", "''")
                sql = """INSERT INTO mooc_event (type,description,courseid,groupid,userid,modulename,instance,timestart,timeduration,timesort,visible,eventtype,priority,name,format,timemodified) VALUES ('0','%s','%s','0','%s','quiz','%s','%s','0','%s','1','open',NULL,'%s','1','%s')""" % (descripcion, cursoid, persona.idusermoodle, instanceid, fechadesde, fechahasta, name1, fecha)
                cursor.execute(sql)

                name1 = u"%s closes" % (tarea.nombretest)
                sql = """INSERT INTO mooc_event (type,description,courseid,groupid,userid,modulename,instance,timestart,timeduration,timesort,visible,eventtype,name,format,timemodified) VALUES ('1','%s','%s','0','%s','quiz','%s','%s','0','%s','1','close','%s','1','%s')""" % (descripcion, cursoid, persona.idusermoodle, instanceid, fechadesde, fechahasta, name1, fecha)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if tarea.calificar and not buscar:
                    materia.crear_actualizar_categoria_notas_curso()
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timecreated,timemodified,hidden)VALUES ('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1','0','0','0','11','0',NULL,'0','0','0','0','%s','%s','%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, tarea.detallemodelo.notamaxima, tarea.detallemodelo.notamaxima, fecha, fecha, fecha)
                else:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timecreated,timemodified,hidden)VALUES ('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1','0','0','0','11','0',NULL,'0','0','0','0','%s','%s','%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, 0, 0, fecha, fecha, fecha)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (
                    cursoid, categoryid, tarea.nombretest, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                grade_items = buscar[0][0]

                if tarea.calificar:
                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) VALUES('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1.00000','0.00000','0.00000','0.00000','11','0',NULL,'0','0','0','0','%s','%s','1','%s',NULL,'%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, tarea.detallemodelo.notamaxima, tarea.detallemodelo.notamaxima, fecha, fecha, grade_items, persona.idusermoodle)
                else:
                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) VALUES('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1.00000','0.00000','0.00000','0.00000','11','0',NULL,'0','0','0','0','%s','%s','1','%s',NULL,'%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, 0, 0, fecha, fecha, grade_items, persona.idusermoodle)
                cursor.execute(sql)

                # # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=17 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)
                # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                # cursor.execute(sql)
                # buscar = cursor.fetchall()
                # course_modules = buscar[0][0]
                #
                # sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and section=4""" % (course_modules, cursoid)
                # cursor.execute(sql)
                #
                #
                # sql = """update mooc_course_modules set section='%s' where course=%s and module=17 and instance=%s""" % (section, cursoid, instanceid)
                # cursor.execute(sql)
                # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=17 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)
                sql = """update mooc_course_modules set section='%s' where course=%s and module='%s' and instance=%s""" % (
                    section, cursoid,idmodulo, instanceid)
                cursor.execute(sql)

                sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and section=4""" % (course_modules, cursoid)
                cursor.execute(sql)

                tarea.idtestmoodle = instanceid
                tarea.estado_id = 4
                tarea.save()
            else:
                introduccion = introduccion.replace("'", "''")
                instanceid = tarea.idtestmoodle
                sql = """UPDATE mooc_quiz set name='%s',timeopen='%s',timeclose='%s',timelimit='%s',grade='%s',attempts='%s',navmethod='%s',intro='%s',timemodified='%s' where id='%s' and course='%s'""" % (tarea.nombretest, fechadesde, fechahasta, limitetiempo, notamaxima, tarea.vecesintento, navegacion, introduccion, fecha, instanceid, cursoid)
                cursor.execute(sql)

                sql = """select id from mooc_course_modules WHERE course=%s AND module=%s and instance='%s' """ % (
                    cursoid,idmodulo, instanceid)

                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if not buscar:
                    sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (course_modules)
                    cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (
                    pathcontext, depthcontext, course_modules)
                cursor.execute(sql)

                descripcion = u"<div class=""no-overflow""><p>%s <br> %s</p></div>" % (
                    tarea.instruccion, tarea.recomendacion)
                name1 = u"%s abre" % (tarea.nombretest)
                descripcion = descripcion.replace("'", "''")
                sql = """UPDATE mooc_event set description='%s',userid='%s',timestart='%s',timeduration='%s',name='%s',timemodified='%s'where courseid='%s' and instance='%s' and eventtype='open'""" % (descripcion, persona.idusermoodle, fechadesde, fechahasta, name1, fecha, cursoid, instanceid)
                cursor.execute(sql)

                name1 = u"%s closes" % (tarea.nombretest)
                sql = """UPDATE mooc_event set description='%s',userid='%s',timestart='%s',timeduration='%s',name='%s',timemodified='%s'where courseid='%s' and instance='%s' and eventtype='close'""" % (descripcion, persona.idusermoodle, fechadesde, fechahasta, name1, fecha, cursoid, instanceid)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if tarea.calificar and not buscar:
                    materia.crear_actualizar_categoria_notas_curso()
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """select id,categoryid from mooc_grade_items WHERE courseid=%s  and iteminstance=%s """ % (cursoid, tarea.idtestmoodle)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    idupdate = buscar[0][0]
                    categoryidcompara = buscar[0][1]

                    if categoryid != categoryidcompara:
                        sql = """UPDATE mooc_grade_items set categoryid='%s'where id='%s'""" % (categoryid, idupdate)
                        cursor.execute(sql)

                        if tarea.calificar:
                            sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        else:
                            sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """UPDATE mooc_grade_items set itemname='%s',grademax='%s',timecreated='%s',timemodified='%s',hidden='%s', gradepass='%s'where courseid='%s' and categoryid='%s' and itemtype='mod' and itemmodule='quiz' and iteminstance='%s'""" % (tarea.nombretest, tarea.detallemodelo.notamaxima, fecha, fecha, fecha, tarea.detallemodelo.notamaxima, cursoid, categoryid, instanceid)
                else:
                    sql = """UPDATE mooc_grade_items set itemname='%s',grademax='%s',timecreated='%s',timemodified='%s',hidden='%s', gradepass='%s'where courseid='%s' and categoryid='%s' and itemtype='mod' and itemmodule='quiz' and iteminstance='%s'""" % (tarea.nombretest, 0, fecha, fecha, fecha, 0, cursoid, categoryid, instanceid)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (cursoid, categoryid, tarea.nombretest, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                grade_items = buscar[0][0]

                # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=17 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)
                sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and section=4""" % (course_modules, cursoid)
                cursor.execute(sql)


                sql = """update mooc_course_modules set section='%s' where course=%s and module='%s' and instance=%s""" % (
                    section,cursoid,idmodulo,  instanceid)

                cursor.execute(sql)

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(sql)

            if tarea.idtestmoodle > 0:
                tarea.estado_id = 4
                tarea.save()
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearTestMoodleAdmision(tareaid, persona):
    from sga.models import TestSilaboSemanalAdmision
    from django.db import connections

    tarea = TestSilaboSemanalAdmision.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    conexion = None
    if materia.coordinacion():
        if materia.coordinacion().id == 9:
            cursor_verbose = 'db_moodle_virtual'
            conexion = connections['db_moodle_virtual']
        else:
            conexion = connections['moodle_db']
            cursor_verbose = 'moodle_db'
    else:
        conexion = connections['moodle_db']
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    # if DEBUG:
    #     tarea.idtestmoodle = 0
    #     tarea.estado_id = 4
    #     tarea.save()
    #     return True, u"Recurso migrado a Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            cursor = conexion.cursor()
            if tarea.silabosemanal.examen:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 12)
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 4)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = ""
            horainicio = 0
            minutodesde = 0
            horafin = 23
            minutohasta = 59
            if tarea.horainicio:
                horainicio = tarea.horainicio.hour
                minutodesde = tarea.horainicio.minute

            if tarea.horafin:
                horafin = tarea.horafin.hour
                minutohasta = tarea.horafin.minute

            fechat = int(time.mktime(datetime.now().timetuple()))
            fecha = datetime(tarea.fecha.year, tarea.fecha.month, tarea.fecha.day, horainicio, minutodesde)
            fecha = int(time.mktime(fecha.timetuple()))
            fechahasta = datetime(tarea.fechahasta.year, tarea.fechahasta.month, tarea.fechahasta.day, horafin, minutohasta)
            fechahasta = int(time.mktime(fechahasta.timetuple()))
            limitetiempo = tarea.tiempoduracion * 60
            descripcion = u"<p>%s <br></p>" % (tarea.descripcion)
            notamaxima = 0
            if tarea.calificar:
                notamaxima = tarea.detallemodelo.notamaxima

            if tarea.navegacion == 1:
                navegacion = 'free'
            else:
                navegacion = 'sequential'
            password = tarea.password
            if tarea.idtestmoodle == 0:
                descripcion = descripcion.replace("'", "''")
                sql = """INSERT INTO mooc_quiz (name,timeopen,timeclose,timelimit,overduehandling,graceperiod,grade,attempts,grademethod,questionsperpage,navmethod,shuffleanswers,preferredbehaviour,canredoquestions,attemptonlast,showuserpicture,decimalpoints,questiondecimalpoints,showblocks,subnet,delay1,delay2,browsersecurity,allowofflineattempts,completionattemptsexhausted,course,intro,introformat,timemodified,password,reviewattempt,reviewcorrectness,reviewmarks,reviewspecificfeedback,reviewgeneralfeedback,reviewrightanswer,reviewoverallfeedback) VALUES('%s','%s','%s','%s','autosubmit','0','%s','%s','1','%s','%s','1','deferredfeedback','0','0','0','2','-1','0','','0','0','-','0','0','%s','%s','5','%s','%s','65552','16','16','16','16','0','16') """ % (
                tarea.titulo, fecha, fechahasta, limitetiempo, notamaxima, tarea.vecesintento, tarea.esquemapregunta, navegacion, cursoid, descripcion, fechat,password)
                cursor.execute(sql)

                sql = """select id from mooc_quiz WHERE course=%s AND name='%s' and timemodified='%s' """ % (
                    cursoid, tarea.titulo, fechat)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course,module,instance,visible,visibleold,visibleoncoursepage,idnumber,groupmode,groupingid,completion,completiongradeitemnumber,completionview,completionexpected,availability,showdescription,added) VALUES('%s','18','%s','1','1','1','','0','0','2','0','0','0',NULL,'1','%s') """ % (
                    cursoid, instanceid, fechat)
                cursor.execute(sql)

                sql = """select id from mooc_course_modules WHERE course=%s AND module=18 and instance='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = """update mooc_course_modules set section='%s' where course=%s and module=18 and instance=%s""" % (section, cursoid, instanceid)
                cursor.execute(sql)


                sql = """INSERT INTO mooc_quiz_sections (quizid,firstslot,heading,shufflequestions) VALUES('%s','1','','0')""" % (instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (course_modules)
                cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (
                    course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (
                    pathcontext, depthcontext, course_modules)
                cursor.execute(sql)

                sql = """DELETE FROM mooc_quiz_feedback WHERE quizid = '%s'""" % (instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_quiz_feedback (quizid,feedbacktext,feedbacktextformat,mingrade,maxgrade) VALUES ('%s','','1','0','11')""" % (instanceid)
                cursor.execute(sql)

                descripcion = u"<div class=""no-overflow"">%s</div>" % (tarea.descripcion)
                name1 = u"%s abre" % (tarea.titulo)

                descripcion = descripcion.replace("'", "''")
                sql = """INSERT INTO mooc_event (type,description,courseid,groupid,userid,modulename,instance,timestart,timeduration,timesort,visible,eventtype,priority,name,format,timemodified) VALUES ('0','%s','%s','0','%s','quiz','%s','%s','0','%s','1','open',NULL,'%s','1','%s')""" % (descripcion, cursoid, persona.idusermoodle, instanceid, fecha, fechahasta, name1, fechat)
                cursor.execute(sql)

                name1 = u"%s closes" % (tarea.titulo)
                sql = """INSERT INTO mooc_event (type,description,courseid,groupid,userid,modulename,instance,timestart,timeduration,timesort,visible,eventtype,name,format,timemodified) VALUES ('1','%s','%s','0','%s','quiz','%s','%s','0','%s','1','close','%s','1','%s')""" % (descripcion, cursoid, persona.idusermoodle, instanceid, fecha, fechahasta, name1, fechat)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timecreated,timemodified,hidden)VALUES ('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1','0','0','0','11','0',NULL,'0','0','0','0','%s','%s','%s')""" % (
                    cursoid, categoryid, tarea.titulo, instanceid, tarea.detallemodelo.notamaxima, tarea.detallemodelo.notamaxima, fechat, fechat, fechat)
                else:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timecreated,timemodified,hidden)VALUES ('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1','0','0','0','11','0',NULL,'0','0','0','0','%s','%s','%s')""" % (
                    cursoid, categoryid, tarea.titulo, instanceid, 0, 0, fechat, fechat, fechat)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (
                    cursoid, categoryid, tarea.titulo, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                grade_items = buscar[0][0]

                if tarea.calificar:
                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) VALUES('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1.00000','0.00000','0.00000','0.00000','11','0',NULL,'0','0','0','0','%s','%s','1','%s',NULL,'%s')""" % (
                    cursoid, categoryid, tarea.titulo, instanceid, tarea.detallemodelo.notamaxima, tarea.detallemodelo.notamaxima, fechat, fechat, grade_items, persona.idusermoodle)
                else:
                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) VALUES('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1.00000','0.00000','0.00000','0.00000','11','0',NULL,'0','0','0','0','%s','%s','1','%s',NULL,'%s')""" % (
                    cursoid, categoryid, tarea.titulo, instanceid, 0, 0, fechat, fechat, grade_items, persona.idusermoodle)
                cursor.execute(sql)


                sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and module=18 and course=%s and section=%s""" % (cursoid, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules_all = buscar[0][0]


                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and id=%s""" % (course_modules_all, cursoid, section)
                cursor.execute(sql)

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fechat, cursoid)
                cursor.execute(sql)


                tarea.idtestmoodle = instanceid
                tarea.estado_id = 4
                tarea.save()
            else:
                sql =  """ SELECT * FROM mooc_quiz WHERE id ='%s' """ % (tarea.idtestmoodle)
                cursor.execute(sql)
                existe = cursor.fetchall()
                if existe:
                    descripcion = descripcion.replace("'", "''")
                    instanceid = tarea.idtestmoodle
                    sql = """UPDATE mooc_quiz set name='%s',timeopen='%s',timeclose='%s',timelimit='%s',grade='%s',attempts='%s', questionsperpage='%s', navmethod='%s',intro='%s',timemodified='%s',password='%s' where id='%s' and course='%s'""" % (tarea.titulo, fecha, fechahasta, limitetiempo, notamaxima, tarea.vecesintento, tarea.esquemapregunta ,navegacion, descripcion, fechat,password, instanceid, cursoid)
                    cursor.execute(sql)

                    sql = """select id from mooc_course_modules WHERE course=%s AND module=18 and instance='%s' """ % (cursoid, instanceid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    course_modules = buscar[0][0]

                    sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fechat, cursoid)
                    cursor.execute(sql)

                    sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (course_modules)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (course_modules)
                        cursor.execute(sql)

                    sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (course_modules)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    contextid = buscar[0][0]

                    sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    pathcontext = buscar[0][0]
                    depthcontext = pathcontext.split("/").__len__()
                    pathcontext = "%s/%s" % (pathcontext, contextid)
                    sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (
                        pathcontext, depthcontext, course_modules)
                    cursor.execute(sql)

                    descripcion = u"<div class=""no-overflow"">%s</div>" % (tarea.descripcion)
                    name1 = u"%s abre" % (tarea.titulo)
                    descripcion = descripcion.replace("'", "''")
                    sql = """UPDATE mooc_event set description='%s',userid='%s',timestart='%s',timeduration='%s',name='%s',timemodified='%s'where courseid='%s' and instance='%s' and eventtype='open'""" % (descripcion, persona.idusermoodle, fecha, fechahasta, name1, fechat, cursoid, instanceid)
                    cursor.execute(sql)

                    name1 = u"%s closes" % (tarea.titulo)
                    sql = """UPDATE mooc_event set description='%s',userid='%s',timestart='%s',timeduration='%s',name='%s',timemodified='%s'where courseid='%s' and instance='%s' and eventtype='close'""" % (descripcion, persona.idusermoodle, fecha, fechahasta, name1, fechat, cursoid, instanceid)
                    cursor.execute(sql)

                    if tarea.calificar:
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    else:
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                    if tarea.calificar:
                        sql = """select id,categoryid from mooc_grade_items WHERE courseid=%s  and iteminstance=%s """ % (cursoid, tarea.idtestmoodle)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        idupdate = buscar[0][0]
                        categoryidcompara = buscar[0][1]

                        if categoryid != categoryidcompara:
                            sql = """UPDATE mooc_grade_items set categoryid='%s'where id='%s'""" % (categoryid, idupdate)
                            cursor.execute(sql)

                            if tarea.calificar:
                                sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                            else:
                                sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                            cursor.execute(sql)
                            buscar = cursor.fetchall()
                            categoryid = buscar[0][0]

                    if tarea.calificar:
                        sql = """UPDATE mooc_grade_items set itemname='%s',grademax='%s',timecreated='%s',timemodified='%s',hidden='%s', gradepass='%s'where courseid='%s' and categoryid='%s' and itemtype='mod' and itemmodule='quiz' and iteminstance='%s'""" % (tarea.titulo, tarea.detallemodelo.notamaxima, fechat, fechat, fechat, tarea.detallemodelo.notamaxima, cursoid, categoryid, instanceid)
                    else:
                        sql = """UPDATE mooc_grade_items set itemname='%s',grademax='%s',timecreated='%s',timemodified='%s',hidden='%s', gradepass='%s'where courseid='%s' and categoryid='%s' and itemtype='mod' and itemmodule='quiz' and iteminstance='%s'""" % (tarea.titulo, 0, fechat, fechat, fechat, 0, cursoid, categoryid, instanceid)
                    cursor.execute(sql)

                    sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (cursoid, categoryid, tarea.titulo, instanceid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    grade_items = buscar[0][0]

                    # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=18 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)
                    sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    course_modules_all = buscar[0][0]

                    sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and id=%s""" % (course_modules_all, cursoid, section)
                    cursor.execute(sql)

                    sql = """update mooc_course_modules set section='%s' where course=%s and module=18 and instance=%s""" % (section, cursoid, instanceid)
                    cursor.execute(sql)

                    sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fechat, cursoid)
                    cursor.execute(sql)
                else:
                    tarea.idtestmoodle=0
                    tarea.save(update_fields=['idtestmoodle'])
                    return False, u"Actualice la página e intente nuevamente"

            if tarea.idtestmoodle > 0:
                tarea.url1 = 'https://aulanivelacion.unemi.edu.ec/mod/quiz/view.php?id=%s' % course_modules
                tarea.estado_id = 4
                tarea.save()
            print("%s ----- %s" % (section, materia.idcursomoodle))
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearExamenMoodle(tareaid, persona):
    from sga.models import TestSilaboSemanal
    from django.db import connections, transaction
    tarea = TestSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    if materia.coordinacion():
        if materia.coordinacion().id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"

    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            cursor = None
            conexion = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    conexion = connections['db_moodle_virtual']
                    idmodule = 17
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodule=17
                else:
                    conexion = connections['aulagradob']
                    idmodule=18
            else:
                conexion = connections['moodle_db']
                idmodule=17
            cursor = conexion.cursor()
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 12)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = ""
            horadesde = 0
            minutodesde = 0
            horahasta = 23
            minutohasta = 59
            if tarea.horadesde:
                horadesde = tarea.horadesde.hour
                minutodesde = tarea.horadesde.minute

            if tarea.horahasta:
                horahasta = tarea.horahasta.hour
                minutohasta = tarea.horahasta.minute

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = datetime(tarea.fechadesde.date().year, tarea.fechadesde.date().month,
                                  tarea.fechadesde.date().day, horadesde, minutodesde)
            fechadesde = int(time.mktime(fechadesde.timetuple()))
            fechahasta = datetime(tarea.fechahasta.date().year, tarea.fechahasta.date().month,
                                  tarea.fechahasta.date().day, horahasta, minutohasta)
            fechahasta = int(time.mktime(fechahasta.timetuple()))
            limitetiempo = tarea.tiempoduracion * 60
            introduccion = u"<p>%s <br> %s</p>" % (tarea.instruccion, tarea.recomendacion)
            notamaxima = 0
            if tarea.calificar:
                if not tarea.detallemodelo:
                    return True, u"No tiene modelo evaluativo"
                else:
                    notamaxima = tarea.detallemodelo.notamaxima

            if tarea.navegacion == 1:
                navegacion = 'free'
            else:
                navegacion = 'sequential'
            password = tarea.password
            if tarea.idtestmoodle == 0:
                introduccion = introduccion.replace("'", "''")
                sql = """INSERT INTO mooc_quiz (name,timeopen,timeclose,timelimit,overduehandling,graceperiod,grade,attempts,grademethod,questionsperpage,navmethod,shuffleanswers,preferredbehaviour,canredoquestions,attemptonlast,showuserpicture,decimalpoints,questiondecimalpoints,showblocks,subnet,delay1,delay2,browsersecurity,allowofflineattempts,completionattemptsexhausted,course,intro,introformat,timemodified,password,reviewattempt,reviewcorrectness,reviewmarks,reviewspecificfeedback,reviewgeneralfeedback,reviewrightanswer,reviewoverallfeedback) VALUES('%s','%s','%s','%s','autosubmit','0','%s','%s','1','1','%s','1','deferredfeedback','0','0','0','2','-1','0','','0','0','-','0','0','%s','%s','5','%s','%s','65552','16','16','16','16','0','16') """ % (
                tarea.nombretest, fechadesde, fechahasta, limitetiempo, notamaxima, tarea.vecesintento, navegacion, cursoid, introduccion, fecha,password)
                cursor.execute(sql)

                sql = """select id from mooc_quiz WHERE course=%s AND name='%s' and timemodified='%s' """ % (
                    cursoid, tarea.nombretest, fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course,module,instance,visible,visibleold,visibleoncoursepage,idnumber,groupmode,groupingid,completion,completiongradeitemnumber,completionview,completionexpected,availability,showdescription,added) VALUES('%s','%s','%s','1','1','1','','0','0','2','0','0','0',NULL,'1','%s') """ % (
                    cursoid,idmodule, instanceid, fecha)
                cursor.execute(sql)

                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' """ % (
                    cursoid,idmodule, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_quiz_sections (quizid,firstslot,heading,shufflequestions) VALUES('%s','1','','0')""" % (instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (course_modules)
                cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (
                    course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (
                    pathcontext, depthcontext, course_modules)
                cursor.execute(sql)

                sql = """DELETE FROM mooc_quiz_feedback WHERE quizid = '%s'""" % (instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_quiz_feedback (quizid,feedbacktext,feedbacktextformat,mingrade,maxgrade) VALUES ('%s','','1','0','11')""" % (instanceid)
                cursor.execute(sql)

                descripcion = u"<div class=""no-overflow""><p>%s <br> %s</p></div>" % (
                    tarea.instruccion, tarea.recomendacion)
                name1 = u"%s abre" % (tarea.nombretest)

                descripcion = descripcion.replace("'", "''")
                sql = """INSERT INTO mooc_event (type,description,courseid,groupid,userid,modulename,instance,timestart,timeduration,timesort,visible,eventtype,priority,name,format,timemodified) VALUES ('0','%s','%s','0','%s','quiz','%s','%s','0','%s','1','open',NULL,'%s','1','%s')""" % (descripcion, cursoid, persona.idusermoodle, instanceid, fechadesde, fechahasta, name1, fecha)
                cursor.execute(sql)

                name1 = u"%s closes" % (tarea.nombretest)
                sql = """INSERT INTO mooc_event (type,description,courseid,groupid,userid,modulename,instance,timestart,timeduration,timesort,visible,eventtype,name,format,timemodified) VALUES ('1','%s','%s','0','%s','quiz','%s','%s','0','%s','1','close','%s','1','%s')""" % (descripcion, cursoid, persona.idusermoodle, instanceid, fechadesde, fechahasta, name1, fecha)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if tarea.calificar and not buscar:
                    materia.crear_actualizar_categoria_notas_curso()
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timecreated,timemodified,hidden)VALUES ('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1','0','0','0','11','0',NULL,'0','0','0','0','%s','%s','%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, tarea.detallemodelo.notamaxima, tarea.detallemodelo.notamaxima, fecha, fecha, fecha)
                else:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timecreated,timemodified,hidden)VALUES ('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1','0','0','0','11','0',NULL,'0','0','0','0','%s','%s','%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, 0, 0, fecha, fecha, fecha)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (
                    cursoid, categoryid, tarea.nombretest, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                grade_items = buscar[0][0]

                if tarea.calificar:
                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) VALUES('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1.00000','0.00000','0.00000','0.00000','11','0',NULL,'0','0','0','0','%s','%s','1','%s',NULL,'%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, tarea.detallemodelo.notamaxima, tarea.detallemodelo.notamaxima, fecha, fecha, grade_items, persona.idusermoodle)
                else:
                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) VALUES('%s','%s','%s','mod','quiz','%s','0',NULL,'',NULL,'1','%s','0',NULL,NULL,'%s','1.00000','0.00000','0.00000','0.00000','11','0',NULL,'0','0','0','0','%s','%s','1','%s',NULL,'%s')""" % (
                    cursoid, categoryid, tarea.nombretest, instanceid, 0, 0, fecha, fecha, grade_items, persona.idusermoodle)
                cursor.execute(sql)

                # # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=17 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)
                # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                # cursor.execute(sql)
                # buscar = cursor.fetchall()
                # course_modules = buscar[0][0]
                #
                # sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and section=4""" % (course_modules, cursoid)
                # cursor.execute(sql)
                #
                #
                # sql = """update mooc_course_modules set section='%s' where course=%s and module=17 and instance=%s""" % (section, cursoid, instanceid)
                # cursor.execute(sql)
                # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=17 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)

                sql = """update mooc_course_modules set section='%s' where course=%s and module=%s and instance=%s""" % (section,cursoid,idmodule,instanceid)
                cursor.execute(sql)

                sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and section=12""" % (course_modules, cursoid)
                cursor.execute(sql)

                tarea.idtestmoodle = instanceid
                tarea.estado_id = 4
                tarea.save()
            else:
                introduccion = introduccion.replace("'", "''")
                instanceid = tarea.idtestmoodle
                sql = """UPDATE mooc_quiz set name='%s',timeopen='%s',timeclose='%s',timelimit='%s',grade='%s',attempts='%s',navmethod='%s',intro='%s',timemodified='%s',password='%s' where id='%s' and course='%s'""" % (tarea.nombretest, fechadesde, fechahasta, limitetiempo, notamaxima, tarea.vecesintento, navegacion, introduccion, fecha, password, instanceid, cursoid)
                cursor.execute(sql)

                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' """ % (cursoid,idmodule, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if not buscar:
                    sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (course_modules)
                    cursor.execute(sql)

                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (course_modules)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (
                    pathcontext, depthcontext, course_modules)
                cursor.execute(sql)

                descripcion = u"<div class=""no-overflow""><p>%s <br> %s</p></div>" % (
                    tarea.instruccion, tarea.recomendacion)
                name1 = u"%s abre" % (tarea.nombretest)
                descripcion = descripcion.replace("'", "''")
                sql = """UPDATE mooc_event set description='%s',userid='%s',timestart='%s',timeduration='%s',name='%s',timemodified='%s'where courseid='%s' and instance='%s' and eventtype='open'""" % (descripcion, persona.idusermoodle, fechadesde, fechahasta, name1, fecha, cursoid, instanceid)
                cursor.execute(sql)

                name1 = u"%s closes" % (tarea.nombretest)
                sql = """UPDATE mooc_event set description='%s',userid='%s',timestart='%s',timeduration='%s',name='%s',timemodified='%s'where courseid='%s' and instance='%s' and eventtype='close'""" % (descripcion, persona.idusermoodle, fechadesde, fechahasta, name1, fecha, cursoid, instanceid)
                cursor.execute(sql)

                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                if tarea.calificar and not buscar:
                    materia.crear_actualizar_categoria_notas_curso()
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """select id,categoryid from mooc_grade_items WHERE courseid=%s  and iteminstance=%s """ % (cursoid, tarea.idtestmoodle)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    idupdate = buscar[0][0]
                    categoryidcompara = buscar[0][1]

                    if categoryid != categoryidcompara:
                        sql = """UPDATE mooc_grade_items set categoryid='%s'where id='%s'""" % (categoryid, idupdate)
                        cursor.execute(sql)

                        if tarea.calificar:
                            sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        else:
                            sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        categoryid = buscar[0][0]

                if tarea.calificar:
                    sql = """UPDATE mooc_grade_items set itemname='%s',grademax='%s',timecreated='%s',timemodified='%s',hidden='%s', gradepass='%s'where courseid='%s' and categoryid='%s' and itemtype='mod' and itemmodule='quiz' and iteminstance='%s'""" % (tarea.nombretest, tarea.detallemodelo.notamaxima, fecha, fecha, fecha, tarea.detallemodelo.notamaxima, cursoid, categoryid, instanceid)
                else:
                    sql = """UPDATE mooc_grade_items set itemname='%s',grademax='%s',timecreated='%s',timemodified='%s',hidden='%s', gradepass='%s'where courseid='%s' and categoryid='%s' and itemtype='mod' and itemmodule='quiz' and iteminstance='%s'""" % (tarea.nombretest, 0, fecha, fecha, fecha, 0, cursoid, categoryid, instanceid)
                cursor.execute(sql)

                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid=%s and itemname='%s' and iteminstance=%s """ % (cursoid, categoryid, tarea.nombretest, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                grade_items = buscar[0][0]

                sql = """update mooc_course_modules set section='%s' where course=%s and module='%s' and instance=%s""" % (
                    section, cursoid,idmodule, instanceid)
                cursor.execute(sql)

                # sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where course=%s and module=17 and instance in (select id from mooc_quiz where course=%s)""" % (cursoid, cursoid)
                sql = """select array_to_string(array_agg(id),',') from mooc_course_modules where deletioninprogress=0 and course=%s and section=%s""" % (cursoid, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE course = %s and section=12""" % (course_modules, cursoid)
                cursor.execute(sql)

                sql = """update mooc_course_modules set section='%s' where course=%s and module='%s' and instance=%s""" % (section, cursoid,idmodule, instanceid)
                cursor.execute(sql)

                sql = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(sql)

            if tarea.idtestmoodle > 0:
                tarea.estado_id = 4
                tarea.save()
            return True, u"Examen migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def EliminarTestMoodle(tareaid):
    from sga.models import TestSilaboSemanal
    from django.db import connections
    tarea = TestSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    cursoid = materia.idcursomoodle
    if materia.coordinacion():
        if materia.coordinacion().id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'

    # delete si ya existen
    with transaction.atomic(using=cursor_verbose):
        try:
            conexion = None
            instanceid = tarea.idtestmoodle
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    conexion = connections['db_moodle_virtual']
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                else:
                    conexion = connections['aulagradob']
            else:
                conexion = connections['moodle_db']
            cursor = conexion.cursor()
            if instanceid > 0:
                sql = """
                      DELETE FROM mooc_quiz WHERE id=%s
                      """ % (instanceid)
                cursor.execute(sql)

                sql = """
                      select id from mooc_course_modules WHERE course=%s AND module=16 and instance='%s' 
                      """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                course_modules = buscar[0][0]

                sql = """
                      DELETE FROM mooc_course_modules WHERE course=%s AND module=16 and instance='%s' 
                      """ % (cursoid, instanceid)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_quiz_sections WHERE quizid=%s and firstslot=1 
                      """ % (instanceid)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_quiz_sections WHERE quizid=%s and firstslot=1 
                      """ % (instanceid)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_context WHERE contextlevel=70 AND instanceid='%s' 
                      """ % (course_modules)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_quiz_feedback WHERE quizid='%s' 
                      """ % (instanceid)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_event WHERE courseid='%s' and instance='%s'
                      """ % (cursoid, instanceid)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_grade_items WHERE courseid='%s' and iteminstance='%s'
                      """ % (cursoid, instanceid)
                cursor.execute(sql)

                sql = """
                      DELETE FROM mooc_grade_items_history WHERE courseid='%s' and iteminstance='%s'
                      """ % (cursoid, instanceid)
                cursor.execute(sql)
            return True, u"Recurso Eliminado"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearPracticasTareasMoodleAux(tareaid, persona):
    from sga.models import TareaPracticaSilaboSemanal
    from django.db import connections
    from sga.funciones import null_to_numeric
    tarea = TareaPracticaSilaboSemanal.objects.get(pk=tareaid)
    materia = tarea.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    materia = tarea.silabosemanal.silabo.materia
    if materia.coordinacion():
        if materia.coordinacion().id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"

    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            conexion = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    conexion = connections['db_moodle_virtual']
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                else:
                    conexion = connections['aulagradob']
            else:
                conexion = connections['moodle_db']

            cursor = conexion.cursor()
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 11)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = ""
            # intro = """
            #         <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>
            #         <p>%s</p>
            #
            #         <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Instrucciones:</h3></p>
            #         <p>%s</p>
            #
            #         <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Recomendaciones:</h3></p>
            #         <p>%s</p>
            # """ % (tarea.objetivo, tarea.instruccion, tarea.recomendacion)

            if tarea.archivotareapracticasilabo:
                archivotareapracticasilabo = ""
                if tarea.archivotareapracticasilabo:
                    namea = tarea.archivotareapracticasilabo.name.split("/")[-1]
                    archivotareapracticasilabo = """
                        <div class="fileuploadsubmission"> 
                        <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>   
                        </div><br>
                        <a target="_blank" href="https://sga.unemi.edu.ec/media/informepractica/informepractica.docx">INFORME DE RESULTADOS DE APLICACIÓN DE LA GUÍA PRACTICAS</a>   
                        </div><br>
                    """ % (tarea.archivotareapracticasilabo.url, namea)
                intro = """%s
                        <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Rúbrica:</h3></p>
                        <p>%s</p>
                        %s
                        <p> </p>                    
                        """ % (intro, tarea.rubrica, archivotareapracticasilabo)

            intro = intro.replace("'", "")
            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = int(time.mktime(tarea.fechadesde.date().timetuple()))
            fechahasta = datetime(tarea.fechahasta.date().year, tarea.fechahasta.date().month, tarea.fechahasta.date().day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            if tarea.idtareapracticamoodle <= 0:
                sql = """
                        INSERT INTO mooc_assign (name, timemodified, course, intro, introformat, alwaysshowdescription, submissiondrafts, requiresubmissionstatement, sendnotifications, sendlatenotifications,
                                         sendstudentnotifications, duedate, cutoffdate, gradingduedate, allowsubmissionsfromdate, grade, completionsubmit, teamsubmission, requireallteammemberssubmit, blindmarking,
                                         hidegrader, attemptreopenmethod, maxattempts, preventsubmissionnotingroup, markingworkflow, markingallocation) 
                            VALUES('%s', '%s', '%s', '%s', '5', '1', '0', '0', '0', '0',
                                '1', '%s', '%s', '0', '%s', '%s', '1', '0', '0', '0',
                                    '0', 'none', '-1', '0', '0', '0')""" % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, cursoid, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA TAREA CREADA
                sql = """select id from mooc_assign WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section) 
                        VALUES('%s', '1', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '0', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_event (modulename,courseid,groupid,userid,instance,type,description,name,eventtype,timestart,timesort,format,timemodified) 
                        VALUES('assign', '%s', '0', '%s','%s', '1','%s','%s','due', '%s','%s','1','%s') 
                """ % (cursoid, persona.idusermoodle, instance, intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,
                        grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,
                        needsupdate,weightoverride,timecreated,timemodified,hidden) 
                        VALUES('%s', '%s', '%s', 'mod','assign','%s', '0', NULL, '', NULL, '%s', '%s', '0', NULL, NULL, '0', '1', '0', '0', '0', '8', '0',
                        NULL, '0', '0', '0', '0','%s','%s', '0') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, fecha)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR GRADE ITEM ID
                sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid='%s' and iteminstance='%s' """ % (cursoid, categoryid, instance)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                gradeitemid = buscar[0][0]

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES raiz
                sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                categoryidraiz = buscar[0][0]

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '%s', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '1', '%s', NULL, '%s') 
                """ % (cursoid, categoryidraiz, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, instanceid, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                        gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                        locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser) 
                        VALUES('%s','%s', '%s', 'mod', 'assign', '%s', '0', NULL, '', NULL, '%s', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                        '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s') 
                """ % (cursoid, categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), instance, '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'onlinetext', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxfilesubmissions', '20') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'maxsubmissionsizebytes', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'file', 'filetypeslist', 'document,spreadsheet,presentation') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignsubmission', 'comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s','assignfeedback','comments', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'comments', 'commentinline', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'editpdf', 'enabled', '1') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'offline', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_assign_plugin_config (assignment,subtype,plugin,name,value) VALUES('%s', 'assignfeedback', 'file', 'enabled', '0') """ % instance
                cursor.execute(sql)

                sql = """INSERT INTO mooc_grading_areas (contextid,component,areaname,activemethod) VALUES('%s', 'mod_assign', 'submissions', NULL) """ % contextid
                cursor.execute(sql)

                sql = """INSERT INTO mooc_block_recent_activity (action,timecreated,courseid,cmid,userid) VALUES('0', '%s', '%s', '%s', '%s') """ % (fecha, cursoid, instanceid, persona.idusermoodle)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                tarea.idtareapracticamoodle = instanceid
                tarea.estado_id = 4
                tarea.save()

            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = tarea.idtareapracticamoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """
                        update mooc_assign 
                        set name='%s', 
                        timemodified='%s', 
                        intro='%s', 
                        duedate='%s', 
                        cutoffdate='%s', 
                        allowsubmissionsfromdate='%s', 
                        grade='%s'
                        where id='%s'
                        """ % ("S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fecha, intro, fechahasta, fechahasta, fechadesde, int(tarea.detallemodelo.notamaxima) if tarea.calificar else 0, instance)
                cursor.execute(sql)

                sql = """UPDATE mooc_event 
                SET description='%s',
                name='%s',
                timestart='%s',
                timesort='%s',
                timemodified='%s'
                WHERE instance='%s' and courseid='%s' 
                """ % (intro, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha, instance, cursoid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if tarea.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    if not buscar:
                        materia.crear_actualizar_categoria_notas_curso()
                        sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, tarea.detallemodelo.nombre)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                sql = """update mooc_grade_items 
                        set categoryid='%s',
                        itemname='%s',
                        gradetype='%s',
                        grademax='%s',
                        timemodified='%s'
                        where courseid='%s' and iteminstance='%s'
                """ % (categoryid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre.replace("'", "")[:252]), '1' if tarea.calificar else '3', null_to_numeric(tarea.detallemodelo.notamaxima, 5) if tarea.calificar else 0, fecha, cursoid, instance)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            # YA CREADA LA TAREA SE PROCEDE A INSERTAR LA RUBRICA
            if tarea.rubricamoodle:
                rubrica = tarea.rubricamoodle
                # PROCEDEMOS A BUSCAR LA AREA
                sql = """select id from mooc_grading_areas where contextid='%s' """ % (contextid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                areaid = buscar[0][0]

                # VERIFICACION SI EXISTEN DATOS PARA BORRARLOS Y LUEGO INSERTAR DE NUEVO
                sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                grading_definitions = 0
                if buscar:
                    grading_definitions = buscar[0][0]
                #     for c in rubrica.items():
                #         orden = c.orden
                #
                #         # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                #         sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                #         cursor.execute(sql)
                #         buscar = cursor.fetchall()
                #         gradingform_rubric_criteria = buscar[0][0]
                #
                #         sql = """DELETE FROM mooc_gradingform_rubric_levels WHERE criterionid = %s """ % (gradingform_rubric_criteria)
                #         cursor.execute(sql)
                #
                #     sql = """DELETE FROM mooc_gradingform_rubric_criteria WHERE definitionid = %s """ % (grading_definitions)
                #     cursor.execute(sql)
                #
                #     sql = """DELETE FROM mooc_grading_definitions WHERE id = %s """ % (grading_definitions)
                #     cursor.execute(sql)

                # FIN DE ELIMINACION

                if grading_definitions == 0:
                    sql = """INSERT INTO mooc_grading_definitions 
                            (areaid,method,timecreated,usercreated,timemodified,usermodified,status,descriptionformat,options,name) 
                            VALUES(%s,'rubric',%s,%s,%s,%s,'20','1',
                            '{"sortlevelsasc":"1","lockzeropoints":"1","alwaysshowdefinition":"1","showdescriptionteacher":"1","showdescriptionstudent":"1","showscoreteacher":"1","showscorestudent":"1","enableremarks":"1","showremarksstudent":"1"}','%s')""" % (areaid, fecha, persona.idusermoodle, fecha, persona.idusermoodle, rubrica.nombre)
                    cursor.execute(sql)

                    # PROCEDEMOS A BUSCAR GRADING_DEFINITIONS
                    sql = """select id from mooc_grading_definitions where areaid='%s' and method='rubric' """ % (areaid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    grading_definitions = buscar[0][0]

                    # INSERTAR LOS CRITERIOS
                    for c in rubrica.items():
                        item = c.item
                        item = item.replace("'", "")
                        orden = c.orden
                        sql = """INSERT INTO mooc_gradingform_rubric_criteria (definitionid,descriptionformat,sortorder,description) 
                                 VALUES(%s,'0',%s,'%s')""" % (grading_definitions, orden, item)
                        cursor.execute(sql)

                        # PROCEDEMOS A BUSCAR GRADINGFORM_RUBRIC_CRITERIA
                        sql = """select id from mooc_gradingform_rubric_criteria where definitionid='%s' and sortorder=%s """ % (grading_definitions, orden)
                        cursor.execute(sql)
                        buscar = cursor.fetchall()
                        gradingform_rubric_criteria = buscar[0][0]

                        for d in c.detalle():
                            descripcion = d.descripcion.replace("'", "")
                            orden1 = d.orden
                            valor = d.valor

                            sql = """INSERT INTO mooc_gradingform_rubric_levels (criterionid, definitionformat, score, definition)
                            VALUES(%s,'0',%s,'%s')""" % (gradingform_rubric_criteria, valor, descripcion)
                            cursor.execute(sql)
                    sql = """UPDATE mooc_grading_areas set activemethod='rubric' where contextid=%s""" % (contextid)
                    cursor.execute(sql)
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearForosClaseMoodle(claseid, persona, observacion, enlace2, enlace3, codigodia):
    from sga.models import Clase, ClaseAsincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = datetime.today().isocalendar()[1]
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        # SOLO FUNCIONA LOCAL
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechaforo = date.today()
        for fechadia in daterange(fechalunes, fechadomingo):
            if int(codigodia) == int(fechadia.isocalendar()[2]):
                fechaforo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechaforo.year, fechaforo.month, fechaforo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        # 2 => CLASE VIRTUAL SINCRÓNICA
        # 7 => CLASE VIRTUAL ASINCRÓNICA
        # 8 => CLASE REFUERZO SINCRÓNICA
        claseasincronica = ClaseAsincronica(clase=clase,
                                            numerosemana=datetime.today().isocalendar()[1],
                                            fechaforo=fechaforo,
                                            enlaceuno=observacion,
                                            enlacedos=enlace2,
                                            enlacetres=enlace3,
                                            idforomoodle=0)
        claseasincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechaforo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                claseasincronica.lecciones.add(leccion.id)
    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                else:
                    cursor = connections['aulagradob'].cursor()
            else:
                cursor = connections['moodle_db'].cursor()

            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            # intro = """<iframe src='%s' width="1040px" height="700px"></iframe>""" %(observacion)
            introtexto = """<h3 class="section-title" style="color: #3b5998;font-weight: bold;">Descripción: </h3>
             <p>La presente actividad corresponde a la clase asincrónica de la semana, esta contiene los videos 
             grabados de la clase sincrónica para que los pueda revisar y tener la opción de comentar.</p>
              <h3 class="section-title" style="color:#3b5998;font-weight: bold;"><span style="font-size: 2.143rem;">Instrucciones:</span><br></h3>
            <p>
            </p>
            <p><span lang="ES">EL alumno tiene como opción realizar
            las siguientes actividades:</span></p>
            <p>
                <ol>
                    <li><span lang="ES" style="font-size: 0.9375rem;">&nbsp;</span><span lang="ES" style="font-size: 0.9375rem;">Visualizar los videos grabados de la clase sincrónica de
            la semana.</span></li>
                    <li><span style="font-size: 0.9375rem;">Durante el horario asignado en su SGA para la clase
            asincrónica, puede realizar comentarios enfocados en preguntas o dudas &nbsp;únicamente sobre el tema revisado durante esa
            semana, no es una actividad obligatoria, pero tiene la opción.</span></li>
                </ol>
            </p>

            <span lang="ES">En caso de plantear
            alguna interrogante, tiene la oportunidad para ingresar posteriormente a la
            actividad para revisar la retroalimentación dada por el docente.</span><br> <br><br>"""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                    <a target="_blank" href="%s">%s</a>""" % (observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                        <a target="_blank" href="%s">%s</a>""" % (enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                        <a target="_blank" href="%s">%s</a>""" % (enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechaforo = date.today()
            for fechadia in daterange(fechalunes, fechadomingo):
                if int(codigodia) == int(fechadia.isocalendar()[2]):
                    fechaforo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechaforo.year, fechaforo.month, fechaforo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            type = 'single'
            idtipoforo = 2

            assessed = '0'

            sql = """
                    INSERT INTO mooc_forum (name,type,duedate,cutoffdate,maxbytes,maxattachments,displaywordcount,forcesubscribe,trackingtype,blockperiod,
                    blockafter,warnafter,grade_forum,assessed,scale,assesstimestart,assesstimefinish,completionposts,completiondiscussions,completionreplies,
                    course,intro,introformat,timemodified) 
                    VALUES('%s', '%s', '%s', '%s', '512000', '9', '0', '0', '5', '0', 
                    '0', '0', '0', '%s', '%s', '0', '0', '1', '0', '0', '%s', '%s', '5', '%s') 
            """ % (u"%s CLASE ASINCRÓNICA" % nombresemana, type, fechahasta, fechahasta, assessed, 0, cursoid, intro, fecha)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_forum WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, u"%s CLASE ASINCRÓNICA" % nombresemana, fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            # creacion tipo foro 2

            sql = """
                INSERT INTO mooc_forum_discussions (course,forum,name,assessed,groupid,firstpost,timemodified,usermodified,userid) 
                VALUES('%s', '%s','%s', '0', '-1', '0', '%s', '%s', '%s') 
            """ % (cursoid, instance, u"%s CLASE ASINCRÓNICA" % nombresemana, fecha, persona.idusermoodle, persona.idusermoodle)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL FORUN DISCUSSIONS
            sql = """select id from mooc_forum_discussions WHERE course=%s AND forum='%s' """ % (cursoid, instance)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            forundiscuid = buscar[0][0]

            sql = """
                INSERT INTO mooc_forum_posts (discussion, parent, privatereplyto, userid, created, modified, mailed, subject, message, messageformat,
                messagetrust,mailnow,wordcount,charcount) 
                VALUES('%s', '0', '0', '%s', '%s', '%s', '0', '%s', '%s', '1',
                '0', '0', '474', '2473') 
            """ % (forundiscuid, persona.idusermoodle, fecha, fecha, u"%s CLASE ASINCRÓNICA" % nombresemana, intro)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL FORUN POST
            sql = """select id from mooc_forum_posts WHERE discussion=%s AND subject='%s' """ % (forundiscuid, u"%s CLASE ASINCRÓNICA" % nombresemana)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            forunpostid = buscar[0][0]

            sql = """update mooc_forum_discussions set firstpost='%s' where id='%s' """ % (forunpostid, forundiscuid)
            cursor.execute(sql)
            # fincreacion tipo foro 2

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '9', '%s', '1', '1', '1', '', '0', '0', '2',
                    NULL, '0', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='9' and instance='%s' and section='%s' """ % (cursoid, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            sql = """INSERT INTO mooc_event (modulename,courseid,groupid,userid,instance,type,description,name,eventtype,timestart,timesort,format,timemodified)
                    VALUES('forum', '%s', '0', '%s','%s', '1','%s','%s','due', '%s','%s','1','%s')
            """ % (cursoid, persona.idusermoodle, instance, intro, u"%s CLASE ASINCRÓNICA" % clase.inicio, fechahasta, fechahasta, fecha)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
            sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            categoryid = buscar[0][0]

            sql = """INSERT INTO mooc_grading_areas (contextid,component,areaname,activemethod) VALUES('%s', 'mod_forum', 'forum', NULL) """ % contextid
            cursor.execute(sql)

            sql = """INSERT INTO mooc_block_recent_activity (action,timecreated,courseid,cmid,userid) VALUES('0', '%s', '%s', '%s', '%s') """ % (fecha, cursoid, instanceid, persona.idusermoodle)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)
            # 2 => CLASE VIRTUAL SINCRÓNICA
            # 7 => CLASE VIRTUAL ASINCRÓNICA
            # 8 => CLASE REFUERZO SINCRÓNICA
            claseasincronica = ClaseAsincronica(clase=clase,
                                                numerosemana=datetime.today().isocalendar()[1],
                                                fechaforo=fechaforo,
                                                enlaceuno=observacion,
                                                enlacedos=enlace2,
                                                enlacetres=enlace3,
                                                idforomoodle=instanceid)
            claseasincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechaforo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    claseasincronica.lecciones.add(leccion.id)


def CrearForosMoodle(foroid, persona):
    from sga.models import ForoSilaboSemanal
    from django.db import connections
    from sga.funciones import null_to_numeric
    foro = ForoSilaboSemanal.objects.get(pk=foroid)
    materia = foro.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'

    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            conexion = None
            if materia.coordinacion():
                if coordinacion_id == 9:
                    conexion = connections['db_moodle_virtual']
                    idmodulo = 9
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                    idmodulo = 9
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodulo = 9
                else:
                    conexion = connections['aulagradob']
                    idmodulo = 10
            else:
                conexion = connections['moodle_db']
                idmodulo = 9

            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            cursor = conexion.cursor()
            seccion_mooc = 0 if coordinacion_id == 7 else 5
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, seccion_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = """
                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>
                    <p>%s</p>

                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Instrucciones:</h3></p>
                    <p>%s</p>

                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Recomendaciones:</h3></p>
                    <p>%s</p>
            """ % (foro.objetivo, foro.instruccion, foro.recomendacion)
            if foro.rubrica or foro.archivorubrica:
                archivorubrica = ""
                if foro.archivorubrica:
                    namea = foro.archivorubrica.name.split("/")[-1]
                    archivorubrica = """
                        <div class="fileuploadsubmission">
                        <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>
                        </div>
                    """ % (foro.archivorubrica.url, namea)
                intro = """%s
                    <p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Rúbrica:</h3></p>
                    <p>%s</p>
                    %s
                    <p> </p>
                    """ % (intro, foro.rubrica, archivorubrica)

            if foro.archivoforo:
                archivoforo = ""
                if foro.archivoforo:
                    namea = foro.archivoforo.name.split("/")[-1]
                    archivoforo = """
                        <div class="fileuploadsubmission">
                        <a target="_blank" href="https://sga.unemi.edu.ec%s">%s</a>
                        </div><br>
                    """ % (foro.archivoforo.url, namea)
                intro = """%s
                        <p><h2 class="section-title" style="color: #3b5998">Archivos Adicionales</h2></p>
                        %s
                        """ % (intro, archivoforo)
            # TOCA INVESTIGAR COMO PONER LA FECHA DESDE
            # intro = intro.replace("'", "")
            intro = intro.replace("'", "''")
            fecha = int(time.mktime(datetime.now().timetuple()))
            fechadesde = int(time.mktime(foro.fechadesde.date().timetuple()))

            fechahasta = datetime(foro.fechahasta.date().year, foro.fechahasta.date().month, foro.fechahasta.date().day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            type = ''
            if foro.tipoforo == 1:
                type = 'qanda'
            elif foro.tipoforo == 2:
                type = 'single'
            elif foro.tipoforo == 3:
                type = 'eachuser'

            assessed = '0'
            if foro.tipoconsolidacion == 1:
                assessed = '1'
            elif foro.tipoconsolidacion == 3:
                assessed = '2'

            # if foro.idforomoodle > 0:
            #     sql = """select id from mooc_course_modules WHERE course=%s AND module='9' and id='%s'""" % (cursoid, foro.idforomoodle)
            #     cursor.execute(sql)
            #     buscar = cursor.fetchall()
            #     if not buscar:
            #         foro.idforomoodle = 0
            if foro.idforomoodle <= 0:
                sql = """
                        INSERT INTO mooc_forum (name,type,duedate,cutoffdate,maxbytes,maxattachments,displaywordcount,forcesubscribe,trackingtype,blockperiod,
                        blockafter,warnafter,grade_forum,assessed,scale,assesstimestart,assesstimefinish,completionposts,completiondiscussions,completionreplies,
                        course,intro,introformat,timemodified) 
                        VALUES('%s', '%s', '%s', '%s', '512000', '9', '0', '0', '1', '0', 
                        '0', '0', '0', '%s', '%s', '0', '0', '1', '0', '0', '%s', '%s', '5', '%s') 
                """ % ("S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), type, fechahasta, fechahasta, assessed, int(foro.detallemodelo.notamaxima) if foro.calificar else 0, cursoid, intro, fecha)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
                sql = """select id from mooc_forum WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                if foro.tipoforo == 2:
                    sql = """
                        INSERT INTO mooc_forum_discussions (course,forum,name,assessed,groupid,firstpost,timemodified,usermodified,userid) 
                        VALUES('%s', '%s','%s', '0', '-1', '0', '%s', '%s', '%s') 
                    """ % (cursoid, instance, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), fecha, persona.idusermoodle, persona.idusermoodle)
                    cursor.execute(sql)

                    # PROCEDEMOS A BUSCAR EL ID DEL FORUN DISCUSSIONS
                    sql = """select id from mooc_forum_discussions WHERE course=%s AND forum='%s' """ % (cursoid, instance)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    forundiscuid = buscar[0][0]

                    sql = """
                        INSERT INTO mooc_forum_posts (discussion, parent, privatereplyto, userid, created, modified, mailed, subject, message, messageformat,
                        messagetrust,mailnow,wordcount,charcount) 
                        VALUES('%s', '0', '0', '%s', '%s', '%s', '0', '%s', '%s', '1',
                        '0', '0', '474', '2473') 
                    """ % (forundiscuid, persona.idusermoodle, fecha, fecha, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), intro)
                    cursor.execute(sql)

                    # PROCEDEMOS A BUSCAR EL ID DEL FORUN POST
                    sql = """select id from mooc_forum_posts WHERE discussion=%s AND subject='%s' """ % (forundiscuid, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]))
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    forunpostid = buscar[0][0]

                    sql = """update mooc_forum_discussions set firstpost='%s' where id='%s' """ % (forunpostid, forundiscuid)
                    cursor.execute(sql)

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '0', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid,idmodulo,instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid,idmodulo, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                sql = """INSERT INTO mooc_event (modulename,courseid,groupid,userid,instance,type,description,name,eventtype,timestart,timesort,format,timemodified)
                        VALUES('forum', '%s', '0', '%s','%s', '1','%s','%s','due', '%s','%s','1','%s')
                """ % (cursoid, persona.idusermoodle, instance, intro, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), fechadesde, fechadesde, fecha)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if foro.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, foro.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                if foro.calificar:
                    sql = """INSERT INTO mooc_grade_items (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,gradetype,
                            grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,locked,locktime,
                            needsupdate,weightoverride,timecreated,timemodified,hidden)
                            VALUES('%s', '%s', '%s', 'mod','forum','%s', '0', NULL, '', NULL, '1', '%s', '0', NULL, NULL, '0', '1', '0', '0', '0', '8', '0',
                            NULL, '0', '0', '0', '0','%s','%s', '0')
                    """ % (cursoid, categoryid, "Rating grade for S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:230]), instance, null_to_numeric(foro.detallemodelo.notamaxima, 5) if foro.calificar else 0, fecha, fecha)
                    cursor.execute(sql)

                    # PROCEDEMOS A BUSCAR GRADE ITEM ID
                    sql = """select id from mooc_grade_items WHERE courseid=%s AND categoryid='%s' and iteminstance='%s' """ % (cursoid, categoryid, instance)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    gradeitemid = buscar[0][0]

                    # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES raiz
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryidraiz = buscar[0][0]

                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                            gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                            locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser)
                            VALUES('%s','%s', '%s', 'mod', 'forum', '%s', '0', NULL, '%s', NULL, '1', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                            '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '1', '%s', NULL, '%s')
                    """ % (cursoid, categoryidraiz, "Rating grade for S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:230]), instance, instanceid, null_to_numeric(foro.detallemodelo.notamaxima, 5) if foro.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                    cursor.execute(sql)

                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                            gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                            locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser)
                            VALUES('%s','%s', '%s', 'mod', 'forum', '%s', '0', NULL, '', NULL, '1', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                            '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s')
                    """ % (cursoid, categoryid, "Rating grade for S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:230]), instance, null_to_numeric(foro.detallemodelo.notamaxima, 5) if foro.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                    cursor.execute(sql)

                    sql = """INSERT INTO mooc_grade_items_history (courseid,categoryid,itemname,itemtype,itemmodule,iteminstance,itemnumber,iteminfo,idnumber,calculation,
                            gradetype,grademax,grademin,scaleid,outcomeid,gradepass,multfactor,plusfactor,aggregationcoef,aggregationcoef2,sortorder,display,decimals,
                            locked,locktime,needsupdate,weightoverride,timemodified,hidden,action,oldid,source,loggeduser)
                            VALUES('%s','%s', '%s', 'mod', 'forum', '%s', '0', NULL, '', NULL, '1', '%s', '0.00000', NULL, NULL, '0.00000', '1.00000',
                            '0.00000', '0.00000', '0.00000', '%s', '0', NULL, '0', '0', '1', '0', '%s', '0', '2', '%s', NULL, '%s')
                    """ % (cursoid, categoryid, "Rating grade for S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:230]), instance, null_to_numeric(foro.detallemodelo.notamaxima, 5) if foro.calificar else 0, depthcontext, fecha, gradeitemid, persona.idusermoodle)
                    cursor.execute(sql)

                sql = """INSERT INTO mooc_grading_areas (contextid,component,areaname,activemethod) VALUES('%s', 'mod_forum', 'forum', NULL) """ % contextid
                cursor.execute(sql)

                sql = """INSERT INTO mooc_block_recent_activity (action,timecreated,courseid,cmid,userid) VALUES('0', '%s', '%s', '%s', '%s') """ % (fecha, cursoid, instanceid, persona.idusermoodle)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                foro.idforomoodle = instanceid
                foro.estado_id = 4
                foro.save()
            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = foro.idforomoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """UPDATE mooc_forum 
                        SET name='%s',
                        type='%s',
                        duedate='%s',
                        cutoffdate='%s',
                        assessed='%s',
                        scale='%s',
                        intro='%s',
                        timemodified='%s'
                        where course='%s' and id='%s' 
                """ % ("S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), type, fechahasta, fechahasta, assessed, int(foro.detallemodelo.notamaxima) if foro.calificar else 0, intro, fecha, cursoid, instance)
                cursor.execute(sql)

                # if foro.tipoforo == 2:
                #     sql = """update mooc_forum_discussions
                #             set name='%s',
                #             timemodified='%s'
                #             where course='%s' and forum='%s'
                #     """ % ("S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), fecha, cursoid, instance)
                #     cursor.execute(sql)
                #
                #     # PROCEDEMOS A BUSCAR EL ID DEL FORUN DISCUSSIONS
                #     sql = """select id from mooc_forum_discussions WHERE course=%s AND forum='%s' """ % (cursoid, instance)
                #     cursor.execute(sql)
                #     buscar = cursor.fetchall()
                #     forundiscuid = buscar[0][0]
                #
                #     sql = """update mooc_forum_posts
                #             set modified='%s',
                #                 subject='%s',
                #                 message='%s'
                #             where discussion='%s'
                #     """ % (fecha, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:252]), intro, forundiscuid)
                #     cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CATEGORIA GRADES
                if foro.calificar:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='%s' and depth='2' """ % (cursoid, foro.detallemodelo.nombre)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]
                else:
                    sql = """select id from mooc_grade_categories WHERE courseid=%s AND fullname='?' and depth='1' """ % (cursoid)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    categoryid = buscar[0][0]

                if foro.calificar:
                    sql = """update mooc_grade_items 
                            set categoryid='%s',
                            itemname='%s',
                            gradetype='%s',
                            grademax='%s',
                            timemodified='%s'
                            where courseid='%s' and iteminstance='%s'
                    """ % (categoryid, "Rating grade for S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre.replace("'", "")[:230]), '1' if foro.calificar else '3', null_to_numeric(foro.detallemodelo.notamaxima, 5) if foro.calificar else 0, fecha, cursoid, instance)
                    cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if foro.idforomoodle > 0:
                foro.estado_id = 4
                foro.save()
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearClaseVirtualClaseMoodle(claseid, persona, observacion, enlace2, enlace3, codigodia):
    from sga.models import Clase, ClaseAsincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = datetime.today().isocalendar()[1]
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date.today()
        for fechadia in daterange(fechalunes, fechadomingo):
            if int(codigodia) == int(fechadia.isocalendar()[2]):
                fechavideo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        # 2 => CLASE VIRTUAL SINCRÓNICA
        # 7 => CLASE VIRTUAL ASINCRÓNICA
        # 8 => CLASE REFUERZO SINCRÓNICA
        claseasincronica = ClaseAsincronica(clase=clase,
                                            numerosemana=datetime.today().isocalendar()[1],
                                            fechaforo=fechavideo,
                                            enlaceuno=observacion,
                                            enlacedos=enlace2,
                                            enlacetres=enlace3,
                                            idforomoodle=0)
        claseasincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                claseasincronica.lecciones.add(leccion.id)
    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                    idmodulo = 23
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                    idmodulo=21
                else:
                    cursor = connections['aulagradob'].cursor()
                    idmodulo = 22
            else:
                cursor = connections['moodle_db'].cursor()
                idmodulo = 21
            nombreclase = ""
            nombrecomienza = ""
            nombrecomienza = clase.turno.comienza
            nombretermina = ""
            nombretermina = clase.turno.termina
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            # if clase.tipoprofesor.id == 1:
            #     sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
            #     nombreclase = "Clase Virtual"

            if clase.tipoprofesor.id == 10:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Refuerzo"
                if clase.grupoprofesor:
                    if clase.grupoprofesor.paralelopractica:
                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        nombreclase = f"Clase Refuerzo ({grupoprofesor})"
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
                nombreclase = "Clase Virtual"
                if clase.grupoprofesor:
                    if clase.grupoprofesor.paralelopractica:
                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        nombreclase = f"Clase Virtual ({grupoprofesor})"

            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                    nombreclase = "Clase Virtual"

            cursor.execute(sql)
            buscar = cursor.fetchall()
            section = buscar[0][0]
            introtexto = ""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechavideo = date.today()
            for fechadia in daterange(fechalunes, fechadomingo):
                if int(codigodia) == int(fechadia.isocalendar()[2]):
                    fechavideo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            url = ''

            sql = """
            INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
            VALUES('%s', '%s', '0', '%s', '%s', '1', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                    """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '1',
                    NULL, '0', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, idmodulo, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)
            # 2 => CLASE VIRTUAL SINCRÓNICA
            # 7 => CLASE VIRTUAL ASINCRÓNICA
            # 8 => CLASE REFUERZO SINCRÓNICA
            claseasincronica = ClaseAsincronica(clase=clase,
                                                numerosemana=datetime.today().isocalendar()[1],
                                                fechaforo=fechavideo,
                                                enlaceuno=observacion,
                                                enlacedos=enlace2,
                                                enlacetres=enlace3,
                                                idforomoodle=instanceid)
            claseasincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    claseasincronica.lecciones.add(leccion.id)


def CrearClaseAsincronicaMoodle(claseid, persona, observacion, enlace2, enlace3, codigodia):
    from sga.models import Clase, ClaseAsincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = datetime.today().isocalendar()[1]
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date.today()
        for fechadia in daterange(fechalunes, fechadomingo):
            if int(codigodia) == int(fechadia.isocalendar()[2]):
                fechavideo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        claseasincronica = ClaseAsincronica(clase=clase,
                                            numerosemana=datetime.today().isocalendar()[1],
                                            fechaforo=fechavideo,
                                            enlaceuno=observacion,
                                            enlacedos=enlace2,
                                            enlacetres=enlace3,
                                            idforomoodle=0)
        claseasincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                claseasincronica.lecciones.add(leccion.id)
    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                    idmodulo = 23
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                    idmodulo = 21
                else:
                    cursor = connections['aulagradob'].cursor()
                    idmodulo = 22

            else:
                cursor = connections['moodle_db'].cursor()
                idmodulo = 21
            nombreclase = ""
            nombrecomienza = ""
            nombrecomienza = clase.turno.comienza
            nombretermina = ""
            nombretermina = clase.turno.termina

            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            # if clase.tipoprofesor.id == 1:
            #     sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
            #     nombreclase = "Clase Virtual"

            if clase.tipoprofesor.id == 10:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Refuerzo"
                if clase.grupoprofesor:
                    if clase.grupoprofesor.paralelopractica:
                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        nombreclase = f"Clase Refuerzo ({grupoprofesor})"
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
                nombreclase = "Clase Virtual (Asincrónica)"
                if clase.grupoprofesor:
                    if clase.grupoprofesor.paralelopractica:
                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        nombreclase = f"Clase Virtual (Asincrónica) ({grupoprofesor})"

            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                    nombreclase = "Clase Virtual"

            cursor.execute(sql)
            buscar = cursor.fetchall()
            section = buscar[0][0]
            introtexto = ""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechavideo = date.today()
            for fechadia in daterange(fechalunes, fechadomingo):
                if int(codigodia) == int(fechadia.isocalendar()[2]):
                    fechavideo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            url = ''

            sql = """
            INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
            VALUES('%s', '%s', '0', '%s', '%s', '1', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                    """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '1',
                    NULL, '0', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, idmodulo, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)
            claseasincronica = ClaseAsincronica(clase=clase,
                                                numerosemana=datetime.today().isocalendar()[1],
                                                fechaforo=fechavideo,
                                                enlaceuno=observacion,
                                                enlacedos=enlace2,
                                                enlacetres=enlace3,
                                                idforomoodle=instanceid)
            claseasincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    claseasincronica.lecciones.add(leccion.id)


def CrearClaseSincronicaMoodle(claseid, persona, observacion, enlace2, enlace3, codigodia):
    from sga.models import Clase, ClaseSincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = datetime.today().isocalendar()[1]
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=numerosemanacalendario, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date.today()
        for fechadia in daterange(fechalunes, fechadomingo):
            if int(codigodia) == int(fechadia.isocalendar()[2]):
                fechavideo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        clasesincronica = ClaseSincronica(clase=clase,
                                          numerosemana=datetime.today().isocalendar()[1],
                                          fechaforo=fechavideo,
                                          enlaceuno=observacion,
                                          enlacedos=enlace2,
                                          enlacetres=enlace3,
                                          idforomoodle=0)
        clasesincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                clasesincronica.lecciones.add(leccion.id)
    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                    idmodulo = 23
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                    idmodulo = 21
                else:
                    cursor = connections['aulagradob'].cursor()
                    idmodulo = 22

            else:
                cursor = connections['moodle_db'].cursor()
                idmodulo = 21
            nombreclase = ""
            nombrecomienza = ""
            nombrecomienza = clase.turno.comienza
            nombretermina = ""
            nombretermina = clase.turno.termina
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            # if clase.tipoprofesor.id == 1:
            #     sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
            #     nombreclase = "Clase Virtual"

            if clase.tipoprofesor.id == 10:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Refuerzo"
                if clase.grupoprofesor:
                    if clase.grupoprofesor.paralelopractica:
                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        nombreclase = f"Clase Refuerzo ({grupoprofesor})"
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
                nombreclase = "Clase Virtual (Sincrónica)"
                if clase.grupoprofesor:
                    if clase.grupoprofesor.paralelopractica:
                        grupoprofesor = clase.grupoprofesor.get_paralelopractica_display()
                        nombreclase = f"Clase Virtual (Sincrónica) ({grupoprofesor})"

            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                    nombreclase = "Clase Virtual"

            cursor.execute(sql)
            buscar = cursor.fetchall()
            section = buscar[0][0]
            introtexto = ""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechavideo = date.today()
            for fechadia in daterange(fechalunes, fechadomingo):
                if int(codigodia) == int(fechadia.isocalendar()[2]):
                    fechavideo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            url = ''

            sql = """
            INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
            VALUES('%s', '%s', '0', '%s', '%s', '1', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                    """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '1',
                    NULL, '0', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, idmodulo, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)
            clasesincronica = ClaseSincronica(clase=clase,
                                              numerosemana=datetime.today().isocalendar()[1],
                                              fechaforo=fechavideo,
                                              enlaceuno=observacion,
                                              enlacedos=enlace2,
                                              enlacetres=enlace3,
                                              idforomoodle=instanceid
                                              )
            clasesincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    clasesincronica.lecciones.add(leccion.id)


def CrearClaseVirtualClaseMoodleDiferido(claseid, persona, observacion, enlace2, enlace3, codigodia, codnumerosemana, fechasubida):
    from sga.models import Clase, ClaseAsincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = codnumerosemana
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
        # fechavideo = date.today()
        # for fechadia in daterange(fechalunes, fechadomingo):
        #     if int(codigodia) == int(fechadia.isocalendar()[2]):
        #         fechavideo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        claseasincronica = ClaseAsincronica(clase=clase,
                                            numerosemana=codnumerosemana,
                                            fechaforo=fechavideo,
                                            enlaceuno=observacion,
                                            enlacedos=enlace2,
                                            enlacetres=enlace3,
                                            diferido=True,
                                            idforomoodle=0)
        claseasincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                claseasincronica.lecciones.add(leccion.id)

    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                    idmodulo = 23
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                    idmodulo = 21
                else:
                    cursor = connections['aulagradob'].cursor()
                    idmodulo = 22

            else:
                cursor = connections['moodle_db'].cursor()
                idmodulo = 21
            nombreclase = ""
            nombrecomienza = ""
            nombrecomienza = clase.turno.comienza
            nombretermina = ""
            nombretermina = clase.turno.termina
            if clase.tipoprofesor.id == 10:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Refuerzo"
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
                nombreclase = "Clase Virtual"
            cursor.execute(sql)
            buscar = cursor.fetchall()
            section = buscar[0][0]
            introtexto = ""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
            # fechavideo = date.today()
            # for fechadia in daterange(fechalunes, fechadomingo):
            #     if int(codigodia) == int(fechadia.isocalendar()[2]):
            #         fechavideo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            url = ''

            sql = """
            INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
            VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                    """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                    NULL, '1', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, idmodulo, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)

            claseasincronica = ClaseAsincronica(clase=clase,
                                                numerosemana=codnumerosemana,
                                                fechaforo=fechavideo,
                                                enlaceuno=observacion,
                                                enlacedos=enlace2,
                                                enlacetres=enlace3,
                                                diferido=True,
                                                idforomoodle=instanceid)
            claseasincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    claseasincronica.lecciones.add(leccion.id)


def CrearClaseAsincronicaMoodleDiferido(claseid, persona, observacion, enlace2, enlace3, codigodia, codnumerosemana, fechasubida):
    from sga.models import Clase, ClaseAsincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = codnumerosemana
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
        # fechavideo = date.today()
        # for fechadia in daterange(fechalunes, fechadomingo):
        #     if int(codigodia) == int(fechadia.isocalendar()[2]):
        #         fechavideo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        claseasincronica = ClaseAsincronica(clase=clase,
                                            numerosemana=codnumerosemana,
                                            fechaforo=fechavideo,
                                            enlaceuno=observacion,
                                            enlacedos=enlace2,
                                            enlacetres=enlace3,
                                            diferido=True,
                                            idforomoodle=0)
        claseasincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                claseasincronica.lecciones.add(leccion.id)

    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                    idmodulo = 23
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                    idmodulo = 21
                else:
                    cursor = connections['aulagradob'].cursor()
                    idmodulo = 22

            else:
                cursor = connections['moodle_db'].cursor()
                idmodulo = 21
            nombreclase = ""
            nombrecomienza = ""
            nombrecomienza = clase.turno.comienza
            nombretermina = ""
            nombretermina = clase.turno.termina
            if clase.tipoprofesor.id == 10:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Refuerzo"
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Virtual (Asincrónica)"
            cursor.execute(sql)
            buscar = cursor.fetchall()
            section = buscar[0][0]
            introtexto = ""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
            # fechavideo = date.today()
            # for fechadia in daterange(fechalunes, fechadomingo):
            #     if int(codigodia) == int(fechadia.isocalendar()[2]):
            #         fechavideo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            url = ''

            sql = """
            INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
            VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                    """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                    NULL, '1', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, idmodulo, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)

            claseasincronica = ClaseAsincronica(clase=clase,
                                                numerosemana=codnumerosemana,
                                                fechaforo=fechavideo,
                                                enlaceuno=observacion,
                                                enlacedos=enlace2,
                                                enlacetres=enlace3,
                                                diferido=True,
                                                idforomoodle=instanceid)
            claseasincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    claseasincronica.lecciones.add(leccion.id)


def EditarClaseAsincronicaMoodleDiferido(id, claseid, observacion, enlace2, enlace3):
    from sga.models import Clase, Leccion, ClaseAsincronica
    from django.db import connections
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save(update_fields=['actualizarhtml'])
    claseasincronica = clase.claseasincronica_set.filter(id=id).first()
    if not DEBUG:
        if materia.idcursomoodle:
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                else:
                    cursor = connections['aulagradob'].cursor()

            else:
                cursor = connections['moodle_db'].cursor()
            introtexto = ""
            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3
            # PROCEDEMOS A BUSCAR EL ID DE LA CLASE CREADA
            sql = "select instance from mooc_course_modules WHERE id={}".format(claseasincronica.idforomoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False
            modulecourse = buscar[0][0]
            sql = "select id from mooc_url WHERE id={}".format(modulecourse)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False
            query = """UPDATE mooc_url SET intro = '{}' WHERE id={}""".format(intro, modulecourse)
            cursor.execute(query)

    claseasincronica.enlaceuno = observacion
    claseasincronica.enlacedos = enlace2
    claseasincronica.enlacetres = enlace3
    claseasincronica.save(update_fields=['enlaceuno', 'enlacedos', 'enlacetres'])
    return True


def CrearClaseSincronicaMoodleDiferido(claseid, persona, observacion, enlace2, enlace3, codigodia, codnumerosemana, fechasubida):
    from sga.models import Clase, ClaseSincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = codnumerosemana
    nombresemana = 'S - '
    if SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'S' + str(silabosemana.numsemana) + ' - '
    if DEBUG:
        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
        # fechavideo = date.today()
        # for fechadia in daterange(fechalunes, fechadomingo):
        #     if int(codigodia) == int(fechadia.isocalendar()[2]):
        #         fechavideo = fechadia.date()
        ###TOCA INVESTIGAR COMO PONER FECHA DESDE
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour),
                              int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))
        clasesincronica = ClaseSincronica(clase=clase,
                                          numerosemana=codnumerosemana,
                                          fechaforo=fechavideo,
                                          enlaceuno=observacion,
                                          enlacedos=enlace2,
                                          enlacetres=enlace3,
                                          diferido=True,
                                          idforomoodle=0)
        clasesincronica.save()
        lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
        if lecciones.values("id").exists():
            for leccion in lecciones:
                clasesincronica.lecciones.add(leccion.id)

    else:
        if materia.idcursomoodle:
            cursoid = materia.idcursomoodle
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                    idmodulo = 23
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                    idmodulo = 21
                else:
                    cursor = connections['aulagradob'].cursor()
                    idmodulo = 22

            else:
                cursor = connections['moodle_db'].cursor()
                idmodulo = 21
            nombreclase = ""
            nombrecomienza = ""
            nombrecomienza = clase.turno.comienza
            nombretermina = ""
            nombretermina = clase.turno.termina
            if clase.tipoprofesor.id == 10:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 2)
                nombreclase = "Clase Refuerzo"
            else:
                sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 1)
                nombreclase = "Clase Virtual (Sincrónica)"
            cursor.execute(sql)
            buscar = cursor.fetchall()
            section = buscar[0][0]
            introtexto = ""

            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            fecha = int(time.mktime(datetime.now().timetuple()))
            fechahoy = datetime.today()
            fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
            fechadomingo = fechalunes + timedelta(days=7)
            fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
            # fechavideo = date.today()
            # for fechadia in daterange(fechalunes, fechadomingo):
            #     if int(codigodia) == int(fechadia.isocalendar()[2]):
            #         fechavideo = fechadia.date()
            ###TOCA INVESTIGAR COMO PONER FECHA DESDE
            fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
            fechadesde = int(time.mktime(fechadesde.timetuple()))

            fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
            fechahasta = int(time.mktime(fechahasta.timetuple()))

            url = ''

            sql = """
            INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
            VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                    """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
            sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instance = buscar[0][0]

            sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                    VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                    NULL, '1', '0', NULL, '0', '%s', '%s')
                  """ % (cursoid, idmodulo, instance, fecha, section)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
            sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            instanceid = buscar[0][0]

            sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR LA CONTEXTID
            sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            contextid = buscar[0][0]

            sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            pathcontext = buscar[0][0]
            depthcontext = pathcontext.split("/").__len__()
            pathcontext = "%s/%s" % (pathcontext, contextid)
            sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
            cursor.execute(sql)

            # PROCEDEMOS A BUSCAR sequence
            sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            sequence = buscar[0][0]

            sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)

            clasesincronica = ClaseSincronica(clase=clase,
                                              numerosemana=codnumerosemana,
                                              fechaforo=fechavideo,
                                              enlaceuno=observacion,
                                              enlacedos=enlace2,
                                              enlacetres=enlace3,
                                              diferido=True,
                                              idforomoodle=instanceid)
            clasesincronica.save()
            lecciones = Leccion.objects.filter(clase__materia=clase.materia, clase__tipohorario=clase.tipohorario, fecha=fechavideo)
            if lecciones.values("id").exists():
                for leccion in lecciones:
                    clasesincronica.lecciones.add(leccion.id)


def EditarClaseSincronicaMoodleDiferido(id, claseid, observacion, enlace2, enlace3):
    from sga.models import Clase
    from django.db import connections
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save(update_fields=['actualizarhtml'])
    clasesincronica = clase.clasesincronica_set.filter(id=id).first()
    if not DEBUG:
        if materia.idcursomoodle:
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                else:
                    cursor = connections['aulagradob'].cursor()

            else:
                cursor = connections['moodle_db'].cursor()
            introtexto = ""
            textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                observacion.replace("'", ""), observacion.replace("'", ""))
            intro = introtexto + textoenlace1
            if enlace2:
                textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace2.replace("'", ""), enlace2.replace("'", ""))
                intro = intro + textoenlace2
            if enlace3:
                textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                                <a target="_blank" href="%s">%s</a>""" % (
                    enlace3.replace("'", ""), enlace3.replace("'", ""))
                intro = intro + textoenlace3

            sql = "select instance from mooc_course_modules WHERE id={}".format(clasesincronica.idforomoodle)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False
            modulecourse = buscar[0][0]
            # PROCEDEMOS A BUSCAR EL ID DE LA CLASE CREADA
            sql = "select id from mooc_url WHERE id={}".format(modulecourse)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False
            query = """UPDATE mooc_url SET intro = '{}' WHERE id={}""".format(intro, modulecourse)
            cursor.execute(query)

    clasesincronica.enlaceuno = observacion
    clasesincronica.enlacedos = enlace2
    clasesincronica.enlacetres = enlace3
    clasesincronica.save(update_fields=['enlaceuno', 'enlacedos', 'enlacetres'])
    return True


def CrearClaseVirtualClaseMoodleDiferidoPosgrado(claseid, persona, observacion, enlace2, enlace3, codigodia, codnumerosemana, fechasubida, id_nombredia):
    from sga.models import Clase, ClaseAsincronica, SilaboSemanal, Leccion
    from django.db import connections
    from sga.lecciones_dia import daterange
    from settings import DEBUG
    clase = Clase.objects.get(pk=claseid)
    materia = clase.materia
    materia.actualizarhtml = True
    materia.save()
    numerosemanacalendario = codnumerosemana
    nombresemana = 'Semana - '
    numerosemana = 0
    if SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True):
        silabosemana = SilaboSemanal.objects.filter(semana=codnumerosemana, silabo__materia=materia, status=True, silabo__status=True)[0]
        nombresemana = 'Semana' + str(silabosemana.numsemana) + ' - '
        numerosemana = int(silabosemana.numsemana)
    if materia.idcursomoodle and numerosemana > 0:
        cursoid = materia.idcursomoodle
        cursor = None
        cursor = connections['moodle_pos'].cursor()
        idmodulo = 21
        nombreclase = ""
        nombrecomienza = ""
        nombrecomienza = clase.turno.comienza
        nombretermina = ""
        nombretermina = clase.turno.termina
        sql = """select id from mooc_course_sections 
                 WHERE course=%s AND SECTION=%s """ % (cursoid, numerosemana)
        nombreclase = "CLASES GRABADAS " + str(id_nombredia)
        cursor.execute(sql)
        buscar = cursor.fetchall()
        section = buscar[0][0]
        introtexto = ""

        textoenlace1 = """<b>Link de la clase grabada 1:</b>  
                        <a target="_blank" href="%s">%s</a>""" % (
            observacion.replace("'", ""), observacion.replace("'", ""))
        intro = introtexto + textoenlace1
        if enlace2:
            textoenlace2 = """<br><br><b>Link de la clase grabada 2:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                enlace2.replace("'", ""), enlace2.replace("'", ""))
            intro = intro + textoenlace2
        if enlace3:
            textoenlace3 = """<br><br><b>Link de la clase grabada 3:</b>  
                            <a target="_blank" href="%s">%s</a>""" % (
                enlace3.replace("'", ""), enlace3.replace("'", ""))
            intro = intro + textoenlace3

        fecha = int(time.mktime(datetime.now().timetuple()))
        fechahoy = datetime.today()
        fechalunes = fechahoy + timedelta(days=-fechahoy.weekday())
        fechadomingo = fechalunes + timedelta(days=7)
        fechavideo = date(int(fechasubida[0:4]), int(fechasubida[5:7]), int(fechasubida[8:10]))
        fechadesde = datetime(clase.inicio.year, clase.inicio.month, clase.inicio.day, int(clase.turno.comienza.hour), int(clase.turno.comienza.minute))
        fechadesde = int(time.mktime(fechadesde.timetuple()))

        fechahasta = datetime(fechavideo.year, fechavideo.month, fechavideo.day, 23, 59)
        fechahasta = int(time.mktime(fechahasta.timetuple()))

        url = ''

        sql = """
        INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
        VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                """ % ("%s %s (%s)" % (nombresemana, nombreclase, fechavideo), url, cursoid, intro, fecha)

        cursor.execute(sql)

        # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
        sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "%s %s (%s)" % (nombresemana, nombreclase, fechavideo), fecha)
        cursor.execute(sql)
        buscar = cursor.fetchall()
        instance = buscar[0][0]

        sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                            completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                NULL, '1', '0', NULL, '0', '%s', '%s')
              """ % (cursoid, idmodulo, instance, fecha, section)
        cursor.execute(sql)

        # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
        sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
        cursor.execute(sql)
        buscar = cursor.fetchall()
        instanceid = buscar[0][0]

        sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
        cursor.execute(sql)

        # PROCEDEMOS A BUSCAR LA CONTEXTID
        sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
        cursor.execute(sql)
        buscar = cursor.fetchall()
        contextid = buscar[0][0]

        sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
        cursor.execute(sql)
        buscar = cursor.fetchall()
        pathcontext = buscar[0][0]
        depthcontext = pathcontext.split("/").__len__()
        pathcontext = "%s/%s" % (pathcontext, contextid)
        sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
        cursor.execute(sql)

        # PROCEDEMOS A BUSCAR sequence
        sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
        cursor.execute(sql)
        buscar = cursor.fetchall()
        sequence = buscar[0][0]

        sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
        cursor.execute(sql)

        query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
        cursor.execute(query)

        claseasincronica = ClaseAsincronica(clase=clase,
                                            numerosemana=codnumerosemana,
                                            fechaforo=fechavideo,
                                            enlaceuno=observacion,
                                            enlacedos=enlace2,
                                            enlacetres=enlace3,
                                            diferido=True,
                                            idforomoodle=instanceid)
        claseasincronica.save()
        return True
    else:
        return False


def CrearRecursoMoodle(recursoid, persona):
    from sga.models import DiapositivaSilaboSemanal
    from django.db import connections
    diapositiva = DiapositivaSilaboSemanal.objects.get(pk=recursoid)
    materia = diapositiva.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    if materia.coordinacion():
        id_coordina=materia.coordinacion().id
        if id_coordina == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif id_coordina == 7 :
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            conexion = None
            id_coordinacion = materia.coordinacion().id
            if materia.coordinacion():
                if id_coordinacion == 9:
                    conexion = connections['db_moodle_virtual']
                    idmodulo = 23
                elif id_coordinacion == 7:
                    conexion = connections['moodle_pos']
                    idmodulo = 21
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodulo = 21
                else:
                    conexion = connections['aulagradob']
                    idmodulo = 22
            else:
                conexion = connections['moodle_db']
                idmodulo = 21
            cursor = conexion.cursor()
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            seccion_mooc = 0 if id_coordinacion == 7 else 7
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, seccion_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = diapositiva.descripcion.replace("'", "")

            url = ""
            if diapositiva.archivodiapositiva:
                url = "https://sga.unemi.edu.ec%s" % diapositiva.archivodiapositiva.url
            else:
                url = diapositiva.url

            fecha = int(time.mktime(datetime.now().timetuple()))

            if diapositiva.iddiapositivamoodle <= 0:
                sql = """
                INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
                VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                        """ % ("S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre.replace("'", "")[:230]), url, cursoid, intro, fecha)

                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
                sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre.replace("'", "")[:230]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '1', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, idmodulo, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                if instanceid == 0:
                    # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                    sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
                    cursor.execute(sql)
                    buscar = cursor.fetchall()
                    instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                diapositiva.iddiapositivamoodle = instanceid
                diapositiva.estado_id = 4
                diapositiva.save()
            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = diapositiva.iddiapositivamoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """update mooc_url 
                        set name='%s',
                            externalurl='%s',
                            intro='%s',
                            timemodified='%s'
                        where course='%s' and id='%s'
                        """ % ("S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre.replace("'", "")[:230]), url, intro, fecha, cursoid, instance)

                cursor.execute(sql)
                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if diapositiva.iddiapositivamoodle > 0:
                diapositiva.estado_id = 4
                diapositiva.save()
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearVidMagistralMoodle(recursoid, persona):
    from sga.models import VideoMagistralSilaboSemanal
    from django.db import connections
    vidmagistral = VideoMagistralSilaboSemanal.objects.get(pk=recursoid)
    materia = vidmagistral.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            conexion = None
            if materia.coordinacion():
                if coordinacion_id == 9:
                    conexion = connections['db_moodle_virtual']
                    idmodulo = 23
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                    idmodulo = 21
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodulo = 21
                else:
                    conexion = connections['aulagradob']
                    idmodulo = 22
            else:
                conexion = connections['moodle_db']
                idmodulo = 21
            cursor = conexion.cursor()
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            section_mooc = 0 if coordinacion_id == 7 else 8
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, section_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = vidmagistral.descripcion.replace("'", "")
            if vidmagistral.urlcrai:
                url = vidmagistral.urlcrai
            elif vidmagistral.url:
                url = vidmagistral.url
            else:
                url = 'https://sga.unemi.edu.ec/media/' + str(vidmagistral.archivovideomagistral)

            fecha = int(time.mktime(datetime.now().timetuple()))

            if vidmagistral.idvidmagistralmoodle <= 0:
                sql = """
                INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
                VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                        """ % ("S%s-%s" % (vidmagistral.silabosemanal.numsemana, vidmagistral.nombre.replace("'", "")[:252]), url, cursoid, intro, fecha)

                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
                sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (vidmagistral.silabosemanal.numsemana, vidmagistral.nombre.replace("'", "")[:252]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '1', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, idmodulo, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                vidmagistral.idvidmagistralmoodle = instanceid
                vidmagistral.estado_id = 4
                vidmagistral.save()
            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = vidmagistral.idvidmagistralmoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """update mooc_url 
                        set name='%s',
                            externalurl='%s',
                            intro='%s',
                            timemodified='%s'
                        where course='%s' and id='%s'
                        """ % ("S%s-%s" % (vidmagistral.silabosemanal.numsemana, vidmagistral.nombre.replace("'", "")[:252]), url, intro, fecha, cursoid, instance)

                cursor.execute(sql)
                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if vidmagistral.idvidmagistralmoodle > 0:
                vidmagistral.estado_id = 4
                vidmagistral.save()
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearCompendioMoodle(recursoid, persona):
    from sga.models import CompendioSilaboSemanal
    from django.db import connections
    compendio = CompendioSilaboSemanal.objects.get(pk=recursoid)
    materia = compendio.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"

    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            cursor = None
            conexion = None
            if materia.coordinacion():
                if coordinacion_id == 9:
                    conexion = connections['db_moodle_virtual']
                    idmodule = 23
                elif coordinacion_id == 7:
                    conexion = connections['moodle_pos']
                    idmodule = 21
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodule = 21
                else:
                    conexion = connections['aulagradob']
                    idmodule = 22
            else:
                conexion = connections['moodle_db']
                idmodule = 21

                # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            cursor = conexion.cursor()
            section_mooc = 0 if coordinacion_id == 7 else 6
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, section_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = compendio.descripcion.replace("'", "")

            url = ""
            if compendio.archivo_logo:
                url = "https://sga.unemi.edu.ec%s" % compendio.archivo_logo.url
            elif compendio.archivocompendio:
                url = "https://sga.unemi.edu.ec%s" % compendio.archivocompendio.url
            # else:
            #     return JsonResponse({"result": "bad","mensaje": u"No existe archivo para exportar."})
            # if compendio.archivocompendio:
            # lista_formato=[]
            # for format in compendio.mis_formatos(materia.nivel.periodo):
            #     lista_formato.append(format.nombre)
            # if lista_formato and 'word' in lista_formato:

            # else:
            #     url = "https://sga.unemi.edu.ec%s" % compendio.archivocompendio.url
            # else:
            #     url = compendio.url

            fecha = int(time.mktime(datetime.now().timetuple()))

            if compendio.idmcompendiomoodle <= 0:
                sql = """
                INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
                VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                        """ % ("S%s-%s" % (compendio.silabosemanal.numsemana, compendio.descripcion.replace("'", "")[:230] + '-Compendio'), url, cursoid, intro, fecha)

                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA COMPENDIO CREADA
                sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (compendio.silabosemanal.numsemana, compendio.descripcion.replace("'", "")[:230] + '-Compendio'), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '1', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, idmodule, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodule, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                compendio.idmcompendiomoodle = instanceid
                compendio.estado_id = 4
                compendio.save()
            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = compendio.idmcompendiomoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """update mooc_url 
                        set name='%s',
                            externalurl='%s',
                            intro='%s',
                            timemodified='%s'
                        where course='%s' and id='%s'
                        """ % ("S%s-%s" % (compendio.silabosemanal.numsemana, compendio.descripcion.replace("'", "")[:230] + '-Compendio'), url, intro, fecha, cursoid, instance)

                cursor.execute(sql)
                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if compendio.idmcompendiomoodle > 0:
                compendio.estado_id = 4
                compendio.save()
            return True, u"Compendio migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearGuiaestudianteMoodle(recursoid, persona):
    from sga.models import GuiaEstudianteSilaboSemanal
    from django.db import connections
    guiaestudiante = GuiaEstudianteSilaboSemanal.objects.get(pk=recursoid)
    materia = guiaestudiante.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    coordinacion_id = materia.coordinacion().id
    if materia.coordinacion():
        if coordinacion_id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif coordinacion_id == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"

    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            conexion = None
            idmodule = 21
            if materia.coordinacion():
                if coordinacion_id == 9:
                    idmodule = 23
                    conexion = connections['db_moodle_virtual']
                elif coordinacion_id == 7:
                    idmodule = 21
                    conexion = connections['moodle_pos']
                elif coordinacion_id in (1,2,3,4,5):
                    if materia.asignaturamalla.malla.modalidad_id in (1, 2):
                        idmodule = 21
                        conexion = connections['aulagradoa']
                    else:
                        idmodule = 22
                        conexion = connections['aulagradob']
            else:
                idmodule = 21
                conexion = connections['moodle_db']
            cursor = conexion.cursor()
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            section_mooc = 0 if coordinacion_id == 7 else 10
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, section_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = guiaestudiante.observacion.replace("'", "")

            url = ""
            # if guiaestudiante.archivoguiaestudiante:
            #     lista_formato = []
            #     for format in guiaestudiante.mis_formatos(materia.nivel.periodo):
            #         lista_formato.append(format.nombre)
            #     if lista_formato and 'word' in lista_formato:
            #         if guiaestudiante.archivo_logo:
            #             url = "https://sga.unemi.edu.ec%s" % guiaestudiante.archivo_logo.url
            #         else:
            #             url = "https://sga.unemi.edu.ec%s" % guiaestudiante.archivoguiaestudiante.url
            #     else:
            #         url = "https://sga.unemi.edu.ec%s" % guiaestudiante.archivoguiaestudiante.url
            # else:
            #     url = guiaestudiante.url
            if guiaestudiante.archivo_logo:
                url = "https://sga.unemi.edu.ec%s" % guiaestudiante.archivo_logo.url
            elif guiaestudiante.archivoguiaestudiante:
                url = "https://sga.unemi.edu.ec%s" % guiaestudiante.archivoguiaestudiante.url
            # else:
            #     return JsonResponse({"result": "bad", "mensaje": u"No existe archivo para exportar."})
            fecha = int(time.mktime(datetime.now().timetuple()))

            if guiaestudiante.idguiaestudiantemoodle <= 0:
                sql = """
                INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
                VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                        """ % ("S%s-%s" % (guiaestudiante.silabosemanal.numsemana, guiaestudiante.observacion.replace("'", "")[:230] + '-Guía Estudiante'), url, cursoid, intro, fecha)

                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
                sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (guiaestudiante.silabosemanal.numsemana, guiaestudiante.observacion.replace("'", "")[:230] + '-Guía Estudiante'), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '1', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, idmodule, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodule, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                guiaestudiante.idguiaestudiantemoodle = instanceid
                guiaestudiante.estado_id = 4
                guiaestudiante.save()
            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = guiaestudiante.idguiaestudiantemoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """update mooc_url 
                        set name='%s',
                            externalurl='%s',
                            intro='%s',
                            timemodified='%s'
                        where course='%s' and id='%s'
                        """ % ("S%s-%s" % (guiaestudiante.silabosemanal.numsemana, guiaestudiante.observacion.replace("'", "")[:230] + '-Guía Estudiante'), url, intro, fecha, cursoid, instance)

                cursor.execute(sql)
                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if guiaestudiante.idguiaestudiantemoodle > 0:
                guiaestudiante.estado_id = 4
                guiaestudiante.save()
            return True, u"Recurso migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearGuiadocenteMoodle(recursoid, persona):
    from sga.models import GuiaDocenteSilaboSemanal
    from django.db import connections
    guiadocente = GuiaDocenteSilaboSemanal.objects.get(pk=recursoid)
    materia = guiadocente.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    if materia.coordinacion():
        if materia.coordinacion().id == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    conexion = connections['db_moodle_virtual']
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulgradoa']
                else:
                    conexion = connections['aulagradob']
            else:
                conexion = connections['moodle_db']

            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            cursor = conexion.cursor()
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 10)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = guiadocente.observacion.replace("'", "")

            url = ""
            if guiadocente.archivoguiadocente:
                url = "https://sga.unemi.edu.ec%s" % guiadocente.archivoguiadocente.url
            else:
                url = guiadocente.url

            fecha = int(time.mktime(datetime.now().timetuple()))

            if guiadocente.idguiadocentemoodle <= 0:
                sql = """
                INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
                VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                        """ % ("S%s-%s" % (guiadocente.silabosemanal.numsemana, guiadocente.observacion.replace("'", "")[:230] + '-Guía Docente'), url, cursoid, intro, fecha)

                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
                sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (guiadocente.silabosemanal.numsemana, guiadocente.observacion.replace("'", "")[:230] + '-Guía Docente'), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '20', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '1', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='20' and instance='%s' and section='%s' """ % (cursoid, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                guiadocente.idguiadocentemoodle = instanceid
                guiadocente.estado = 4
                guiadocente.save()

            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = guiadocente.idguiadocentemoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """update mooc_url 
                        set name='%s',
                            externalurl='%s',
                            intro='%s',
                            timemodified='%s'
                        where course='%s' and id='%s'
                        """ % ("S%s-%s" % (guiadocente.silabosemanal.numsemana, guiadocente.observacion.replace("'", "")[:230] + '-Guía Docente'), url, intro, fecha, cursoid, instance)

                cursor.execute(sql)
                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if guiadocente.idguiadocentemoodle > 0:
                guiadocente.estado = 4
                guiadocente.save()
            return True, u"Guia migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


def CrearMaterialesMoodle(recursoid, persona):
    from sga.models import MaterialAdicionalSilaboSemanal
    from django.db import connections
    diapositiva = MaterialAdicionalSilaboSemanal.objects.get(pk=recursoid)
    materia = diapositiva.silabosemanal.silabo.materia
    materia.actualizarhtml = True
    materia.save()
    id_coordinacion = materia.coordinacion().id
    if materia.coordinacion():
        if id_coordinacion == 9:
            cursor_verbose = 'db_moodle_virtual'
        elif id_coordinacion == 7:
            cursor_verbose = 'moodle_pos'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            cursor_verbose = 'aulagradoa'
        else:
            cursor_verbose = 'aulagradob'
    else:
        cursor_verbose = 'moodle_db'
    if materia.idcursomoodle == 0:
        return False, u"Materia no tiene creado el curso en Moodle"
    with transaction.atomic(using=cursor_verbose):
        try:
            cursoid = materia.idcursomoodle
            # cursoid = 3345
            cursor = None
            id_coordinacion = materia.coordinacion().id
            if materia.coordinacion():
                if id_coordinacion == 9:
                    conexion = connections['db_moodle_virtual']
                    idmodulo = 23
                elif id_coordinacion == 7:
                    conexion = connections['moodle_pos']
                    idmodulo = 21
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    conexion = connections['aulagradoa']
                    idmodulo = 21
                else:
                    conexion = connections['aulagradob']
                    idmodulo = 22
            else:
                conexion = connections['moodle_db']
                idmodulo = 21
            cursor = conexion.cursor()
            # Module = 1        el modulo assing es cuando se crean tareas
            # vamos a buscar la seccion o panel de moodle en base a la semana del silabo
            seccion_mooc = 0 if id_coordinacion == 7 else 9
            sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, seccion_mooc)
            cursor.execute(sql)
            buscar = cursor.fetchall()
            if not buscar:
                return False, u"La configuración de secciones de moodle es diferente a la establecida"
            section = buscar[0][0]
            intro = diapositiva.descripcion.replace("'", "")
            url = ""
            if diapositiva.archivomaterial:
                url = "https://sga.unemi.edu.ec%s" % diapositiva.archivomaterial.url
            else:
                url = diapositiva.testourl

            fecha = int(time.mktime(datetime.now().timetuple()))

            if diapositiva.idmaterialesmoodle <= 0:
                sql = """
                INSERT INTO mooc_url (name,externalurl,display,course,intro,introformat,parameters,displayoptions,timemodified) 
                VALUES('%s', '%s', '0', '%s', '%s', '5', 'a:0:{}', 'a:1:{s:10:"printintro";i:1;}', '%s') 
                        """ % ("S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre.replace("'", "")[:230]), url, cursoid, intro, fecha)

                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
                sql = """select id from mooc_url WHERE course=%s AND name='%s' and timemodified='%s' """ % (cursoid, "S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre.replace("'", "")[:230]), fecha)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """INSERT INTO mooc_course_modules (course, module, instance, visible, visibleold, visibleoncoursepage, idnumber, groupmode, groupingid, completion,
                                    completiongradeitemnumber, completionview, completionexpected, availability, showdescription, added, section)
                        VALUES('%s', '%s', '%s', '1', '1', '1', '', '0', '0', '2',
                        NULL, '1', '0', NULL, '0', '%s', '%s')
                      """ % (cursoid, idmodulo, instance, fecha, section)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                sql = """select id from mooc_course_modules WHERE course=%s AND module='%s' and instance='%s' and section='%s' """ % (cursoid, idmodulo, instance, section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instanceid = buscar[0][0]

                sql = """INSERT INTO mooc_context (contextlevel,instanceid,depth,path,locked) VALUES('70','%s','0',NULL,'0')""" % (instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR LA CONTEXTID
                sql = """select id from mooc_context WHERE contextlevel=70 AND instanceid='%s' """ % (instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                contextid = buscar[0][0]

                sql = """select path from mooc_context WHERE contextlevel=50 AND instanceid='%s' """ % (cursoid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                pathcontext = buscar[0][0]
                depthcontext = pathcontext.split("/").__len__()
                pathcontext = "%s/%s" % (pathcontext, contextid)
                sql = """update mooc_context set path='%s', depth='%s' WHERE contextlevel=70 AND instanceid='%s' """ % (pathcontext, depthcontext, instanceid)
                cursor.execute(sql)

                # PROCEDEMOS A BUSCAR sequence
                sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                sequence = buscar[0][0]

                sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % ("%s,%s" % (sequence, instanceid), section)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

                diapositiva.idmaterialesmoodle = instanceid
                diapositiva.estado_id = 4
                diapositiva.save()
            else:
                # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
                instanceid = diapositiva.idmaterialesmoodle
                sql = """select instance from mooc_course_modules WHERE course=%s AND id='%s' """ % (cursoid, instanceid)
                cursor.execute(sql)
                buscar = cursor.fetchall()
                instance = buscar[0][0]

                sql = """update mooc_url 
                        set name='%s',
                            externalurl='%s',
                            intro='%s',
                            timemodified='%s'
                        where course='%s' and id='%s'
                        """ % ("S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre.replace("'", "")[:230]), url, intro, fecha, cursoid, instance)

                cursor.execute(sql)
                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)

            if diapositiva.idmaterialesmoodle > 0:
                diapositiva.estado_id = 4
                diapositiva.save()
            return True, u"Material migrado a Moodle"
        except Exception as ex:
            transaction.set_rollback(True, using=cursor_verbose)
            return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
        finally:
            cursor.close()


# persona =  Persona.objects.get(pk=822)
# CrearMaterialesMoodle(1001, persona)
def crearhtmlphpmoodle(materia_id):
    try:
        from settings import SITE_STORAGE
        import requests
        from django.db import connections
        import uuid
        import warnings
        warnings.filterwarnings('ignore', message='Unverified HTTPS request')
        materia = Materia.objects.get(pk=materia_id.id)
        if materia.idcursomoodle > 0 and materia.actualizarhtml:
            print("%s ----- %s" % (materia, materia.idcursomoodle))
            cursoid = materia.idcursomoodle
            fecha = int(time.mktime(datetime.now().timetuple()))
            cursor = None
            if materia.coordinacion():
                if materia.coordinacion().id == 9:
                    cursor = connections['db_moodle_virtual'].cursor()
                elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                    cursor = connections['aulagradoa'].cursor()
                else:
                    cursor = connections['aulagradob'].cursor()
            else:
                cursor = connections['moodle_db'].cursor()
            if not materia.namehtml or materia.namehtml == 'contruyendo_silabo.html':
                htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
            else:
                htmlname = materia.namehtml
            urlname = SITE_STORAGE + "/media/htmlmoodlestatic/%s" % htmlname
            # a = requests.get('https://aulagrado.unemi.edu.ec/silabo/versionhtml.php?codisakai=%s' % materia.id, verify=False)
            a = requests.get('https://sga.unemi.edu.ec/adm_silabo?action=pregrado&codigo=%s' % encrypt(materia.id), verify=False)
            with open(urlname, "wb") as f:
                f.write(a.content)
            f.close()
            if not materia.namehtml or materia.namehtml == 'contruyendo_silabo.html':
                materia.namehtml = htmlname
                materia.urlhtml = urlname
                materia.save()
            if materia.fecha_modificacion:
                version = '?v=%s' % materia.fecha_modificacion.strftime('%Y%m%d_%H%M%S')
            else:
                version = '?v=%s' % materia.fecha_creacion.strftime('%Y%m%d_%H%M%S')
            summary = """
                <iframe src="https://sga.unemi.edu.ec/media/htmlmoodlestatic/%s%s"  class="filter_hvp" id="hvp_4383" style="width:100%s; height:1000px; border:0;" frameborder="0" allowfullscreen="allowfullscreen"></iframe>
            """ % (htmlname, version, '%')
            sql = """UPDATE mooc_course_sections set summary='%s' WHERE course=%s AND SECTION='0' """ % (summary, cursoid)
            cursor.execute(sql)

            query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
            cursor.execute(query)
            materia.actualizarhtml = False
            materia.save()
    except Exception as ex:
        import sys
        print('Error al crear html %s ---- %s ---- %s' % (ex, materia, sys.exc_info()[-1].tb_lineno))


def crearhtmlphpmoodleadmision(materia):
    from settings import SITE_STORAGE
    import requests
    from django.db import connections
    import uuid
    import warnings
    warnings.filterwarnings('ignore', message='Unverified HTTPS request')
    if materia.idcursomoodle > 0 and materia.actualizarhtml:
        cursoid = materia.idcursomoodle
        fecha = int(time.mktime(datetime.now().timetuple()))
        cursor = None
        if materia.coordinacion():
            if materia.coordinacion().id == 9:
                cursor = connections['db_moodle_virtual'].cursor()
            elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
                cursor = connections['aulagradoa'].cursor()
            else:
                cursor = connections['aulagradob'].cursor()
        else:
            cursor = connections['moodle_db'].cursor()
        if not materia.namehtml or materia.namehtml == 'contruyendo_silabo.html':
            htmlname = "%s%s" % (uuid.uuid4().hex, '.html')
        else:
            htmlname = materia.namehtml
        urlname = SITE_STORAGE + "/media/htmlmoodlestatic/%s" % htmlname

        print("%s ----- %s" % (materia, materia.idcursomoodle))

        # a = requests.get('https://aulanivelacion.unemi.edu.ec/silaboadmision/versionhtml.php?codisakai=%s' % materia.id, verify=False)
        # print('https://sga.unemi.edu.ec/adm_silabo?action=admision&codigo=%s' % encrypt(materia.id))
        a = requests.get('https://sga.unemi.edu.ec/adm_silabo?action=admision&codigo=%s' % encrypt(materia.id), verify=False)
        with open(urlname, "wb") as f:
            f.write(a.content)
        f.close()
        if not materia.namehtml or materia.namehtml == 'contruyendo_silabo.html':
            materia.namehtml = htmlname
            materia.urlhtml = urlname
            materia.save()

        if materia.fecha_modificacion:
            version = '?v=%s' % materia.fecha_modificacion.strftime('%Y%m%d_%H%M%S')
        else:
            version = '?v=%s' % materia.fecha_creacion.strftime('%Y%m%d_%H%M%S')
        summary = """
            <iframe src="https://sga.unemi.edu.ec/media/htmlmoodlestatic/%s%s"  class="filter_hvp" id="hvp_4383" style="width:100%s; height:1000px; border:0;" frameborder="0" allowfullscreen="allowfullscreen"></iframe>
        """ % (htmlname, version, '%')
        sql = """UPDATE mooc_course_sections set summary='%s' WHERE course=%s AND SECTION='0' """ % (summary, cursoid)
        cursor.execute(sql)

        query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
        cursor.execute(query)
        materia.actualizarhtml = False
        materia.save()


def updaterubroepunemi(codrubroepunemi):
    from django.db import connections
    cursor = connections['epunemi'].cursor()
    rubro = Rubro.objects.get(idrubroepunemi=codrubroepunemi, status=True)
    query = u"UPDATE sagest_rubro SET valor=%s,valortotal=%s, saldo=%s WHERE id = %s" % (rubro.valor, rubro.valortotal, rubro.saldo, codrubroepunemi)
    cursor.execute(query)
# from sga.models import Materia
# materia = Materia.objects.get(pk=32968)
# crearhtmlphpmoodle(materia)

def buscarUsuario(username,cursor):
    queryest = """ SELECT use.id
                        FROM  mooc_user use
                        WHERE use.username='%s' and use.deleted=0
                """ % (username)
    cursor.execute(queryest)
    rowest = cursor.fetchall()
    if rowest:
        for registro in rowest:
            return registro[0]
    return None


def buscarQuiz(idquiz, coordinacion_id):
    from django.db import connections
    try:
        if coordinacion_id == 9:
            conexion = connections['db_moodle_virtual']
            cursor = conexion.cursor()
        else:
            conexion = connections['moodle_db']
            cursor = conexion.cursor()
        sql = """SELECT id, timeopen, timeclose, timelimit, attempts FROM mooc_quiz WHERE id=%s""" % idquiz
        cursor.execute(sql)
        rowest = cursor.fetchall()
        if rowest:
            for registro in rowest:
                return registro
        return None
    except Exception as ex:
        return None


def estadoQuizIndividual(username, materia, instanceid):
    from django.db import connections
    if materia.coordinacion():
        if materia.coordinacion().id == 9:
            conexion = connections['db_moodle_virtual']
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            conexion = connections['aulagradoa'].cursor()
        else:
            conexion = connections['aulagradob'].cursor()
    cursor = conexion.cursor()
    sql = """SELECT qatt.state
                FROM mooc_quiz_attempts AS qatt
                INNER JOIN mooc_user AS us1 ON us1.id=qatt.userid
                WHERE us1.username='%s' AND qatt.quiz=%s""" % (username, instanceid)
    cursor.execute(sql)
    rowest = cursor.fetchall()
    if rowest:
        for registro in rowest:
            return registro
    return None


def accesoQuizIndividual(username, materia, quiz_id, data):
    from django.db import connections
    if materia.coordinacion():
        fecha = int(time.mktime(datetime.now().timetuple()))
        if materia.coordinacion().id == 9:
            conexion = connections['db_moodle_virtual']
            cursor_verbose = 'db_moodle_virtual'
        elif materia.asignaturamalla.malla.modalidad_id in (1, 2):
            conexion = connections['aulagradoa']
            cursor_verbose = 'aulagradoa'
        else:
            conexion = connections['aulagradob']
            cursor_verbose = 'aulagradob'
        with transaction.atomic(using=cursor_verbose):
            try:
                user_id = None
                id_overrides = None
                password = None
                if data['password']:
                    password = data['password']
                # print(f"Password: {password}")
                cursor = conexion.cursor()
                user_id = buscarUsuario(username, cursor)
                sql = """SELECT id FROM mooc_quiz_overrides WHERE userid=%s and quiz=%s""" % (int(user_id), int(quiz_id))
                # print(f"Q1 {sql}")
                cursor.execute(sql)
                rowest = cursor.fetchall()
                # print(rowest)
                if rowest:
                    for registro in rowest:
                        id_overrides = registro[0]
                    if id_overrides:
                        if password is None:
                            params = (data['timeopen'], data['timeclose'], data['timelimit'], data['attempts'], id_overrides)
                            sql = """UPDATE mooc_quiz_overrides SET timeopen=%s, timeclose=%s, timelimit=%s, password=NULL, attempts=%s where id=%s""" % params
                        else:
                            params = (data['timeopen'], data['timeclose'], data['timelimit'], password, data['attempts'], id_overrides)
                            sql = """UPDATE mooc_quiz_overrides SET timeopen=%s, timeclose=%s, timelimit=%s, password='%s', attempts=%s where id=%s""" % params
                        # print(f"Q2 {sql}")
                        cursor.execute(sql)
                else:
                    if password is None:
                        params = (int(user_id), data['timeopen'], data['timeclose'], data['timelimit'], data['attempts'], int(quiz_id))
                        sql = """INSERT INTO mooc_quiz_overrides (userid,password,timeopen,timeclose,timelimit,attempts,quiz) VALUES (%s, NULL, %s, %s, %s, %s, %s) """ % params
                    else:
                        params = (int(user_id), password, data['timeopen'], data['timeclose'], data['timelimit'], data['attempts'], int(quiz_id))
                        sql = """INSERT INTO mooc_quiz_overrides (userid,password,timeopen,timeclose,timelimit,attempts,quiz) VALUES (%s, '%s', %s, %s, %s, %s, %s) """ % params
                    # print(f"Q3 {sql}")
                    cursor.execute(sql)
                if not DEBUG:
                    query = u"UPDATE mooc_course SET cacherev=%s WHERE id=%s" % (fecha, materia.idcursomoodle)
                    # print(f"Q4 {query}")
                    cursor.execute(query)
                return True, ''
            except Exception as ex:
                transaction.set_rollback(True, using=cursor_verbose)
                return False, "%s - %s" % (ex.__str__(), sys.exc_info()[-1].tb_lineno)
            finally:
                cursor.close()


#new
def CrearUsuarioQuery(cursor,person):
    try:
        username=person.usuario.username
        estudiante_id = buscarUsuario(username, cursor)
        fcreacion = int(time.mktime(start.timetuple()))
        if estudiante_id is None:
            idusuario=None
            print(f'Creando usuario...')
            auth_ = 'db'
            pass_ = 'not cached'
            sql3_ = f"""INSERT INTO {MY_PRIFIX_MOODLE}user (username, auth, PASSWORD, firstname, lastname, email, city, country, idnumber, lang, calendartype, confirmed, mnethostid, maildisplay, mailformat, maildigest, autosubscribe, trackforums)
                     VALUES('{username}', '{auth_}', '{pass_}',  '{person.nombres}', '{person.apellidos()}', '{person.emailinst}', 'MILAGRO', 'EC', '{person.identificacion()}', 'es', 'gregorian', '1', '1', '2', '1', '0', '1', '0');"""
            #print(sql3_)
            a = cursor.execute(sql3_)
            #print(a)
            sql4_ = f"SELECT id FROM {MY_PRIFIX_MOODLE}user WHERE username = '{username}' AND mnethostid = '1' LIMIT 1"
            cursor.execute(sql4_)
            result4_ = cursor.fetchall()
            #print(result4_)
            if result4_:
                idusuario = result4_[0][0]
                print(f'Usuario creado id: {idusuario}')
                print(f'Creando contexto...')
                sql5_ = f"INSERT INTO {MY_PRIFIX_MOODLE}context (contextlevel, instanceid, DEPTH, PATH, locked) VALUES('30', '{idusuario}', '0', NULL, '0') RETURNING id;"
                cursor.execute(sql5_)
                sql6_ = f"SELECT * FROM {MY_PRIFIX_MOODLE}context WHERE contextlevel = '30' AND instanceid = '{idusuario}';"
                cursor.execute(sql6_)
                result6_ = cursor.fetchall()
                if result6_:
                    idcontext = result6_[0][0]
                    print(f'Contexto creado id: {idcontext}')
                    sql7 = f"UPDATE {MY_PRIFIX_MOODLE}context SET contextlevel = '30',instanceid ='{idusuario}', depth = '2',path = '/1/{idcontext}', locked = '0' WHERE id='{idcontext}';"
                    cursor.execute(sql7)
            # cursor.close()
            return True, '', idusuario
        else:
            return True, "Usuario ya creado", estudiante_id
    except Exception as ex:
        print(ex)
        return False, ex.__str__(), 0

def EnrolarUsuarioQuery(cursor,idusuario, idcurso, rol):
    try:
        sql2_ = f"SELECT id FROM {MY_PRIFIX_MOODLE}context WHERE contextlevel = '50' AND instanceid = '{idcurso}'"
        cursor.execute(sql2_)
        result2_ = cursor.fetchall()
        if result2_:
            idcontext = result2_[0][0]
            sql3_ = f"SELECT id FROM {MY_PRIFIX_MOODLE}enrol WHERE courseid = '{idcurso}' AND status = '0'  ORDER BY sortorder,id;"
            cursor.execute(sql3_)
            result3_ = cursor.fetchall()
            if result3_:
                idrolmanual = result3_[0][0]
                sql4_ = f"SELECT * FROM {MY_PRIFIX_MOODLE}user_enrolments WHERE enrolid = '{idrolmanual}' AND userid ='{idusuario}'"
                cursor.execute(sql4_)
                result4_ = cursor.fetchall()
                if not result4_:
                    print(f"Inscribiendo...")
                    sql5_ = f"INSERT INTO {MY_PRIFIX_MOODLE}user_enrolments (enrolid,status,userid,timestart,timeend,modifierid,timecreated,timemodified)" \
                            f"VALUES('{idrolmanual}', '0', '{idusuario}', '0', '0', '2', '{fcreacion}', '{fcreacion}')"
                    cursor.execute(sql5_)
                    sql6_ = f"SELECT * FROM {MY_PRIFIX_MOODLE}role_assignments WHERE roleid = '{rol}' AND contextid = '{idcontext}' AND userid = '{idusuario}' AND component = '' AND itemid = '0'  ORDER BY id"
                    cursor.execute(sql6_)
                    result6_ = cursor.fetchall()
                    if not result6_:
                        print(f"Confirmar inscripción...")
                        sql7_ = f"INSERT INTO {MY_PRIFIX_MOODLE}role_assignments (roleid, contextid, userid, component, itemid, timemodified, modifierid, sortorder) " \
                                f"VALUES('{rol}', '{idcontext}', '{idusuario}', '', '0', '{fcreacion}', '2', '0')"
                        cursor.execute(sql7_)
                        sql8_ = f"SELECT * FROM {MY_PRIFIX_MOODLE}cache_flags WHERE name = '{idusuario}' AND flagtype = 'accesslib/dirtyusers' LIMIT 1"
                        cursor.execute(sql8_)
                        result8_ = cursor.fetchall()
                        if not result8_:
                            print(f"Creando Cache...")
                            sql9_ = f"INSERT INTO {MY_PRIFIX_MOODLE}cache_flags (flagtype, name, value, expiry, timemodified) " \
                                    f"VALUES('accesslib/dirtyusers', '{idusuario}', '1', '{fcreacion}','{fcreacion}')"
                            cursor.execute(sql9_)
                        # cursor.close()
                        return True,'',0
                    else:
                        return False, f'Usuario ya esta en role_assignments', 0
                else:
                    return False, f'Usuario ya esta enrolado', 0
        else:
            return False, f'Curso no tiene contexto', 0
    except Exception as ex:
        return False, ex.__str__(), 0


def BuscarCursoQuery(cursor, idcurso_number=None):
    try:
        idcurso=0
        if idcurso_number:
            # print(f'Buscando curso... %s', idcurso_number)
            sql4_ = f"SELECT id FROM {MY_PRIFIX_MOODLE}course WHERE idnumber = '{idcurso_number}'"
            cursor.execute(sql4_)
            result4_ = cursor.fetchall()
            if result4_:
                idcurso = result4_[0][0]
            if idcurso == 0:
                sql4_ = f"SELECT id FROM {MY_PRIFIX_MOODLE}course WHERE idnumber = '{idcurso_number}P'"
                cursor.execute(sql4_)
                result4_ = cursor.fetchall()
                if result4_:
                    idcurso = result4_[0][0]

        return idcurso
    except Exception as ex:
        print(ex)
        return 0


def BuscarCategoriaQuery(cursor, idnumber=None):
    idcategoria = 0
    try:
        if idnumber:
            sql4_ = f"SELECT id FROM {MY_PRIFIX_MOODLE}_course_categories WHERE idnumber = '{idnumber}'"
            cursor.execute(sql4_)
            result4_ = cursor.fetchall()
            if result4_:
                idcategoria = result4_[0][0]
        return idcategoria
    except Exception as ex:
        return idcategoria