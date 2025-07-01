# import sys
# import os
# import random
# import xlwt
# import time
# from datetime import datetime, timedelta
# from django.db.models import Q
# from sga.commonviews import traerNotificaciones
# from settings import MEDIA_ROOT, MEDIA_URL, DEBUG
# from sga.models import Matricula, Malla, RequisitoTitulacionMalla, Persona, Notificacion, Periodo
# from webpush import send_user_notification
# _ePersona = Persona.objects.get(pk=10730)
# ePeriodo = Periodo.objects.get(pk=317)
# try:
#     directory = os.path.join(MEDIA_ROOT, 'reportes')
#     try:
#         os.stat(directory)
#     except:
#         os.mkdir(directory)
#     nombre_archivo = "reporte_derecho_en_linea_{}.xls".format(random.randint(1, 10000).__str__())
#     directory = os.path.join(MEDIA_ROOT, 'reportes', nombre_archivo)
#     fuentecabecera = xlwt.easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
#     fuentenormal = xlwt.easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
#     wb = xlwt.Workbook()
#     ws_1 = wb.add_sheet("Hoja1")
#     fil = 0
#     columnas = [
#         (u"idMatricula", 7000, 0),
#         (u"Documento", 7000, 0),
#         (u"NombreCompleto", 7000, 0),
#         (u"NivelMatricula", 7000, 0),
#         (u"idMateria", 7000, 0),
#         (u"Asignatura", 7000, 0),
#         (u"NivelAsignatura", 7000, 0),
#     ]
#     aRequisitos = []
#     eMalla = Malla.objects.get(pk=480)
#     eRequisitoTitulacionMallas = RequisitoTitulacionMalla.objects.filter(malla=eMalla, status=True).order_by('requisito__nombre')
#     num = 1
#     for eRequisitoTitulacionMalla in eRequisitoTitulacionMallas:
#         columnas.append((f"R{num}", 7000, 0))
#         aRequisitos.append({'id': eRequisitoTitulacionMalla.requisito_id, 'name': eRequisitoTitulacionMalla.requisito.nombre, 'num': num})
#         num += 1
#     for col_num in range(len(columnas)):
#         ws_1.write(fil, col_num, columnas[col_num][0], fuentecabecera)
#         ws_1.col(col_num).width = columnas[col_num][1]
#     filtro = Q(nivel__periodo=ePeriodo) & Q(status=True) & Q(inscripcion__inscripcionmalla__malla=eMalla) & \
#              Q(inscripcion__inscripcionmalla__status=True) & Q(nivelmalla_id__gte=8)
#     eMatriculas = Matricula.objects.filter(filtro)
#     total = eMatriculas.values("id").count()
#     cont = 1
#     fila = 1
#     for eMatricula in eMatriculas:
#         eInscripcion = eMatricula.inscripcion
#         ePersona = eInscripcion.persona
#         _eMaterias = eMatricula.materias()
#         for _eMateria in _eMaterias:
#             eMateria = _eMateria.materia
#             print(f"({total}/{cont}) -> {ePersona.nombre_completo_inverso()} >> {eMateria.asignaturamalla.asignatura.nombre}")
#             ws_1.write(fila, 0, "%s" % eMatricula.id, fuentenormal)  # idmatricula
#             ws_1.write(fila, 1, "%s" % ePersona.documento(), fuentenormal)  # documento
#             ws_1.write(fila, 2, "%s" % ePersona.nombre_completo_inverso(), fuentenormal)  # nombre_completo
#             ws_1.write(fila, 3, "%s" % eMatricula.nivelmalla.nombre if eMatricula.nivelmalla else "", fuentenormal)  # NivelMatricula
#             ws_1.write(fila, 4, "%s" % eMateria.id, fuentenormal) #idMateria
#             ws_1.write(fila, 5, "%s" % eMateria.asignaturamalla.asignatura.nombre, fuentenormal) #Asignatura
#             ws_1.write(fila, 6, "%s" % eMateria.asignaturamalla.nivelmalla.nombre, fuentenormal) #NivelAsignatura
#             col = 6
#             for aRequisito in aRequisitos:
#                 col += 1
#                 idRequisito = aRequisito.get('id', '0')
#                 if (eRequisito := eMateria.requisitomateriaunidadintegracioncurricular_set.filter(status=True, inscripcion=True, activo=True, obligatorio=True, requisito_id=idRequisito).first()) is not None:
#                     cumple = eRequisito.run(eInscripcion.pk)
#                     ws_1.write(fila, col, "%s" % 'SI' if cumple else 'NO', fuentenormal)  #REQUISITO
#                 else:
#                     ws_1.write(fila, col, "N/A", fuentenormal)  #REQUISITO
#             fila += 1
#             cont += 1
#
#     """HOJA2"""
#     ws_2 = wb.add_sheet("Hoja2")
#     fil = 0
#     columnas = [
#         (u"Requisito", 7000, 0),
#         (u"Descripción", 7000, 0),
#     ]
#     for col_num in range(len(columnas)):
#         ws_2.write(fil, col_num, columnas[col_num][0], fuentecabecera)
#         ws_2.col(col_num).width = columnas[col_num][1]
#     fila = 1
#     for aRequisito in aRequisitos:
#         ws_2.write(fila, 0, "%s" % aRequisito.get('num', '0'), fuentenormal) #Requisito
#         ws_2.write(fila, 1, "%s" % aRequisito.get('name', ''), fuentenormal) #Descripción
#         fila += 1
#     wb.save(directory)
#
#     eNotificacion = Notificacion(cuerpo=f'Reporte de estudiantes de la carrera de derecho en línea listo',
#                                  titulo=f'Reporte de estudiantes de la carrera de derecho en línea',
#                                  destinatario=_ePersona,
#                                  url="{}reportes/{}".format(MEDIA_URL, nombre_archivo),
#                                  prioridad=1,
#                                  app_label='SGA',
#                                  fecha_hora_visible=datetime.now() + timedelta(days=1),
#                                  tipo=2,
#                                  en_proceso=False)
#     eNotificacion.save()
#     send_user_notification(user=_ePersona.usuario,
#                            payload={"head": "Reporte de estudiantes de la carrera de derecho en línea",
#                                     "body": 'Reporte de estudiantes de la carrera de derecho en línea listo',
#                                     "action": "notificacion",
#                                     "timestamp": time.mktime(datetime.now().timetuple()),
#                                     "url": "{}reportes/{}".format(MEDIA_URL, nombre_archivo),
#                                     "btn_notificaciones": traerNotificaciones(None, None, _ePersona),
#                                     "mensaje": 'Su reporte ha sido generado con exito'
#                                     },
#                            ttl=500)
#     print("Proceso finalizado. . .")
#
# except Exception as ex:
#     msg = ex.__str__()
#     textoerror = '{} Linea:{}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
#     print(textoerror)
#     print(msg)
#     eNotificacion = Notificacion(cuerpo=textoerror,
#                                  titulo=f'Reporte de estudiantes de la carrera de derecho en línea ha fallado',
#                                  destinatario=_ePersona,
#                                  prioridad=1,
#                                  app_label='SGA',
#                                  fecha_hora_visible=datetime.now() + timedelta(days=1),
#                                  tipo=2,
#                                  en_proceso=False,
#                                  error=True)
#     eNotificacion.save()
#     send_user_notification(user=_ePersona.usuario,
#                            payload={"head": "Reporte de estudiantes de la carrera de derecho en línea ha fallado en la ejecución",
#                                     "body": 'Reporte de estudiantes de la carrera de derecho en línea ha fallado',
#                                     "action": "notificacion",
#                                     "timestamp": time.mktime(datetime.now().timetuple()),
#                                     "btn_notificaciones": traerNotificaciones(None, None, _ePersona),
#                                     "mensaje": textoerror,
#                                     "error": True
#                                     },
#                            ttl=500)



#!/bin/bash

# Lista de aplicaciones Django
APPS=['channels',
    'sga',
    'sagest',
    'med',
    'bib',
    'socioecon',
    'mobile',
    'moodle',
    'posgrado',
    'helpdesk',
    'investigacion',
    'admision',
    'clrncelery',
    'balcon',
    'inno',
    'bd',
    'api',
    'crispy_forms',
    'certi',
    'elfinderfs',
    'voto',
    'even',
    'matricula',
    'evath',
    'soap',
    'pdip',
    'postulaciondip',
    'webpush',
    'pwa',
    'wpush',
    'postulate',
    'poli',
    'becadocente',
    'ws',
    'gdocumental',
    'feria',
    'faceid',
    'empresa',
    'empleo',
    'cita',
    'plan',
    'secretaria',
    'vincula',
    'homologa',
    'edcon',
    'automatiza',
    'idioma',
    'oma',
    'ejecuform',
    'juventud']  # Agrega aquí el nombre de tus aplicaciones

# Directorio donde se encuentra el proyecto Django
PROJECT_DIR="D:/UNEMI/github/academico"
import os

def create_migrations_structure():
    # Navegar al directorio del proyecto
    os.chdir(PROJECT_DIR)

    # Recorrer cada aplicación y crear la carpeta migrations con el archivo __init__.py
    for app in APPS:
        print(f"/{app}/migrations/");
        migrations_dir = os.path.join(app, "migrations")

        # Crear la carpeta migrations si no existe
        if not os.path.exists(migrations_dir):
            os.makedirs(migrations_dir)

        # Crear el archivo __init__.py dentro de la carpeta migrations
        init_file = os.path.join(migrations_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, "w") as f:
                pass  # Archivo vacío

    print("Estructura de migrations creada exitosamente.")


if __name__ == "__main__":
    create_migrations_structure()