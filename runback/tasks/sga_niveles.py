import sys
import random
import json
import xlwt
import os
import time
import pandas as pd
from datetime import datetime, timedelta
from django.contrib.auth.models import User
from django.db import connections
from django.http import HttpResponse

from inno.funciones import haber_aprobado_modulos_computacion
from sga.commonviews import traerNotificaciones
from settings import MEDIA_ROOT, MEDIA_URL, SITE_STORAGE
from sga.models import Periodo, Inscripcion, Persona, Notificacion
from wpush.models import SubscriptionInfomation
from webpush.utils import _send_notification


def rpt_matriculados_pregrado_sin_modulos(params):
    try:
        periodo_id = params.get('periodo_id', 0)
        persona_id = params.get('persona_id', 0)
        ePeriodo = Periodo.objects.get(pk=periodo_id)
        nombre_archivo = "rpt_matriculados_sin_modulos_{}.xls".format(random.randint(1, 10000).__str__())
        os.makedirs(os.path.join(SITE_STORAGE, 'media', 'niveles', 'reportes', ''), exist_ok=True)
        directory = os.path.join(MEDIA_ROOT, 'niveles', 'reportes', nombre_archivo)
        ePersona = Persona.objects.get(pk=persona_id)
        usernotify = ePersona.usuario
        eNotificacion = Notificacion(titulo=f'Reporte de matriculados del periodo {ePeriodo.nombre} en proceso'.strip(),
                                     cuerpo=f'Reporte de matriculados del periodo {ePeriodo.nombre} desde el módulo de niveles',
                                     destinatario=ePersona,
                                     # url="{}reportes/matriculados/{}".format(MEDIA_URL, nombre_archivo),
                                     prioridad=1,
                                     app_label='SGA',
                                     fecha_hora_visible=datetime.now() + timedelta(days=1),
                                     tipo=2,
                                     perfil=ePersona.perfilusuario_administrativo(),
                                     en_proceso=True)
        eNotificacion.save(usuario_id=usernotify.id)
        cursor = connections['sga_select'].cursor()
        wb = xlwt.Workbook(encoding='utf-8')
        ws = wb.add_sheet('Hoja1')
        estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
        ws.col(0).width = 1000
        ws.col(1).width = 6000
        ws.col(2).width = 3000
        ws.col(3).width = 3000
        ws.col(4).width = 6000
        ws.col(5).width = 6000
        ws.col(6).width = 6000
        ws.col(7).width = 6000
        ws.col(8).width = 4000
        ws.col(9).width = 6000
        ws.col(10).width = 6000
        ws.col(11).width = 1000
        ws.col(14).width = 4000
        ws.col(15).width = 4000
        ws.col(16).width = 4000
        ws.write(4, 0, 'N.')
        ws.write(4, 1, 'PERIODO')
        ws.write(4, 2, 'NIVEL_CRE')
        ws.write(4, 3, 'NIVEL_MAT')
        ws.write(4, 4, 'SECCION')
        ws.write(4, 5, 'CEDULA')
        ws.write(4, 6, 'APELLIDOS')
        ws.write(4, 7, 'NOMBRES')
        ws.write(4, 8, 'SEXO')
        ws.write(4, 9, 'FECHANACIMIENTO')
        ws.write(4, 10, 'EMAIL')
        ws.write(4, 11, 'EMAILINST')
        ws.write(4, 12, 'COORDINACION')
        ws.write(4, 13, 'CARRERA')
        ws.write(4, 14, 'COD. SENESCYT')
        ws.write(4, 15, 'TELEFONO')
        # ws.write(4, 16, 'USUARIO')
        ws.write(4, 16, 'INSCRIPCION')
        # ws.write(4, 17, '# MATRICULAS')
        ws.write(4, 17, 'LGTBI')
        ws.write(4, 18, 'ETNIA')
        ws.write(4, 19, 'NACIONALIDAD')
        ws.write(4, 20, 'PAIS')
        ws.write(4, 21, 'PROVINCIA')
        ws.write(4, 22, 'CANTON')
        ws.write(4, 23, 'DIRECCION')
        ws.write(4, 24, 'ESTADO SOCIO ECONOMICO')
        ws.write(4, 25, 'REALIZADO')
        # ws.write(4, 26, 'HORAS PRACTICAS')
        # ws.write(4, 27, 'HORAS VINCULACION')
        ws.write(4, 26, 'FECHA INICIO PRIMER NIVEL')
        ws.write(4, 27, 'FECHA CONVALIDACION')
        # ws.write(4, 28, 'PROMEDIO ASISTENCIA')
        # ws.write(4, 29, 'PROMEDIO NOTAS')
        # ws.write(4, 30, 'ULTIMO MODULO')
        # ws.write(4, 31, 'MATRICULADO MODULO')
        ws.write(4, 28, 'TIENE DISCAPACIDAD')
        ws.write(4, 29, 'DISCAPACIDAD')
        # ws.write(4, 30, 'ITINETARIOS CUMPLIDOS')
        ws.write(4, 30, 'ID MATRICULA')
        ws.write(4, 31, 'TIPO MATRICULA')
        ws.write(4, 32, 'TIPO ESTUDIANTE')
        ws.write(4, 33, 'CONTACTO EMERGENCIA')
        ws.write(4, 34, 'COLEGIO')
        ws.write(4, 35, 'MODALIDAD')
        ws.write(4, 36, 'PPL')
        ws.write(4, 37, 'ES AUTOMATRICULA')
        ws.write(4, 38, 'ACEPTA TERMINOS')
        ws.write(4, 39, 'FECHA TERMINOS')
        ws.write(4, 40, 'MÓDULOS DE COMPUTACIÓN COMPLETO')
        a = 4
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        # listaestudiante = """
        #                     select peri.nombre as PERIODO, nimalla.nombre as NIVEL_CRE,sesion.nombre as SECCION,
        #                     perso.cedula, perso.apellido1 || ' ' || perso.apellido2 as apellidos,
        #                     perso.nombres as nompersona, se.nombre as sexo,
        #                     perso.nacimiento as fechanacimiento,perso.email,perso.emailinst, coor.nombre as facultad, carr.nombre as carrera,
        #                     (select ma.codigo from sga_inscripcionmalla insmalla inner join sga_malla ma on insmalla.malla_id=ma.id where insmalla.inscripcion_id=ins.id and insmalla.status=True),
        #                     perso.telefono,ins.id as INSCRIPCION,
        #                     CASE WHEN perso.lgtbi = True THEN 'SI' else 'NO' END as lgtbi,
        #                     (select rasa.nombre from sga_perfilinscripcion perfil inner join sga_raza rasa on perfil.raza_id=rasa.id where perfil.persona_id=perso.id and perfil.status=True) as etnia,
        #                     perso.nacionalidad, pais.nombre as pais, provincia.nombre as provincia, canton.nombre as canton,
        #                     perso.direccion || ' ' || perso.direccion2 as direccion,
        #                     (select gru.codigo || ' ' || gru.nombre from socioecon_fichasocioeconomicainec fi inner join socioecon_gruposocioeconomico gru on fi.grupoeconomico_id=gru.id where fi.persona_id=perso.id and fi.status=True) as gruposocioeconomico,
        #                     ins.fechainicioprimernivel,ins.fechainicioconvalidacion,
        #                     (select CASE WHEN perfilin.tienediscapacidad = True THEN 'SI' else 'NO' END  from sga_perfilinscripcion perfilin where perfilin.persona_id=perso.id and perfilin.status=True) as tienediscapacidad,
        #                     (select disca.nombre  from sga_perfilinscripcion perfilin,sga_discapacidad disca where perfilin.persona_id=perso.id and perfilin.tipodiscapacidad_id=disca.id and perfilin.status=True) as discapacidad,
        #                     matri.id as idmatricula, CASE WHEN gruso.tipomatricula=1 THEN 'REGULAR' WHEN gruso.tipomatricula=2 THEN 'IRREGULAR' END as tipomatricula,
        #                     tima.nombre as tipoestudiante, ext.contactoemergencia as contactoemergencia,
        #                     uni.nombre as unidadeducativa, modal.nombre as modalidad,
        #                     Case when (select count(*) from sga_matricula matr where matr.inscripcion_id=ins.id and matr.status=True
        #                     and matr.retiradomatricula=False)> 1 then 2 else 1 end   as veces_matricula , perso.ppl, matri.termino,
        #                     matri.automatriculaadmision, matri.termino AND matri.automatriculaadmision
        #                     from sga_matricula matri
        #                     inner join sga_tipomatricula tima on tima.id=matri.tipomatricula_id and tima.status=True
        #                     inner join sga_nivel ni on matri.nivel_id=ni.id and ni.status=True
        #                     inner join sga_inscripcion ins on matri.inscripcion_id=ins.id and ins.status=True
        #                     left join sga_coordinacion coor on coor.id=ins.coordinacion_id
        #                     left join sga_carrera carr on carr.id=ins.carrera_id
        #                     left join sga_institucionescolegio uni on uni.id=ins.unidadeducativa_id and uni.status=True
        #                     left join sga_matriculagruposocioeconomico gruso on gruso.matricula_id=matri.id and gruso.status=True
        #                     inner join sga_persona perso on ins.persona_id=perso.id
        #                     left join med_personaextension ext on ext.persona_id=perso.id and ext.status=True
        #                     left join sga_sexo se on se.id=perso.sexo_id and se.status=True
        #                     left join sga_pais pais on perso.pais_id=pais.id and pais.status=True
        #                     left join sga_provincia provincia on perso.provincia_id=provincia.id and provincia.status=True
        #                     left join sga_canton canton on perso.canton_id=canton.id and canton.status=True
        #                     inner join sga_periodo peri on ni.periodo_id=peri.id
        #                     inner join sga_nivelmalla nimalla on matri.nivelmalla_id=nimalla.id
        #                     left join sga_sesion sesion on ins.sesion_id=sesion.id
        #                     inner join sga_modalidad modal on ins.modalidad_id=modal.id
        #                     where  matri.status=True and matri.retiradomatricula=False
        #                     and ni.periodo_id= %s
        #                     and matri.id not in(
        #                     SELECT DISTINCT sga_matricula.id
        #                     FROM sga_matricula
        #                     INNER JOIN sga_nivel ON (sga_matricula.nivel_id = sga_nivel.id)
        #                     INNER JOIN sga_periodo ON (sga_nivel.periodo_id = sga_periodo.id)
        #                     INNER JOIN sga_materiaasignada ON (sga_matricula.id = sga_materiaasignada.matricula_id)
        #                     INNER JOIN sga_materia ON (sga_materiaasignada.materia_id = sga_materia.id)
        #                     INNER JOIN sga_asignatura ON (sga_materia.asignatura_id = sga_asignatura.id)
        #                     INNER JOIN sga_inscripcion ON (sga_matricula.inscripcion_id = sga_inscripcion.id)
        #                     WHERE (sga_nivel.periodo_id = %s AND sga_matricula.status = TRUE AND sga_asignatura.modulo = TRUE
        #                     AND ((SELECT COUNT(mta.id)
        #                     FROM sga_materiaasignada mta
        #                     WHERE mta.matricula_id=sga_matricula.id) = 1)
        #                     AND NOT (sga_inscripcion.carrera_id IN (
        #                     SELECT U3.carrera_id AS Col1
        #                     FROM sga_coordinacion_carrera U3
        #                     WHERE U3.coordinacion_id = 9))
        #                     AND NOT (coor.id= 7)
        #                     AND NOT (sga_matricula.retiradomatricula = TRUE)))
        #     """ % (ePeriodo.id, ePeriodo.id)

        query = """
                SELECT 
                    sga_p.nombre AS periodo,
                    sga_nmm.nombre AS nivel_cre,
                    sga_mat.nivelmalla_id AS nivelmatricula,
                    sga_sec.nombre AS seccion,
                    (CASE WHEN sga_per.cedula != '' THEN sga_per.cedula WHEN sga_per.pasaporte != '' THEN sga_per.pasaporte ELSE '' END) AS cedula,
                    sga_per.apellido1 || ' ' || sga_per.apellido2 AS apellidos,
                    sga_per.nombres AS nompersona,
                    sga_sex.nombre AS sexo,
                    TO_CHAR(sga_per.nacimiento, 'YYYY-MM-DD') AS fechanacimiento,
                    sga_per.email,
                    sga_per.emailinst,
                    sga_coor_ins.nombre AS facultad,
                    sga_carr_ins.nombre AS carrera,
                    sga_mall.codigo AS codigo,
                    sga_per.telefono,
                    sga_i.id AS inscripcion,
                    /*(CASE WHEN (
                    SELECT COUNT(*)
                    FROM sga_matricula matr
                    WHERE matr.inscripcion_id=sga_i.id AND matr.status= TRUE AND matr.retiradomatricula= FALSE)> 1 THEN 2 ELSE 1 END) AS veces_matricula,*/
                    (CASE WHEN sga_per.lgtbi = TRUE THEN 'SI' ELSE 'NO' END) AS lgtbi,
                    sga_r.nombre AS etnia,
                    sga_pai.nacionalidad AS nacionalidad,
                    sga_pai.nombre AS pais,
                    sga_prov.nombre AS provincia,
                    sga_cant.nombre AS canton,
                    --sga_parro.nombre AS parroquia,
                    sga_per.direccion || ' ' || sga_per.direccion2 AS direccion,
                    (socio_g.codigo || ' ' || socio_g.nombre) AS gruposocioeconomico,
                    'SI' AS realizado,
                    TO_CHAR(sga_i.fechainicioprimernivel, 'YYYY-MM-DD') AS fechainicioprimernivel, 
                    TO_CHAR(sga_i.fechainicioconvalidacion, 'YYYY-MM-DD') AS fechainicioconvalidacion,
                    (CASE WHEN sga_pi.tienediscapacidad = TRUE THEN 'SI' ELSE 'NO' END) AS tienediscapacidad,
                    sga_dis.nombre AS discapacidad,
                    sga_mat.id AS idmatricula,
                    (CASE WHEN sga_mgs.tipomatricula=1 THEN 'REGULAR' WHEN sga_mgs.tipomatricula=2 THEN 'IRREGULAR' END) AS tipomatricula,
                    sga_tm.nombre AS tipoestudiante,
                    med_per_ex.contactoemergencia AS contactoemergencia,
                    sga_ins_col.nombre AS unidadeducativa,
                    sga_mod.nombre AS modalidad,
                    sga_per.ppl, 
                    sga_mat.automatriculapregrado,
                    sga_mat.termino, 
                    sga_mat.fechatermino/*,
                    TO_CHAR(sga_mat.fecha, 'YYYY-MM-DD') AS fechamatricula, 
                    TO_CHAR(sga_mat.fecha_creacion, 'YYYY-MM-DD') AS fechacreacion,
                    usu_cre_mat.username AS ususuarioname*/
                FROM sga_matricula AS sga_mat
                    INNER JOIN sga_matriculagruposocioeconomico AS sga_mgs ON sga_mgs.matricula_id=sga_mat.id AND sga_mgs.status= TRUE
                    INNER JOIN sga_tipomatricula AS sga_tm ON sga_tm.id=sga_mat.tipomatricula_id AND sga_tm.status= TRUE
                    INNER JOIN sga_inscripcion AS sga_i ON sga_i.id=sga_mat.inscripcion_id AND sga_i.status=TRUE
                    INNER JOIN sga_modalidad AS sga_mod ON sga_mod.id=sga_i.modalidad_id
                    INNER JOIN sga_persona AS sga_per ON sga_per.id=sga_i.persona_id
                    INNER JOIN sga_nivelmalla AS sga_nmm ON sga_nmm.id=sga_mat.nivelmalla_id
                    INNER JOIN sga_nivel AS sga_n ON sga_n.id=sga_mat.nivel_id
                    INNER JOIN sga_periodo AS sga_p ON sga_p.id=sga_n.periodo_id
                    LEFT JOIN sga_sesion AS sga_sec ON sga_sec.id=sga_i.sesion_id
                    LEFT JOIN sga_sexo AS sga_sex ON sga_sex.id=sga_per.sexo_id
                    LEFT JOIN sga_coordinacion AS sga_coor_ins ON sga_coor_ins.id=sga_i.coordinacion_id
                    LEFT JOIN sga_carrera AS sga_carr_ins ON sga_carr_ins.id=sga_i.carrera_id
                    LEFT JOIN sga_perfilinscripcion AS sga_pi ON sga_pi.persona_id=sga_i.id
                    LEFT JOIN sga_raza AS sga_r ON sga_r.id=sga_pi.raza_id
                    LEFT JOIN sga_discapacidad AS sga_dis ON sga_dis.id=sga_pi.tipodiscapacidad_id
                    LEFT JOIN sga_pais AS sga_pai ON sga_pai.id=sga_per.pais_id
                    LEFT JOIN sga_provincia AS sga_prov ON sga_prov.id=sga_per.provincia_id
                    LEFT JOIN sga_canton AS sga_cant ON sga_cant.id=sga_per.canton_id
                    LEFT JOIN sga_parroquia AS sga_parro ON sga_parro.id=sga_per.parroquia_id
                    LEFT JOIN med_personaextension AS med_per_ex ON med_per_ex.persona_id=sga_per.id
                    LEFT JOIN sga_institucionescolegio AS sga_ins_col ON sga_ins_col.id=sga_i.unidadeducativa_id AND sga_ins_col.status= TRUE
                    LEFT JOIN auth_user AS usu_cre_mat ON usu_cre_mat.id=sga_mat.usuario_creacion_id
                    INNER JOIN sga_inscripcionmalla AS sga_ins_mall ON sga_ins_mall.inscripcion_id=sga_i.id AND sga_ins_mall.status=TRUE
                    INNER JOIN sga_malla AS sga_mall ON sga_mall.id=sga_ins_mall.malla_id
                    INNER JOIN socioecon_fichasocioeconomicainec AS socio_ficha_ec ON socio_ficha_ec.persona_id=sga_per.id AND socio_ficha_ec."status"=TRUE
                    INNER JOIN socioecon_gruposocioeconomico AS socio_g ON socio_g.id=socio_ficha_ec.grupoeconomico_id
                WHERE sga_p.id=%s AND 
                    sga_mat.status=TRUE AND 
                    sga_mat.retiradomatricula=FALSE AND
                    sga_i.coordinacion_id IN (1,2,3,4,5)
                """ % periodo_id

        ###sga_matricula.estado_matricula = 2 AND
        cursor.execute(query)
        results = cursor.fetchall()
        # periodo_actual = Periodo.objects.get(pk=ePeriodo.id)

        # periodo_anterior = Periodo.objects.filter(status=True, clasificacion=3, fin__lt=periodo_actual.fin).order_by('-inicio').first()
        # if periodo_actual.clasificacion == 3:
        #     matriz_periodo = periodo_actual.subirmatrizinscripcion_set.filter(estado=2, status=True).first()
        #     matriz_periodo_anterior = periodo_anterior.subirmatrizinscripcion_set.filter(estado=2, status=True).first() if periodo_anterior is not None else None
        #     columnas_excel = ['CARRERA_ID', 'CEDULA']
        #     df_matriz_periodo = pd.read_excel(matriz_periodo.archivo, usecols=columnas_excel) if matriz_periodo else []
        #     df_matriz_periodo_anterior = pd.read_excel(matriz_periodo_anterior.archivo, usecols=columnas_excel) if matriz_periodo_anterior else []

        # a = 0
        for per in results:
            a += 1
            ws.write(a, 0, a - 4)
            ws.write(a, 1, '%s' % per[0])
            ws.write(a, 2, '%s' % per[1])
            ws.write(a, 3, '%s' % per[2])
            ws.write(a, 4, '%s' % per[3])
            ws.write(a, 5, '%s' % per[4])
            ws.write(a, 6, '%s' % per[5])
            ws.write(a, 7, '%s' % per[6])
            ws.write(a, 8, '%s' % per[7])
            ws.write(a, 9, '%s' % per[8], date_format)
            ws.write(a, 10, '%s' % per[9])
            ws.write(a, 11, '%s' % per[10])
            ws.write(a, 12, '%s' % per[11])
            ws.write(a, 13, '%s' % per[12])
            ws.write(a, 14, '%s' % per[13])
            ws.write(a, 15, '%s' % per[14])
            ws.write(a, 16, '%s' % per[15])
            ws.write(a, 17, '%s' % per[16])  # per[33]
            ws.write(a, 18, '%s' % per[17])
            ws.write(a, 19, '%s' % per[18])
            ws.write(a, 20, '%s' % per[19])
            ws.write(a, 21, '%s' % per[20])
            ws.write(a, 22, '%s' % per[21])
            ws.write(a, 23, '%s' % per[22])
            ws.write(a, 24, '%s' % per[23])
            ws.write(a, 25, '%s' % per[24])
            ws.write(a, 26, '%s' % per[25] if per[25] else '')
            ws.write(a, 27, '%s' % per[26] if per[26] else '')
            ws.write(a, 28, '%s' % per[27])
            ws.write(a, 29, '%s' % per[28] if per[28] else '')
            ws.write(a, 30, '%s' % per[29] if per[29] else '')
            ws.write(a, 31, '%s' % per[30])
            ws.write(a, 32, '%s' % per[31])
            ws.write(a, 33, '%s' % per[32])
            ws.write(a, 34, '%s' % per[33] if per[33] else '')
            ws.write(a, 35, '%s' % per[34])
            ws.write(a, 36, '%s' % 'SI' if per[35] else 'NO')
            ws.write(a, 37, '%s' % "SI" if per[36] else "NO")
            ws.write(a, 38, '%s' % ('SI' if per[37] else 'NO') if per[36] else "")
            ws.write(a, 39, '%s' % (per[38] if per[38] else '') if per[36] else "")
            ws.write(a, 40, '%s' % 'SI' if haber_aprobado_modulos_computacion(per[15]) else 'NO')
        wb.save(directory)
        if eNotificacion:
            titulo = f'Reporte de matriculados del periodo {ePeriodo.nombre} listo'.strip()
            eNotificacion.en_proceso = False
            eNotificacion.titulo = titulo
            eNotificacion.url = "{}/niveles/reportes/{}".format(MEDIA_URL, nombre_archivo)
            eNotificacion.save(usuario_id=usernotify.id)
        subscriptions = ePersona.usuario.webpush_info.select_related("subscription")
        push_infos = SubscriptionInfomation.objects.filter(subscription_id__in=subscriptions.values_list('subscription__id', flat=True), app=1, status=True).select_related("subscription")
        for device in push_infos:
            try:
                payload = {"head": "Reporte de matriculados terminado",
                           "body": f'Reporte de matriculados del periodo {ePeriodo.nombre} desde el módulo de niveles',
                           "action": "notificacion",
                           "timestamp": time.mktime(datetime.now().timetuple()),
                           "url": eNotificacion.url,
                           "btn_notificaciones": traerNotificaciones(None, None, ePersona),
                           "mensaje": 'Su reporte ha sido generado con exito'}
                _send_notification(device.subscription, json.dumps(payload), ttl=500)
            except Exception as exep:
                print(f"Fallo de envio del push notification: {exep.__str__()}")
    except Exception as ex:
        print(ex)
        print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
        textoerror = '{} Linea:{}'.format(ex, sys.exc_info()[-1].tb_lineno)
        if eNotificacion:
            eNotificacion = Notificacion.objects.get(pk=eNotificacion.pk)
            eNotificacion.en_proceso = False
            eNotificacion.cuerpo = textoerror
            eNotificacion.url = None
            eNotificacion.save(usuario_id=usernotify.id)
        else:
            eNotificacion = Notificacion(cuerpo=textoerror,
                                         titulo=f'Error en el reporte de matriculados del periodo {ePeriodo.nombre}'.strip(),
                                         destinatario=ePersona,
                                         url=None,
                                         prioridad=1,
                                         app_label='SGA',
                                         fecha_hora_visible=datetime.now() + timedelta(days=1),
                                         tipo=2,
                                         perfil=ePersona.perfilusuario_administrativo(),
                                         en_proceso=False)
            eNotificacion.save(usuario_id=usernotify.id)
