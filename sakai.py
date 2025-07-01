# -*- coding: UTF-8 -*-
from datetime import timedelta
from xml.dom import minidom
from django.shortcuts import render
from reportlab.lib.enums import TA_LEFT
from django.http.response import HttpResponseRedirect
from sga.funciones import querymysqlsakai, validarcedula, convertir_fecha, extraer_carrera, null_to_decimal
from sga.funcionesxhtml2pdf import add_titulo_reportlab, generar_pdf_reportlab, add_tabla_reportlab, \
    conviert_html_to_pdf


def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'informeactividad':
                try:
                    data = {}
                    listas_materias=[]
                    lista_carreras=[]
                    lista_paralelos=[]
                    data['cedula']= cedula = request.POST['cedula'].strip()
                    data['fechadesde'] = fechadesde = convertir_fecha(request.POST['fechadesde'])
                    data['fechahasta'] = fechahasta = convertir_fecha(request.POST['fechahasta'])
                    id_rol_instructor = 'tutor'
                    id_sitio = None
                    id_rol_autor = 'Autor'
                    apellido_autor = ""
                    nombre_autor = ""
                    apellidos = ""
                    nombres = ""
                    total_enviados = 0
                    total_calificados = 0
                    total_foros_calificados = 0
                    total_foros_participados = 0
                    total_foros_por_calificar = 0
                    total_aportaciones = 0
                    if validarcedula(cedula):
                        sql = "select distinct a.USER_ID as idusuario, a.EID as cedula, b.LAST_NAME as apellido, b.FIRST_NAME, b.EMAIL as email from SAKAI_USER_ID_MAP as a inner join SAKAI_USER as b on b.USER_ID=a.USER_ID inner join SAKAI_SITE_USER as c on c.USER_ID=a.USER_ID where a.EID='" + cedula +"'"
                        resultados_usuario = querymysqlsakai(sql, True)
                        if resultados_usuario:
                            listas_tareas = []
                            listas_foros = []
                            listas_salas_chats = []
                            id_usuario = resultados_usuario[0][0]
                            data['cedula'] = cedula = resultados_usuario[0][1]
                            data['apellidos'] = apellidos = resultados_usuario[0][2]
                            data['nombres'] = nombres = resultados_usuario[0][3]
                            data['email'] = resultados_usuario[0][4]
                            # EXTRAE LOS CURSOS ASIGNADOS DE LA PERSONA
                            sql_cursos = "select site.SITE_ID as sitio, site.TITLE as nombre_curso, site.type as tipo, " \
                                         "(select SRR.ROLE_NAME from SAKAI_REALM_RL_GR SRRG  " \
                                         "inner join SAKAI_REALM SR on SRRG.REALM_KEY = SR.REALM_KEY  " \
                                         "inner join SAKAI_REALM_ROLE SRR on SRRG.ROLE_KEY = SRR.ROLE_KEY  " \
                                         "where SR.REALM_ID = CONCAT ( '/site/', site.SITE_ID) and SRRG.USER_ID = c.USER_ID and SRRG.ACTIVE = '1') as rol " \
                                         "from SAKAI_USER_ID_MAP as a " \
                                         "inner join SAKAI_USER as b on b.USER_ID=a.USER_ID " \
                                         "inner join SAKAI_SITE_USER as c on c.USER_ID=a.USER_ID " \
                                         "inner join SAKAI_SITE as site on site.SITE_ID = c.SITE_ID " \
                                         "where a.EID='"+cedula+"' and site.IS_SOFTLY_DELETED = 0 and site.PUBVIEW = '1' order by site.TITLE"
                            resultados_cursos = querymysqlsakai(sql_cursos, True)

                            for curso in resultados_cursos:
                                nombre_curso = curso[1]
                                id_rol = curso[3]
                                extraer_carrera(nombre_curso, lista_carreras, lista_paralelos)
                                if id_rol.strip().lower() == id_rol_instructor.strip().lower():
                                    id_sitio = curso[0]
                                    # EXTRAER TAREAS
                                    sql_tareas = "select tareas.ASSIGNMENT_ID, tareas.XML, tareas.CONTEXT from ASSIGNMENT_ASSIGNMENT tareas where tareas.CONTEXT = '"+id_sitio+"'"
                                    resultados_tareas = querymysqlsakai(sql_tareas, True)
                                    total_estudiantes_curso = "SELECT count(SRRG.REALM_KEY) " \
                                                              "FROM SAKAI_REALM_RL_GR SRRG " \
                                                              "INNER JOIN SAKAI_REALM SR ON SRRG.REALM_KEY = SR.REALM_KEY " \
                                                              "INNER JOIN SAKAI_REALM_ROLE SRR ON SRRG.ROLE_KEY = SRR.ROLE_KEY " \
                                                              "WHERE SR.REALM_ID = CONCAT ('/site/', '"+id_sitio+"') AND SRRG.ACTIVE = '1' AND SRR.ROLE_NAME = 'Student'"
                                    resultados_total_estudiante_curso = querymysqlsakai(total_estudiantes_curso, True)
                                    total_enviados=0
                                    total_calificados = 0
                                    for tarea in resultados_tareas:
                                        id_tarea = tarea[0]
                                        id_xml_tarea = tarea[1]
                                        xmltext = minidom.parseString(id_xml_tarea)
                                        itemlist = xmltext.getElementsByTagName("assignment")
                                        fecha_inicio_sinformato = itemlist[0].getAttribute('opendate')
                                        fecha_fin_sinformato = itemlist[0].getAttribute('duedate')
                                        fecha_inicio = convertir_fecha(u'%s-%s-%s'%(fecha_inicio_sinformato[6:8], fecha_inicio_sinformato[4:6], fecha_inicio_sinformato[0:4]))
                                        fecha_fin = convertir_fecha(u'%s-%s-%s'%(fecha_fin_sinformato[6:8], fecha_fin_sinformato[4:6], fecha_fin_sinformato[0:4]))
                                        restardias = timedelta(days=-1)
                                        fecha_fin = fecha_fin + restardias
                                        # if (fechadesde <= fecha_inicio and fecha_fin <= fechahasta) or (fecha_inicio.month==11 and fechadesde.month == 12) or (fecha_inicio.day in [30,31] and fecha_inicio<fechahasta) :
                                        # if fecha_inicio > fechadesde and fecha_fin <= fechahasta:
                                        if (fecha_fin >= fechadesde and fecha_fin <=  fechahasta):
                                            nombre_tarea = itemlist[0].getAttribute('title')
                                            sql_total_estudiante_tarea = "select count(submission.SUBMISSION_ID) " \
                                                                         "from ASSIGNMENT_SUBMISSION submission  " \
                                                                         "inner join SAKAI_REALM_RL_GR SRRG on SRRG.USER_ID = submission.SUBMITTER_ID " \
                                                                         "INNER JOIN SAKAI_REALM SR ON SRRG.REALM_KEY = SR.REALM_KEY " \
                                                                         "INNER JOIN SAKAI_REALM_ROLE SRR ON SRRG.ROLE_KEY = SRR.ROLE_KEY " \
                                                                         "where submission.CONTEXT ='"+id_tarea+"' and " \
                                                                         "SR.REALM_ID = CONCAT ('/site/', '"+id_sitio+"') AND SRRG.ACTIVE = '1'and  SRR.ROLE_NAME = 'Student' "
                                            sql_total_estudiante_enviaron_tarea = sql_total_estudiante_tarea + "AND submission.SUBMIT_TIME is not null AND submission.SUBMITTED='true'"
                                            resultados_total_estudiante_enviaron_tarea = querymysqlsakai(sql_total_estudiante_enviaron_tarea, True)
                                            sql_total_estudiante_enviaron_tarea_borrador = sql_total_estudiante_tarea + "AND submission.SUBMIT_TIME is not null AND submission.SUBMITTED='false'"
                                            resultados_total_estudiante_enviaron_tarea_borrador = querymysqlsakai(sql_total_estudiante_enviaron_tarea_borrador, True)
                                            sql_total_estudiante_no_enviaron_tarea = sql_total_estudiante_tarea + "AND submission.SUBMIT_TIME is null"
                                            resultados_total_estudiante_no_enviaron_tarea = querymysqlsakai(sql_total_estudiante_no_enviaron_tarea, True)
                                            sql_total_estudiante_calificada_tarea = sql_total_estudiante_tarea + "AND submission.SUBMIT_TIME is not null AND submission.SUBMITTED='true' AND submission.GRADED = 'true'"
                                            resultados_total_estudiante_calificada_tarea = querymysqlsakai(sql_total_estudiante_calificada_tarea, True)
                                            sql_total_estudiante_calificada_tarea_borrador = sql_total_estudiante_tarea + "AND submission.SUBMIT_TIME is not null AND submission.SUBMITTED='false' AND submission.GRADED = 'true'"
                                            resultados_total_estudiante_calificada_tarea_borrador = querymysqlsakai(sql_total_estudiante_calificada_tarea_borrador, True)
                                            sql_total_estudiante_no_calificada_tarea = sql_total_estudiante_tarea + "AND submission.SUBMIT_TIME is not null and submission.GRADED = 'false'"
                                            resultados_total_estudiante_no_calificada_tarea = querymysqlsakai(sql_total_estudiante_no_calificada_tarea, True)
                                            total_enviados += resultados_total_estudiante_enviaron_tarea[0][0]
                                            total_calificados += resultados_total_estudiante_calificada_tarea[0][0]
                                            listas_tareas.append([nombre_tarea, fecha_inicio.strftime('%d-%m-%Y'),
                                                                  resultados_total_estudiante_curso[0][0],
                                                                  resultados_total_estudiante_enviaron_tarea[0][0],
                                                                  resultados_total_estudiante_enviaron_tarea_borrador[0][0],
                                                                  resultados_total_estudiante_no_enviaron_tarea[0][0],
                                                                  resultados_total_estudiante_calificada_tarea[0][0],
                                                                  resultados_total_estudiante_calificada_tarea_borrador[0][0],
                                                                  resultados_total_estudiante_no_calificada_tarea[0][0], fecha_fin.strftime('%d-%m-%Y')])
                                            listas_tareas.sort(key=lambda clasesimp: (clasesimp[1]), reverse=True)
                                    # EXTRAER FOROS
                                    # sql_foros = "select openforumi0_.ID as ID50_0_, topicsset1_.ID as ID47_1_, attachment2_.ID as ID44_2_, " \
                                    #             "attachment3_.ID as ID44_3_, openforumi0_.VERSION as VERSION50_0_, openforumi0_.UUID as UUID50_0_, " \
                                    #             "openforumi0_.CREATED as CREATED50_0_, openforumi0_.CREATED_BY as CREATED6_50_0_,  " \
                                    #             "openforumi0_.MODIFIED as MODIFIED50_0_, openforumi0_.MODIFIED_BY as MODIFIED8_50_0_,  " \
                                    #             "openforumi0_.DEFAULTASSIGNNAME as DEFAULTA9_50_0_, openforumi0_.TITLE as TITLE50_0_,  " \
                                    #             "openforumi0_.SHORT_DESCRIPTION as SHORT11_50_0_, openforumi0_.EXTENDED_DESCRIPTION as EXTENDED12_50_0_,  " \
                                    #             "openforumi0_.TYPE_UUID as TYPE13_50_0_, openforumi0_.SORT_INDEX as SORT14_50_0_, openforumi0_.LOCKED as LOCKED50_0_,  " \
                                    #             "openforumi0_.DRAFT as DRAFT50_0_, openforumi0_.AVAILABILITY_RESTRICTED as AVAILAB17_50_0_, openforumi0_.AVAILABILITY as AVAILAB18_50_0_,  " \
                                    #             "openforumi0_.OPEN_DATE as OPEN19_50_0_, openforumi0_.CLOSE_DATE as CLOSE20_50_0_, openforumi0_.surrogateKey as surroga21_50_0_,  " \
                                    #             "openforumi0_.MODERATED as MODERATED50_0_, openforumi0_.AUTO_MARK_THREADS_READ as AUTO23_50_0_, openforumi0_.POST_FIRST as POST24_50_0_,  " \
                                    #             "openforumi0_.FORUM_DTYPE as FORUM2_50_0_, topicsset1_.VERSION as VERSION47_1_, topicsset1_.UUID as UUID47_1_, topicsset1_.CREATED as CREATED47_1_,  " \
                                    #             "topicsset1_.CREATED_BY as CREATED6_47_1_, topicsset1_.MODIFIED as MODIFIED47_1_, topicsset1_.MODIFIED_BY as MODIFIED8_47_1_,  " \
                                    #             "topicsset1_.DEFAULTASSIGNNAME as DEFAULTA9_47_1_, topicsset1_.TITLE as TITLE47_1_, topicsset1_.SHORT_DESCRIPTION as SHORT11_47_1_,  " \
                                    #             "topicsset1_.EXTENDED_DESCRIPTION as EXTENDED12_47_1_, topicsset1_.MODERATED as MODERATED47_1_, topicsset1_.POST_FIRST as POST14_47_1_,  " \
                                    #             "topicsset1_.POST_ANONYMOUS as POST15_47_1_, topicsset1_.REVEAL_IDS_TO_ROLES as REVEAL16_47_1_, topicsset1_.AUTO_MARK_THREADS_READ as AUTO17_47_1_,  " \
                                    #             "topicsset1_.MUTABLE as MUTABLE47_1_, topicsset1_.SORT_INDEX as SORT19_47_1_, topicsset1_.TYPE_UUID as TYPE20_47_1_, topicsset1_.AVAILABILITY_RESTRICTED as AVAILAB21_47_1_,  " \
                                    #             "topicsset1_.AVAILABILITY as AVAILAB22_47_1_, topicsset1_.OPEN_DATE as OPEN23_47_1_, topicsset1_.CLOSE_DATE as CLOSE24_47_1_, topicsset1_.of_surrogateKey as of25_47_1_,  " \
                                    #             "topicsset1_.pf_surrogateKey as pf26_47_1_, topicsset1_.USER_ID as USER27_47_1_, topicsset1_.CONTEXT_ID as CONTEXT28_47_1_, topicsset1_.pt_surrogateKey as pt29_47_1_,  " \
                                    #             "topicsset1_.LOCKED as LOCKED47_1_, topicsset1_.DRAFT as DRAFT47_1_, topicsset1_.CONFIDENTIAL_RESPONSES as CONFIDE32_47_1_,  " \
                                    #             "topicsset1_.MUST_RESPOND_BEFORE_READING as MUST33_47_1_, topicsset1_.HOUR_BEFORE_RESPONSES_VISIBLE as HOUR34_47_1_, topicsset1_.TOPIC_DTYPE as TOPIC2_47_1_,  " \
                                    #             "topicsset1_.of_surrogateKey as of25_50_0__, topicsset1_.ID as ID0__, attachment2_.VERSION as VERSION44_2_, attachment2_.UUID as UUID44_2_,  " \
                                    #             "attachment2_.CREATED as CREATED44_2_, attachment2_.CREATED_BY as CREATED5_44_2_, attachment2_.MODIFIED as MODIFIED44_2_, attachment2_.MODIFIED_BY as MODIFIED7_44_2_,  " \
                                    #             "attachment2_.ATTACHMENT_ID as ATTACHMENT8_44_2_, attachment2_.ATTACHMENT_URL as ATTACHMENT9_44_2_, attachment2_.ATTACHMENT_NAME as ATTACHMENT10_44_2_,  " \
                                    #             "attachment2_.ATTACHMENT_SIZE as ATTACHMENT11_44_2_, attachment2_.ATTACHMENT_TYPE as ATTACHMENT12_44_2_, attachment2_.m_surrogateKey as m13_44_2_,  " \
                                    #             "attachment2_.of_surrogateKey as of14_44_2_, attachment2_.pf_surrogateKey as pf15_44_2_, attachment2_.t_surrogateKey as t16_44_2_, attachment2_.t_surrogateKey as t16_47_1__,  " \
                                    #             "attachment2_.ID as ID1__, attachment3_.VERSION as VERSION44_3_, attachment3_.UUID as UUID44_3_, attachment3_.CREATED as CREATED44_3_, attachment3_.CREATED_BY as CREATED5_44_3_,  " \
                                    #             "attachment3_.MODIFIED as MODIFIED44_3_, attachment3_.MODIFIED_BY as MODIFIED7_44_3_, attachment3_.ATTACHMENT_ID as ATTACHMENT8_44_3_,  " \
                                    #             "attachment3_.ATTACHMENT_URL as ATTACHMENT9_44_3_, attachment3_.ATTACHMENT_NAME as ATTACHMENT10_44_3_, attachment3_.ATTACHMENT_SIZE as ATTACHMENT11_44_3_,  " \
                                    #             "attachment3_.ATTACHMENT_TYPE as ATTACHMENT12_44_3_, attachment3_.m_surrogateKey as m13_44_3_, attachment3_.of_surrogateKey as of14_44_3_,  " \
                                    #             "attachment3_.pf_surrogateKey as pf15_44_3_, attachment3_.t_surrogateKey as t16_44_3_, attachment3_.of_urrogateKey as of17_50_2__, attachment3_.ID as ID2__,  " \
                                    #             "(SELECT COUNT(DISTINCT msj.CREATED_BY) FROM MFR_MESSAGE_T msj INNER JOIN MFR_TOPIC_T topico ON msj.surrogateKey=topico.ID INNER JOIN MFR_OPEN_FORUM_T foro ON topico.of_surrogateKey= foro.ID " \
                                    #             "INNER JOIN MFR_AREA_T areas ON foro.surrogateKey=areas.ID WHERE areas.CONTEXT_ID='"+id_sitio+"' AND topico.ID= topicsset1_.ID ) AS cant_aportaciones " \
                                    #             "from MFR_OPEN_FORUM_T openforumi0_ left outer join MFR_TOPIC_T topicsset1_ on openforumi0_.ID=topicsset1_.of_surrogateKey  " \
                                    #             "left outer join MFR_ATTACHMENT_T attachment2_ on topicsset1_.ID=attachment2_.t_surrogateKey  " \
                                    #             "left outer join MFR_ATTACHMENT_T attachment3_ on openforumi0_.ID=attachment3_.of_urrogateKey  " \
                                    #             "cross join MFR_AREA_T areaimpl4_  " \
                                    #             "where openforumi0_.surrogateKey=areaimpl4_.ID " \
                                    #             "and areaimpl4_.CONTEXT_ID='"+id_sitio+"' order by openforumi0_.CREATED or topicsset1_.OPEN_DATE desc"
                                    sql_foros = "SELECT topicsset1_.ID, topicsset1_.TITLE as titulo_topico, topicsset1_.DEFAULTASSIGNNAME as asigname_topico, openforumi0_.TITLE as titulo_foro, openforumi0_.DEFAULTASSIGNNAME as asigname_foro, topicsset1_.OPEN_DATE AS fecha_apertura, topicsset1_.CLOSE_DATE AS fecha_cierre,  (SELECT COUNT(DISTINCT msj.CREATED_BY) FROM MFR_MESSAGE_T msj INNER JOIN MFR_TOPIC_T topico ON msj.surrogateKey=topico.ID INNER JOIN MFR_OPEN_FORUM_T foro ON topico.of_surrogateKey= foro.ID " \
                                                "INNER JOIN MFR_AREA_T areas ON foro.surrogateKey=areas.ID WHERE areas.CONTEXT_ID='"+id_sitio+"' AND topico.ID= topicsset1_.ID ) AS cant_aportaciones " \
                                                "FROM MFR_OPEN_FORUM_T openforumi0_ LEFT OUTER JOIN MFR_TOPIC_T topicsset1_ ON openforumi0_.ID=topicsset1_.of_surrogateKey CROSS JOIN MFR_AREA_T areaimpl4_ " \
                                                "WHERE openforumi0_.surrogateKey=areaimpl4_.ID AND areaimpl4_.CONTEXT_ID='"+id_sitio+"'  and topicsset1_.CLOSE_DATE < CURDATE()"
                                    resultados_foros = querymysqlsakai(sql_foros, True)
                                    # for foro in resultados_foros:
                                    #     nombre_foro = foro[34]
                                    #     fecha_creacion = convertir_fecha(foro[6].strftime('%d-%m-%Y'))
                                    #     if foro[47]:
                                    #         fecha_apertura = convertir_fecha(foro[47].strftime('%d-%m-%Y'))
                                    #         if fechadesde <= fecha_apertura and fecha_apertura <= fechahasta:
                                    #             listas_foros.append([nombre_foro, fecha_apertura.strftime('%d-%m-%Y')])
                                    #     elif fechadesde <= fecha_creacion and fecha_creacion <= fechahasta:
                                    #         listas_foros.append([nombre_foro, fecha_creacion.strftime('%d-%m-%Y')])
                                    #     listas_foros.sort(key=lambda clasesimp: (clasesimp[1]), reverse=True)
                                    for foro in resultados_foros:
                                        foros_calificados = 0
                                        foros_por_calificar=0
                                        titulo_topico = foro[1]
                                        asigname_topico = foro[2]
                                        titulo_foro = foro[3]
                                        asigname_foro = foro[4]
                                        # fecha_creacion = convertir_fecha(foro[6].strftime('%d-%m-%Y'))

                                        if not asigname_topico==None:
                                            sql_foros_posible="SELECT DISTINCT objeto.POINTS_POSSIBLE AS notaposible FROM GB_GRADABLE_OBJECT_T objeto INNER JOIN GB_GRADEBOOK_T curso ON objeto.GRADEBOOK_ID=curso.ID " \
                                                        "WHERE curso.GRADEBOOK_UID='" + id_sitio + "' AND objeto.NAME ='" + asigname_topico + "' AND (objeto.EXTERNAL_APP_NAME is null) AND objeto.REMOVED=0"
                                            sql_foro_puntos = querymysqlsakai(sql_foros_posible, True)
                                            default_name = 'SI' if sql_foro_puntos.__len__() > 0 else 'NO'
                                        else:
                                            default_name='No'

                                        # default_name = 'SI' if not foro[2] == None else 'NO'

                                        if foro[6]:
                                            fecha_finalizacion = convertir_fecha(foro[6].strftime('%d-%m-%Y'))
                                            fecha_apertura = convertir_fecha(foro[5].strftime('%d-%m-%Y'))
                                            # if fechadesde <= fecha_apertura and fecha_apertura <= fechahasta:
                                            if (fecha_finalizacion >= fechadesde and fecha_finalizacion <=  fechahasta):
                                            # if ( fecha_finalizacion <= fechahasta):
                                                if default_name == 'SI':
                                                    sql_foros_calificados = "SELECT calificacion.POINTS_EARNED,foro.NAME,calificacion.STUDENT_ID FROM GB_GRADE_RECORD_T calificacion INNER JOIN GB_GRADABLE_OBJECT_T foro ON calificacion.GRADABLE_OBJECT_ID=foro.ID " \
                                                                            "INNER JOIN GB_GRADEBOOK_T curso ON foro.GRADEBOOK_ID=curso.ID AND curso.NAME ='"+id_sitio+"' AND foro.NAME like '%Foro%' AND foro.NAME='"+foro[2]+"'"
                                                    resultado_foros_calificados = querymysqlsakai(sql_foros_calificados, True)

                                                    for calificados in resultado_foros_calificados:
                                                        sql_foros_aportados = "SELECT topicsset1_.ID, topicsset1_.TITLE AS titulo_topico, topicsset1_.DEFAULTASSIGNNAME AS asigname_topico, openforumi0_.TITLE AS titulo_foro, openforumi0_.DEFAULTASSIGNNAME AS asigname_foro, topicsset1_.OPEN_DATE AS fecha_apertura,topicsset1_.CLOSE_DATE AS fecha_cierre, " \
                                                                              "(SELECT COUNT(DISTINCT msj.CREATED_BY) FROM MFR_MESSAGE_T msj INNER JOIN MFR_TOPIC_T topico ON msj.surrogateKey=topico.ID  INNER JOIN MFR_OPEN_FORUM_T foro ON topico.of_surrogateKey= foro.ID INNER JOIN MFR_AREA_T areas ON foro.surrogateKey=areas.ID " \
                                                                              " WHERE areas.CONTEXT_ID='" + id_sitio + "' AND topico.ID= topicsset1_.ID AND topico.DEFAULTASSIGNNAME LIKE '%Foro%' AND msj.CREATED_BY='"+calificados[2]+"') AS cant_aportaciones " \
                                                                              " FROM MFR_OPEN_FORUM_T openforumi0_ LEFT OUTER JOIN MFR_TOPIC_T topicsset1_ ON openforumi0_.ID=topicsset1_.of_surrogateKey CROSS JOIN MFR_AREA_T areaimpl4_ WHERE openforumi0_.surrogateKey=areaimpl4_.ID AND areaimpl4_.CONTEXT_ID='" + id_sitio + "' AND topicsset1_.DEFAULTASSIGNNAME LIKE '%Foro%' AND topicsset1_.ID='"+str(foro[0])+"' "
                                                        foros_aportados = querymysqlsakai(sql_foros_aportados, True)

                                                        aportado= foros_aportados[0][7] if foros_aportados.__len__() > 0 else 0
                                                        if not calificados[0] == None:
                                                            if calificados[0] >= 0  and aportado > 0 and (calificados[1] == asigname_topico or titulo_topico in calificados[1]):
                                                                foros_calificados += 1
                                                            else:
                                                                titulo_foro = titulo_foro.replace(u'.', '')
                                                                if calificados[0] > 0 and aportado > 0 and  ((calificados[1] == asigname_foro or titulo_foro in calificados[1])):
                                                                    foros_calificados+=1

                                                    foros_por_calificar = foro[7] - foros_calificados if not foros_calificados > foro[7] else 0
                                                    total_foros_participados += foro[7]
                                                    total_foros_calificados += foros_calificados
                                                    listas_foros.append([titulo_topico,fecha_apertura.strftime('%d-%m-%Y'), fecha_finalizacion.strftime('%d-%m-%Y'),default_name,foro[7],foros_calificados,foros_por_calificar,resultados_total_estudiante_curso[0][0]])
                                    listas_foros.sort(key=lambda clasesimp: (clasesimp[1]),reverse=False)

                                                    # foros_calificados=0
                                        # elif fechadesde <= fecha_creacion and fecha_creacion <= fechahasta:
                                        #     listas_foros.append([titulo_topico, fecha_creacion.strftime('%d-%m-%Y')])
                                    # EXTRAER MENSAJES
                                    # sql_chats = "SELECT distinct chatchanne0_.CHANNEL_ID as idchannel, chatchanne0_.CREATION_DATE as fechacreacion, chatchanne0_.title, chatchanne0_.START_DATE as apertura, chatchanne0_.END_DATE as fin " \
                                    #             "FROM CHAT2_CHANNEL chatchanne0_ LEFT OUTER JOIN CHAT2_MESSAGE messages1_ ON chatchanne0_.CHANNEL_ID=messages1_.CHANNEL_ID " \
                                    #             "WHERE chatchanne0_.CONTEXT = '"+id_sitio+"' AND (CAST(messages1_.MESSAGE_DATE AS DATE) >= '"+fechadesde.strftime('%Y-%m-%d')+"' AND CAST(messages1_.MESSAGE_DATE AS DATE) <= '"+fechahasta.strftime('%Y-%m-%d')+"') order by chatchanne0_.CREATION_DATE desc"
                                    # resultados_chats = querymysqlsakai(sql_chats, True)
                                    # for chats in resultados_chats:
                                    #     id_chat = chats[0]
                                    #     sql_contador_chats = "select count(chatchanne0_.CHANNEL_ID) as contador_mensaje " \
                                    #                          "from CHAT2_CHANNEL chtchaanne0_ left outer join CHAT2_MESSAGE messages1_ on chatchanne0_.CHANNEL_ID=messages1_.CHANNEL_ID " \
                                    #                          "where chatchanne0_.CHANNEL_ID='"+id_chat+"' AND (CAST(messages1_.MESSAGE_DATE AS DATE) >= '"+fechadesde.strftime('%Y-%m-%d')+"' AND CAST(messages1_.MESSAGE_DATE AS DATE) <= '"+fechahasta.strftime('%Y-%m-%d')+"')"
                                    #     resultados_contador_chats = querymysqlsakai(sql_contador_chats, True)
                                    #     if chats[1].strftime('%m-%Y') == fechadesde.strftime('%m-%Y'):
                                    #         fecha_creacion = chats[1].strftime('%d-%m-%Y')
                                    #     else:
                                    #         fecha_creacion = fechadesde.strftime('%m-%Y')
                                    #     nombre_sala = chats[2]
                                    #     fecha_apertura = chats[3].strftime('%d-%m-%Y') if chats[3] else ''
                                    #     fecha_fin = chats[4].strftime('%d-%m-%Y') if chats[4] else ''
                                    #     listas_salas_chats.append([nombre_sala, fecha_creacion, fecha_apertura, fecha_fin, resultados_contador_chats[0][0]])
                                    listas_salas_chats = []
                                    sql_chats = "SELECT distinct chatchanne0_.CHANNEL_ID as idchannel, chatchanne0_.CREATION_DATE as fechacreacion, chatchanne0_.title, chatchanne0_.START_DATE as apertura, chatchanne0_.END_DATE as fin " \
                                                "FROM CHAT2_CHANNEL chatchanne0_ LEFT OUTER JOIN CHAT2_MESSAGE messages1_ ON chatchanne0_.CHANNEL_ID=messages1_.CHANNEL_ID " \
                                                "WHERE chatchanne0_.CONTEXT = '" + id_sitio + "' AND (CAST(messages1_.MESSAGE_DATE AS DATE) >= '" + fechadesde.strftime('%Y-%m-%d') + "' AND CAST(messages1_.MESSAGE_DATE AS DATE) <= '" + fechahasta.strftime('%Y-%m-%d') + "') order by chatchanne0_.CREATION_DATE desc"
                                    resultados_chats = querymysqlsakai(sql_chats, True)
                                    for chats in resultados_chats:
                                        id_chat = chats[0]
                                        sql_contador_chats = "select count(chatchanne0_.CHANNEL_ID) as contador_mensaje " \
                                                             "from CHAT2_CHANNEL chatchanne0_ left outer join CHAT2_MESSAGE messages1_ on chatchanne0_.CHANNEL_ID=messages1_.CHANNEL_ID " \
                                                             "where chatchanne0_.CHANNEL_ID='" + id_chat + "' AND (CAST(messages1_.MESSAGE_DATE AS DATE) >= '" + fechadesde.strftime('%Y-%m-%d') + "' AND CAST(messages1_.MESSAGE_DATE AS DATE) <= '" + fechahasta.strftime('%Y-%m-%d') + "')"
                                        sql_contador_chats_persona = sql_contador_chats + "and messages1_.OWNER='" + id_usuario + "' "
                                        resultados_contador_chats = querymysqlsakai(sql_contador_chats, True)
                                        resultados_contador_chats_persona = querymysqlsakai(sql_contador_chats_persona,True)
                                        nombre_sala = chats[2]
                                        if chats[1].strftime('%m-%Y') == fechadesde.strftime('%m-%Y'):
                                            fecha_creacion = chats[1].strftime('%d-%m-%Y')
                                        else:
                                            fecha_creacion = fechadesde.strftime('%m-%Y')
                                        fecha_apertura = chats[3].strftime('%d-%m-%Y') if chats[3] else ''
                                        fecha_fin = chats[4].strftime('%d-%m-%Y') if chats[4] else ''
                                        listas_salas_chats.append([nombre_sala, fecha_creacion, fecha_apertura, fecha_fin, resultados_contador_chats[0][0], resultados_contador_chats_persona[0][0]])
                                    # EXTRAER MENSAJES ENVIADOS
                                    sql_mensajes_enviados = "SELECT COUNT(privatemes0_.ID) " \
                                                            "FROM MFR_MESSAGE_T privatemes0_ " \
                                                            "left outer join MFR_PVT_MSG_USR_T recipients1_ on privatemes0_.ID=recipients1_.messageSurrogateKey  " \
                                                            "where privatemes0_.MESSAGE_DTYPE='PM' and  " \
                                                            "recipients1_.USER_ID='"+id_usuario+"' and  " \
                                                                                                "privatemes0_.CREATED_BY = '"+id_usuario+"' and " \
                                                                                                                                         "recipients1_.CONTEXT_ID='"+id_sitio+"' " \
                                                                                                                                                                              "and (CAST(privatemes0_.CREATED AS DATE) >= '"+fechadesde.strftime('%Y-%m-%d')+"' AND CAST(privatemes0_.CREATED AS DATE) <= '"+fechahasta.strftime('%Y-%m-%d')+"') "
                                    resultados_mensajes_enviados = querymysqlsakai(sql_mensajes_enviados, True)
                                    num_mensajes_enviados= int(resultados_mensajes_enviados[0][0]) if resultados_mensajes_enviados else 0
                                    # EXTRAER MENSAJES RECIBIDOS
                                    sql_mensajes_recibidos = "SELECT COUNT(privatemes0_.ID) " \
                                                             "FROM MFR_MESSAGE_T privatemes0_ " \
                                                             "left outer join MFR_PVT_MSG_USR_T recipients1_ on privatemes0_.ID=recipients1_.messageSurrogateKey  " \
                                                             "where privatemes0_.MESSAGE_DTYPE='PM' and  " \
                                                             "recipients1_.USER_ID='"+id_usuario+"' and not " \
                                                                                                 "privatemes0_.CREATED_BY = '"+id_usuario+"' and " \
                                                                                                                                          "recipients1_.CONTEXT_ID='"+id_sitio+"' " \
                                                                                                                                                                               "and (CAST(privatemes0_.CREATED AS DATE) >= '"+fechadesde.strftime('%Y-%m-%d')+"' AND CAST(privatemes0_.CREATED AS DATE) <= '"+fechahasta.strftime('%Y-%m-%d')+"') "
                                    # EXTRAER MENSAJES RECIBIDOS SIN LEER
                                    sql_mensajes_recibidos_sin_leer = sql_mensajes_recibidos + "and recipients1_.READ_STATUS=0;"
                                    resultados_mensajes_recibidos_sin_leer = querymysqlsakai(sql_mensajes_recibidos_sin_leer, True)
                                    num_mensajes_recibidos_sin_leer = int(resultados_mensajes_recibidos_sin_leer[0][0]) if resultados_mensajes_recibidos_sin_leer else 0
                                    # EXTRAER MENSAJES RECIBIDOS LEIDOS
                                    sql_mensajes_recibidos_leidos = sql_mensajes_recibidos + "and recipients1_.READ_STATUS=1;"
                                    resultados_mensajes_recibidos_leidos = querymysqlsakai(sql_mensajes_recibidos_leidos, True)
                                    num_mensajes_recibidos_leidos = int(resultados_mensajes_recibidos_leidos[0][0]) if resultados_mensajes_recibidos_leidos else 0
                                    listas_materias.append([nombre_curso, listas_tareas, listas_foros, listas_salas_chats, num_mensajes_enviados, num_mensajes_recibidos_sin_leer, num_mensajes_recibidos_leidos, num_mensajes_recibidos_sin_leer + num_mensajes_recibidos_leidos])
                            # EXTRAER AUTOR
                            if id_sitio:
                                sql_autor="SELECT b.LAST_NAME, b.FIRST_NAME, " \
                                          "(SELECT CASE WHEN SRR.ROLE_NAME = '"+id_rol_autor.__str__()+"' THEN SRR.ROLE_NAME ELSE '' END " \
                                                                                                       "FROM SAKAI_REALM_RL_GR SRRG " \
                                                                                                       "INNER JOIN SAKAI_REALM SR ON SRRG.REALM_KEY = SR.REALM_KEY " \
                                                                                                       "INNER JOIN SAKAI_REALM_ROLE SRR ON SRRG.ROLE_KEY = SRR.ROLE_KEY " \
                                                                                                       "WHERE SR.REALM_ID = CONCAT ('/site/', site.SITE_ID) AND SRRG.USER_ID = c.USER_ID AND SRRG.ACTIVE = '1') AS rol " \
                                                                                                       "FROM SAKAI_USER_ID_MAP AS a " \
                                                                                                       "INNER JOIN SAKAI_USER AS b ON b.USER_ID=a.USER_ID " \
                                                                                                       "INNER JOIN SAKAI_SITE_USER AS c ON c.USER_ID=a.USER_ID " \
                                                                                                       "INNER JOIN SAKAI_SITE AS site ON site.SITE_ID = c.SITE_ID " \
                                                                                                       "WHERE site.SITE_ID = '"+id_sitio+"' AND site.IS_SOFTLY_DELETED = 0 AND site.PUBVIEW = '1' and not b.USER_ID = 'admin' order by rol desc LIMIT 1"
                                resultados_autor = querymysqlsakai(sql_autor, True)
                                if resultados_autor:
                                    id_rol_aut = resultados_autor[0][2]
                                    if id_rol_aut:
                                        if id_rol_aut.strip().lower() == id_rol_autor.strip().lower():
                                            apellido_autor = resultados_autor[0][0]
                                            nombre_autor = resultados_autor[0][1]
                            data['apellido_autor'] = apellido_autor
                            data['nombre_autor'] = nombre_autor

                            # ----------------------------CREACION POR HTML------------------------------

                            data['listas_materias'] = listas_materias
                            data['lista_carreras'] = lista_carreras
                            data['lista_paralelos'] = lista_paralelos
                            data['total_enviados'] = total_enviados
                            data['total_calificados'] = total_calificados
                            data['total_foros_calificados'] = total_foros_calificados
                            data['total_foros_participados'] = total_foros_participados
                            data['porcentaje_cumplimiento'] = 0
                            data['porcentaje_cumplimiento_foros'] = '-'
                            if total_enviados>0:
                                data['porcentaje_cumplimiento'] = null_to_decimal((total_calificados*100)/total_enviados,2)
                            if total_foros_participados > 0:
                                if total_foros_calificados  > total_foros_participados:
                                    data['porcentaje_cumplimiento_foros']= 100
                                else:
                                    data['porcentaje_cumplimiento_foros'] = null_to_decimal((total_foros_calificados * 100) / total_foros_participados, 2)
                            return conviert_html_to_pdf('sakai/informeactividad.html', {'pagesize': 'A4', 'data': data})

                            # ---------------------------CREACION DE REPORTE-----------------------------

                            # add_titulo_reportlab(descripcion='U N I V E R S I D A D  E S T A T A L  D E  M I L A G R O')
                            # add_titulo_reportlab(descripcion='SECCIÓN DE ADMISIÓN Y NIVELACIÓN')
                            # add_titulo_reportlab(descripcion='REPORTE DE SEGUIMIENTO Y CONTROL DE ACTIVIDADES')
                            # add_titulo_reportlab(descripcion=u'DESDE: %s HASTA: %s' % (fechadesde.strftime('%d-%m-%Y'), fechahasta.strftime('%d-%m-%Y')))
                            # # ----------DATOS GENERALES----------
                            # add_titulo_reportlab(descripcion='DATOS PERSONALES', alineacion=TA_LEFT)
                            # encabezado_datos_personales = [('Nombre del profesor', 'Carrera', 'Paralelo')]
                            # cadena_carreras = ''
                            # for carrera in lista_carreras:
                            #     cadena_carreras = carrera + ', '
                            # cadena_paralelos = ''
                            # for paralelo in lista_paralelos:
                            #     cadena_paralelos = paralelo + ', '
                            # detalle_datospersonales = [(u'%s %s'%(apellidos.__str__(), nombres.__str__()), cadena_carreras[:cadena_carreras.__len__()-2] if cadena_carreras else '', cadena_paralelos[:cadena_paralelos.__len__()-2] if cadena_paralelos else '')]
                            # ancho_datospersonales = [175, 175, 175]
                            # left_center_datospersonales = [False, False, False]
                            # add_tabla_reportlab(encabezado=encabezado_datos_personales, detalles=detalle_datospersonales, anchocol=ancho_datospersonales, cabecera_left_center=left_center_datospersonales, detalle_left_center=left_center_datospersonales)
                            # # ----------MATERIAS----------
                            # for materia in listas_materias:
                            #     add_titulo_reportlab(descripcion=materia[0].__str__(), alineacion=TA_LEFT, beforeespacio=5)
                            #     # -----TAREAS-----
                            #     encabezado_tareas = [('Tarea', 'Fec. inicio', 'Tot. est.', 'Tot. env.', 'Tot. env. borrador', 'Tot. no env.', 'Tot. calif.', 'Tot. calif. borrador', 'Tot. no calif.')]
                            #     detalle_tareas = []
                            #     for tarea in materia[1]:
                            #         detalle_tareas.append([tarea[0].__str__(), tarea[1].__str__(), tarea[2].__str__(), tarea[3].__str__(), tarea[4].__str__(), tarea[5].__str__(), tarea[6].__str__(), tarea[7].__str__(), tarea[8].__str__()])
                            #     ancho_tareas = [138, 65, 40, 40, 55, 45, 40, 55, 45]
                            #     left_center_tareas = [False, True, True, True, True, True, True, True, True]
                            #     add_tabla_reportlab(encabezado=encabezado_tareas, detalles=detalle_tareas, anchocol=ancho_tareas, cabecera_left_center=left_center_tareas, detalle_left_center=left_center_tareas)
                            #     # -----FOROS-----
                            #     lista_foros = materia[2]
                            #     encabezado_tareas = [('Foro', 'Fecha inicio')]
                            #     detalle_foros = []
                            #     ancho_foros = [425, 100]
                            #     left_center_foros = [False, True]
                            #     for foro in lista_foros:
                            #         detalle_foros.append([foro[0].__str__(), foro[1].__str__()])
                            #     add_tabla_reportlab(encabezado=encabezado_tareas, detalles=detalle_foros, anchocol=ancho_foros, cabecera_left_center=left_center_foros, detalle_left_center=left_center_foros)
                            #     # -----SALA CHAT-----
                            #     lista_chats = materia[3]
                            #     encabezado_chats = [('Sala chat', 'Fecha creación', 'Fecha apertura', 'Fecha fin', 'No. chat')]
                            #     detalle_chats = []
                            #     for chat in lista_chats:
                            #         detalle_chats.append([chat[0].__str__(), chat[1].__str__(), chat[2].__str__(), chat[3].__str__(), chat[4].__str__()])
                            #     ancho_chats = [205, 80, 80, 80, 80]
                            #     left_center_chats = [False, True, True, True, True]
                            #     add_tabla_reportlab(encabezado=encabezado_chats, detalles=detalle_chats, anchocol=ancho_chats, cabecera_left_center=left_center_chats, detalle_left_center=left_center_chats)
                            #     # -----MENSAJES ENVIADOS-----
                            #     encabezado_enviados = [['Mensajes enviados']]
                            #     detalle_enviados = [[materia[4].__str__()]]
                            #     ancho_enviados = [525]
                            #     left_center_enviados = [True]
                            #     add_tabla_reportlab(encabezado=encabezado_enviados, detalles=detalle_enviados, anchocol=ancho_enviados, cabecera_left_center=left_center_enviados, detalle_left_center=left_center_enviados)
                            #     # -----MENSAJES RECIBIDOS-----
                            #     encabezado_recibidos = [('Mensajes recibidos sin leer', 'Mensajes recibidos leidos', 'Total')]
                            #     detalle_recibidos = [(materia[5].__str__() if materia[5] else 0, materia[6].__str__() if materia[6] else 0, materia[7].__str__() if materia[7] else 0)]
                            #     ancho_recibidos = [175, 175, 175]
                            #     left_center_recibidos = [True, True, True]
                            #     add_tabla_reportlab(encabezado=encabezado_recibidos, detalles=detalle_recibidos, anchocol=ancho_recibidos, cabecera_left_center=left_center_recibidos, detalle_left_center=left_center_recibidos)
                            #     # -----FIRMA-----
                            #     add_titulo_reportlab(descripcion='FIRMAS DE RESPONSABILIDAD', alineacion=TA_LEFT)
                            #     encabezado_firmas = [('Elaborado por:', 'Revisado por:', 'Aprobado por:')]
                            #     detalle_firmas = [(materia[5].__str__() if materia[5] else 0, materia[6].__str__() if materia[6] else 0,  materia[7].__str__() if materia[7] else 0)]
                            #     ancho_recibidos = [175, 175, 175]
                            #     left_center_recibidos = [True, True, True]
                            #     add_tabla_reportlab(encabezado=encabezado_recibidos, detalles=detalle_recibidos, anchocol=ancho_recibidos, cabecera_left_center=left_center_recibidos, detalle_left_center=left_center_recibidos)
                            # return generar_pdf_reportlab()
                except Exception as ex:
                    return HttpResponseRedirect("/campusvirtual?info=No se puede generar el informe de actividades virtual")

            return HttpResponseRedirect("/campusvirtual?info=No se puede generar el informe de actividades virtual")
    else:
        if 'info' in request.GET:
            data['mensaje'] = request.GET['info']
        return render(request, "sakai/adddatosinforme.html", data)
