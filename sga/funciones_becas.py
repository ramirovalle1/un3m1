import io

import xlsxwriter
from datetime import datetime, timedelta
from django.db import connection
from django.http import HttpResponse

from sga.models import BecaSolicitud, BecaSolicitudRecorrido, Notificacion, miinstitucion


def listado_mejores_puntuados_query(periodo_anterior, periodo_actual, excluir_inscripcion_2carrera_con_matricula=''):
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        *
    FROM 
            (SELECT 
                i.id "Incripcion_id",
                mat.id "Matricula_id",
                (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
                i.coordinacion_id "Coordinacion_id",
                i.carrera_id "Carrera_id",
                mat.nivelmalla_id "NivelMalla_id",
                record_qu."promedio",
                ROW_NUMBER() OVER ( 
                    PARTITION BY i.coordinacion_id, i.carrera_id, mat.nivelmalla_id
                    ORDER BY i.coordinacion_id, i.carrera_id, mat.nivelmalla_id, record_qu."promedio" DESC
                )"Orden"
            FROM 
                sga_inscripcion i
                INNER JOIN sga_persona p ON p.id=i.persona_id
                INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
               INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
               INNER JOIN sga_matriculagruposocioeconomico matg ON ( matg.matricula_id=mat.id 
                                                                 AND matg.tipomatricula=1
                                                                 AND matg."status")
    
               INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
                INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
                INNER JOIN sga_malla mall ON mall.id=im.malla_id
               LEFT JOIN LATERAL(
                   SELECT	 
                       count(sa.asignatura_id) "cantidad", 
                       sum(sa.creditos) "creditos"
                   FROM	
                       sga_asignaturamalla sa 
                   WHERE	 
                       sa.malla_id=im.malla_id 
                       and sa.nivelmalla_id = mat.nivelmalla_id
                       and sa.status
                       and not sa.opcional
                       and sa.itinerario IN(NULL,0,i.itinerario)
               )malla_materias on True
    
                LEFT JOIN LATERAL(
                 select 
                     SUM(rc.creditos) "creditos_aprobados", 
                     ROUND(AVG(rc.nota),2) "promedio",
                     COUNT(rc.id) "cantidad_asigantura_aprobadas"			
                 FROM 
                     sga_recordacademico rc
                     INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
                 WHERE 
                     rc.status
                     AND rc.inscripcion_id=i.id
                     AND rc.aprobada
                     AND rc.matriculas=1
                     AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                     AND	NOT asigm_rc.opcional
                     AND rc.asignatura_id IN(select 
                                                 sa.asignatura_id
                                             from 
                                                 sga_asignaturamalla sa 
                                             where 
                                                 sa.malla_id=im.malla_id
                                                 and sa.nivelmalla_id =mat.nivelmalla_id
                                                 and sa.status)
                )record_qu on TRUE
            WHERE 
                mat."status"
                AND mat.bloqueomatricula=False
                AND pu.visible
                AND pu."status"
                AND niv.periodo_id={periodo_anterior.id}
                AND mall.vigente
                AND i.coordinacion_id IN(1,2,3,4,5)
                AND NOT	mat.retiradomatricula
                AND im."status"
                AND NOT p.ppl
                AND p.pais_id=1
                AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
    
               /*MATRICULADO EN EL PERIODO ACTUAL*/
               AND EXISTS(SELECT 	
                             mat_a.nivelmalla_id
                         FROM	
                             sga_matricula mat_a
                             INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id and niv_a.periodo_id={periodo_actual.id})
                             INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                     matgs_a.matricula_id=mat_a.id
                                     AND matgs_a.tipomatricula=1
                                     AND matgs_a."status"
                             ) 
                         WHERE 
                             mat_a.retiradomatricula=false
                             and mat_a.inscripcion_id=i.id
                             AND mat_a.status
                             and not exists(
                                 select id 
                                 from sga_retiromatricula 
                                 rtm 
                                 where 
                                     rtm.matricula_id=mat_a.id 
                                     AND rtm."status"
                             ) 
               )
                /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
                AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                                FROM sga_inscripcion insc	
                                    INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                                    INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                                WHERE 
                                    insc.id=i.id 
                                    AND his_rc_g.aprobada=FALSE
                                    AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                                    and not asim_g.opcional
                                GROUP BY his_rc_g.recordacademico_id
                                HAVING COUNT(his_rc_g.id)>0)=FALSE
                /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
                AND EXISTS(
                       SELECT 
                           mattit 
                       FROM  
                           sga_matriculatitulacion mattit 
                           INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                       WHERE  
                           i_ti.persona_id=p.id
                           AND mattit."status" 
                           AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
                )=FALSE
                /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
                AND NOT EXISTS(
                    SELECT id FROM sagest_rubro WHERE 
                    persona_id=p.id
                    AND fechavence>=NOW()
                  AND cancelado=False 
                    AND status=True
                )
                /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
                AND NOT EXISTS(
                    select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
                )
                /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
                AND NOT EXISTS(SELECT id 
                            FROM 
                                sga_retirocarrera ret_carr WHERE  (ret_carr.inscripcion_id=i.id AND ret_carr."status")
                              )
                /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
                AND exists(SELECT  FROM (SELECT 
                        COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                        COUNT(mtas_aux.id) total_general
                    FROM 
                        sga_materiaasignada mtas_aux
                        INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                        INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
                    WHERE	 
                        mtas_aux.status
                        AND not mtas_aux.retiramateria
                        AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
                /*VALIDACIÓN QUE No ser becario en otra institución pública */
                AND NOT EXISTS(
                    SELECT id FROM sga_becapersona 
                    where 
                        persona_id=p.id
                        and status
                        and fechainicio >= Now()::date and Now()::date <=fechafin
                        and tipoinstitucion=1
                        and verificado
                )
                /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
                AND NOT EXISTS(
                    SELECT san.id FROM sga_sacionestudiante san
                    inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
                    where 
                        i_san.persona_id=p.id
                        and san.status
                        and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                             or san.indifinido
                             or san.periodo_id=niv.periodo_id
                            )
    
                )
                /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
                {excluir_inscripcion_2carrera_con_matricula}
                
                /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
                AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
                
                /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
                AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
            ORDER BY i.coordinacion_id, i.carrera_id, mat.nivelmalla_id, record_qu."promedio" DESC
            )listado_estudiantes
            WHERE 
                listado_estudiantes."Orden" = 1
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def listado_artistas_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        mat.id "Codigo Matricula",
        i.id "Codigo Inscripcion", 
        i.coordinacion_id "Coordinacion_id" ,
        i.carrera_id "Carrera_id" ,
        artp.id "Artista_id",
        (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
        p.cedula "Cedula",
        record_qu."promedio",
        ROW_NUMBER() OVER ( 
            ORDER BY record_qu."promedio" DESC
        )"Orden"
    FROM 
        sga_inscripcion i
        INNER JOIN sga_persona p ON p.id=i.persona_id
        INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
        INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
        INNER JOIN sga_matriculagruposocioeconomico matg ON (matg.matricula_id=mat.id  AND matg.tipomatricula=1 AND matg."status")
        INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
        INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
        INNER JOIN sga_malla mall ON mall.id=im.malla_id
        INNER JOIN  sga_artistapersona artp ON (artp.persona_id=p.id AND artp.status and artp.estadoarchivo=2)
        LEFT JOIN LATERAL(
        select 
            count(sa.asignatura_id) "cantidad", 
            sum(sa.creditos) "creditos"
        from 
            sga_asignaturamalla sa 
        where 
            sa.malla_id=mall.id 
            and sa.nivelmalla_id =mat.nivelmalla_id
            and sa.status
            and not sa.opcional
            and sa.itinerario IN(NULL,0,i.itinerario)
        )malla_materias on True
        LEFT JOIN LATERAL(
            select 
                SUM(rc.creditos) "creditos_aprobados", 
                ROUND(AVG(rc.nota),2) "promedio",
                COUNT(rc.id) "cantidad_asigantura_aprobadas"			
            FROM 
                sga_recordacademico rc
                INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
            WHERE 
                rc.status
                AND rc.inscripcion_id=i.id
                AND rc.aprobada
                AND rc.matriculas=1
                AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                and not asigm_rc.opcional
                AND rc.asignatura_id IN(select 
                                            sa.asignatura_id
                                        from 
                                            sga_asignaturamalla sa 
                                        where 
                                            sa.malla_id=mall.id 
                                            and sa.nivelmalla_id =mat.nivelmalla_id
                                            and sa.status)
        )record_qu on TRUE
    WHERE 
        mat."status"
        {exclude_query}
        and mat.bloqueomatricula=False 
        AND record_qu."promedio" >= 70
        AND i.coordinacion_id IN(1,2,3,4,5)
        AND niv.periodo_id={periodo_anterior.id}
        AND pu.visible 
        AND pu."status"
        AND mall.vigente
        AND NOT	mat.retiradomatricula
        AND im."status"
        AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
        --AND piu."status"
        /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
        AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                        FROM sga_inscripcion insc	
                            INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                            INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                        WHERE 
                            insc.id=i.id 
                            AND his_rc_g.aprobada=FALSE
                            AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                            and not asim_g.opcional
                        GROUP BY his_rc_g.recordacademico_id
                        HAVING COUNT(his_rc_g.id)>0)=FALSE
                        
        /*MATRICULADO EN EL PERIODO ACTUAL*/
        AND EXISTS(SELECT 	
                            mat_a.nivelmalla_id
                        FROM	
                            sga_matricula mat_a
                            INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                and niv_a.periodo_id={periodo_actual.id}
                                                                                )
                            INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                    matgs_a.matricula_id=mat_a.id
                                    AND matgs_a.tipomatricula=1
                                    AND matgs_a."status"
                            ) 
                        WHERE 
                            mat_a.retiradomatricula=false
                            and mat_a.inscripcion_id=i.id
                            AND mat_a.status
                            and not exists(
                                select id 
                                from sga_retiromatricula 
                                rtm 
                                where 
                                    rtm.matricula_id=mat_a.id 
                                    AND rtm."status"
                            ) 
        )
        /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
        AND EXISTS(
                   SELECT 
                       mattit 
                   FROM  
                       sga_matriculatitulacion mattit 
                       INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                   WHERE  
                       i_ti.persona_id=p.id
                       AND mattit."status" 
                       AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
        )=FALSE 
        /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
        AND NOT EXISTS(
            SELECT id FROM sagest_rubro WHERE 
            persona_id=p.id
            AND fechavence>=NOW()
          AND cancelado=False 
            AND status=True
        )
        /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
        AND NOT EXISTS(
            select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
        )
        /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
        AND NOT EXISTS(SELECT id 
                    FROM 
                        sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
        /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
        AND exists(SELECT  FROM (SELECT 
                COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                COUNT(mtas_aux.id) total_general
            FROM 
                sga_materiaasignada mtas_aux
                INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
            WHERE	 
                mtas_aux.status
                AND not mtas_aux.retiramateria
                AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
        /*VALIDACIÓN QUE No ser becario en otra institución pública */
        AND NOT EXISTS(
            SELECT id FROM sga_becapersona 
            where 
                persona_id=p.id
                and status
                and fechainicio >= Now()::date and Now()::date <=fechafin
                and tipoinstitucion=1
                and verificado
        )
        /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
        AND NOT EXISTS(
            SELECT san.id FROM sga_sacionestudiante san
            inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
            where 
                i_san.persona_id=p.id
                and san.status
                and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                     or san.indifinido
                     or san.periodo_id=niv.periodo_id
                    )
            
        )
        /*VALIDACIÓN DE SER ECUATORIANO O RESIDENCIA EN EL ECUADOR*/
        AND p.pais_id=1
        /*VALIDACIÓN DE EXCLUIR PPL*/
        AND not p.ppl
        /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
        {excluir_inscripcion_2carrera_con_matricula}
        
        /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
        
        /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
    ORDER BY record_qu."promedio" DESC
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results



def listado_discapacitados_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        mat.id "Codigo Matricula",
        i.id "Codigo Inscripcion",  
        co.nombre "Coordinacion",
        co.id "Coordinacion_id" ,
        ca.id "Carrera_id" ,
        ca.nombre "Carrera",
        piu.tipodiscapacidad_id "TipoDiscapacidad_id",
        piu.porcientodiscapacidad "PorcentajeDiscapacidad",
        piu.carnetdiscapacidad "CarneDiscapacidad",
        moda.nombre "Modalidad",
        (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
        sex.nombre "Sexo",
        p.cedula "Cedula",
        record_qu."promedio",
        ROW_NUMBER() OVER ( 
            ORDER BY record_qu."promedio" DESC
        )"Orden"
    FROM 
        sga_inscripcion i
        INNER JOIN sga_persona p   ON p.id=i.persona_id
        LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
        LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
        LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
        INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
        INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
        INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
        LEFT JOIN sga_raza raz on raz.id = piu.raza_id
        LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
        INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
        INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
        INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
        INNER JOIN sga_matriculagruposocioeconomico matg ON ( matg.matricula_id=mat.id 
                                                              AND matg.tipomatricula=1
                                                              AND matg."status")
        INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
        INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
        INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
        INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
        INNER JOIN sga_malla mall ON mall.id=im.malla_id
        LEFT JOIN LATERAL(
        select 
            count(sa.asignatura_id) "cantidad", 
            sum(sa.creditos) "creditos"
        from 
            sga_asignaturamalla sa 
        where 
            sa.malla_id=mall.id 
            and sa.nivelmalla_id =nivm.id
            and sa.status
            and not sa.opcional
            and sa.itinerario IN(NULL,0,i.itinerario)
        )malla_materias on True
        LEFT JOIN LATERAL(
            select 
                SUM(rc.creditos) "creditos_aprobados", 
                ROUND(AVG(rc.nota),2) "promedio",
                COUNT(rc.id) "cantidad_asigantura_aprobadas"			
            FROM 
                sga_recordacademico rc
                INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
            WHERE 
                rc.status
                AND rc.inscripcion_id=i.id
                AND rc.aprobada
                AND rc.matriculas=1
                AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                and not asigm_rc.opcional
                AND rc.asignatura_id IN(select 
                                            sa.asignatura_id
                                        from 
                                            sga_asignaturamalla sa 
                                        where 
                                            sa.malla_id=mall.id 
                                            and sa.nivelmalla_id =nivm.id
                                            and sa.status)
        )record_qu on TRUE
    WHERE 
        mat."status"
        {exclude_query}
        and mat.bloqueomatricula=False 
        AND piu.tienediscapacidad
        --AND piu.verificadiscapacidad
        AND piu.estadoarchivodiscapacidad=2
        AND record_qu."promedio" >= 75
        AND co.id IN(1,2,3,4,5)
        AND peri.id={periodo_anterior.id}
        AND pu.visible 
        AND pu."status"
        AND mall.vigente
        AND NOT	mat.retiradomatricula
        AND im."status"
        AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
        AND piu."status"
        --and asignatura_matri.total_general !=asignatura_matri.total_ingles
        /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
        AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                        FROM sga_inscripcion insc	
                            INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                            INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                        WHERE 
                            insc.id=i.id 
                            AND his_rc_g.aprobada=FALSE
                            AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                            and not asim_g.opcional
                        GROUP BY his_rc_g.recordacademico_id
                        HAVING COUNT(his_rc_g.id)>0)=FALSE
                        
        /*MATRICULADO EN EL PERIODO ACTUAL*/
        AND EXISTS(SELECT 	
                            mat_a.nivelmalla_id
                        FROM	
                            sga_matricula mat_a
                            INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                and niv_a.periodo_id={periodo_actual.id}
                                                                                )
                            INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                    matgs_a.matricula_id=mat_a.id
                                    AND matgs_a.tipomatricula=1
                                    AND matgs_a."status"
                            ) 
                            --LEFT JOIN sga_retiromatricula rtm ON (rtm.matricula_id=mat_a.id AND rtm."status")
                        WHERE 
                            mat_a.retiradomatricula=false
                            and mat_a.inscripcion_id=i.id
                            AND mat_a.status
                            --AND rtm.id IS NULL
                            and not exists(
                                select id 
                                from sga_retiromatricula 
                                rtm 
                                where 
                                    rtm.matricula_id=mat_a.id 
                                    AND rtm."status"
                            ) 
        )
        /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
        AND EXISTS(
                   SELECT 
                       mattit 
                   FROM  
                       sga_matriculatitulacion mattit 
                       INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                   WHERE  
                       i_ti.persona_id=p.id
                       AND mattit."status" 
                       AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
        )=FALSE 
        /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
        AND NOT EXISTS(
            SELECT id FROM sagest_rubro WHERE 
            persona_id=p.id
            AND fechavence>=NOW()
          AND cancelado=False 
            AND status=True
        )
        /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
        AND NOT EXISTS(
            select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
        )
        /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
        AND NOT EXISTS(SELECT id 
                    FROM 
                        sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
        /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
        AND exists(SELECT  FROM (SELECT 
                COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                COUNT(mtas_aux.id) total_general
            FROM 
                sga_materiaasignada mtas_aux
                INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
            WHERE	 
                mtas_aux.status
                AND not mtas_aux.retiramateria
                AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
        /*VALIDACIÓN QUE No ser becario en otra institución pública */
        AND NOT EXISTS(
            SELECT id FROM sga_becapersona 
            where 
                persona_id=p.id
                and status
                and fechainicio >= Now()::date and Now()::date <=fechafin
                and tipoinstitucion=1
                and verificado
        )
        /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
        AND NOT EXISTS(
            SELECT san.id FROM sga_sacionestudiante san
            inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
            where 
                i_san.persona_id=p.id
                and san.status
                and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                     or san.indifinido
                     or san.periodo_id=peri.id
                    )
            
        )
        AND p.pais_id=1
        /*VALIDACIÓN DE EXCLUIR PPL*/
        AND not p.ppl
        /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
        {excluir_inscripcion_2carrera_con_matricula}
             
        /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
        
        /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
    ORDER BY record_qu."promedio" DESC
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def listado_enfcatastroficas_discap_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
        SET statement_timeout = 3600000; 
        SELECT 
            mat.id "Codigo Matricula",
            i.id "Codigo Inscripcion",  
            co.nombre "Coordinacion",
            co.id "Coordinacion_id" ,
            ca.id "Carrera_id" ,
            ca.nombre "Carrera",
            piu.tipodiscapacidad_id "TipoDiscapacidad_id",
            piu.porcientodiscapacidad "PorcentajeDiscapacidad",
            piu.carnetdiscapacidad "CarneDiscapacidad",
            moda.nombre "Modalidad",
            (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
            sex.nombre "Sexo",
            p.cedula "Cedula",
            record_qu."promedio",
            ROW_NUMBER() OVER ( 
                ORDER BY record_qu."promedio" DESC
            )"Orden"
        FROM 
            sga_inscripcion i
            INNER JOIN sga_persona p   ON p.id=i.persona_id
            LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
            LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
            LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
            INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
            INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
            INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
            LEFT JOIN sga_raza raz on raz.id = piu.raza_id
            LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
            INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
            INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
            INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
            INNER JOIN sga_matriculagruposocioeconomico matg ON ( matg.matricula_id=mat.id 
                                                                  AND matg.tipomatricula=1
                                                                  AND matg."status")
            INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
            INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
            INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
            INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
            INNER JOIN sga_malla mall ON mall.id=im.malla_id
            LEFT JOIN LATERAL(
            select 
                count(sa.asignatura_id) "cantidad", 
                sum(sa.creditos) "creditos"
            from 
                sga_asignaturamalla sa 
            where 
                sa.malla_id=mall.id 
                and sa.nivelmalla_id =nivm.id
                and sa.status
                and not sa.opcional
                and sa.itinerario IN(NULL,0,i.itinerario)
            )malla_materias on True
            LEFT JOIN LATERAL(
                select 
                    SUM(rc.creditos) "creditos_aprobados", 
                    ROUND(AVG(rc.nota),2) "promedio",
                    COUNT(rc.id) "cantidad_asigantura_aprobadas"			
                FROM 
                    sga_recordacademico rc
                    INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
                WHERE 
                    rc.status
                    AND rc.inscripcion_id=i.id
                    AND rc.aprobada
                    AND rc.matriculas=1
                    AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                    and not asigm_rc.opcional
                    AND rc.asignatura_id IN(select 
                                                sa.asignatura_id
                                            from 
                                                sga_asignaturamalla sa 
                                            where 
                                                sa.malla_id=mall.id 
                                                and sa.nivelmalla_id =nivm.id
                                                and sa.status)
            )record_qu on TRUE
        WHERE 
            mat."status"
            {exclude_query}
            and mat.bloqueomatricula=False 
            --AND piu.tienediscapacidad
            --AND piu.verificadiscapacidad
            --AND piu.estadoarchivodiscapacidad=2
            AND record_qu."promedio" >= 75
            AND co.id IN(1,2,3,4,5)
            AND peri.id={periodo_anterior.id}
            AND pu.visible 
            AND pu."status"
            AND mall.vigente
            AND NOT	mat.retiradomatricula
            AND im."status"
            AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
            AND piu."status"
            --and asignatura_matri.total_general !=asignatura_matri.total_ingles
            /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
            AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                            FROM sga_inscripcion insc	
                                INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                                INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                            WHERE 
                                insc.id=i.id 
                                AND his_rc_g.aprobada=FALSE
                                AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                                and not asim_g.opcional
                            GROUP BY his_rc_g.recordacademico_id
                            HAVING COUNT(his_rc_g.id)>0)=FALSE

            /*MATRICULADO EN EL PERIODO ACTUAL*/
            AND EXISTS(SELECT 	
                                mat_a.nivelmalla_id
                            FROM	
                                sga_matricula mat_a
                                INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                    and niv_a.periodo_id={periodo_actual.id}
                                                                                    )
                                INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                        matgs_a.matricula_id=mat_a.id
                                        AND matgs_a.tipomatricula=1
                                        AND matgs_a."status"
                                ) 
                                --LEFT JOIN sga_retiromatricula rtm ON (rtm.matricula_id=mat_a.id AND rtm."status")
                            WHERE 
                                mat_a.retiradomatricula=false
                                and mat_a.inscripcion_id=i.id
                                AND mat_a.status
                                --AND rtm.id IS NULL
                                and not exists(
                                    select id 
                                    from sga_retiromatricula 
                                    rtm 
                                    where 
                                        rtm.matricula_id=mat_a.id 
                                        AND rtm."status"
                                ) 
            )
            /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
            AND EXISTS(
                       SELECT 
                           mattit 
                       FROM  
                           sga_matriculatitulacion mattit 
                           INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                       WHERE  
                           i_ti.persona_id=p.id
                           AND mattit."status" 
                           AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
            )=FALSE 
            /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
            AND NOT EXISTS(
                SELECT id FROM sagest_rubro WHERE 
                persona_id=p.id
                AND fechavence>=NOW()
              AND cancelado=False 
                AND status=True
            )
            /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
            AND NOT EXISTS(
                select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
            )
            /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
            AND NOT EXISTS(SELECT id 
                        FROM 
                            sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
            /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
            AND exists(SELECT  FROM (SELECT 
                    COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                    COUNT(mtas_aux.id) total_general
                FROM 
                    sga_materiaasignada mtas_aux
                    INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                    INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
                WHERE	 
                    mtas_aux.status
                    AND not mtas_aux.retiramateria
                    AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
            /*VALIDACIÓN QUE No ser becario en otra institución pública */
            AND NOT EXISTS(
                SELECT id FROM sga_becapersona 
                where 
                    persona_id=p.id
                    and status
                    and fechainicio >= Now()::date and Now()::date <=fechafin
                    and tipoinstitucion=1
                    and verificado
            )
            /*VALIDACIÓN de enfermedad catastrofica */
            AND EXISTS(
                SELECT pe.id FROM sga_personaenfermedad as pe
                INNER JOIN sga_persona per ON per.id = pe.persona_id
                INNER JOIN med_enfermedad med ON med.id = pe.enfermedad_id
                WHERE med.tipo_id=5 AND pe.estadoarchivo = 2 AND persona_id=p.id
            )
            /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
            AND NOT EXISTS(
                SELECT san.id FROM sga_sacionestudiante san
                inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
                where 
                    i_san.persona_id=p.id
                    and san.status
                    and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                         or san.indifinido
                         or san.periodo_id=peri.id
                        )

            )
            AND p.pais_id=1
            /*VALIDACIÓN DE EXCLUIR PPL*/
            AND not p.ppl
            /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
            {excluir_inscripcion_2carrera_con_matricula}

            /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
            AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )

            /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
            AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
        ORDER BY record_qu."promedio" DESC
        """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results



def listado_deportistas_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        mat.id "Codigo Matricula",
        i.id "Codigo Inscripcion",  
        co.nombre "Coordinacion",
        co.id "Coordinacion_id" ,
        ca.id "Carrera_id" ,
        ca.nombre "Carrera",
        dp.id "Deportista_id",
        moda.nombre "Modalidad",
        (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
        sex.nombre "Sexo",
        p.cedula "Cedula",
        record_qu."promedio",
        ROW_NUMBER() OVER ( 
            ORDER BY record_qu."promedio" DESC
        )"Orden"
    FROM 
        sga_inscripcion i
        INNER JOIN sga_persona p ON p.id=i.persona_id
        LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
        LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
        LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
        INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
        INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
        INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
        LEFT JOIN sga_raza raz on raz.id = piu.raza_id
        LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
        INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
        INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
        INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
        INNER JOIN sga_matriculagruposocioeconomico matg ON ( matg.matricula_id=mat.id 
                                                              AND matg.tipomatricula=1
                                                              AND matg."status")
        INNER JOIN  sga_deportistapersona dp ON (dp.persona_id=p.id AND dp.status AND dp.vigente=1 AND dp.estadoarchivoevento=2 AND dp.estadoarchivoentrena=2)
        INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
        INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
        INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
        INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
        INNER JOIN sga_malla mall ON mall.id=im.malla_id
        LEFT JOIN LATERAL(
        select 
            count(sa.asignatura_id) "cantidad", 
            sum(sa.creditos) "creditos"
        from 
            sga_asignaturamalla sa 
        where 
            sa.malla_id=mall.id 
            and sa.nivelmalla_id =nivm.id
            and sa.status
            and not sa.opcional
            and sa.itinerario IN(NULL,0,i.itinerario)
        )malla_materias on True
        LEFT JOIN LATERAL(
            select 
                SUM(rc.creditos) "creditos_aprobados", 
                ROUND(AVG(rc.nota),2) "promedio",
                COUNT(rc.id) "cantidad_asigantura_aprobadas"			
            FROM 
                sga_recordacademico rc
                INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
            WHERE 
                rc.status
                AND rc.inscripcion_id=i.id
                AND rc.aprobada
                AND rc.matriculas=1
                AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                and not asigm_rc.opcional
                AND rc.asignatura_id IN(select 
                                            sa.asignatura_id
                                        from 
                                            sga_asignaturamalla sa 
                                        where 
                                            sa.malla_id=mall.id 
                                            and sa.nivelmalla_id =nivm.id
                                            and sa.status)
        )record_qu on TRUE
    WHERE 
        mat."status"
        {exclude_query}
        and mat.bloqueomatricula=False 
        AND record_qu."promedio" >= 70
        AND co.id IN(1,2,3,4,5)
        AND peri.id={periodo_anterior.id}
        AND pu.visible 
        AND pu."status"
        AND mall.vigente
        AND NOT	mat.retiradomatricula
        AND im."status"
        AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
        AND piu."status"
        /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
        AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                        FROM sga_inscripcion insc	
                            INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                            INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                        WHERE 
                            insc.id=i.id 
                            AND his_rc_g.aprobada=FALSE
                            AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                            and not asim_g.opcional
                        GROUP BY his_rc_g.recordacademico_id
                        HAVING COUNT(his_rc_g.id)>0)=FALSE
                        
        /*MATRICULADO EN EL PERIODO ACTUAL*/
        AND EXISTS(SELECT 	
                            mat_a.nivelmalla_id
                        FROM	
                            sga_matricula mat_a
                            INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                and niv_a.periodo_id={periodo_actual.id}
                                                                                )
                            INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                    matgs_a.matricula_id=mat_a.id
                                    AND matgs_a.tipomatricula=1
                                    AND matgs_a."status"
                            ) 
                        WHERE 
                            mat_a.retiradomatricula=false
                            and mat_a.inscripcion_id=i.id
                            AND mat_a.status
                            and not exists(
                                select id 
                                from sga_retiromatricula 
                                rtm 
                                where 
                                    rtm.matricula_id=mat_a.id 
                                    AND rtm."status"
                            ) 
        )
        /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
        AND EXISTS(
                   SELECT 
                       mattit 
                   FROM  
                       sga_matriculatitulacion mattit 
                       INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                   WHERE  
                       i_ti.persona_id=p.id
                       AND mattit."status" 
                       AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
        )=FALSE 
        /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
        AND NOT EXISTS(
            SELECT id FROM sagest_rubro WHERE 
            persona_id=p.id
            AND fechavence>=NOW()
          AND cancelado=False 
            AND status=True
        )
        /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
        AND NOT EXISTS(
            select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
        )
        /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
        AND NOT EXISTS(SELECT id 
                    FROM 
                        sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
        /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
        AND exists(SELECT  FROM (SELECT 
                COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                COUNT(mtas_aux.id) total_general
            FROM 
                sga_materiaasignada mtas_aux
                INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
            WHERE	 
                mtas_aux.status
                AND not mtas_aux.retiramateria
                AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
        /*VALIDACIÓN QUE No ser becario en otra institución pública */
        AND NOT EXISTS(
            SELECT id FROM sga_becapersona 
            where 
                persona_id=p.id
                and status
                and fechainicio >= Now()::date and Now()::date <=fechafin
                and tipoinstitucion=1
                and verificado
        )
        /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
        AND NOT EXISTS(
            SELECT san.id FROM sga_sacionestudiante san
            inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
            where 
                i_san.persona_id=p.id
                and san.status
                and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                     or san.indifinido
                     or san.periodo_id=peri.id
                    )
            
        )
        /*VALIDACIÓN DE SER ECUATORIANO O RESIDENCIA EN EL ECUADOR*/
        AND (p.pais_id=1 OR p.paisnacimiento_id=1)
        /*VALIDACIÓN DE EXCLUIR PPL*/
        AND not p.ppl
        /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
        {excluir_inscripcion_2carrera_con_matricula}
        
        /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
        
        /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
    ORDER BY record_qu."promedio" DESC
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def listado_etnias_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        mat.id "Codigo Matricula",
        i.id "Codigo Inscripcion",  
        co.nombre "Coordinacion",
        co.id "Coordinacion_id" ,
        ca.id "Carrera_id" ,
        ca.nombre "Carrera",
        raz.id "Raza_id",
        moda.nombre "Modalidad",
        (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
        sex.nombre "Sexo",
        p.cedula "Cedula",
        record_qu."promedio",
        ROW_NUMBER() OVER ( 
            ORDER BY record_qu."promedio" DESC
        )"Orden"
    FROM 
        sga_inscripcion i
        INNER JOIN sga_persona p ON p.id=i.persona_id
        LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
        LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
        LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
        INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
        INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
        INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
        LEFT JOIN sga_raza raz on raz.id = piu.raza_id
        LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
        INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
        INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
        INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
        INNER JOIN sga_matriculagruposocioeconomico matg ON ( matg.matricula_id=mat.id 
                                                              AND matg.tipomatricula=1
                                                              AND matg."status")
        INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
        INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
        INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
        INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
        INNER JOIN sga_malla mall ON mall.id=im.malla_id
        LEFT JOIN LATERAL(
        select 
            count(sa.asignatura_id) "cantidad", 
            sum(sa.creditos) "creditos"
        from 
            sga_asignaturamalla sa 
        where 
            sa.malla_id=mall.id 
            and sa.nivelmalla_id =nivm.id
            and sa.status
            and not sa.opcional
            and sa.itinerario IN(NULL,0,i.itinerario)
        )malla_materias on True
        LEFT JOIN LATERAL(
            select 
                SUM(rc.creditos) "creditos_aprobados", 
                ROUND(AVG(rc.nota),2) "promedio",
                COUNT(rc.id) "cantidad_asigantura_aprobadas"			
            FROM 
                sga_recordacademico rc
                INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
            WHERE 
                rc.status
                AND rc.inscripcion_id=i.id
                AND rc.aprobada
                AND rc.matriculas=1
                AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                and not asigm_rc.opcional
                AND rc.asignatura_id IN(select 
                                            sa.asignatura_id
                                        from 
                                            sga_asignaturamalla sa 
                                        where 
                                            sa.malla_id=mall.id 
                                            and sa.nivelmalla_id =nivm.id
                                            and sa.status)
        )record_qu on TRUE
    WHERE 
        mat."status"
        {exclude_query}
        and mat.bloqueomatricula=False 
        AND record_qu."promedio" >= 85
        AND co.id IN(1,2,3,4,5)
        AND peri.id={periodo_anterior.id}
        AND pu.visible 
        AND pu."status"
        AND mall.vigente
        AND NOT	mat.retiradomatricula
        AND im."status"
        AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
        AND piu."status"
        /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
        AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                        FROM sga_inscripcion insc	
                            INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                            INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                        WHERE 
                            insc.id=i.id 
                            AND his_rc_g.aprobada=FALSE
                            AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                            and not asim_g.opcional
                        GROUP BY his_rc_g.recordacademico_id
                        HAVING COUNT(his_rc_g.id)>0)=FALSE
                        
        /*MATRICULADO EN EL PERIODO ACTUAL*/
        AND EXISTS(SELECT 	
                            mat_a.nivelmalla_id
                        FROM	
                            sga_matricula mat_a
                            INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                and niv_a.periodo_id={periodo_actual.id}
                                                                                )
                            INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                    matgs_a.matricula_id=mat_a.id
                                    AND matgs_a.tipomatricula=1
                                    AND matgs_a."status"
                            ) 
                        WHERE 
                            mat_a.retiradomatricula=false
                            and mat_a.inscripcion_id=i.id
                            AND mat_a.status
                            and not exists(
                                select id 
                                from sga_retiromatricula 
                                rtm 
                                where 
                                    rtm.matricula_id=mat_a.id 
                                    AND rtm."status"
                            ) 
        )
        /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
        AND EXISTS(
                   SELECT 
                       mattit 
                   FROM  
                       sga_matriculatitulacion mattit 
                       INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                   WHERE  
                       i_ti.persona_id=p.id
                       AND mattit."status" 
                       AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
        )=FALSE 
        /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
        AND NOT EXISTS(
            SELECT id FROM sagest_rubro WHERE 
            persona_id=p.id
            AND fechavence>=NOW()
          AND cancelado=False 
            AND status=True
        )
        /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
        AND NOT EXISTS(
            select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
        )
        /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
        AND NOT EXISTS(SELECT id 
                    FROM 
                        sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
        /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
        AND exists(SELECT  FROM (SELECT 
                COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                COUNT(mtas_aux.id) total_general
            FROM 
                sga_materiaasignada mtas_aux
                INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
            WHERE	 
                mtas_aux.status
                AND not mtas_aux.retiramateria
                AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
        /*VALIDACIÓN QUE No ser becario en otra institución pública */
        AND NOT EXISTS(
            SELECT id FROM sga_becapersona 
            where 
                persona_id=p.id
                and status
                and fechainicio >= Now()::date and Now()::date <=fechafin
                and tipoinstitucion=1
                and verificado
        )
        /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
        AND NOT EXISTS(
            SELECT san.id FROM sga_sacionestudiante san
            inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
            where 
                i_san.persona_id=p.id
                and san.status
                and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                     or san.indifinido
                     or san.periodo_id=peri.id
                    )
            
        )
        /*VALIDACIÓN DE SER ECUATORIANO O RESIDENCIA EN EL ECUADOR. EN ESTE TIPO DE BECAS SOLO ES PARA ECUATORIANOS NACIDOS  EN EL PAIS*/
        AND p.pais_id=1
        /*VALIDACIÓN DE EXCLUIR PPL*/
        AND not p.ppl
        /*VALIDACIÓN DE PERTENECER A PUEBLOS Y NACIONALIDADES INDIGENAS*/
        AND piu.raza_id in(1, 2, 5)
        AND piu.estadoarchivoraza = 2
        /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
        {excluir_inscripcion_2carrera_con_matricula}
        
        /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
        
        /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
    ORDER BY record_qu."promedio" DESC
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def listado_exteriores_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        mat.id "Codigo Matricula",
        i.id "Codigo Inscripcion",  
        co.nombre "Coordinacion",
        co.id "Coordinacion_id" ,
        ca.id "Carrera_id" ,
        ca.nombre "Carrera",
        p.pais_id "PaisResidencia_id",
        moda.nombre "Modalidad",
        (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
        sex.nombre "Sexo",
        p.cedula "Cedula",
        record_qu."promedio",
        ROW_NUMBER() OVER ( 
            ORDER BY record_qu."promedio" DESC
        )"Orden"
    FROM 
        sga_inscripcion i
        INNER JOIN sga_persona p ON p.id=i.persona_id
        LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
        LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
        LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
        INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
        INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
        INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
        LEFT JOIN sga_raza raz on raz.id = piu.raza_id
        LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
        INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
        INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
        INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
        INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
        INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
        INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
        INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
        INNER JOIN sga_malla mall ON mall.id=im.malla_id
        LEFT JOIN LATERAL(
        select 
            count(sa.asignatura_id) "cantidad", 
            sum(sa.creditos) "creditos"
        from 
            sga_asignaturamalla sa 
        where 
            sa.malla_id=mall.id 
            and sa.nivelmalla_id =nivm.id
            and sa.status
            and not sa.opcional
            and sa.itinerario IN(NULL,0,i.itinerario)
        )malla_materias on True
        LEFT JOIN LATERAL(
            select 
                SUM(rc.creditos) "creditos_aprobados", 
                ROUND(AVG(rc.nota),2) "promedio",
                COUNT(rc.id) "cantidad_asigantura_aprobadas"			
            FROM 
                sga_recordacademico rc
                INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
            WHERE 
                rc.status
                AND rc.inscripcion_id=i.id
                AND rc.aprobada
                AND rc.matriculas=1
                AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                and not asigm_rc.opcional
                AND rc.asignatura_id IN(select 
                                            sa.asignatura_id
                                        from 
                                            sga_asignaturamalla sa 
                                        where 
                                            sa.malla_id=mall.id 
                                            and sa.nivelmalla_id =nivm.id
                                            and sa.status)
        )record_qu on TRUE
    WHERE 
        mat."status"
        {exclude_query}
        and mat.bloqueomatricula=False 
        AND record_qu."promedio" >= 85
        AND co.id IN(1,2,3,4,5)
        AND peri.id={periodo_anterior.id}
        AND pu.visible 
        AND pu."status"
        AND mall.vigente
        AND NOT	mat.retiradomatricula
        AND im."status"
        AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
        AND piu."status"
        /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
        AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                        FROM sga_inscripcion insc	
                            INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                            INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                        WHERE 
                            insc.id=i.id 
                            AND his_rc_g.aprobada=FALSE
                            AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                            and not asim_g.opcional
                        GROUP BY his_rc_g.recordacademico_id
                        HAVING COUNT(his_rc_g.id)>0)=FALSE
                        
        /*MATRICULADO EN EL PERIODO ACTUAL*/
        AND EXISTS(SELECT 	
                            mat_a.nivelmalla_id
                        FROM	
                            sga_matricula mat_a
                            INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                and niv_a.periodo_id={periodo_actual.id}
                                                                                )
                            INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                    matgs_a.matricula_id=mat_a.id
                                    AND matgs_a.tipomatricula=1
                                    AND matgs_a."status"
                            ) 
                            --LEFT JOIN sga_retiromatricula rtm ON (rtm.matricula_id=mat_a.id AND rtm."status")
                        WHERE 
                            mat_a.retiradomatricula=false
                            and mat_a.inscripcion_id=i.id
                            AND mat_a.status
                            --AND rtm.id IS NULL
                            and not exists(
                                select id 
                                from sga_retiromatricula 
                                rtm 
                                where 
                                    rtm.matricula_id=mat_a.id 
                                    AND rtm."status"
                            ) 
        )
        /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
        AND EXISTS(
                   SELECT 
                       mattit 
                   FROM  
                       sga_matriculatitulacion mattit 
                       INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                   WHERE  
                       i_ti.persona_id=p.id
                       AND mattit."status" 
                       AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
        )=FALSE 
        /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
        AND NOT EXISTS(
            SELECT id FROM sagest_rubro WHERE 
            persona_id=p.id
            AND fechavence>=NOW()
          AND cancelado=False 
            AND status=True
        )
        /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
        AND NOT EXISTS(
            select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
        )
        /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
        AND NOT EXISTS(SELECT id 
                    FROM 
                        sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
        /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
        AND exists(SELECT  FROM (SELECT 
                COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                COUNT(mtas_aux.id) total_general
            FROM 
                sga_materiaasignada mtas_aux
                INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
            WHERE	 
                mtas_aux.status
                AND not mtas_aux.retiramateria
                AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
        /*VALIDACIÓN QUE No ser becario en otra institución pública */
        AND NOT EXISTS(
            SELECT id FROM sga_becapersona 
            where 
                persona_id=p.id
                and status
                and fechainicio >= Now()::date and Now()::date <=fechafin
                and tipoinstitucion=1
                and verificado
        )
        /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
        AND NOT EXISTS(
            SELECT san.id FROM sga_sacionestudiante san
            inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
            where 
                i_san.persona_id=p.id
                and san.status
                and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                     or san.indifinido
                     or san.periodo_id=peri.id
                    )
            
        )
        /*VALIDACIÓN DE EXCLUIR PPL*/
        AND not p.ppl
        /*VALIDACIÓN DE SER ECUATORIANO EN EL EXTERIOR*/
        AND p.pais_id !=1 AND p.paisnacimiento_id=1
        /*VALIDACIÓN DE NO SER MIGRANTE*/
        AND NOT EXISTS(
            SELECT id FROM sga_migrantepersona mp 
            WHERE mp.persona_id=p.id AND mp.status
        )
        /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
        {excluir_inscripcion_2carrera_con_matricula}
        
        /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
        
        /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
    ORDER BY record_qu."promedio" DESC

    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def listado_migrantes_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        mat.id "Codigo Matricula",
        i.id "Codigo Inscripcion",  
        co.nombre "Coordinacion",
        co.id "Coordinacion_id" ,
        ca.id "Carrera_id" ,
        ca.nombre "Carrera",
        mp.id "Migrante_id",
        moda.nombre "Modalidad",
        (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
        sex.nombre "Sexo",
        p.cedula "Cedula",
        record_qu."promedio",
        ROW_NUMBER() OVER ( 
            ORDER BY record_qu."promedio" DESC
        )"Orden"
    FROM 
        sga_inscripcion i
        INNER JOIN sga_persona p ON p.id=i.persona_id
        LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
        LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
        LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
        INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
        INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
        INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
        LEFT JOIN sga_raza raz on raz.id = piu.raza_id
        LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
        INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
        INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
        INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
        INNER JOIN sga_matriculagruposocioeconomico matg ON ( matg.matricula_id=mat.id 
                                                              AND matg.tipomatricula=1
                                                              AND matg."status")
        INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
        INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
        INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
        INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
        INNER JOIN sga_malla mall ON mall.id=im.malla_id
        INNER JOIN sga_migrantepersona mp ON (mp.persona_id=p.id AND mp.status AND mp.estadoarchivo=2)
        LEFT JOIN LATERAL(
        select 
            count(sa.asignatura_id) "cantidad", 
            sum(sa.creditos) "creditos"
        from 
            sga_asignaturamalla sa 
        where 
            sa.malla_id=mall.id 
            and sa.nivelmalla_id =nivm.id
            and sa.status
            and not sa.opcional
            and sa.itinerario IN(NULL,0,i.itinerario)
        )malla_materias on True
        LEFT JOIN LATERAL(
            select 
                SUM(rc.creditos) "creditos_aprobados", 
                ROUND(AVG(rc.nota),2) "promedio",
                COUNT(rc.id) "cantidad_asigantura_aprobadas"			
            FROM 
                sga_recordacademico rc
                INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
            WHERE 
                rc.status
                AND rc.inscripcion_id=i.id
                AND rc.aprobada
                AND rc.matriculas=1
                AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                and not asigm_rc.opcional
                AND rc.asignatura_id IN(select 
                                            sa.asignatura_id
                                        from 
                                            sga_asignaturamalla sa 
                                        where 
                                            sa.malla_id=mall.id 
                                            and sa.nivelmalla_id =nivm.id
                                            and sa.status)
        )record_qu on TRUE
    WHERE 
        mat."status"
        {exclude_query}
        and mat.bloqueomatricula=False 
        AND record_qu."promedio" >= 85
        AND co.id IN(1,2,3,4,5)
        AND peri.id={periodo_anterior.id}
        AND pu.visible 
        AND pu."status"
        AND mall.vigente
        AND NOT	mat.retiradomatricula
        AND im."status"
        AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
        AND piu."status"
        /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
        AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                        FROM sga_inscripcion insc	
                            INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                            INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                        WHERE 
                            insc.id=i.id 
                            AND his_rc_g.aprobada=FALSE
                            AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                            and not asim_g.opcional
                        GROUP BY his_rc_g.recordacademico_id
                        HAVING COUNT(his_rc_g.id)>0)=FALSE
                        
        /*MATRICULADO EN EL PERIODO ACTUAL*/
        AND EXISTS(SELECT 	
                            mat_a.nivelmalla_id
                        FROM	
                            sga_matricula mat_a
                            INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id 
                                                                                and niv_a.periodo_id={periodo_actual.id}
                                                                                )
                            INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                    matgs_a.matricula_id=mat_a.id
                                    AND matgs_a.tipomatricula=1
                                    AND matgs_a."status"
                            ) 
                            --LEFT JOIN sga_retiromatricula rtm ON (rtm.matricula_id=mat_a.id AND rtm."status")
                        WHERE 
                            mat_a.retiradomatricula=false
                            and mat_a.inscripcion_id=i.id
                            AND mat_a.status
                            --AND rtm.id IS NULL
                            and not exists(
                                select id 
                                from sga_retiromatricula 
                                rtm 
                                where 
                                    rtm.matricula_id=mat_a.id 
                                    AND rtm."status"
                            ) 
        )
        /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
        AND EXISTS(
               SELECT 
                   mattit 
               FROM  
                   sga_matriculatitulacion mattit 
                   INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
               WHERE  
                   i_ti.persona_id=p.id
                   AND mattit."status" 
                   AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
        )=FALSE 
        /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
        AND NOT EXISTS(
            SELECT id FROM sagest_rubro WHERE 
            persona_id=p.id
            AND fechavence>=NOW()
          AND cancelado=False 
            AND status=True
        )
        /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
        AND NOT EXISTS(
            select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
        )
        /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
        AND NOT EXISTS(SELECT id 
                    FROM 
                        sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
        /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
        AND exists(SELECT  FROM (SELECT 
                COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                COUNT(mtas_aux.id) total_general
            FROM 
                sga_materiaasignada mtas_aux
                INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
            WHERE	 
                mtas_aux.status
                AND not mtas_aux.retiramateria
                AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
        /*VALIDACIÓN QUE No ser becario en otra institución pública */
        AND NOT EXISTS(
            SELECT id FROM sga_becapersona 
            where 
                persona_id=p.id
                and status
                and fechainicio >= Now()::date and Now()::date <=fechafin
                and tipoinstitucion=1
                and verificado
        )
        /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
        AND NOT EXISTS(
            SELECT san.id FROM sga_sacionestudiante san
            inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
            where 
                i_san.persona_id=p.id
                and san.status
                and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                     or san.indifinido
                     or san.periodo_id=peri.id
                    )
            
        )
        /*VALIDACIÓN DE EXCLUIR PPL*/
        AND not p.ppl
        /*VALIDACIÓN DE SER ESTAR EN EL PAIS*/
        AND p.pais_id =1 AND p.paisnacimiento_id=1
        /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
        {excluir_inscripcion_2carrera_con_matricula}
        
        /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
        
        /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
        AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
    ORDER BY record_qu."promedio" DESC
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def listado_socioeconomico_query(periodo_anterior, periodo_actual, exclude=[], excluir_inscripcion_2carrera_con_matricula=''):
    exclude = tuple(exclude)
    exclude_query = ''
    if exclude.__len__() > 0:
        exclude_query = str(exclude)
        exclude_query = f"AND NOT p.id IN{exclude_query}"
        exclude_query = exclude_query if exclude.__len__() > 1 else exclude_query.replace(',', '')
    cursor = connection.cursor()
    sql = f"""
    SET statement_timeout = 3600000; 
    SELECT 
        listado_socioeconomico.*,
        ROW_NUMBER() OVER ( 
                    ORDER BY listado_socioeconomico."Orden", listado_socioeconomico."promedio" DESC
                )"Orden Final"

    FROM (SELECT 
            * 
        FROM (
            SELECT 
                mat.id "Codigo Matricula",
                i.id "Codigo Inscripcion",  
                co.nombre "Coordinacion",
                co.id "Coordinacion_id" ,
                ca.id "Carrera_id" ,
                ca.nombre "Carrera",
                grup_socio.id "GrupoSocioeconomico_id",
                moda.nombre "Modalidad",
                (p.nombres || ' ' || p.apellido1 || ' ' || p.apellido2) "Estudiante",
                sex.nombre "Sexo",
                p.cedula "Cedula",
                record_qu."promedio",
                ROW_NUMBER() OVER ( 
                    PARTITION BY co.nombre, ca.nombre
                    ORDER BY co.nombre, ca.nombre, record_qu."promedio" DESC
                )"Orden"
            FROM 
                sga_inscripcion i
                INNER JOIN sga_persona p ON p.id=i.persona_id
                LEFT JOIN socioecon_fichasocioeconomicainec ficha on ficha.persona_id=p.id
                LEFT JOIN socioecon_gruposocioeconomico grup_socio on grup_socio.id=ficha.grupoeconomico_id
                LEFT JOIN sga_sexo sex ON sex.id=p.sexo_id
                INNER JOIN sga_perfilinscripcion piu ON piu.persona_id=p.id 
                INNER JOIN sga_carrera ca ON ca.id=i.carrera_id
                INNER JOIN sga_perfilusuario pu ON pu.inscripcion_id=i.id
                LEFT JOIN sga_raza raz on raz.id = piu.raza_id
                LEFT JOIN sga_discapacidad tpd on tpd.id = piu.tipodiscapacidad_id
                INNER JOIN sga_coordinacion co ON co.id=i.coordinacion_id
                INNER JOIN sga_modalidad moda ON moda.id=i.modalidad_id 
                INNER JOIN sga_matricula mat ON mat.inscripcion_id=i.id
                INNER JOIN sga_matriculagruposocioeconomico matg ON (
                            matg.matricula_id=mat.id
                            AND matg.tipomatricula=1
                            AND matg."status"
                    ) 
                INNER JOIN sga_nivel niv ON niv.id=mat.nivel_id
                INNER JOIN sga_nivelmalla nivm ON nivm.id=mat.nivelmalla_id
                INNER JOIN sga_periodo peri ON peri.id=niv.periodo_id
                INNER JOIN sga_inscripcionmalla im ON im.inscripcion_id=i.id
                INNER JOIN sga_malla mall ON mall.id=im.malla_id
                LEFT JOIN LATERAL(
                select 
                    count(sa.asignatura_id) "cantidad", 
                    sum(sa.creditos) "creditos"
                from 
                    sga_asignaturamalla sa 
                where 
                    sa.malla_id=mall.id 
                    and sa.nivelmalla_id =nivm.id
                    and sa.status
                    and not sa.opcional
                    and sa.itinerario IN(NULL,0,i.itinerario)
                )malla_materias on True
                LEFT JOIN LATERAL(
                    select 
                        SUM(rc.creditos) "creditos_aprobados", 
                        ROUND(AVG(rc.nota),2) "promedio",
                        COUNT(rc.id) "cantidad_asigantura_aprobadas"			
                    FROM 
                        sga_recordacademico rc
                        INNER JOIN sga_asignaturamalla asigm_rc on asigm_rc.id=rc.asignaturamalla_id
                    WHERE 
                        rc.status
                        AND rc.inscripcion_id=i.id
                        AND rc.aprobada
                        AND rc.matriculas=1
                        AND asigm_rc.itinerario IN(NULL,0,i.itinerario)
                        and not asigm_rc.opcional
                        AND rc.asignatura_id IN(select 
                                                    sa.asignatura_id
                                                from 
                                                    sga_asignaturamalla sa 
                                                where 
                                                    sa.malla_id=mall.id 
                                                    and sa.nivelmalla_id =nivm.id
                                                    and sa.status)
                )record_qu on TRUE
            WHERE 
                mat."status"
                {exclude_query}
                and mat.bloqueomatricula=False 
                AND co.id IN(1,2,3,4,5)
                AND peri.id={periodo_anterior.id}
                AND pu.visible 
                AND pu."status"
                AND mall.vigente
                AND NOT	mat.retiradomatricula
                AND im."status"
                AND record_qu."cantidad_asigantura_aprobadas"=malla_materias."cantidad"
                AND piu."status"
                --and asignatura_matri.total_general !=asignatura_matri.total_ingles
                /*VALIDACIÓN DE TENER UN RECORD ACADEMICO INTEGRO SIN REPETIR NINGUNA MATERIA EN TODOS LOS NIVELES*/	
                AND EXISTS(SELECT his_rc_g.recordacademico_id, count(his_rc_g.id) 
                                FROM sga_inscripcion insc	
                                    INNER JOIN sga_historicorecordacademico his_rc_g ON his_rc_g.inscripcion_id=insc.id
                                    INNER JOIN sga_asignaturamalla asim_g ON asim_g.id=his_rc_g.asignaturamalla_id
                                WHERE 
                                    insc.id=i.id 
                                    AND his_rc_g.aprobada=FALSE
                                    AND asim_g.itinerario IN(NULL,0,insc.itinerario)
                                    and not asim_g.opcional
                                GROUP BY his_rc_g.recordacademico_id
                                HAVING COUNT(his_rc_g.id)>0)=FALSE
                                
                /*MATRICULADO EN EL PERIODO ACTUAL*/
                AND EXISTS(SELECT 	
                                    mat_a.nivelmalla_id
                                FROM	
                                    sga_matricula mat_a
                                    INNER JOIN sga_nivel niv_a ON (niv_a.id=mat_a.nivel_id and niv_a.periodo_id={periodo_actual.id})
                                    INNER JOIN sga_matriculagruposocioeconomico matgs_a ON (
                                            matgs_a.matricula_id=mat_a.id
                                            AND matgs_a.tipomatricula=1
                                            AND matgs_a."status"
                                    ) 
                                    --LEFT JOIN sga_retiromatricula rtm ON (rtm.matricula_id=mat_a.id AND rtm."status")
                                WHERE 
                                    mat_a.retiradomatricula=false
                                    and mat_a.inscripcion_id=i.id
                                    AND mat_a.status
                                    --AND rtm.id IS NULL
                                    and not exists(
                                        select id 
                                        from sga_retiromatricula 
                                        rtm 
                                        where 
                                            rtm.matricula_id=mat_a.id 
                                            AND rtm."status"
                                    ) 
                )
                /*VALIDACIÓN DE NO ESTAR MATRICULADO EN PROCESO DE TITULACIÓN*/	
                AND EXISTS(
                           SELECT 
                               mattit 
                           FROM  
                               sga_matriculatitulacion mattit 
                               INNER JOIN sga_inscripcion i_ti ON i_ti.id=mattit.inscripcion_id 
                           WHERE  
                               i_ti.persona_id=p.id
                               AND mattit."status" 
                               AND (mattit.estadotitulacion IN(1, 3) OR mattit.estado IN (1, 10, 9))
                )=FALSE 
                /*VALIDACIÓN DE NO TENER DEUDAS VENCIDAS*/
                /*AND NOT EXISTS(
                    SELECT id FROM sagest_rubro WHERE 
                    persona_id=p.id
                    AND fechavence>=NOW()
                  AND cancelado=False 
                    AND status=True
                )*/
                /*VALIDACIÓN DE EXCLUIR GRADUADOS*/
                AND NOT EXISTS(
                    select id from sga_graduado grado WHERE (grado.inscripcion_id=i.id AND grado."status")
                )
                /*VALIDACIÓN DE EXCLUIR RETIRADO DE LA CARRERA*/
                AND NOT EXISTS(SELECT id 
                            FROM 
                                sga_retiromatricula mat_rt WHERE  (mat_rt.matricula_id=mat.id AND mat_rt."status"))
                /*VALIDACIÓN QUE NO SOLO ESTE MATRICULADO EN INGLES*/
                AND exists(SELECT  FROM (SELECT 
                        COUNT(mtas_aux.id) FILTER(Where asim_aux.malla_id IN(353, 22)) total_ingles,
                        COUNT(mtas_aux.id) total_general
                    FROM 
                        sga_materiaasignada mtas_aux
                        INNER JOIN sga_materia mt_aux ON mt_aux.id=mtas_aux.materia_id
                        INNER JOIN sga_asignaturamalla asim_aux ON asim_aux.id=mt_aux.asignaturamalla_id
                    WHERE	 
                        mtas_aux.status
                        AND not mtas_aux.retiramateria
                        AND mtas_aux.matricula_id=mat.id) asignaturas_matri WHERE asignaturas_matri.total_ingles !=asignaturas_matri.total_general)
                /*VALIDACIÓN QUE No ser becario en otra institución pública */
                AND NOT EXISTS(
                    SELECT id FROM sga_becapersona 
                    where 
                        persona_id=p.id
                        and status
                        and fechainicio >= Now()::date and Now()::date <=fechafin
                        and tipoinstitucion=1
                        and verificado
                )
                /*VALIDACIÓN No haber recibido sanciones disciplinarias por cometer faltas graves; */
                AND NOT EXISTS(
                    SELECT san.id FROM sga_sacionestudiante san
                    inner join sga_inscripcion i_san on i_san.id=san.inscripcion_id
                    where 
                        i_san.persona_id=p.id
                        and san.status
                        and (san.fechadesde >= Now()::date and Now()::date <=san.fechahasta 
                             or san.indifinido
                             or san.periodo_id=peri.id
                            )
                    
                )
                AND p.pais_id=1
                /*VALIDACIÓN DE EXCLUIR PPL*/
                AND not p.ppl
                /*VALIDACIÓN DE GRUPO SOCIOECONOMICO*/
                AND grup_socio.id in(4,5)
                AND record_qu."promedio" > 75
                /*VALIDACIÓN DE EXCLUIR INSCRIPCIONES APARTIR DE LAS 2 INSCRIPCION MATRICULADA EN EL PERIODO ACTUAL */
                {excluir_inscripcion_2carrera_con_matricula}	
                
                /*VALIDACIÓN DE NO SER ADMINISTRATIVO ACTIVO EN LA UNEMI*/
                AND NOT EXISTS (SELECT id FROM sga_administrativo  where status and activo and persona_id=p.id )
                
                /*VALIDACIÓN DE NO SER DOCENTE ACTIVO EN LA UNEMI*/
                AND NOT EXISTS (SELECT id FROM sga_profesor  where status and activo and persona_id=p.id)
                
            ORDER BY "Coordinacion", "Carrera", record_qu."promedio" DESC
            )listado_estudiantes
        ) listado_socioeconomico
    ORDER BY listado_socioeconomico."Orden", listado_socioeconomico."promedio" DESC
    """
    cursor.execute(sql)
    results = cursor.fetchall()
    return results


def generar_precandidatos_becas(periodoanterior, periodoactual, usuario_ejecuta_id=1, limit_economico=100, enviarcorreo=False):
    from sga.models import PreInscripcionBeca
    from datetime import datetime

    ID_PRIMER_NIVEL = 16
    ID_MEJOR_PROMEDIO = 17
    ID_DISCAPACIDAD = 19
    ID_DEPORTISTA = 20
    ID_EXTERIOR_MIGRANTE = 22
    ID_ETNIA = 21
    ID_GRUPO_VULNERABLE = 18
    ID_ENFERMEDADES_CATASTROFICAS = 24
    EXCLUDES = []
    SELECCIONADOS = []

    becaperiodo = periodoactual.becaperiodo_set.filter(status=True).first()
    if becaperiodo is None:
        raise NameError("No existe periodo beca configurado")

    mejores_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_MEJOR_PROMEDIO).first()
    if mejores_config is None:
        raise NameError("No existe configurado tipo beca  ALTO PROMEDIO Y DISTINCIÓN ACADÉMICA O ARTÍSTICA (DESDE EL SEGUNDO NIVEL)")

    discapacitados_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_DISCAPACIDAD).first()
    if discapacitados_config is None:
        raise NameError("No existe configurado tipo beca  POR DISCAPACIDAD")

    #PERSONAS CON ENFERMEDADES CATASTROFICAS
    enfermedades_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_ENFERMEDADES_CATASTROFICAS).first()
    if enfermedades_config is None:
        raise NameError("No existe configurado tipo beca  POR ENFERMEDADES CATASTROFICAS")

    deportistas_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_DEPORTISTA).first()
    if deportistas_config is None:
        raise NameError("No existe configurado becatipo ALTO RENDIMIENTO EN DEPORTES")

    exteriores_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_EXTERIOR_MIGRANTE).first()
    if exteriores_config is None:
        raise NameError("No existe configurado tipo beca  POR SER ECUATORIANO EN EL EXTERIOR, MIGRANTE RETORNADO O DEPORTADO")

    etnias_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_ETNIA).first()
    if etnias_config is None:
        raise NameError("No existe configurado tipo beca  POR PERTENECER A PUEBLOS Y NACIONALIDADES DEL ECUADOR")

    socioeconomico_config = becaperiodo.becatipoconfiguracion_set.filter(status=True, becatipo_id=ID_GRUPO_VULNERABLE).first()
    if socioeconomico_config is None:
        raise NameError("No existe configurado tipo beca  SITUACIÓN ECONÓMICA VULNERABLE")

    cantidad_maximas_becados = becaperiodo.limitebecados
    if cantidad_maximas_becados <= 1000:
        raise NameError("Debe configurar mas de 1000 becarios en el periodo de becas")

    cursor = connection.cursor()
    """
    *************************************************************************************************************************************************************
    *                                                                                                                                                           *
    *       ESTE QUERY PERMITE IDENTIFICAR LAS INSCRIPCIONES QUE TIENEN MATRICULA EN EL PERIODO ACTUAL  QUE SIGUEN 2 O 3 CARRERAS                               *
    *       SE EXCLUYE LA PRIMERA INSCRIPCION  QUE INGRESARON A LA UNEMI, YA QUE ES LA VALIDA PARA BECAS LAS DEMAS  SALDRÁN EN EL RESTULTADO DEL QUERY          *
    *       POR QUE SE LAS EXCLUYE EN TODO EL PROCESO DE GENERACIÓN DE PRECANDIDATOS Y NO DE DOLORES DE CABEZA LOS GENIOS QUE VEN VARIAS CARRERAS               *
    *                                                                                                                                                           *
    *************************************************************************************************************************************************************
    """
    sql_idinscripcion_segunda_tercera_matricula_actual_periodo = f"""
    SET statement_timeout = 500000; 
    SELECT i_seg.id
    from 
        sga_inscripcion i_seg
        left join lateral(SELECT 
                    p_s.id,p_s.cedula,  COUNT(i_s.id), (select 
                                            array_agg(sga_inscripcion.id) 
                                            from sga_inscripcion
                                            --INNER JOIN sga_perfilusuario  ON  sga_perfilusuario.inscripcion_id=sga_inscripcion.id
                                           where 
                                            --sga_perfilusuario.visible
                                            --and sga_perfilusuario.status
                                            sga_inscripcion.activo
                                            and sga_inscripcion.coordinacion_id in(1,2,3,4,5)
                                            and sga_inscripcion.persona_id=p_s.id
                                            and sga_inscripcion.status	
                                           )"Id Incripciones", (
                                           select 
                                            sga_inscripcion.id
                                            from sga_inscripcion
                                            --INNER JOIN sga_perfilusuario  ON  sga_perfilusuario.inscripcion_id=sga_inscripcion.id
                                           where 
                                            --sga_perfilusuario.visible
                                            --and sga_perfilusuario.status
                                            sga_inscripcion.activo
                                            and sga_inscripcion.coordinacion_id in(1,2,3,4,5)
                                            and sga_inscripcion.persona_id=p_s.id
                                            and sga_inscripcion.status
                                            order by fecha
                                            limit 1
                                           ) id_primera_incripcion
              FROM
                  sga_inscripcion i_s
                  INNER JOIN sga_persona p_s ON p_s.id=i_s.persona_id
                  INNER JOIN sga_perfilusuario pu_s ON (pu_s.inscripcion_id=i_s.id and pu_s.persona_id=p_s.id)
                  INNER JOIN sga_matricula mat_s ON mat_s.inscripcion_id=i_s.id
                  INNER JOIN sga_nivel niv_s ON niv_s.id=mat_s.nivel_id
              WHERE 
                  i_s."status"
                  AND mat_s."status"
                  AND NOT mat_s.retiradomatricula
                  AND i_s.coordinacion_id IN(1,2,3,4,5)
                  AND niv_s.periodo_id IN({periodoactual.id})
                  AND pu_s.visible
                  AND pu_s."status"
                  and pu_s.visible
                  AND i_s.activo
              GROUP BY p_s.cedula, 	p_s.id, "Id Incripciones"
              HAVING COUNT(i_s.id) >1)lista_inscripones on True 
     where
        lista_inscripones.id_primera_incripcion !=i_seg.id
        and i_seg.persona_id=lista_inscripones.id
        and i_seg.coordinacion_id in(1,2,3,4,5)
    """
    cursor.execute(sql_idinscripcion_segunda_tercera_matricula_actual_periodo)
    result_id_inscripciones = cursor.fetchall()
    result_id_inscripciones = tuple([res[0] for res in result_id_inscripciones])
    
    exclude_query_segunda_tercera_matricula = ''
    if result_id_inscripciones.__len__() > 0:
        exclude_query_segunda_tercera_matricula = str(result_id_inscripciones)
        exclude_query_segunda_tercera_matricula = f"AND NOT i.id IN{exclude_query_segunda_tercera_matricula}"
        exclude_query_segunda_tercera_matricula = exclude_query_segunda_tercera_matricula if result_id_inscripciones.__len__() > 1 else exclude_query_segunda_tercera_matricula.replace(',', '')

    """ELIMINO MEJORES PUNTUADOS GENERADOS EN PRESELECCION PRELIMINAR"""
    PreInscripcionBeca.objects.filter(periodo=periodoactual, status=True).update(status=False)
    BecaSolicitud.objects.filter(periodo=periodoactual, periodocalifica=periodoanterior, status=True).update(status=False)
    BecaSolicitudRecorrido.objects.filter(solicitud__periodo=periodoactual, status=True).update(status=False)
    
    """LISTADO DE LOS MEJORES ESTUDIANTES"""
    mejores = listado_mejores_puntuados_query(periodoanterior, periodoactual, exclude_query_segunda_tercera_matricula)
    for mejor in mejores:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=mejor[1],
                                                               becatipo_id=ID_MEJOR_PROMEDIO,
                                                               periodo=periodoactual,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                inscripcion_id=mejor[0],
                matricula_id=mejor[1],
                promedio=mejor[-2],
                orden=mejor[-1],
                becatipo_id=ID_MEJOR_PROMEDIO,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    artistas = listado_artistas_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)
    for artista in artistas:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=artista[1],
                                                               becatipo_id=ID_MEJOR_PROMEDIO,
                                                               artista_id=artista[4],
                                                               periodo=periodoactual,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=artista[0],
                inscripcion_id=artista[1],
                artista_id=artista[4],
                promedio=artista[-2],
                orden=artista[-1],
                becatipo_id=ID_MEJOR_PROMEDIO,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    discapacitados = listado_discapacitados_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)

    for discapacitado in discapacitados:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=discapacitado[1],
                                                               becatipo_id=ID_DISCAPACIDAD,
                                                               periodo=periodoactual,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=discapacitado[0],
                inscripcion_id=discapacitado[1],
                tipodiscapacidad_id=discapacitado[6],
                porcientodiscapacidad=discapacitado[7],
                carnetdiscapacidad=discapacitado[8],
                promedio=discapacitado[-2],
                orden=discapacitado[-1],
                becatipo_id=ID_DISCAPACIDAD,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    #La funcion filtrapersonas con discapacidad y enfermedades catastroficas
    enfermos = listado_enfcatastroficas_discap_query(periodoanterior, periodoactual, EXCLUDES,
                                                     exclude_query_segunda_tercera_matricula)

    for enfermo in enfermos:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=enfermo[1],
                                                               periodo=periodoactual,
                                                               becatipo_id=ID_ENFERMEDADES_CATASTROFICAS,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=enfermo[0],
                inscripcion_id=enfermo[1],
                deportista_id=enfermo[6],
                promedio=enfermo[-2],
                orden=enfermo[-1],
                becatipo_id=ID_ENFERMEDADES_CATASTROFICAS,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    deportistas = listado_deportistas_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)

    for deportista in deportistas:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=deportista[1],
                                                               periodo=periodoactual,
                                                               becatipo_id=ID_DEPORTISTA,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=deportista[0],
                inscripcion_id=deportista[1],
                deportista_id=deportista[6],
                promedio=deportista[-2],
                orden=deportista[-1],
                becatipo_id=ID_DEPORTISTA,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    etnias = listado_etnias_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)

    for etnia in etnias:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=etnia[1],
                                                               periodo=periodoactual,
                                                               becatipo_id=ID_ETNIA,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=etnia[0],
                inscripcion_id=etnia[1],
                raza_id=etnia[6],
                promedio=etnia[-2],
                orden=etnia[-1],
                becatipo_id=ID_ETNIA,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    exteriores = listado_exteriores_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)

    for exterior in exteriores:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=exterior[1],
                                                               periodo=periodoactual,
                                                               becatipo_id=ID_EXTERIOR_MIGRANTE,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=exterior[0],
                inscripcion_id=exterior[1],
                promedio=exterior[-2],
                orden=exterior[-1],
                pais_id=exterior[6],
                becatipo_id=ID_EXTERIOR_MIGRANTE,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)
    migrantes = listado_migrantes_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)

    for migrante in migrantes:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=migrante[1],
                                                               periodo=periodoactual,
                                                               becatipo_id=ID_EXTERIOR_MIGRANTE,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=migrante[0],
                inscripcion_id=migrante[1],
                migrante_id=migrante[6],
                promedio=migrante[-2],
                orden=migrante[-1],
                becatipo_id=ID_EXTERIOR_MIGRANTE,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)

    socios_economicos = listado_socioeconomico_query(periodoanterior, periodoactual, EXCLUDES, exclude_query_segunda_tercera_matricula)

    for socio_economico in socios_economicos:
        preinscripcionbeca = PreInscripcionBeca.objects.filter(inscripcion_id=socio_economico[1],
                                                               periodo=periodoactual,
                                                               becatipo_id=ID_GRUPO_VULNERABLE,
                                                               status=True).first()
        if not preinscripcionbeca:
            preinscripcionbeca = PreInscripcionBeca(
                matricula_id=socio_economico[0],
                inscripcion_id=socio_economico[1],
                gruposocioeconomico_id=socio_economico[6],
                promedio=socio_economico[-3],
                orden=socio_economico[-1],
                becatipo_id=ID_GRUPO_VULNERABLE,
                fecha=datetime.now().date(),
                periodo=periodoactual,
                seleccionado=EXCLUDES.__len__() < cantidad_maximas_becados,
                cumplerequisitos=True,
                becaperiodo=becaperiodo
            )
            preinscripcionbeca.save(usuario_id=usuario_ejecuta_id)
            EXCLUDES.append(preinscripcionbeca.inscripcion.persona_id)
            #print(preinscripcionbeca)
            if preinscripcionbeca.seleccionado:
                SELECCIONADOS.append(preinscripcionbeca)
    print("Cantidad de becados", EXCLUDES.__len__())
    """"
        NOTIFICAR AL ESTUDIANTE QUE FUE SELECCIONADO PARA UNA BECA ESTUDIANTIL
    """
    lista_envio_masivo = []
    for preinscripcionbeca in SELECCIONADOS:
        becado = BecaSolicitud(inscripcion=preinscripcionbeca.inscripcion,
                               becatipo=preinscripcionbeca.becatipo,
                               periodo=preinscripcionbeca.periodo,
                               periodocalifica=periodoanterior,
                               estado=1,
                               notificado=enviarcorreo,
                               tiposolicitud=preinscripcionbeca.tipo_renovacion_nueva(periodoanterior),
                               observacion=f'SEMESTRE REGULAR {preinscripcionbeca.periodo.nombre}')
        becado.save(usuario_id=usuario_ejecuta_id)
        recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=1).first()
        if recorrido is None:
            recorrido = BecaSolicitudRecorrido(solicitud=becado,
                                               observacion="SOLICITUD AUTOMÁTICA",
                                               estado=1)
            recorrido.save(usuario_id=1)
            recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=4).first()
            # REGISTRO EN ESTADO DE REVISION
            if recorrido is None:
                becado.estado = 4
                becado.save(usuario_id=usuario_ejecuta_id)
                recorrido = BecaSolicitudRecorrido(solicitud=becado,
                                                   observacion="EN REVISION",
                                                   estado=4)
                recorrido.save(usuario_id=1)
                #log(u'Agrego recorrido de beca: %s' % recorrido, request, "add")

            recorrido = BecaSolicitudRecorrido.objects.filter(solicitud=becado, estado=2).first()
            if recorrido is None:
                becado.estado = 2
                becado.becaaceptada = 1
                becado.save(usuario_id=usuario_ejecuta_id)
                recorrido = BecaSolicitudRecorrido(solicitud=becado,
                                                   observacion="PENDIENTE DE ACEPTACIÓN O RECHAZO",
                                                   estado=2)
                recorrido.save(usuario_id=usuario_ejecuta_id)
                #log(u'Agrego recorrido de beca: %s' % recorrido, request, "add")
                # Envio de e-mail de notificación al solicitante
                if enviarcorreo:
                    notificacion = Notificacion(titulo=f"Solicitud de Beca en Revisión - {preinscripcionbeca.periodo.nombre}",
                                                cuerpo=f"Solicitud de aplicación a la beca por {becado.becatipo.nombre.upper()} para el periodo académico {becado.periodo.nombre} ha sido {'APROBADA' if becado.estado == 2 else 'RECHAZADA'}",
                                                destinatario=preinscripcionbeca.inscripcion.persona,
                                                url="/alu_becas",
                                                content_type=None,
                                                object_id=None,
                                                prioridad=2,
                                                perfil=preinscripcionbeca.inscripcion.perfil_usuario(),
                                                app_label='SIE',  # request.session['tiposistema'],
                                                fecha_hora_visible=datetime.now() + timedelta(days=2)
                                                )
                    notificacion.save(usuario_id=1)
                    tituloemail = "Beca estudiantil"
                    data = {'sistema': u'SGA - UNEMI',
                            'fase': 'AR',
                            'tipobeca': becado.becatipo.nombre.upper(),
                            'fecha': datetime.now().date(),
                            'hora': datetime.now().time(),
                            'saludo': 'Estimada' if becado.inscripcion.persona.sexo_id == 1 else 'Estimado',
                            'estado': 'APROBADA' if becado.estado == 2 else "RECHAZADA",
                            'estudiante': becado.inscripcion.persona.nombre_minus(),
                            'autoridad2': '',
                            'observaciones': '',
                            'periodo': becado.periodo.nombre,
                            't': miinstitucion()
                            }
                    list_email = becado.inscripcion.persona.lista_emails_envio()
                    lista_envio_masivo.append({'tituloemail': tituloemail,
                                               'data': data,
                                               'list_email': list_email,
                                               'plantilla': "emails/notificarestadosolicitudbeca.html"})

    return lista_envio_masivo


def generar_reportes_por_query(sql, report_title, name_worksheet, name_report):
    cursor = connection.cursor()
    cursor.execute(sql)
    rows_effected = cursor.rowcount
    results = cursor.fetchall()
    campos = [desc.name for desc in cursor.description]
    __author__ = 'Unemi'
    ahora = datetime.now()
    time_codigo = ahora.strftime('%Y%m%d_%H%M%S')
    name_file = f'{name_report}{time_codigo}.xlsx'
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output)
    ws = workbook.add_worksheet(name_worksheet)

    fuentecabecera = workbook.add_format({
        'align': 'center',
        'bg_color': 'silver',
        'border': 1,
        'bold': 1
    })
    formatoceldafecha = workbook.add_format({
        'num_format': 'dd/mm/yyyy',
        'border': 1,
        'valign': 'vcenter',
        'align': 'center'
    })

    formatoceldacenter = workbook.add_format({
        'border': 1,
        'valign': 'vcenter',
        'align': 'center'})

    fuenteencabezado = workbook.add_format({
        'align': 'center',
        'bg_color': '#1C3247',
        'font_color': 'white',
        'border': 1,
        'font_size': 24,
        'bold': 1
    })

    ws.merge_range(0, 0, 0, campos.__len__() - 1, 'UNIVERSIDAD ESTATAL ESTATAL DE MILAGRO', fuenteencabezado)
    ws.merge_range(1, 0, 1, campos.__len__() - 1, report_title, fuenteencabezado)
    row_num, numcolum = 2, 0

    for col_name in campos:
        ws.write(row_num, numcolum, col_name, fuentecabecera)
        ws.set_column(numcolum, numcolum, 40)
        numcolum += 1

    row_num += 1
    for lis in results:
        colum_num = 0
        for l in lis:
            ws.write(row_num, colum_num, l, formatoceldacenter)
            ws.set_column(row_num, numcolum, 40)
            colum_num += 1
        row_num += 1
    workbook.close()
    output.seek(0)
    response = HttpResponse(
        output,
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = 'attachment; filename=%s' % name_file

    return response
