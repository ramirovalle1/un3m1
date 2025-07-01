#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

from django.db import transaction

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
import xlrd
from time import sleep
from sga.models import *
from sagest.models import *
from datetime import date
from settings import PROFESORES_GROUP_ID
from sga.funciones import calculate_username, generar_usuario, fechatope, null_to_decimal
import xlwt
from xlwt import *
import unicodedata


# for materias in Materia.objects.filter(nivel__periodo_id=82).exclude(nivel__sesion_id__in=[12, 13]).distinct('asignaturamalla__malla').order_by('asignaturamalla__malla'):
#     print('%s' % materias.asignaturamalla.malla)

# # ARREGLA SALDOS DEL KARDEX
# # arregla kardex ay que poner al comienzo un id menor para que funcione
# producto = Producto.objects.get(pk=102)
# idanterior = 29768
# idnormal = 29774
# arregloid = KardexInventario.objects.values_list('id', flat=True).filter(producto=producto, id__gte=idanterior, status=True).order_by('id')
# i = 0
# for k in KardexInventario.objects.filter(producto=producto, id__gte=idnormal, status=True).order_by('id'):
#     print (k.id)
#     saldoanterior = KardexInventario.objects.get(pk=arregloid[i]).saldofinalvalor
#     cantidadanterior = KardexInventario.objects.get(pk=arregloid[i]).saldofinalcantidad
#     print (saldoanterior)
#     k.saldoinicialvalor = saldoanterior
#     k.saldoinicialcantidad = cantidadanterior
#     k.costo = Decimal(2.7048).quantize(Decimal('.0000000000000001'))
#     valor = Decimal(k.cantidad * k.costo).quantize(Decimal('.0000000000000001'))
#     if k.valor != valor:
#         k.valor = valor
#     if k.tipomovimiento == 2:
#         k.saldofinalvalor = saldoanterior - k.valor
#         k.saldofinalcantidad = cantidadanterior - k.cantidad
#     else:
#         k.saldofinalvalor = saldoanterior + k.valor
#         k.saldofinalcantidad = cantidadanterior + k.cantidad
#     k.save()
#     i += 1
# kardex = KardexInventario.objects.filter(producto=producto, status=True).order_by('-id')[0]
# valorproducto = kardex.saldofinalvalor
# cantidadproducto = kardex.saldofinalcantidad
# costoproducto = kardex.costo
# InventarioReal.objects.filter(producto=producto, status=True).update(valor=valorproducto, cantidad=cantidadproducto, costo=costoproducto)
# #

# while True:
#     #do some serial sending here
#     sleep(60)
#     print("hola")

# # SOLICITAR CAMBIO DE CLAVE
# for ins in Inscripcion.objects.all():
#     ins.persona.cambiar_clave()
#     print(ins.persona)
#
#
# for adm in Administrativo.objects.all():
#     adm.persona.cambiar_clave()
#     print(adm.persona)
#
# for adm in Profesor.objects.all():
#     adm.persona.cambiar_clave()
#     print(adm.persona)

# for noticia in Noticia.objects.all():
#     tiponoticia = TipoNoticias.objects.get(pk=noticia.tipo)
#     noticia.tipos.add(tiponoticia)
#     if noticia.tipo == 4 or noticia.tipo == 5:
#         for c in Coordinacion.objects.filter(status=True).exclude(pk__in=[6, 7, 8]):
#             for ca in c.carreras():
#                 noticia.carreras.add(ca)

# MASIVO PARA ASIGNAR COMO DOCENTE
# workbook = xlrd.open_workbook("tutores.xlsx")
# sheet = workbook.sheet_by_index(0)
# linea = 1
# for rowx in range(sheet.nrows):
#     if linea>1:
#         cols = sheet.row_values(rowx)
#         if Persona.objects.values("id").filter(cedula=cols[0]).exists():
#             persona = Persona.objects.get(cedula=cols[0])
#             if not persona.es_profesor():
#                 profesor = Profesor(persona=persona,
#                                     activo=True,
#                                     fechaingreso=datetime.now().date(),
#                                     coordinacion=Coordinacion.objects.all()[0],
#                                     dedicacion=TiempoDedicacionDocente.objects.all()[0])
#                 profesor.save()
#                 grupo = Group.objects.get(pk=PROFESORES_GROUP_ID)
#                 if not persona.usuario:
#                     username = calculate_username(persona)
#                     generar_usuario(persona, username, PROFESORES_GROUP_ID)
#
#                 grupo.user_set.add(persona.usuario)
#                 grupo.save()
#                 persona.crear_perfil(profesor=profesor)
#         else:
#             print("Cedula no existe: %s" % cols[0])
#     linea = linea + 1

# homologa asignaturas individual por malla
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, carrera__coordinacion__id=4):
#         malla = inscripcion.carrera.malla()
#         print('%s - %s' % (linea, inscripcion))
#         for asignaturashomologa in malla.asignaturamalla_set.filter(status=True).exclude(pk__in=[x.asignaturamalla_id for x in RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion)]):
#             if not asignaturashomologa.id in [7450, 6424]:
#                 inscripcionold = inscripcion.inscripcionold
#                 equivalencias = asignaturashomologa.tablaequivalenciaasignaturas_set.filter(status=True)
#                 notamayor = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold, asignatura__in=[x.asignatura for x in equivalencias]).order_by('-nota')
#                 if notamayor:
#                     noaplica = False
#                     nota = notamayor[0].nota
#                     asistencia = notamayor[0].asistencia
#                     fecha = notamayor[0].fecha
#                     observaciones = u'%s (MIGRACION - PROCESO DE RECONOCIMIENTO DE CREDITOS 2019 - SOLICITADO POR LA DECANA)' % notamayor[0].asignatura
#                     if not RecordAcademico.objects.filter(inscripcion=inscripcion, asignatura=asignaturashomologa.asignatura, asignaturamalla=asignaturashomologa).exists():
#                         record = RecordAcademico(inscripcion=inscripcion,
#                                                  asignatura=asignaturashomologa.asignatura,
#                                                  asignaturamalla=asignaturashomologa,
#                                                  fecha=fecha,
#                                                  valida=True,
#                                                  validapromedio=True,
#                                                  aprobada=True,
#                                                  homologada=False,
#                                                  convalidacion=False,
#                                                  pendiente=False)
#                     else:
#                         record = RecordAcademico.objects.get(inscripcion=inscripcion, asignatura=asignaturashomologa.asignatura, asignaturamalla=asignaturashomologa)
#                     record.creditos = asignaturashomologa.creditos
#                     record.horas = asignaturashomologa.horas
#                     record.observaciones = observaciones
#                     record.noaplica = noaplica
#                     record.asistencia = asistencia
#                     record.nota = nota
#                     record.save()
#                     record.actualizar()
#                     if MateriaAsignada.objects.filter(matricula__inscripcion=inscripcion, materia__asignaturamalla=asignaturashomologa, matricula__nivel__periodo_id=85).exists():
#                         MateriaAsignada.objects.filter(matricula__inscripcion=inscripcion, materia__asignaturamalla=asignaturashomologa, matricula__nivel__periodo_id=85).delete()
#                     print('%s - %s' % (linea, asignaturashomologa.asignatura))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
#




# # Limpia matricula por coordinaciones
# try:
#     linea = 0
#     for matricula in Matricula.objects.filter(nivel__periodo_id=85, inscripcion__carrera__coordinacion__id=5):
#         linea += 1
#         print('%s - %s' % (linea, matricula))
#         matricula.delete()
#
# except Exception as ex:
#     print('error: %s' % ex)





# try:
#     linea = 0
#     cursor = connection.cursor()
#     periodonuevo = Periodo.objects.get(pk=85)
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, carrera__coordinacion__id__in=[2, 3, 4, 5]).exclude(matricula__nivel__periodo=periodonuevo):
#         linea += 1
#         # if Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodonuevo).exists():
#         #     Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodonuevo).delete()
#
#         if not Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodonuevo).exists():
#
#             sql = """SELECT masig.matricula_id,niv.sesion_id,sesi.nombre,count(niv.sesion_id) as d
#                     FROM sga_materiaasignada masig
#                     INNER JOIN sga_materia mate ON masig.materia_id=mate.id
#                     INNER JOIN sga_nivel niv ON mate.nivel_id=niv.id
#                     INNER JOIN sga_matricula mat ON mat.id=masig.matricula_id
#                     INNER JOIN sga_sesion sesi ON niv.sesion_id=sesi.id
#                     WHERE niv.periodo_id=82 AND mat.inscripcion_id=%s
#                     group by masig.matricula_id,niv.sesion_id,sesi.nombre
#                     order BY d desc limit 1""" % inscripcion.inscripcionold_id
#             cursor.execute(sql)
#             results = cursor.fetchall()
#             bandera = False
#             sesion = None
#             for r in results:
#                 bandera = True
#                 sesion = Sesion.objects.get(pk=int(r[1]))
#             if not bandera:
#                 sesion = Sesion.objects.get(pk=inscripcion.sesion_id)
#             coordinacion = inscripcion.carrera.coordinacion_carrera()
#             nivel = Nivel.objects.filter(periodo=periodonuevo, sesion=sesion, nivellibrecoordinacion__coordinacion=coordinacion).exclude(modalidad__id=3)
#             malla = inscripcion.carrera.malla()
#             nivelinscripcion = malla.lista_materias_nivelmigrado_aux(inscripcion)
#             materiasamatricular = malla.lista_materias_nivelmigrado_amatricular(inscripcion, nivelinscripcion)
#             matricula = Matricula(inscripcion=inscripcion,
#                                   nivel=nivel[0],
#                                   nivelmalla_id=nivelinscripcion,
#                                   pago=False,
#                                   iece=False,
#                                   becado=False,
#                                   porcientobeca=0,
#                                   fecha=datetime.now().date(),
#                                   hora=datetime.now().time(),
#                                   fechatope=fechatope(datetime.now().date()),
#                                   estado_matricula=2)
#             matricula.save()
#             paralelos = ['A1', 'B1', 'C1', 'S1']
#             for materia in Materia.objects.filter(nivel__periodo=periodonuevo, asignaturamalla__malla__carrera=inscripcion.carrera, nivel__sesion=sesion, paralelo__in=paralelos, asignaturamalla__in=materiasamatricular).distinct():
#                 materianueva = materia
#                 if not RecordAcademico.objects.filter(inscripcion=inscripcion, status=True, asignaturamalla=materianueva.asignaturamalla, aprobada=True).exists():
#                     if not MateriaAsignada.objects.values('id').filter(matricula=matricula, materia=materianueva).exists():
#                         materiaasignada = MateriaAsignada(matricula=matricula,
#                                                           materia=materianueva,
#                                                           notafinal=0,
#                                                           asistenciafinal=0,
#                                                           cerrado=False,
#                                                           matriculas=1,
#                                                           observaciones='',
#                                                           estado_id=NOTA_ESTADO_EN_CURSO)
#                         materiaasignada.save()
#                         materiaasignada.asistencias()
#                         materiaasignada.evaluacion()
#                         materiaasignada.mis_planificaciones()
#                         materiaasignada.save()
#
#             matricula.actualizar_horas_creditos()
#             matricula.estado_matricula = 2
#             matricula.save()
#             if inscripcion.tiene_nivel():
#                 ficha = inscripcion.inscripcionnivel_set.all()[0]
#             else:
#                 ficha = InscripcionNivel(inscripcion=inscripcion)
#             ficha.nivel_id = nivelinscripcion
#             ficha.save()
#             matricula.calcula_nivel()
#
#
#         print('%s - %s' % (linea, inscripcion))
#
# except Exception as ex:
#     print('error: %s' % ex)
# #



# import xlwt
# from xlwt import *
# from django.http import HttpResponse
#
# inicio = (datetime(2018, 6, 25, 0, 0, 0)).date()
# fin = (datetime(2018, 7, 1, 23, 59, 59)).date()
#
# response = HttpResponse(content_type="application/ms-excel")
# response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
# style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
# style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
# style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
# title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
# style1 = easyxf(num_format_str='D-MMM-YY')
# font_style = XFStyle()
# font_style.font.bold = True
# font_style2 = XFStyle()
# font_style2.font.bold = False
# wb = xlwt.Workbook()
# ws = wb.add_sheet('Sheetname')
# estilo = xlwt.easyxf('font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
# ws.write_merge(0, 0, 0, 9, 'UNIVERSIDAD ESTATAL DE MILAGRO', estilo)
# output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
# nombre = "LISTADOFINAL" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
# filename = os.path.join(output_folder, nombre)
# columns = [ (u"FACULTAD", 6000),
#             (u"CARRERA", 6000),
#             (u"NIVEL", 6000),
#             (u"ALUMNO", 6000),
#             (u"SESION", 6000),
#             (u"ASIGNATURA", 6000),
#             ]
# row_num = 3
# for col_num in range(len(columns)):
#     ws.write(row_num, col_num, columns[col_num][0], font_style)
#     ws.col(col_num).width = columns[col_num][1]
# row_num = 4
# print(Inscripcion.objects.filter(inscripcionold__isnull=False).count())
# con = 0
# for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#     malla = inscripcion.mi_malla()
#     listaasignatura = AsignaturaMalla.objects.filter(malla=malla).exclude(pk__in=[ x.asignaturamalla_id for x in RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion, asignaturamalla__isnull=False)]).order_by("nivelmalla")[:5]
#     for asignatura in listaasignatura:
#         ws.write(row_num, 0, u'%s' % inscripcion.carrera.mi_coordinacion(), font_style2)
#         ws.write(row_num, 1, u'%s' % inscripcion.carrera, font_style2)
#         ws.write(row_num, 2, u'%s' % asignatura.nivelmalla, font_style2)
#         ws.write(row_num, 3, u'%s' % inscripcion.persona, font_style2)
#         ws.write(row_num, 4, u'%s' % inscripcion.sesion, font_style2)
#         ws.write(row_num, 5, u'%s' % asignatura.asignatura, font_style2)
#         row_num += 1
#     con += 1
#     print(u'%s - %s' % (con, inscripcion))
# wb.save(filename)


#
# linea = 0
# for matricula in Matricula.objects.filter(nivel__periodo_id=85, inscripcion__carrera__coordinacion__id__in=[2, 3, 4, 5]):
#     matricula.grupo_socio_economico(1)
#     linea += 1
#     print("%s - %s" % (linea, matricula))


### homologa modulos de los estudiantes
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False).exclude(pk=83939):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold, modulomalla__isnull=False).order_by('id')
#         for record in modulos:
#             record.id = None
#             record.inscripcion = inscripcion
#             observaciones = u'%s (MIGRACION - PROCESO DE RC 2019)' % record.observaciones
#             record.observaciones = observaciones
#             record.save()
#             record.actualizar()
#             print('------------------  %s - %s' % (linea, record.modulomalla))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)


# for n in Nivel.objects.filter(id__in=[419,420,418,421]):
#     for m in n.materia_set.all():
#         m.clase_set.all().delete()


## CAMBIAR PRACTICAS A LA NUEVA MALLA
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         practicas = ParticipantesMatrices.objects.filter(status=True, inscripcion=inscripcionold).order_by('id')
#         for practica in practicas:
#             practica.inscripcion = inscripcion
#             practica.save()
#             print('------------------  %s - %s' % (linea, practica))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)


# poner asistencia dia lunes


# fecha = (datetime(2019, 8, 5, 0, 0, 0)).date()
# print("FECHA A PROCESAR: " + fecha.__str__() + "\r")
# for cl in Clase.objects.filter(activo=True, inicio__lte=fecha, fin__gte=fecha, dia=(fecha.weekday() + 1), status=True, materia__nivel__periodo_id=85):
#     if cl.materia.profesor_principal():
#         if LeccionGrupo.objects.filter(profesor=cl.materia.profesor_principal(), turno=cl.turno, fecha=fecha).exists():
#             lecciongrupo = LeccionGrupo.objects.get(profesor=cl.materia.profesor_principal(), turno=cl.turno, fecha=fecha)
#         else:
#             lecciongrupo = LeccionGrupo(profesor=cl.materia.profesor_principal(),
#                                         turno=cl.turno,
#                                         aula=cl.aula,
#                                         dia=cl.dia,
#                                         fecha=fecha,
#                                         horaentrada=cl.turno.comienza,
#                                         horasalida=cl.turno.termina,
#                                         abierta=False,
#                                         automatica=True,
#                                         contenido='REGISTRO MASIVO 2019 - AUTORIZADO POR DIRECTOR TICS',
#                                         observaciones='REGISTRO MASIVO 2019 - AUTORIZADO POR DIRECTOR TICS')
#             lecciongrupo.save()
#         if Leccion.objects.filter(clase=cl, fecha=fecha).exists():
#             leccion = Leccion.objects.get(clase=cl, fecha=fecha)
#         else:
#             leccion = Leccion(clase=cl,
#                               fecha=fecha,
#                               horaentrada=cl.turno.comienza,
#                               horasalida=cl.turno.termina,
#                               abierta=True,
#                               contenido=lecciongrupo.contenido,
#                               observaciones=lecciongrupo.observaciones)
#             leccion.save()
#         if not lecciongrupo.lecciones.filter(pk=leccion.id).exists():
#             lecciongrupo.lecciones.add(leccion)
#         if AsistenciaLeccion.objects.filter(leccion=leccion).exists():
#             for asis in AsistenciaLeccion.objects.filter(leccion=leccion):
#                 if not asis.asistio:
#                     asis.asistio = True
#                     asis.save()
#                     mateasig = asis.materiaasignada
#                     mateasig.save(actualiza=True)
#                     mateasig.actualiza_estado()
#         else:
#             for materiaasignada in cl.materia.asignados_a_esta_materia():
#                 if not AsistenciaLeccion.objects.filter(leccion=leccion, materiaasignada=materiaasignada).exists():
#                     asistencialeccion = AsistenciaLeccion(leccion=leccion,
#                                                           materiaasignada=materiaasignada,
#                                                           asistio=True)
#                     asistencialeccion.save()
#                     materiaasignada.save(actualiza=True)
#                     materiaasignada.actualiza_estado()
#                 # guardar temas de silabo
#         lecciongrupo.save()
#         print(cl)


# fin poner asistencia dia lunes





# for ma in Materia.objects.filter(status=True, nivel__periodo__id=variable_valor('PERIODO_PROCESO_MOODLE')):
#     clase = Clase.objects.filter(materia=ma, status=True, activo=True, dia=inicio.isoweekday(), inicio__lte=inicio, fin__gte=inicio, turno__comienza__gte='18:00')
#     for cl in clase:
#         if not Leccion.objects.filter(clase=cl, status=True, fecha=inicio).exists():
#             lec = Leccion(clase=cl,
#                               fecha=inicio,
#                               horaentrada=cl.turno.comienza,
#                               abierta=False,
#                               horasalida=cl.turno.termina,
#                               observaciones='INCONVENIENTE TECNOLOGICO',
#                               automatica=True,
#                               aperturaleccion=True)
#             lec.save()
#             if LeccionGrupo.objects.filter(profesor=ma.profesor_materia_principal().profesor, turno=cl.turno, fecha=inicio).exists():
#                 lecciongrupo = LeccionGrupo.objects.get(profesor=ma.profesor_materia_principal().profesor, turno=cl.turno, fecha=inicio)
#             else:
#                 lecciongrupo = LeccionGrupo(profesor=ma.profesor_materia_principal().profesor,
#                                             turno=cl.turno,
#                                             aula=cl.aula,
#                                             dia=cl.dia,
#                                             fecha=inicio,
#                                             horaentrada=cl.turno.comienza,
#                                             horasalida=cl.turno.termina,
#                                             abierta=False,
#                                             automatica=True,
#                                             observaciones=lec.observaciones)
#                 lecciongrupo.save()
#             lecciongrupo.lecciones.add(lec)
#             for materiaasignada in ma.asignados_a_esta_materia():
#                 asistencialeccion = AsistenciaLeccion(leccion=lec,
#                                                       materiaasignada=materiaasignada,
#                                                       asistio=True)
#                 asistencialeccion.save()
#                 asistencialeccion.save(actualiza=True)
#             lecciongrupo.save()
#             print(cl)
#





# ## homologa modulos de los estudiantes
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         for asigmal in AsignaturaMalla.objects.filter(malla_id=22):
#             modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold, asignatura=asigmal.asignatura).order_by('id')
#             if modulos:
#                 if not RecordAcademico.objects.filter(inscripcion=inscripcion, asignatura=asigmal.asignatura, status=True):
#                     for record in modulos:
#                         record.id = None
#                         record.inscripcion = inscripcion
#                         observaciones = u'%s (MIGRACION - PROCESO DE RC 2019)' % record.observaciones
#                         record.observaciones = observaciones
#                         record.save()
#                         record.actualizar()
#                         print('------------------  %s - %s' % (linea, record.asignatura))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)

# cursor = connection.cursor()
# sql="""
#     SELECT t.*
#     FROM (SELECT COUNT(id) AS cant, s.silabo_id, s.fechainiciosemana, s.fechafinciosemana
#     from sga_silabosemanal s
#     GROUP BY s.silabo_id, s.fechainiciosemana, s.fechafinciosemana) AS t
#     WHERE t.cant>1
# """
# cursor.execute(sql)
# results = cursor.fetchall()
# for r in results:
#     recorre = 1
#     for dele in SilaboSemanal.objects.filter(silabo_id=int(r[1]), fechainiciosemana=r[2], fechafinciosemana=r[3]).order_by('-id'):
#         if recorre < int(r[0]):
#             dele.delete()
#         recorre += 1
#         print(dele)


# # ## COPIA DE BACKCUP ASISTENCIA
# try:
#     linea = 1
#     cursorbackup = connections['backup'].cursor()
#     cursor = connections['default'].cursor()
#     sql="""
#             SELECT l.id, l.clase_id, l.fecha, l.horaentrada, l.horasalida, l.abierta, l.contenido, l.observaciones,
#             l.estrategiasmetodologicas, l.status, l.usuario_creacion_id, l.fecha_creacion, l.usuario_modificacion_id,
#             l.fecha_modificacion, l.ipingreso, l.ipexterna, l.motivoapertura, l.origen_movil, l.origen_coordinador, l.automatica,
#             l.solicitada, l.aperturaleccion
#             FROM sga_leccion l
#             INNER JOIN sga_clase cl ON cl.id=l.clase_id
#             INNER JOIN sga_materia ma ON ma.id=cl.materia_id
#             INNER JOIN sga_nivel ni ON ni.id=ma.nivel_id AND ni.periodo_id=82
#     """
#     cursorbackup.execute(sql)
#     results = cursorbackup.fetchall()
#     for r in results:
#         if not Leccion.objects.values("id").filter(status=True, pk=r[0]).exists():
#             Leccion.objects.filter(clase_id=r[1], fecha=r[2]).delete()
#             leccion = Leccion(id=r[0],
#                               clase_id=r[1], fecha=r[2], horaentrada=r[3], horasalida=r[4],
#                               abierta=r[5], contenido=r[6], observaciones=r[7], estrategiasmetodologicas=r[8], status=r[9], usuario_creacion_id=r[10],
#                               fecha_creacion=r[11], usuario_modificacion_id=r[12],fecha_modificacion=r[13],
#                               ipingreso=r[14], ipexterna=r[15], motivoapertura=r[16], origen_movil=r[17],
#                               origen_coordinador=r[18], automatica=r[19], solicitada=r[20], aperturaleccion=r[21])
#             leccion.save()
#         else:
#             leccion = Leccion.objects.get(status=True, pk=r[0])
#         ############ verificar si estan todas las asistencias cargadas
#         sqlasi = """
#                     SELECT id, leccion_id, asistio, materiaasignada_id, status, usuario_creacion_id,
#                     fecha_creacion,usuario_modificacion_id,fecha_modificacion,asistenciajustificada
#                     FROM sga_asistencialeccion a
#                     WHERE a.leccion_id=%s
#             """ % r[0]
#         cursorbackup.execute(sqlasi)
#         resultsasi = cursorbackup.fetchall()
#         for ra in resultsasi:
#             if MateriaAsignada.objects.filter(pk=ra[3]).exists():
#                 if not leccion.asistencialeccion_set.values("id").filter(materiaasignada_id=ra[3]).exists():
#                     asistencialeccion = AsistenciaLeccion(id=ra[0],leccion_id=ra[1],asistio=ra[2],materiaasignada_id=ra[3],
#                                                           status=ra[4],usuario_creacion_id=ra[5],
#                                                           fecha_creacion=ra[6],usuario_modificacion_id=ra[7],fecha_modificacion=ra[8],asistenciajustificada=ra[9])
#                     asistencialeccion.save()
#
#         ############ verificar si estan todas las evaluaciones lecciones cargadas
#         sqleva = """
#                     SELECT id, leccion_id, evaluacion, materiaasignada_id, status, usuario_creacion_id, fecha_creacion, usuario_modificacion_id, fecha_modificacion
#                     FROM sga_evaluacionleccion
#                     WHERE leccion_id=%s
#             """ % r[0]
#         cursorbackup.execute(sqleva)
#         resultseva = cursorbackup.fetchall()
#         for re in resultseva:
#             if not leccion.evaluacionleccion_set.values("id").filter(materiaasignada_id=re[3]).exists():
#                 evaluacionleccion = EvaluacionLeccion(id=re[0], leccion_id=re[1], evaluacion=re[2], materiaasignada_id=re[3], status=re[4], usuario_creacion_id=re[5],
#                                                       fecha_creacion=re[6], usuario_modificacion_id=re[7], fecha_modificacion=re[8])
#                 evaluacionleccion.save()
#
#         ############ verificar si estan todos los silabos cargadas
#         sqltem = """
#                     SELECT id, status, usuario_creacion_id, fecha_creacion, usuario_modificacion_id, fecha_modificacion,
#                     leccion_id, tema_id, fecha
#                     FROM sga_temaasistencia
#                     WHERE leccion_id=%s
#             """ % r[0]
#         cursorbackup.execute(sqltem)
#         resultstem = cursorbackup.fetchall()
#         for rt in resultstem:
#             if TemaAsistencia.objects.values("id").filter(pk=rt[0]).exists():
#                 temaasistencia = TemaAsistencia.objects.get(pk=rt[0])
#                 temaasistencia.leccion_id = r[0]
#                 temaasistencia.save()
#
#         ############ verificar si estan todas las leccionesGrupo cargadas
#         sqllgr = """
#                     SELECT id, lecciongrupo_id, leccion_id FROM sga_lecciongrupo_lecciones
#                     WHERE leccion_id=%s
#             """ % r[0]
#         cursorbackup.execute(sqllgr)
#         resultslgr = cursorbackup.fetchall()
#         for rlg in resultslgr:
#             sqlgr = """
#                         SELECT id, profesor_id, turno_id, aula_id, dia, fecha, horaentrada, horasalida, abierta, contenido, observaciones,
#                         estrategiasmetodologicas,origen_movil,motivoapertura,automatica,origen_coordinador,solicitada,
#                         status,usuario_creacion_id,fecha_creacion,usuario_modificacion_id,fecha_modificacion,ipingreso,ipexterna
#                         FROM sga_lecciongrupo
#                         WHERE id=%s
#                     """ % rlg[1]
#
#             cursorbackup.execute(sqlgr)
#             resultsgr = cursorbackup.fetchall()
#             for rg in resultsgr:
#                 if not LeccionGrupo.objects.values("id").filter(status=True, pk=rg[0]).exists():
#                     lecciongrupo = LeccionGrupo(id=rg[0],
#                                                 profesor_id=rg[1], turno_id=rg[2], aula_id=rg[3], dia=rg[4],
#                                                 fecha=rg[5], horaentrada=rg[6], horasalida=rg[7], abierta=rg[8],
#                                                 contenido=rg[9], observaciones=rg[10],
#                                                 estrategiasmetodologicas=rg[11], origen_movil=rg[12], motivoapertura=rg[13],
#                                                 automatica=rg[14], origen_coordinador=rg[15], solicitada=rg[16], status=rg[17],
#                                                 usuario_creacion_id=rg[18], fecha_creacion=rg[19], usuario_modificacion_id=rg[20], fecha_modificacion=rg[21],
#                                                 ipingreso=rg[22], ipexterna=rg[23])
#                     lecciongrupo.save()
#                 else:
#                     lecciongrupo = LeccionGrupo.objects.get(status=True, pk=rg[0])
#
#                 sqlunemi = """
#                             SELECT id, lecciongrupo_id, leccion_id FROM sga_lecciongrupo_lecciones
#                             WHERE leccion_id=%s and lecciongrupo_id=%s
#                             """ % (rlg[2], rlg[1])
#                 cursor.execute(sqlunemi)
#                 resultsunemi = cursor.fetchall()
#                 if not resultsunemi:
#                     sqlune = """
#                             INSERT INTO sga_lecciongrupo_lecciones(id, leccion_id, lecciongrupo_id) values(%s, %s, %s)
#                             """ % (rlg[0], rlg[2], rlg[1])
#                     cursor.execute(sqlune)
#         linea += 1
#         print("%s - %s" % (linea, leccion))
# except Exception as ex:
#     print('error: %s' % ex)

### FIN DE COPIA DE ASISTENCIA BACKCUP


# rubros = [125830,
# 103415,
# 125248,
# 122600,
# 125830,
# 103845,
# 103629,
# 122726,
# 128125,
# 103361,
# 129274,
# 128571,
# 122666,
# 122667,
# 128259,
# 129196,
# 103456,
# 127765,
# 127841,
# 126363
# ]
#
# for r in Rubro.objects.filter(id__in=rubros):
#     r.save()


# try:
#     __author__ = 'Unemi'
#
#     title = easyxf(
#         'font: name Times New Roman, color-index black, bold on , height 220; alignment: horiz left')
#     title2 = easyxf(
#         'font: name Verdana, color-index black, bold on , height 170; alignment: horiz left')
#
#     fuentecabecera = easyxf(
#         'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
#     fuentenormal = easyxf(
#         'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
#     fuentenormalneg = easyxf(
#         'font: name Verdana, color-index black, bold on , height 150; borders: left thin, right thin, top thin, bottom thin')
#     fuentenormalder = easyxf(
#         'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')
#     fuentemoneda = easyxf(
#         'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
#         num_format_str=' "$" #,##0.00')
#     fuentemonedaneg = easyxf(
#         'font: name Verdana, color-index black, bold on, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right; pattern: pattern solid, fore_colour gray25',
#         num_format_str=' "$" #,##0.00')
#
#     fuentenumero = easyxf(
#         'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
#         num_format_str='#,##0.00')
#
#     font_style = XFStyle()
#     font_style.font.bold = True
#     font_style2 = XFStyle()
#     font_style2.font.bold = False
#     wb = Workbook(encoding='utf-8')
#     ws = wb.add_sheet('Listado')
#
#     output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media', 'maestriainformes'))
#     nombre = "INFORME_MOVIMIENTOS_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#     filename = os.path.join(output_folder, nombre)
#
#
#
#     ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
#     ws.write_merge(1, 1, 0, 6, 'DIRECCIÓN ADMINISTRATIVA Y FINANCIERA', title)
#     ws.write_merge(2, 2, 0, 6, 'DEUDAS DE ESTUDIANTES', title)
#
#     row_num = 5
#
#     columns = [
#         (u"N°", 700),
#         (u"PERIODO", 8300),
#         (u"CARRERA", 8300),
#         (u"ESTUDIANTE", 8300),
#         (u"TIPO MOVIMIENTO", 4000),
#         (u"VALOR MAESTRIA", 3500),
#         (u"TOTAL GENERADO", 3500),
#         (u"TOTAL PAGADO", 3500),
#         (u"FORMA PAGO", 3500),
#         (u"FACTURA", 3500),
#         (u"TOTAL VENCIDO", 3500),
#         (u"TOTAL PENDIENTE", 3500),
#         (u"DESCUENTO", 3500)
#     ]
#     for col_num in range(len(columns)):
#         ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
#         ws.col(col_num).width = columns[col_num][1]
#     date_format = xlwt.XFStyle()
#     date_format.num_format_str = 'yyyy/mm/dd'
#
#     secuencia = 0
#     totalgenerado = Decimal(0)
#     totalpagado = Decimal(0)
#     totalvencido = Decimal(0)
#     totalpendiente = Decimal(0)
#     totalreprobado = Decimal(0)
#     totalvalormaestria = Decimal(0)
#     matriculas = Matricula.objects.filter(nivel__periodo__tipo_id__in=[3,4], status=True).distinct().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')[:200]
#     for lista in matriculas:
#         row_num += 1
#         secuencia += 1
#
#         alumno = lista.inscripcion.persona.apellido1 + ' ' + lista.inscripcion.persona.apellido2 + ' ' + lista.inscripcion.persona.nombres
#
#         # valorpagado = lista.total_pagado_alumno()
#         # valorreprobado = lista.total_rubro_modulo_reprobado()
#
#         valorgenerado = lista.total_generado_alumno()
#         valorvencido = lista.vencido_a_la_fechamatricula()
#         valorpendiente = lista.total_saldo_rubrosinanular()
#         # if not lista.retiradomatricula:
#         #     pass
#             # valorpendiente = lista.total_saldo_rubrosinanular()
#         # else:
#         #     valorgenerado = lista.total_generado_alumno_retirado()
#             # valorvencido = lista.total_saldo_alumno_retirado()
#             # valorpendiente = valorvencido
#
#         valormaestria = PeriodoCarreraCosto.objects.get(periodo=lista.nivel.periodo, carrera=lista.inscripcion.carrera).costo
#
#         ws.write(row_num, 0, secuencia, fuentenormalder)
#         ws.write(row_num, 1, u'%s' % lista.nivel.periodo, fuentenormal)
#         ws.write(row_num, 2, u'%s' % lista.inscripcion.carrera, fuentenormal)
#         ws.write(row_num, 3, alumno, fuentenormal)
#         ws.write(row_num, 4, 'COSTO', fuentenormal)
#         ws.write(row_num, 5, valormaestria, fuentemonedaneg)
#         ws.write(row_num, 6, valorgenerado, fuentemonedaneg)
#         # ws.write(row_num, 7, valorpagado, fuentemonedaneg)
#         ws.write(row_num, 8, '', fuentenormal)
#         ws.write(row_num, 9, '', fuentenormal)
#         ws.write(row_num, 10, valorvencido, fuentemonedaneg)
#         ws.write(row_num, 11, valorpendiente, fuentemonedaneg)
#         porcentaje = 0
#         valorbeca = 0
#         if lista.matriculanovedad_set.exists():
#             porcentaje = lista.matriculanovedad_set.all()[0].porcentajedescuento
#         if porcentaje > 0:
#             valordescontado = Decimal(null_to_decimal((valormaestria * porcentaje) / 100, 2)).quantize(Decimal('.01'))
#             valorbeca = valormaestria - null_to_decimal(valordescontado, 2)
#         ws.write(row_num, 12, valorbeca, fuentemonedaneg)
#         cuota = 0
#         for rubro in lista.rubro_set.filter(status=True).distinct().order_by('fechavence'):
#             row_num += 1
#             secuencia += 1
#             cuota += 1
#             anulado = Decimal(null_to_decimal(rubro.pago_set.filter(status=True, factura__valida=False, factura__status=True).aggregate(valor=Sum('valortotal'))['valor'], 2)).quantize(Decimal('.01'))
#             liquidado = Decimal(null_to_decimal(PagoLiquidacion.objects.filter(status=True, pagos__rubro=rubro).aggregate(valor=Sum('pagos__valortotal'))['valor'], 2)).quantize(Decimal('.01'))
#             ws.write(row_num, 0, secuencia, fuentenormalder)
#             ws.write(row_num, 1, u'%s' % lista.nivel.periodo, fuentenormal)
#             ws.write(row_num, 2, u'%s' % lista.inscripcion.carrera, fuentenormal)
#             ws.write(row_num, 3, alumno, fuentenormal)
#             ws.write(row_num, 4, 'CUOTA', fuentenormal)
#             ws.write(row_num, 5, '', fuentenormal)
#             ws.write(row_num, 6, (rubro.valortotal - (liquidado + anulado)), fuentemoneda)
#             ws.write(row_num, 7, 0, fuentemoneda)
#             ws.write(row_num, 8, '', fuentenormal)
#             ws.write(row_num, 9, '', fuentenormal)
#             for pago in rubro.pago_set.filter(status=True, pagoliquidacion__isnull=True):
#                 row_num += 1
#                 secuencia += 1
#                 ws.write(row_num, 0, secuencia, fuentenormalder)
#                 ws.write(row_num, 1, u'%s' % lista.nivel.periodo, fuentenormal)
#                 ws.write(row_num, 2, u'%s' % lista.inscripcion.carrera, fuentenormal)
#                 ws.write(row_num, 3, alumno, fuentenormal)
#                 ws.write(row_num, 4, 'PAGO', fuentenormal)
#                 ws.write(row_num, 5, '', fuentenormal)
#                 ws.write(row_num, 6, '', fuentenormal)
#                 ws.write(row_num, 7, pago.valortotal, fuentemoneda)
#                 ws.write(row_num, 8, pago.tipo(), fuentenormal)
#                 ws.write(row_num, 9, pago.factura().numerocompleto if pago.factura() else '', fuentenormal)
#
#         # ws.write(row_num, 5, valorgenerado, fuentemoneda)
#         # ws.write(row_num, 6, valorpagado, fuentemoneda)
#         # ws.write(row_num, 7, valorvencido, fuentemoneda)
#         # ws.write(row_num, 8, valorpendiente, fuentemoneda)
#         # ws.write(row_num, 9, valorreprobado, fuentemoneda)
#
#         # totalgenerado += Decimal(valorgenerado)
#         # totalpagado += Decimal(valorpagado)
#         # totalvencido += Decimal(valorvencido)
#         # totalpendiente += Decimal(valorpendiente)
#         # totalreprobado += Decimal(valorreprobado)
#         totalvalormaestria += Decimal(valormaestria)
#
#     row_num += 1
#     # ws.write_merge(row_num, row_num, 0, 3, "TOTALES", fuentenormalneg)
#     # ws.write(row_num, 4, totalvalormaestria, fuentemonedaneg)
#     # ws.write(row_num, 5, totalgenerado, fuentemonedaneg)
#     # ws.write(row_num, 6, totalpagado, fuentemonedaneg)
#     # ws.write(row_num, 7, totalvencido, fuentemonedaneg)
#     # ws.write(row_num, 8, totalpendiente, fuentemonedaneg)
#     # ws.write(row_num, 9, totalreprobado, fuentemonedaneg)
#
#     wb.save(filename)
# except Exception as ex:
#     pass


# try:
#     workbook = xlrd.open_workbook('kerly6.xlsx')
#     sheet = workbook.sheet_by_index(0)
#     linea = 1
#     for rowx in range(sheet.nrows):
#         if linea > 1:
#             cols = sheet.row_values(rowx)
#             matriculaold = None
#             if Matricula.objects.filter(pk=int(cols[0])):
#                 matriculaold = Matricula.objects.get(pk=int(cols[0]))
#             if matriculaold:
#                 persona = matriculaold.inscripcion.persona
#                 inscripcionold = matriculaold.inscripcion
#                 sede = inscripcionold.sede
#                 sesion = inscripcionold.sesion
#                 modalidad = inscripcionold.modalidad
#                 carrera = Carrera.objects.get(pk=int(cols[1]))
#
#                 if Inscripcion.objects.filter(persona=persona, carrera=carrera).exists():
#                     inscripcion = Inscripcion.objects.get(persona=persona, carrera=carrera)
#                     inscripcion.aplica_b2 = inscripcionold.aplica_b2
#                     inscripcion.save()
#                 else:
#                     hoy = datetime.now().date()
#                     inscripcion = Inscripcion(persona=persona,
#                                               fecha=hoy,
#                                               carrera=carrera,
#                                               modalidad=modalidad,
#                                               inscripcionold=inscripcionold,
#                                               confirmacion=False,
#                                               sesion=sesion,
#                                               aplica_b2=inscripcionold.aplica_b2,
#                                               sede=sede)
#                     inscripcion.save()
#                     persona.crear_perfil(inscripcion=inscripcion, visible=False)
#                     inscripcion.cambio_malla_inscripcion(Malla.objects.get(pk=int(cols[2])))
#                 mallanew = inscripcion.malla_inscripcion().malla
#                 #sumando los creditos ganados
#                 # creditosganados = null_to_decimal(RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold).exclude(asignaturamalla__isnull=True).aggregate(creditosganados=Sum('creditos'))['creditosganados'], 2)
#                 creditosganados = null_to_decimal(RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold).exclude(asignaturamalla__isnull=True).aggregate(creditosganados=Sum('asignaturamalla__creditos'))['creditosganados'], 2)
#                 # realizando la conversion de los creditos ganados
#                 conversioncreditos = 0
#                 if int(cols[3]) == 1:
#                     horaformula = 32
#                     conversioncreditos = null_to_decimal((creditosganados * horaformula) / 48, 0)
#                 elif int(cols[3]) == 2:
#                     horaformula = 40
#                     conversioncreditos = null_to_decimal((creditosganados * horaformula) / 48, 0)
#                 elif int(cols[3]) == 3:
#                     conversioncreditos = null_to_decimal(creditosganados * 0.75, 0)
#
#                 # if inscripcionold.carrera_id in [90, 88, 7, 78, 95, 89, 21, 6, 92, 61, 46, 79]:
#                 #     horaformula = 40
#
#                 #
#                 # verificar el nivel de Matricula
#                 nivelmatricula = TablaReconocimientoCreditos.objects.filter(min__lte=conversioncreditos, max__gte=conversioncreditos, status=True)[0].nivelmalla
#                 # buscando asignaturas a homologar
#                 # VERIFICAR SI EL ALUMNO PUEDE EGRESAR
#                 materiasobligatorias = []
#                 if conversioncreditos >= 120:
#                     # materias aprobadas profesionalizantes
#                     asignaturashomologa = mallanew.asignaturamalla_set.filter(nivelmalla_id__lt=nivelmatricula.id + 1, status=True)
#                     mallaold = inscripcionold.malla_inscripcion().malla
#                     asigmallaprofe = null_to_decimal(mallaold.asignaturamalla_set.filter(ejeformativo__id=3, status=True).aggregate(cant=Count('id'))['cant'], 0)
#                     aprobadasprofe = null_to_decimal(RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, asignaturamalla__ejeformativo__id=3, inscripcion=inscripcionold).exclude(asignaturamalla__isnull=True).aggregate(cant=Count('id'))['cant'], 0)
#                     if asigmallaprofe > 0:
#                         buscarobligatorias = True
#                         if aprobadasprofe > 0:
#                             if null_to_decimal((aprobadasprofe / asigmallaprofe) * 100, 0) >= 80:
#                                 # aqui procedemos a mandar al alumno al proceso de titulacion
#                                 inscripcion.egresadorc = True
#                                 inscripcion.save()
#                                 buscarobligatorias = False
#                             else:
#                                 buscarobligatorias = True
#                         else:
#                             buscarobligatorias = True
#                         if buscarobligatorias:
#                             # aqui procedemos a mandar al alumno ah que vea ciertas asignaturas de 7mo y 8vo nivel
#                             con = 0
#                             for obli in TablaAsignaturasObligatorias.objects.filter(asignaturamalla__malla=mallanew):
#                                 equiobli = obli.asignaturamalla.tablaequivalenciaasignaturas_set.filter(status=True)
#                                 if not equiobli:
#                                     con +=1
#                                     if con <=4:
#                                         materiasobligatorias.append(obli.asignaturamalla)
#                                 else:
#                                     aproequi = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold, asignatura__in=[x.asignatura for x in equiobli]).order_by('-nota')
#                                     if not aproequi:
#                                         con += 1
#                                         if con <= 4:
#                                             materiasobligatorias.append(obli.asignaturamalla)
#                 else:
#                     asignaturashomologa = mallanew.asignaturamalla_set.filter(nivelmalla_id__lt=nivelmatricula.id, status=True)
#
#                 praobli = []
#                 for obli in TablaPracticasObligatorias.objects.filter(asignaturamalla__malla=mallanew):
#                     praobli.append(obli.asignaturamalla)
#                 tienerc = True
#                 if not asignaturashomologa:
#                     asignaturashomologa = mallanew.asignaturamalla_set.filter(nivelmalla_id=nivelmatricula.id, status=True)
#                     tienerc = False
#
#                 for asigmalla in asignaturashomologa.exclude(pk__in=[x.id for x in materiasobligatorias]).exclude(pk__in=[x.id for x in praobli]):
#                     # buscamos materias posibles a homologar segun criterio de los directores de carrera
#                     equivalencias = asigmalla.tablaequivalenciaasignaturas_set.filter(status=True)
#                     nota = asistencia = 0
#                     noaplica = False
#                     observaciones = ''
#                     notamayor = []
#                     if equivalencias:
#                         notamayor = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcionold, asignatura__in=[x.asignatura for x in equivalencias]).order_by('-nota')
#                         if notamayor:
#                             noaplica = False
#                             nota = notamayor[0].nota
#                             asistencia = notamayor[0].asistencia
#                             fecha = notamayor[0].fecha
#                             observaciones = u'%s (MIGRACION - PROCESO DE RECONOCIMIENTO DE CREDITOS 2019)' % notamayor[0].asignatura
#                         else:
#                             observaciones = u'NO APLICA - PROCESO DE RECONOCIMIENTO DE CREDITOS 2019'
#                             noaplica = True
#                             fecha = datetime.now().date()
#                     else:
#                         nota = asistencia = 0
#                         fecha = datetime.now().date()
#                         noaplica = True
#                         observaciones = u'NO APLICA - PROCESO DE RECONOCIMIENTO DE CREDITOS 2019'
#
#                     if tienerc or notamayor:
#                         if not RecordAcademico.objects.filter(inscripcion=inscripcion, asignatura=asigmalla.asignatura, asignaturamalla=asigmalla).exists():
#                             record = RecordAcademico(inscripcion=inscripcion,
#                                                      asignatura=asigmalla.asignatura,
#                                                      asignaturamalla=asigmalla,
#                                                      fecha=fecha,
#                                                      valida=True,
#                                                      validapromedio=True,
#                                                      aprobada=True,
#                                                      homologada=False,
#                                                      convalidacion=False,
#                                                      pendiente=False)
#                         else:
#                             record = RecordAcademico.objects.get(inscripcion=inscripcion, asignatura=asigmalla.asignatura, asignaturamalla=asigmalla)
#
#                         record.creditos = asigmalla.creditos
#                         record.horas = asigmalla.horas
#                         record.observaciones = observaciones
#                         record.noaplica = noaplica
#                         record.asistencia = asistencia
#                         record.nota = nota
#                         record.save()
#                         record.actualizar()
#
#                 if inscripcion.tiene_nivel():
#                     ficha = inscripcion.inscripcionnivel_set.all()[0]
#                 else:
#                     ficha = InscripcionNivel(inscripcion=inscripcion)
#                 ficha.nivel = nivelmatricula
#                 ficha.save()
#                 print('%s - %s' % (linea, persona))
#         linea += 1
#     print(linea)
# except Exception as ex:
#     print('error: %s' % ex)


# try:
#     linea = 1
#     periodo_id = 90
#     for materia in Materia.objects.filter(status=True, nivel__periodo__id=periodo_id, asignaturamalla__malla__inicio__year=2019,asignaturamalla__malla__carrera__coordinacion__id=9,asignaturamalla__malla__carrera__id__in=[104], modeloevaluativo_id__in=[17, 18]):
#         print('%s - %s - %s' % (linea, materia, materia.idcursomoodle))
#
#         materia.crear_actualizar_categoria_notas_curso()
#
#         # cursor = connections['db_moodle_virtual'].cursor()
#         # sql="""     SELECT id from mooc_grade_categories
#         #         WHERE courseid=%s AND DEPTH=1
#         # """ % materia.idcursomoodle
#         # cursor.execute(sql)
#         # results = cursor.fetchall()
#         # print(results[0][0])
#         # sql = """   DELETE from mooc_grade_categories
#         #         WHERE courseid=%s AND DEPTH=2 AND parent=%s
#         #         """ % (materia.idcursomoodle, results[0][0])
#         # cursor.execute(sql)
#         # sql="""  DELETE from mooc_grade_categories
#         #         WHERE courseid=%s AND DEPTH=1
#         # """ % materia.idcursomoodle
#         # cursor.execute(sql)
#         #
#         # sql="""  DELETE from mooc_grade_items
#         #         WHERE courseid=%s
#         # """ % materia.idcursomoodle
#         # cursor.execute(sql)#
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)


# # homologa asignaturas individual por malla
# try:
#     linea = 1
#     periodos_id = [85, 90]
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, reverso=True, procesado=False):
#         print('%s - %s - %s' % (linea, inscripcion, inscripcion.id))
#         if inscripcion.matricula_set.filter(status=True, nivel__periodo_id__in=periodos_id).exists():
#             matricula = inscripcion.matricula_set.filter(status=True, nivel__periodo_id=90)[0] if inscripcion.matricula_set.filter(status=True, nivel__periodo_id=90).exists() else inscripcion.matricula_set.filter(status=True, nivel__periodo_id=85)[0]
#             nivelmatricula = matricula.nivelmalla
#             persona = inscripcion.persona
#             inscripcion2012 = inscripcion.inscripcionold
#             ## HABILITAMOS EL PERFIL ANTERIOR DESHABILITAMOS EL NUEVO 2019
#             persona.perfilusuario_set.filter(inscripcion=inscripcion).update(visible=False)
#             persona.perfilusuario_set.filter(inscripcion=inscripcion2012).update(visible=True)
#
#             ## BUSCAMOS LAS ASIGNATURAS APROBADAS EN EL NUEVO PERIODO 2019
#             materiaasignadas = MateriaAsignada.objects.filter(matricula__in=inscripcion.matricula_set.filter(status=True, nivel__periodo_id__in=periodos_id), status=True, materiaasignadaretiro__isnull=True, retiramateria=False)
#             recordsmallaall = inscripcion.recordacademico_set.filter(asignaturamalla_id__in=[x.materia.asignaturamalla_id for x in materiaasignadas])
#             recordsmallaap = recordsmallaall.filter(aprobada=True)
#
#             idfijos = [7070, 7394, 6948, 7633, 7386, 7543, 7179, 7601, 7477, 7698, 6939, 7735, 7435, 7665, 7589, 7260, 7203, 4271] #aqui van los codigos
#
#             recordfijo = inscripcion.recordacademico_set.filter(asignaturamalla_id__in=idfijos, aprobada=True)
#
#             if recordfijo:
#                 recordsmallanew = recordsmallaap | recordfijo
#             else:
#                 recordsmallanew = recordsmallaap
#
#             malla2012 = inscripcion2012.malla_inscripcion().malla
#             for asignatura2012 in malla2012.asignaturamalla_set.filter(status=True).exclude(asignatura_id__in=[x.asignatura_id for x in RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion2012)]):
#                 aprobada = False
#                 if TablaEquivalenciaAsignaturasReverso.objects.filter(asignatura2012=asignatura2012).exists():
#                     equivalencia = TablaEquivalenciaAsignaturasReverso.objects.filter(asignatura2012=asignatura2012)[0]
#                     bloqueada = False
#                     if equivalencia.asignatura2019:
#                         if recordsmallaall.filter(asignatura_id=equivalencia.asignatura2019.asignatura_id, aprobada=False).exists():
#                             bloqueada = True
#                         if not RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists() and not bloqueada:
#                             asignatura2019 = equivalencia.asignatura2019
#                             if recordsmallanew.filter(asignatura_id=asignatura2019.asignatura_id).exists() and not bloqueada:
#                                 record2019 = recordsmallanew.filter(asignatura_id=asignatura2019.asignatura_id)[0]
#                                 if record2019.materiaregular:
#                                     observaciones = u'%s - %s' % (record2019.materiaregular.nivel.periodo.nombre, record2019.materiaregular.profesor_principal())
#                                 else:
#                                     observaciones = record2019.observaciones
#                                 if not RecordAcademico.objects.filter(aprobada=False, status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists():
#                                     record = RecordAcademico(inscripcion=inscripcion2012,
#                                                              asignatura_id=asignatura2012.asignatura_id,
#                                                              asignaturamalla=asignatura2012,
#                                                              validapromedio=True,
#                                                              noaplica=False,
#                                                              homologada=False,
#                                                              convalidacion=False,
#                                                              pendiente=False)
#                                 else:
#                                     record = RecordAcademico.objects.filter(aprobada=False, status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id)[0]
#                                 record.observaciones = observaciones
#                                 record.nota = record2019.nota
#                                 record.reverso = True
#                                 record.aprobada = True
#                                 record.valida = True
#                                 record.asistencia = record2019.asistencia
#                                 record.fecha = record2019.fecha
#                                 record.creditos = asignatura2012.creditos
#                                 record.horas = asignatura2012.horas
#                                 record.save()
#                                 record.actualizar()
#                                 aprobada = True
#                                 print('%s - %s- %s' % (linea, asignatura2012.asignatura, asignatura2019.asignatura))
#
#                     if equivalencia.asignatura2019salto and aprobada == False and not bloqueada:
#                         asignatura2019 = equivalencia.asignatura2019salto
#                         if not RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists():
#                             if recordsmallanew.filter(asignatura_id=asignatura2019.asignatura_id).exists() and not bloqueada:
#                                 record2019 = recordsmallanew.filter(asignatura_id=asignatura2019.asignatura_id)[0]
#                                 if record2019.materiaregular:
#                                     observaciones = u'%s - %s' % (record2019.materiaregular.nivel.periodo.nombre, record2019.materiaregular.profesor_principal())
#                                 else:
#                                     observaciones = record2019.observaciones
#                                 if not RecordAcademico.objects.filter(aprobada=False, status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists():
#                                     record = RecordAcademico(inscripcion=inscripcion2012,
#                                                              asignatura_id=asignatura2012.asignatura_id,
#                                                              asignaturamalla=asignatura2012,
#                                                              validapromedio=True,
#                                                              noaplica=False,
#                                                              homologada=False,
#                                                              convalidacion=False,
#                                                              pendiente=False)
#                                 else:
#                                     record = RecordAcademico.objects.filter(aprobada=False, status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id)[0]
#                                 record.observaciones = observaciones
#                                 record.nota = record2019.nota
#                                 record.reverso = True
#                                 record.aprobada = True
#                                 record.valida = True
#                                 record.asistencia = record2019.asistencia
#                                 record.fecha = record2019.fecha
#                                 record.creditos = asignatura2012.creditos
#                                 record.horas = asignatura2012.horas
#                                 record.save()
#                                 record.actualizar()
#                                 print('%s - %s- %s' % (linea, asignatura2012.asignatura, asignatura2019.asignatura))
#
#                     if equivalencia.asignatura2019salto2 and aprobada == False and not bloqueada:
#                         asignatura2019 = equivalencia.asignatura2019salto2
#                         if not RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists():
#                             if recordsmallanew.filter(asignatura_id=asignatura2019.asignatura_id).exists() and not bloqueada:
#                                 record2019 = recordsmallanew.filter(asignatura_id=asignatura2019.asignatura_id)[0]
#                                 if record2019.materiaregular:
#                                     observaciones = u'%s - %s' % (record2019.materiaregular.nivel.periodo.nombre, record2019.materiaregular.profesor_principal())
#                                 else:
#                                     observaciones = record2019.observaciones
#                                 if not RecordAcademico.objects.filter(aprobada=False, status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists():
#                                     record = RecordAcademico(inscripcion=inscripcion2012,
#                                                              asignatura_id=asignatura2012.asignatura_id,
#                                                              asignaturamalla=asignatura2012,
#                                                              validapromedio=True,
#                                                              noaplica=False,
#                                                              homologada=False,
#                                                              convalidacion=False,
#                                                              pendiente=False)
#                                 else:
#                                     record = RecordAcademico.objects.filter(aprobada=False, status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id)[0]
#                                 record.observaciones = observaciones
#                                 record.nota = record2019.nota
#                                 record.reverso = True
#                                 record.aprobada = True
#                                 record.valida = True
#                                 record.asistencia = record2019.asistencia
#                                 record.fecha = record2019.fecha
#                                 record.creditos = asignatura2012.creditos
#                                 record.horas = asignatura2012.horas
#                                 record.save()
#                                 record.actualizar()
#                                 print('%s - %s- %s' % (linea, asignatura2012.asignatura, asignatura2019.asignatura))
#
#                     if not RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion2012, asignatura_id=asignatura2012.asignatura_id).exists():
#                         if asignatura2012.nivelmalla_id <= nivelmatricula.id:
#                             NoSePudoHomologar.objects.filter(inscripcion=inscripcion2012, asignaturamalla=asignatura2012).delete()
#                             NoSePudoHomologar.objects.create(inscripcion=inscripcion2012, asignaturamalla=asignatura2012)
#                 elif asignatura2012.nivelmalla_id <= nivelmatricula.id:
#                     NoSePudoHomologar.objects.filter(inscripcion=inscripcion2012, asignaturamalla=asignatura2012).delete()
#                     NoSePudoHomologar.objects.create(inscripcion=inscripcion2012, asignaturamalla=asignatura2012)
#         inscripcion.procesado = True
#         inscripcion.save()
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)

# # ## homologa modulos de los estudiantes
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         for asigmal in AsignaturaMalla.objects.filter(malla_id=22):
#             modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion, asignatura=asigmal.asignatura).order_by('id')
#             for record in modulos:
#                 if not RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura=asigmal.asignatura, status=True).exists():
#                     record.id = None
#                     record.inscripcion = inscripcionold
#                     observaciones = u'%s (MIGRACION - PROCESO DE RV 2020)' % record.observaciones
#                     record.observaciones = observaciones
#                     record.reverso = True
#                     record.save()
#                     record.actualizar()
#                     print('------------------ INC INGLES %s - %s' % (linea, record.asignatura))
#                 else:
#                     record2 = RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura=asigmal.asignatura, status=True)[0]
#                     record2.nota = record.nota
#                     record2.aprobada = record.aprobada
#                     record2.valida = True
#                     record2.asistencia = record.asistencia
#                     record2.fecha = record.fecha
#                     record2.creditos = record.creditos
#                     record2.horas = record.horas
#                     record2.save()
#                     record2.actualizar()
#                     print('-------------------. UP %s - %s' % (linea, record.asignatura))
#         inscripcion.procesadoingles = True
#         inscripcion.save()
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
#
# #
# # ## migrar titulacion
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, reverso=True, procesado=True):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         if MatriculaTitulacion.objects.filter(inscripcion=inscripcion, status=True).exists():
#             MatriculaTitulacion.objects.filter(inscripcion=inscripcion, status=True).update(inscripcion=inscripcionold)
#             inscripcion.procesadotitulacion = True
#             inscripcion.save()
#             print('---- %s - %s-%s OK' % (linea, inscripcion.id, inscripcion))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
#

# # ## migrar practicas
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         if PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True).exists():
#             PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True).update(inscripcion=inscripcionold)
#             inscripcion.procesadopracticas = True
#             inscripcion.save()
#             print('---- %s - %s-%s OK' % (linea, inscripcion.id, inscripcion))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
# #
# #
# # ## migrar Vinculacion
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         if ParticipantesMatrices.objects.filter(inscripcion=inscripcion, status=True).exists():
#             ParticipantesMatrices.objects.filter(inscripcion=inscripcion, status=True).update(inscripcion=inscripcionold)
#             inscripcion.procesadovinculacion = True
#             inscripcion.save()
#             print('---- %s - %s-%s OK' % (linea, inscripcion.id, inscripcion))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
#
# # ## migrar Complexivo
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, reverso=True, procesado=True):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         if ExamenComplexivo.objects.filter(inscripcion=inscripcion, status=True).exists():
#             ExamenComplexivo.objects.filter(inscripcion=inscripcion, status=True).update(inscripcion=inscripcionold)
#             print('---- %s - %s-%s OK' % (linea, inscripcion.id, inscripcion))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
#
# ## migrar MateriaAsignadaCurso
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, reverso=True, procesado=True):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         if MatriculaCursoEscuelaComplementaria.objects.filter(inscripcion=inscripcion, status=True, curso__cerrado=False).exists():
#             if not MatriculaCursoEscuelaComplementaria.objects.filter(inscripcion=inscripcionold, status=True, curso__cerrado=False).exists():
#                 MatriculaCursoEscuelaComplementaria.objects.filter(inscripcion=inscripcion, status=True, curso__cerrado=False).update(inscripcion=inscripcionold)
#                 print('---- %s - %s-%s OK' % (linea, inscripcion.id, inscripcion))
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)
#
#
# # homologa modulos de los estudiantes computacion
# try:
#     linea = 1
#     for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#         print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#         inscripcionold = inscripcion.inscripcionold
#         for asigmal in AsignaturaMalla.objects.filter(malla_id=32):
#             modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion, asignatura=asigmal.asignatura).order_by('id')
#             for record in modulos:
#                 if not RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura=asigmal.asignatura, status=True).exists():
#                     record.id = None
#                     record.inscripcion = inscripcionold
#                     observaciones = u'%s (MIGRACION - PROCESO DE RV 2020)' % record.observaciones
#                     record.observaciones = observaciones
#                     record.reverso = True
#                     record.save()
#                     record.actualizar()
#                     print('------------------ COMPINS %s - %s' % (linea, record.asignatura))
#                 else:
#                     record2 = RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura=asigmal.asignatura, status=True)[0]
#                     record2.nota = record.nota
#                     record2.aprobada = record.aprobada
#                     record2.valida = True
#                     record2.asistencia = record.asistencia
#                     record2.fecha = record.fecha
#                     record2.creditos = record.creditos
#                     record2.horas = record.horas
#                     record2.save()
#                     record2.actualizar()
#                     print('------------------ COMPUP %s - %s' % (linea, record.asignatura))
#         inscripcion.procesadocomputacion = True
#         inscripcion.save()
#         linea += 1
# except Exception as ex:
#     print('error: %s' % ex)


# for asigmigra in AsignaturaMigracion.objects.filter(asignatura_id__isnull=True):
#     asigsga = Asignatura.objects.filter(nombre__unaccent=asigmigra.nombre.upper()).order_by('id')[0] if Asignatura.objects.filter(nombre__unaccent=asigmigra.nombre.upper()).exists() else None
#     if asigsga:
#         asigmigra.asignatura = asigsga
#         print("%s; %s" % (asigsga.nombre, asigmigra.nombre))
#         asigmigra.save()


# MASIVO PARA ASIGNAR COMO DOCENTE
# workbook = xlrd.open_workbook("notas.xlsx")
# sheet = workbook.sheet_by_index(0)
# linea = 1
# for rowx in range(sheet.nrows):
#     if linea>1:
#         cols = sheet.row_values(rowx)
#         cedula = "%s" % int(cols[0])
#         if cedula.__len__() < 10:
#             cedula = "0%s" % cedula
#         carrerami = CarreraMigracion.objects.get(nombre=cols[1])
#         if not MigracionSistemaIntegrador.objects.filter(cedula=cedula, carreramigracion=carrerami).exists():
#             persona = None
#             if Persona.objects.values("id").filter(cedula=cedula).exists():
#                 persona = Persona.objects.filter(cedula=cedula).order_by("id")[0]
#             inscripcion = None
#             if Inscripcion.objects.values("id").filter(persona=persona, carrera=carrerami.carrera).exists():
#                 inscripcion = Inscripcion.objects.get(persona=persona, carrera=carrerami.carrera)
#             migracionsistemaintegrador = MigracionSistemaIntegrador(cedula=cedula, carreramigracion=carrerami, persona=persona, inscripcion=inscripcion)
#             migracionsistemaintegrador.save()
#         else:
#             migracionsistemaintegrador = MigracionSistemaIntegrador.objects.get(cedula=cedula, carreramigracion=carrerami)
#
#
#         asignaturami = AsignaturaMigracion.objects.get(nombre=cols[3])
#         nivel_id = int(cols[2])
#         if not MigracionNotasSistemaIntegrador.objects.filter(migracionsistemaintegrador=migracionsistemaintegrador, asignaturamigracion=asignaturami, nivel_id=nivel_id).exists():
#             notareal = int(cols[4])
#             if notareal < 70:
#                 nota = 70
#             else:
#                 nota = notareal
#             fecha = xlrd.xldate.xldate_as_datetime(cols[5], workbook.datemode).date()
#             record = None
#             if migracionsistemaintegrador.inscripcion_id and asignaturami.asignatura_id:
#                 if RecordAcademico.objects.values("id").filter(inscripcion_id=migracionsistemaintegrador.inscripcion_id, asignatura_id=asignaturami.asignatura_id, status=True).exists():
#                     record = RecordAcademico.objects.get(inscripcion_id=migracionsistemaintegrador.inscripcion_id, asignatura_id=asignaturami.asignatura_id, status=True)
#             migracionnotassistemaintegrador = MigracionNotasSistemaIntegrador(migracionsistemaintegrador=migracionsistemaintegrador,
#                                                                               asignaturamigracion=asignaturami,
#                                                                               nivel_id=nivel_id,
#                                                                               puntajereal=notareal,
#                                                                               recordacademico=record,
#                                                                               fecha=fecha,
#                                                                               procesado=True if record else False,
#                                                                               puntajesga=nota)
#             migracionnotassistemaintegrador.save()
#         print(migracionsistemaintegrador)
#
#     linea = linea + 1



# for inscrimigra in MigracionSistemaIntegrador.objects.filter(carreramigracion_id=13, inscripcion__isnull=True):
#     inscripcion = None
#     if Inscripcion.objects.values("id").filter(persona=inscrimigra.persona, carrera=inscrimigra.carreramigracion.carrera).exists():
#         inscripcion = Inscripcion.objects.get(persona=inscrimigra.persona, carrera=inscrimigra.carreramigracion.carrera)
#         inscrimigra.inscripcion = inscripcion
#         inscrimigra.save()
#         for notasmigra in inscrimigra.migracionnotassistemaintegrador_set.all():
#             if RecordAcademico.objects.values("id").filter(inscripcion=inscripcion, asignatura_id=notasmigra.asignaturamigracion.asignatura_id, status=True).exists():
#                 notasmigra.recordacademico = RecordAcademico.objects.get(inscripcion=inscripcion, asignatura_id=notasmigra.asignaturamigracion.asignatura_id, status=True)
#                 notasmigra.save()
#         print(inscrimigra)

# for notamigra in MigracionNotasSistemaIntegrador.objects.filter(migracionsistemaintegrador__inscripcion__isnull=False, procesado=False):
#     inscripcion = notamigra.migracionsistemaintegrador.inscripcion
#     if RecordAcademico.objects.values("id").filter(inscripcion=inscripcion, observaciones__unaccent__startswith=notamigra.asignaturamigracion.nombre, status=True).exists():
#         notamigra.recordacademico = RecordAcademico.objects.filter(inscripcion=inscripcion, observaciones__unaccent__startswith=notamigra.asignaturamigracion.nombre, status=True)[0]
#         notamigra.save()
#         print(inscripcion)

# linea = 0
# for inscrimigra in MigracionSistemaIntegrador.objects.all():
#     inscrimigra.totalregistros = inscrimigra.migracionnotassistemaintegrador_set.all().count()
#     inscrimigra.registrosencontrados = inscrimigra.migracionnotassistemaintegrador_set.filter(procesado=True).count()
#     inscrimigra.save()
#     linea = linea + 1
#     print("%s - Inscripcion actulizada de %s" % (linea, inscrimigra.persona))
#

# linea = 0
# for notamigra in MigracionNotasSistemaIntegrador.objects.filter(migracionsistemaintegrador__inscripcion__isnull=False, procesado=False, recordacademico__isnull=True):
#     inscripcion = notamigra.migracionsistemaintegrador.inscripcion
#     linea = linea + 1
#     malla = inscripcion.malla_inscripcion().malla
#     asignaturamalla = malla.asignaturamalla_set.filter(status=True, asignatura_id=notamigra.asignaturamigracion.asignatura_id)[0] if malla.asignaturamalla_set.filter(status=True, asignatura_id=notamigra.asignaturamigracion.asignatura_id).exists() else None
#     with transaction.atomic():
#         record = None
#         if not RecordAcademico.objects.filter(status=True, inscripcion=inscripcion, asignatura_id=notamigra.asignaturamigracion.asignatura_id).exists():
#             record = RecordAcademico(inscripcion=inscripcion,
#                                      asignaturamalla=asignaturamalla,
#                                      asignatura=notamigra.asignaturamigracion.asignatura,
#                                      validapromedio=True,
#                                      noaplica=False,
#                                      homologada=False,
#                                      convalidacion=False,
#                                      pendiente=False)
#             record.observaciones= '%s (MIGRACION-L)' % notamigra.asignaturamigracion.nombre
#             record.nota = notamigra.puntajesga
#             record.aprobada = True
#             record.valida = True
#             record.asistencia = 100
#             record.fecha = notamigra.fecha
#             record.creditos = asignaturamalla.creditos if asignaturamalla else 0
#             record.horas = asignaturamalla.horas if asignaturamalla else 0
#             record.save()
#             notamigra.recordacademico = record
#             notamigra.procesado = True
#             notamigra.recuperado = True
#             notamigra.save()
#             notamigra.migracionsistemaintegrador.registrosrecuperados = notamigra.migracionsistemaintegrador.registrosrecuperados + 1
#             notamigra.migracionsistemaintegrador.save()
#             print('%s - %s - %s' %(linea, inscripcion, asignaturamalla))

# linea = 1
# for matricula in Matricula.objects.filter(nivel__periodo_id=110, materiaasignada__matriculas__gte=3, materiaasignada__materia__asignatura__modulo=False).distinct():
#     print("%s - %s" % (linea,matricula.id))
#     linea = linea + 1

from django.db import connections
from sga.funciones import null_to_numeric

# for tarea in TareaSilaboSemanal.objects.filter(idtareamoodle=0, estado_id=4):
#     materia = tarea.silabosemanal.silabo.materia
#     if materia.idcursomoodle:
#         cursoid = materia.idcursomoodle
#         cursor = None
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#
#         # PROCEDEMOS A BUSCAR EL ID DE LA TAREA CREADA
#         instance = 0
#         sql = """select id from mooc_assign WHERE course=%s AND name='%s' """ % (cursoid, "S%s-%s" % (tarea.silabosemanal.numsemana, tarea.nombre))
#         cursor.execute(sql)
#         buscar = cursor.fetchall()
#         if buscar:
#             instance = buscar[0][0]
#         section = 0
#         if instance > 0:
#             sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 3)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 section = buscar[0][0]
#
#         if section > 0:
#             # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
#             sql = """select id from mooc_course_modules WHERE course=%s AND module='1' and instance='%s' and section='%s' """ % (cursoid, instance, section)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 instanceid = buscar[0][0]
#                 tarea.idtareamoodle = instanceid
#                 tarea.save()
#                 print(tarea)
#
# for foro in ForoSilaboSemanal.objects.filter(idforomoodle=0, estado_id=4):
#     materia = foro.silabosemanal.silabo.materia
#     if materia.idcursomoodle:
#         cursoid = materia.idcursomoodle
#         cursor = None
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#
#         # PROCEDEMOS A BUSCAR EL ID DE LA foro CREADA
#         instance = 0
#         sql = """select id from mooc_forum WHERE course=%s AND name='%s' """ % (cursoid, "S%s-%s" % (foro.silabosemanal.numsemana, foro.nombre))
#         cursor.execute(sql)
#         buscar = cursor.fetchall()
#         if buscar:
#             instance = buscar[0][0]
#         section = 0
#         if instance > 0:
#             sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 5)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 section = buscar[0][0]
#
#         if section > 0:
#             # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
#             sql = """select id from mooc_course_modules WHERE course=%s AND module='9' and instance='%s' and section='%s' """ % (cursoid, instance, section)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 instanceid = buscar[0][0]
#                 foro.idforomoodle = instanceid
#                 foro.save()
#                 print(foro)
#

# for diapositiva in DiapositivaSilaboSemanal.objects.filter(iddiapositivamoodle=0, estado_id=4):
#     materia = diapositiva.silabosemanal.silabo.materia
#     if materia.idcursomoodle:
#         cursoid = materia.idcursomoodle
#         cursor = None
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#
#         # PROCEDEMOS A BUSCAR EL ID DE LA diapositiva CREADA
#         instance = 0
#         sql = """select id from mooc_url WHERE course=%s AND name='%s' """ % (cursoid, "S%s-%s" % (diapositiva.silabosemanal.numsemana, diapositiva.nombre))
#         cursor.execute(sql)
#         buscar = cursor.fetchall()
#         if buscar:
#             instance = buscar[0][0]
#         section = 0
#         if instance > 0:
#             sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 7)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 section = buscar[0][0]
#
#         if section > 0:
#             # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
#             sql = """select id from mooc_course_modules WHERE course=%s AND module='20' and instance='%s' and section='%s' """ % (cursoid, instance, section)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 instanceid = buscar[0][0]
#                 diapositiva.iddiapositivamoodle = instanceid
#                 diapositiva.save()
#                 print(diapositiva)

# for material in MaterialAdicionalSilaboSemanal.objects.filter(idmaterialesmoodle=0, estado_id=4):
#     materia = material.silabosemanal.silabo.materia
#     if materia.idcursomoodle:
#         cursoid = materia.idcursomoodle
#         cursor = None
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#
#         # PROCEDEMOS A BUSCAR EL ID DE LA diapositiva CREADA
#         instance = 0
#         sql = """select id from mooc_url WHERE course=%s AND name='%s' """ % (cursoid, "S%s-%s" % (material.silabosemanal.numsemana, material.nombre))
#         cursor.execute(sql)
#         buscar = cursor.fetchall()
#         if buscar:
#             instance = buscar[0][0]
#         section = 0
#         if instance > 0:
#             sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 9)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 section = buscar[0][0]
#
#         if section > 0:
#             # PROCEDEMOS A BUSCAR EL ID DEL CURSO MODULO
#             sql = """select id from mooc_course_modules WHERE course=%s AND module='20' and instance='%s' and section='%s' """ % (cursoid, instance, section)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             if buscar:
#                 instanceid = buscar[0][0]
#                 material.idmaterialesmoodle = instanceid
#                 material.save()
#                 print(material)
#
# cursorbackup = connections['moodle_db_prueba'].cursor()
# cursorproduc = connections['moodle_db'].cursor()
#
# # PROCEDEMOS A BUSCAR EL ID DE LA diapositiva CREADA
# sql = """
# SELECT f.id, cs.section, fd.id, fp.id,fp.parent, fp.userid, fp.subject, fp.message, cs.course,
# (SELECT l.other
# FROM mooc_logstore_standard_log l
# WHERE l.userid=fp.userid AND l.objecttable='forum_posts' AND l."action"='uploaded' AND l.courseid=cs.course AND l.objectid=fp.id
# ORDER BY id ASC LIMIT 1)
# FROM mooc_forum f
# INNER JOIN mooc_course_modules cm ON cm.course=f.course AND cm.instance=f.id AND cm.module='9'
# INNER JOIN mooc_course_sections cs ON cs.id=cm.section AND cm.course=cs.course AND cs.section=5
# INNER JOIN mooc_forum_discussions fd ON fd.course=cm.course AND fd.forum=f.id
# INNER JOIN mooc_forum_posts fp ON fp.discussion=fd.id AND fp.parent!=0
# WHERE f.type='single'
# AND fp.message LIKE '%<p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>%'
# AND  fp.id IN(
# 396956,396942,396989,394808,397021,397022,394918,399069,395000,393119,399141,399142,395009,393229,401481,396264,396275,391942,393361,396237,
# 399262,396328,396362,396381,396476,401268,399330,405301,396515,395256,401564,401574,401575,396553,395366,384267,398869,399162,393555,390688,
# 385140,384497,384060,381880,378814,396616,396484,398462,395636,402095,399808,397088,397098,397275,397114,397117,393922,397141,401758,402770,
# 401809,402823,399637,402873,396788,401750,396824,396825,397265,397321,392070,397336,396639,396661,396667,397355,396677,396682,399303,399457,
# 397379,398425,398441,397408,397440,396724,396757,394158,397172,401943,401944,401968,397213,397216,399757,399504,393797,399510,395447,392394,
# 392397,394053,392409,399520,399522,399529,397475,397476,394608,392672,376339,381057,379124,376346,379147,376349,379157,376379,379165,376381,
# 380152,378981,396842,377943,380172,376431,376438,376455,392696,379235,380725,392454,378006,376496,376502,376506,379264,400405,384523,387697,
# 376526,379285,390308,380249,376568,379312,376594,376599,393449,376607,398626,376616,378134,376657,376666,394504,395225,379372,377803,376679,
# 399855,376690,378155,399872,379398,380318,396173,396366,396287,378209,378227,380346,400609,395835,379461,378251,380822,376799,379475,380829,
# 379231,376845,395581,376868,394306,380852,379508,393402,389653,389608,378337,378363,389040,387746,379536,380433,376945,385706,385487,376968,
# 378405,379569,399919,379589,399924,377005,392449,384205,382365,381444,392500,397745,397057,396887,396414,396222,379625,377062,400662,378510,
# 380510,379717,377168,378582,380536,380972,395959,395964,377236,400284,377252,378658,378666,397634,400960,379824,377324,378723,377353,377378,
# 377381,397647,395805,397512,397522,395977,379901,395883,377480,377488,396030,377493,377503,396047,377526,396064,396086,396107,377597,379967,
# 379994,396140,394194,395921,396170,377697,392602,396193,377724,380035,379010,379011,379034,379050,377788,378764,378139,379080,377838,394219,
# 400128,400800,402239,387814,400167,397613,397581,379118,384645,388664,381318,398616,384696,384509,397986,387200,384769,384786,381538,381543,
# 384846,397848,384875,384864,384931,381779,381805,385013,385048,397874,398033,385103,385115,387453,385123,382064,396210,388839,396218,385224,
# 387565,387568,385250,385279,382288,387634,385350,385347,385359,382391,385388,382433,385392,385416,398840,385445,385488,387738,382599,385530,
# 385538,388913,385561,387782,394445,382686,387798,398693,382719,385619,398703,382780,382805,382710,387871,382886,385727,382898,382909,389378,
# 382960,382994,383008,387947,389030,389039,388081,386068,386136,397697,388161,386191,383541,383611,383628,383663,383667,383675,389614,383695,
# 383709,383751,388308,388314,383823,383935,386613,389198,386671,384048,384059,386701,386807,386830,384315,384347,389274,388577,384463,384486,
# 401114,384511,388626,384575,391148,391158,390422,389914,390657,390552,398987,389999,390016,390746,391258,390806,391284,391295,391320,390205,
# 391199,394476,390928,391687,392987,393355,393218,393927,394715,395095,396413,396626,396633,396953,397174,396957,397574,397890,397894,398923,
# 399085,398368,398010,393925,392973,392685,392499,391818,390368,390228,388384,388260,387796,387370,387378,387231,387106,386827,386803,386780,
# 386778,386562,386408,385572,385541,385304,384903,384895,384862,384850,384811,384746,384404,384173,383587,382053,381997,380645,378595,377968,
# 377861,377642,377636,377627,377209,376351,399659,397998,397835,397739,397529,397211,397033,396982,393950,393855,393163,392922,392437,391896,
# 391311,389501,388758,388616,385040,384992,384777,384656,383922,383282,382753,382130,381579,381290,380141,380010,376405,396588,394838,393258,
# 385515,385490,385426,385406,383831,379195,379104,378971,376685,399210,401795,403541,404747)
# ORDER BY fp.id, fp.parent, fp.userid
# """
# import time
# import json
# cursorproduc.execute(sql)
# data = cursorproduc.fetchall()
# fecha = int(time.mktime(datetime.now().timetuple()))
# for forumpost in data:
#     sql = """ select fp.subject, fp.message from mooc_forum_posts fp
#     WHERE fp.message LIKE '%s<p><h3 class="section-title" style="color: #3b5998;font-weight: bold;">Objetivo:</h3></p>%s'
#     and fp.id=%s""" % ('%', '%', forumpost[3])
#     cursorproduc.execute(sql)
#     resultado = cursorproduc.fetchall()
#     if resultado:
#         logbusqueda = forumpost[9].split(";s:")[1][:-1].split(':"')[1]
#         if resultado[0][1] != logbusqueda:
#             sqlfinal = """
#                     UPDATE mooc_forum_posts
#                     SET subject='%s',
#                     message='%s'
#                     WHERE id='%s'
#             """ %(forumpost[6].replace("'", '"'), logbusqueda.replace("'", '"'), forumpost[3])
#             cursorproduc.execute(sqlfinal)
#
#             query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, forumpost[8])
#             cursorproduc.execute(query)
#
#
#             print("%s," % forumpost[3])


# linea = 1
# for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False):
#     print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#     inscripcionold = inscripcion.inscripcionold
#     for asigmal in AsignaturaMalla.objects.filter(malla_id=22):
#         modulos = RecordAcademico.objects.filter(Q(aprobada=True) | Q(noaplica=True), status=True, inscripcion=inscripcion, asignatura=asigmal.asignatura).order_by('id')
#         for record in modulos:
#             if not RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura=asigmal.asignatura, status=True).exists():
#                 record.id = None
#                 record.inscripcion = inscripcionold
#                 observaciones = u'%s (MIGRACION - PROCESO DE RV 2020)' % record.observaciones
#                 record.observaciones = observaciones
#                 record.reverso = True
#                 record.save()
#                 record.actualizar()
#                 print('------------------ INC INGLES %s - %s' % (linea, record.asignatura))
#             else:
#                 record2 = RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura=asigmal.asignatura, status=True)[0]
#                 record2.nota = record.nota
#                 record2.aprobada = record.aprobada
#                 record2.valida = True
#                 record2.asistencia = record.asistencia
#                 record2.fecha = record.fecha
#                 record2.creditos = record.creditos
#                 record2.horas = record.horas
#                 record2.save()
#                 record2.actualizar()
#                 print('-------------------. UP %s - %s' % (linea, record.asignatura))
#     inscripcion.procesadoingles = True
#     inscripcion.save()
#     linea += 1

# # ## homologa modulos de los estudiantes
# try:
#     linea = 1
#     inscripciones2012 = Inscripcion.objects.values("inscripcionold").filter(inscripcionold__isnull=False, carrera_id=153, carrera__coordinacion__id=4, status=True)
#
#     # for recordnoaplica in RecordAcademico.objects.filter(nota=0, valida=True, aprobada=True, reverso=True, noaplica=False, inscripcion_id__in=inscripciones2012, status=True, asignaturamalla__isnull=False):
#     for recordnoaplica in RecordAcademico.objects.filter(inscripcion_id__in=inscripciones2012, status=True, asignaturamalla__isnull=False):
#         inscripcion2019 = Inscripcion.objects.get(inscripcionold=recordnoaplica.inscripcion, status=True)
#         print(inscripcion2019)
#         if recordnoaplica.noaplica:
#             bloqueada = False
#             for tabla in TablaEquivalenciaAsignaturasReverso.objects.filter(asignatura2012=recordnoaplica.asignaturamalla):
#                 if tabla.asignatura2019 and not bloqueada:
#                     linea += 1
#                     asignatura2019 = tabla.asignatura2019
#                     if RecordAcademico.objects.filter(nota__gte=70, aprobada=True, asignaturamalla=asignatura2019, inscripcion=inscripcion2019, asignatura_id=asignatura2019.asignatura_id):
#                         record2019 = RecordAcademico.objects.filter(nota__gte=70, aprobada=True, asignaturamalla=asignatura2019, inscripcion=inscripcion2019, asignatura_id=asignatura2019.asignatura_id)[0]
#                         if record2019.materiaregular:
#                             observaciones = u'%s - %s - Fase 4' % (record2019.materiaregular.nivel.periodo.nombre, record2019.materiaregular.profesor_principal())
#                         else:
#                             observaciones = u'%s - Fase 4' % record2019.observaciones
#                         recordnoaplica.observaciones = observaciones
#                         recordnoaplica.nota = record2019.nota
#                         recordnoaplica.noaplica = False
#                         recordnoaplica.reverso = True
#                         recordnoaplica.aprobada = True
#                         recordnoaplica.valida = True
#                         recordnoaplica.asistencia = record2019.asistencia
#                         recordnoaplica.fecha = record2019.fecha
#                         recordnoaplica.save()
#                         # recordnoaplica.actualizar()
#                         bloqueada = True
#                         print('%s - %s- %s- %s' % (linea, recordnoaplica.inscripcion, recordnoaplica.asignaturamalla.asignatura, asignatura2019.asignatura))
#                 if tabla.asignatura2019salto and not bloqueada:
#                     linea += 1
#                     asignatura2019 = tabla.asignatura2019salto
#                     if RecordAcademico.objects.filter(nota__gte=70, aprobada=True, asignaturamalla=asignatura2019, inscripcion=inscripcion2019, asignatura_id=asignatura2019.asignatura_id):
#                         record2019 = RecordAcademico.objects.filter(nota__gte=70, aprobada=True, asignaturamalla=asignatura2019, inscripcion=inscripcion2019, asignatura_id=asignatura2019.asignatura_id)[0]
#                         if record2019.materiaregular:
#                             observaciones = u'%s - %s - Fase 4' % (record2019.materiaregular.nivel.periodo.nombre, record2019.materiaregular.profesor_principal())
#                         else:
#                             observaciones = u'%s - Fase 4' % record2019.observaciones
#                         recordnoaplica.observaciones = observaciones
#                         recordnoaplica.nota = record2019.nota
#                         recordnoaplica.noaplica = False
#                         recordnoaplica.reverso = True
#                         recordnoaplica.aprobada = True
#                         recordnoaplica.valida = True
#                         recordnoaplica.asistencia = record2019.asistencia
#                         recordnoaplica.fecha = record2019.fecha
#                         recordnoaplica.save()
#                         # recordnoaplica.actualizar()
#                         bloqueada = True
#                         print('%s - %s- %s- %s' % (linea, recordnoaplica.inscripcion, recordnoaplica.asignaturamalla.asignatura, asignatura2019.asignatura))
#
# except Exception as ex:
#     print('error: %s' % ex)

# ## homologa modulos de los estudiantes
# try:
#     linea = 1
#     eliminarcedulas = ['0107164931','0302760707','0605175520','0605393156','0916450851','0921652483','0921657284','0923192744','0924396518','0925988974','0927784983','0928185248','0928545813','0928967298','0929232148','0929765956','0940144975','0940145758','0940493661','0940663370','0940730286','0940811748','0940813579','0940814163','0941117301','0941336489','0941528671','0941661571','0941786162','0941995110','0942442583','0944252832','0950257139','0951415108','0952386944','0952464410','0954789038','0955711031','0956418768','1206321869','1207023746','1207961986','1727365601']
#     inscripciones2012 = Inscripcion.objects.values("inscripcionold").filter(persona__cedula__in=eliminarcedulas, inscripcionold__isnull=False, carrera__coordinacion__id=4, status=True)
#
#     RecordAcademico.objects.filter(inscripcion_id__in=inscripciones2012, status=True, asignaturamalla__isnull=False, noaplica=True).update(status=False)
#
# except Exception as ex:
#     print('error: %s' % ex)
#
# for matricula in Matricula.objects.filter(nivel__periodo__id=110, retiradomatricula=False):
#     matricula.calcula_nivel()
#     print(matricula)
#
# for inscripcion in Inscripcion.objects.filter(matricula__nivel__periodo__id=110, matricula__retiradomatricula=False):
#     inscripcion.actualizar_nivel()
#     inscripcion.save()
#     print(inscripcion.id)
#
# for matricula in Matricula.objects.filter(nivel__periodo_id=110, inscripcion__carrera_id=24):
#     print(matricula)


#
# linea = 1
# for inscripcion in Inscripcion.objects.filter(inscripcionold__isnull=False, carrera_id=144):
#     print('%s - %s-%s' % (linea, inscripcion.id, inscripcion))
#     inscripcionold = inscripcion.inscripcionold
#     # 7436
#     for asigmal in AsignaturaMalla.objects.filter(id=6359):
#         modulos = RecordAcademico.objects.filter(aprobada=True, status=True, inscripcion=inscripcion, asignatura=asigmal.asignatura).order_by('id')
#         for record in modulos:
#             if not RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura_id=118, status=True).exists():
#                 record.id = None
#                 record.inscripcion = inscripcionold
#                 observaciones = u'%s (MIGRACION - PROCESO DE RV 2020 INICIAL)' % record.observaciones
#                 record.observaciones = observaciones
#                 record.asignaturamalla_id = 6359
#                 record.asignatura_id = 118
#                 record.reverso = True
#                 record.save()
#                 record.actualizar()
#                 print('------------------ INC MATERIA %s - %s' % (linea, record.asignatura))
#             else:
#                 if record.aprobada:
#                     record2 = RecordAcademico.objects.filter(inscripcion=inscripcionold, asignatura_id=118, status=True)[0]
#                     record2.nota = record.nota
#                     record2.aprobada = record.aprobada
#                     record2.valida = True
#                     record2.asistencia = record.asistencia
#                     record2.fecha = record.fecha
#                     record2.creditos = record.creditos
#                     record2.horas = record.horas
#                     record2.save()
#                     record2.actualizar()
#                     print('-------------------. UP %s - %s' % (linea, record.asignatura))
#     inscripcion.save()
#     linea += 1
#
# for matricula in Matricula.objects.filter(nivel__periodo_id=99, inscripcion__carrera_id=181):
#     if not MateriaAsignada.objects.values('id').filter(matricula=matricula).exists():
#         inscripcion = matricula.inscripcion
#         sesion = matricula.nivel.sesion
#         carrera = inscripcion.carrera
#         mallaalu = inscripcion.inscripcionmalla_set.all()
#         mallaalu.delete()
#         mimalla = inscripcion.malla_inscripcion()
#         print("%s - %s" % (inscripcion, mimalla))
#         for materia in Materia.objects.filter(nivel__periodo_id=99, paralelo='0A1', asignaturamalla__malla=mimalla.malla, asignaturamalla__malla__carrera=carrera, nivel__sesion=sesion):
#             if not MateriaAsignada.objects.values('id').filter(matricula=matricula, materia=materia).exists():
#                 matriculas = matricula.inscripcion.historicorecordacademico_set.values('id').filter(asignatura=materia.asignatura, fecha__lt=materia.nivel.fin).count() + 1
#                 materiaasignada = MateriaAsignada(matricula=matricula,
#                                                   materia=materia,
#                                                   notafinal=0,
#                                                   asistenciafinal=0,
#                                                   cerrado=False,
#                                                   matriculas=matriculas,
#                                                   observaciones='',
#                                                   estado_id=NOTA_ESTADO_EN_CURSO)
#                 materiaasignada.save()
#                 materiaasignada.asistencias()
#                 materiaasignada.evaluacion()
#                 materiaasignada.mis_planificaciones()
#                 materiaasignada.save()
#                 print(materiaasignada)
#         matricula.actualizar_horas_creditos()
#         matricula.calcula_nivel()
#         inscripcion.actualizar_nivel()
#
#
# # for matricula in Matricula.objects.filter(nivel__periodo_id=99, estado_matricula=1):
# #     if not Rubro.objects.filter(matricula=matricula):
# #         matricula.estado_matricula = 2
# #         matricula.save()
# #         print(matricula)

from django.http import HttpResponseRedirect, HttpResponse, JsonResponse

# try:
#     cursor = connections['sga_select'].cursor()
#     response = HttpResponse(content_type="application/ms-excel")
#     response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
#     wb = xlwt.Workbook()
#     ws = wb.add_sheet('Sheetname')
#     estilo = xlwt.easyxf(
#         'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#     ws.col(0).width = 1000
#     ws.col(1).width = 9000
#     ws.col(2).width = 4000
#     ws.col(3).width = 9000
#     ws.col(4).width = 9000
#     ws.col(5).width = 3000
#     ws.write(1, 0, 'N.')
#     ws.write(1, 1, 'DOCENTE')
#     ws.write(1, 2, 'IDENTIFICACION')
#     ws.write(1, 3, 'CARRERA')
#     ws.write(1, 4, 'ASIGNATURA')
#     ws.write(1, 5, 'PARALELO')
#     ws.write(1, 6, 'CANT. TAREAS')
#     ws.write(1, 7, 'TAREAS CALI.')
#     ws.write(1, 8, 'TAREAS NO CALI.')
#     ws.write(1, 9, 'CAN. ACCESOS')
#     a = 1
#     date_format = xlwt.XFStyle()
#     date_format.num_format_str = 'yyyy/mm/dd'
#     listaestudiante = """
#                     select DISTINCT pe.apellido1 || ' ' || pe.apellido2 || ' ' || pe.nombres as docente, pe.cedula, pe.pasaporte,
#                     asi.nombre, ma.paralelo, pe.idusermoodle, ma.idcursomoodle, ma.id, ca.nombre
#                     from sga_profesormateria pm
#                     inner join sga_materia ma on ma.id=pm.materia_id
#                     inner join sga_asignaturamalla am on am.id=ma.asignaturamalla_id
#                     inner join sga_malla mal on mal.id=am.malla_id
#                     inner join sga_carrera ca on ca.id=mal.carrera_id
#                     inner join sga_asignatura asi on asi.id=ma.asignatura_id
#                     inner join sga_nivel ni on ni.id=ma.nivel_id and ni.periodo_id=112
#                     inner join sga_profesor pro on pro.id=pm.profesor_id
#                     inner join sga_persona pe on pro.persona_id=pe.id
#                     where pm.activo and pm."status"
#                     order by ca.nombre, asi.nombre, ma.paralelo
#     """
#     cursor.execute(listaestudiante)
#     results = cursor.fetchall()
#     cursormoodle = connections['moodle_db'].cursor()
#     for per in results:
#         a += 1
#         ws.write(a, 0, a - 1)
#         ws.write(a, 1, per[0])
#         ws.write(a, 2, per[1] if not per[1] == "" else per[2])
#         ws.write(a, 3, per[8])
#         ws.write(a, 4, per[3])
#         ws.write(a, 5, per[4])
#
#         # tareas de moodle
#         sql= """
#                 SELECT l.id, name,
#                 (SELECT COUNT(submission.id)
#                 FROM mooc_assign_submission submission
#                 INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
#                 INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
#                 INNER JOIN mooc_course AS course ON course.id=assign.course
#                 WHERE course.id=l.course AND assign.id=l.id AND submission.status='submitted') as totaltareasenviadas
#                 ,(
#                 select count(usuario_calificado) as totalcalificados from (
#                 SELECT grades.userid AS usuario_calificado
#                 FROM mooc_assign_grades grades
#                 INNER JOIN mooc_assign assign ON assign.id=grades.ASSIGNMENT
#                 WHERE assign.course=l.course AND assign.id=l.id AND grades.grade >= 0 AND grades.userid IN (
#                 SELECT submission.userid
#                 FROM mooc_assign_submission submission
#                 INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
#                 INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
#                 INNER JOIN mooc_course AS course ON course.id=assign.course
#                 WHERE course.id=l.course AND assign.id=l.id AND submission.status='submitted')
#                 UNION
#                 SELECT grades.userid AS usuario_calificado
#                 FROM mooc_assignfeedback_comments com
#                 INNER JOIN mooc_assign_grades grades ON grades.id=com.grade
#                 WHERE com.assignment=l.id AND grades.userid IN (
#                 SELECT submission.userid
#                 FROM mooc_assign_submission submission
#                 INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
#                 INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
#                 INNER JOIN mooc_course AS course ON course.id=assign.course
#                 WHERE course.id=l.course AND assign.id=l.id AND submission.status='submitted')) as tablacalificadas)
#                 FROM mooc_assign l
#                 LEFT JOIN mooc_grade_items g ON l.id=g.iteminstance AND l.course=g.courseid
#                 WHERE l.course=%s AND (l.duedate >= 1606712400 AND l.duedate <= 1609477140)
#                 and l.grade<>0
#                 ORDER BY l.allowsubmissionsfromdate
#         """ % per[6]
#
#         cursormoodle.execute(sql)
#         re_tarea = cursormoodle.fetchall()
#         totaltarea = 0
#         totaltareacali = 0
#         for tarea in re_tarea:
#             totaltarea += 1
#             if tarea[3] > 0:
#                 if (tarea[3] / tarea[2]) >= 0.8:
#                     totaltareacali += 1
#
#         ws.write(a, 6, totaltarea)
#         ws.write(a, 7, totaltareacali)
#         ws.write(a, 8, totaltarea - totaltareacali)
#
#         # acceso al sistema
#         sql = """
#                 select count(distinct to_date(to_char(TO_TIMESTAMP(timecreated), 'YYYY/MM/DD'), 'YYYY/MM/DD'))
#                 from mooc_logstore_standard_log
#                 where userid=%s and action='loggedin'and timecreated BETWEEN 1606712400 and 1609477140
#         """ % per[5]
#         cursormoodle.execute(sql)
#         accesos = cursormoodle.fetchall()
#         cantacceso = 0
#         for ca in accesos:
#             cantacceso = ca[0]
#         ws.write(a, 9, cantacceso)
#     output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
#     nombre = "SEGUIMIENTO" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#     filename = os.path.join(output_folder, nombre)
#     wb.save(filename)
# except Exception as ex:
#     pass

# try:
#     cursor = connections['sga_select'].cursor()
#     response = HttpResponse(content_type="application/ms-excel")
#     response['Content-Disposition'] = 'attachment; filename=listado_alumnos.xls'
#     wb = xlwt.Workbook()
#     ws = wb.add_sheet('Sheetname')
#     estilo = xlwt.easyxf(
#         'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
#     ws.col(0).width = 1000
#     ws.col(1).width = 9000
#     ws.col(2).width = 4000
#     ws.col(3).width = 9000
#     ws.col(4).width = 9000
#     ws.col(5).width = 3000
#     ws.write(1, 0, 'N.')
#     ws.write(1, 1, 'DOCENTE')
#     ws.write(1, 2, 'IDENTIFICACION')
#     ws.write(1, 3, 'CARRERA')
#     ws.write(1, 4, 'ASIGNATURA')
#     ws.write(1, 5, 'PARALELO')
#
#     ws.write(1, 6, 'TAREA')
#     ws.write(1, 7, 'INICIO')
#     ws.write(1, 8, 'FIN')
#     ws.write(1, 9, 'ENVIADAS')
#     ws.write(1, 10, 'CALIFICADAS')
#     # ws.write(1, 9, 'CAN. ACCESOS')
#     a = 1
#     date_format = xlwt.XFStyle()
#     date_format.num_format_str = 'yyyy/mm/dd'
#     listaestudiante = """
#                     select DISTINCT pe.apellido1 || ' ' || pe.apellido2 || ' ' || pe.nombres as docente, pe.cedula, pe.pasaporte,
#                     asi.nombre, ma.paralelo, pe.idusermoodle, ma.idcursomoodle, ma.id, ca.nombre
#                     from sga_profesormateria pm
#                     inner join sga_materia ma on ma.id=pm.materia_id
#                     inner join sga_asignaturamalla am on am.id=ma.asignaturamalla_id
#                     inner join sga_malla mal on mal.id=am.malla_id
#                     inner join sga_carrera ca on ca.id=mal.carrera_id
#                     inner join sga_asignatura asi on asi.id=ma.asignatura_id
#                     inner join sga_nivel ni on ni.id=ma.nivel_id and ni.periodo_id=112
#                     inner join sga_profesor pro on pro.id=pm.profesor_id
#                     inner join sga_persona pe on pro.persona_id=pe.id
#                     where pm.activo and pm."status"
#                     order by ca.nombre, asi.nombre, ma.paralelo
#     """
#     cursor.execute(listaestudiante)
#     results = cursor.fetchall()
#     cursormoodle = connections['moodle_db'].cursor()
#     for per in results:
#         # tareas de moodle
#         sql= """
#                 SELECT l.id, name,
#                 (SELECT COUNT(submission.id)
#                 FROM mooc_assign_submission submission
#                 INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
#                 INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
#                 INNER JOIN mooc_course AS course ON course.id=assign.course
#                 WHERE course.id=l.course AND assign.id=l.id AND submission.status='submitted') as totaltareasenviadas
#                 ,(
#                 select count(usuario_calificado) as totalcalificados from (
#                 SELECT grades.userid AS usuario_calificado
#                 FROM mooc_assign_grades grades
#                 INNER JOIN mooc_assign assign ON assign.id=grades.ASSIGNMENT
#                 WHERE assign.course=l.course AND assign.id=l.id AND grades.grade >= 0 AND grades.userid IN (
#                 SELECT submission.userid
#                 FROM mooc_assign_submission submission
#                 INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
#                 INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
#                 INNER JOIN mooc_course AS course ON course.id=assign.course
#                 WHERE course.id=l.course AND assign.id=l.id AND submission.status='submitted')
#                 UNION
#                 SELECT grades.userid AS usuario_calificado
#                 FROM mooc_assignfeedback_comments com
#                 INNER JOIN mooc_assign_grades grades ON grades.id=com.grade
#                 WHERE com.assignment=l.id AND grades.userid IN (
#                 SELECT submission.userid
#                 FROM mooc_assign_submission submission
#                 INNER JOIN mooc_assign AS assign ON submission.ASSIGNMENT=assign.id
#                 INNER JOIN mooc_user AS usuario ON submission.userid=usuario.id
#                 INNER JOIN mooc_course AS course ON course.id=assign.course
#                 WHERE course.id=l.course AND assign.id=l.id AND submission.status='submitted')) as tablacalificadas),
#                 to_date(to_char(TO_TIMESTAMP(l.allowsubmissionsfromdate), 'YYYY/MM/DD'), 'YYYY/MM/DD'),
#                 to_date(to_char(TO_TIMESTAMP(l.duedate), 'YYYY/MM/DD'), 'YYYY/MM/DD')
#                 FROM mooc_assign l
#                 LEFT JOIN mooc_grade_items g ON l.id=g.iteminstance AND l.course=g.courseid
#                 WHERE l.course=%s AND (l.duedate >= 1606712400 AND l.duedate <= 1609477140)
#                 and l.grade<>0
#                 ORDER BY l.allowsubmissionsfromdate
#         """ % per[6]
#
#         cursormoodle.execute(sql)
#         re_tarea = cursormoodle.fetchall()
#         for tarea in re_tarea:
#             a += 1
#             ws.write(a, 0, a - 1)
#             ws.write(a, 1, per[0])
#             ws.write(a, 2, per[1] if not per[1] == "" else per[2])
#             ws.write(a, 3, per[8])
#             ws.write(a, 4, per[3])
#             ws.write(a, 5, per[4])
#             ws.write(a, 6, tarea[1])
#             ws.write(a, 7, tarea[4])
#             ws.write(a, 8, tarea[5])
#             ws.write(a, 9, tarea[2])
#             ws.write(a, 10, tarea[3])
#
#     output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
#     nombre = "SEGUIMIENTO DETALLE TAREAS" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#     filename = os.path.join(output_folder, nombre)
#     wb.save(filename)
# except Exception as ex:
#     pass


from django.db import connections
from settings import SITE_STORAGE
import requests
from django.db import connections
import uuid
import warnings
import os
import sys
import time
from datetime import datetime, timedelta, date


# warnings.filterwarnings('ignore', message='Unverified HTTPS request')
#
# for materia in Materia.objects.filter(status=True, idcursomoodle__gt=0, nivel__periodo_id=113):
#     fecha = int(time.mktime(datetime.now().timetuple()))
#     print(materia)
#     cursor = None
#     if materia.coordinacion():
#         if materia.coordinacion().id == 9:
#             cursor = connections['db_moodle_virtual'].cursor()
#         else:
#             # cursor = connections['moodle_db_prueba'].cursor()
#             cursor = connections['moodle_db'].cursor()
#     else:
#         cursor = connections['moodle_db'].cursor()
#     if materia.namehtml:
#         summary = """
#             <iframe src="https://sga.unemi.edu.ec/media/htmlmoodlestatic/%s"  class="filter_hvp" id="hvp_4383" style="width:100%s; height:1000px; border:0;" frameborder="0" allowfullscreen="allowfullscreen"></iframe>
#         """ % (materia.namehtml, '%')
#         sql = """UPDATE mooc_course_sections set summary='%s' WHERE course=%s AND SECTION='0' """ % (summary, materia.idcursomoodle)
#         cursor.execute(sql)
#
#         query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, materia.idcursomoodle)
#         cursor.execute(query)

# workbook = xlrd.open_workbook("borrar_presentacionesmoodle.xlsx")
# sheet = workbook.sheet_by_index(0)
# linea = 1
# for rowx in range(sheet.nrows):
#     if linea > 1:
#         cols = sheet.row_values(rowx)
#
#         diapositiva = DiapositivaSilaboSemanal.objects.get(id=int(cols[0]))
#         fecha = int(time.mktime(datetime.now().timetuple()))
#         materia = diapositiva.silabosemanal.silabo.materia
#         instanceid = int(cols[8])
#         print(materia)
#         cursor = None
#         if materia.coordinacion():
#             if materia.coordinacion().id == 9:
#                 cursor = connections['db_moodle_virtual'].cursor()
#             else:
#                 # cursor = connections['moodle_db_prueba'].cursor()
#                 cursor = connections['moodle_db'].cursor()
#         else:
#             cursor = connections['moodle_db'].cursor()
#         if materia.idcursomoodle > 0:
#             cursoid = materia.idcursomoodle
#             sql = """select id from mooc_course_sections WHERE course=%s AND SECTION='%s' """ % (cursoid, 7)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             section = buscar[0][0]
#
#             sql = """select sequence from mooc_course_sections WHERE id=%s""" % (section)
#             cursor.execute(sql)
#             buscar = cursor.fetchall()
#             sequence = buscar[0][0]
#
#             sequencenew = str(sequence).replace(',%s' % instanceid, '')
#
#             sql = """UPDATE mooc_course_sections SET sequence = '%s' WHERE id = '%s' """ % (sequencenew, section)
#             cursor.execute(sql)
#
#             query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
#             cursor.execute(query)
#
#     linea += 1
#

# for matricula in Matricula.objects.filter(nivel__periodo__id__gt=110, retiradomatricula=False):
#     matricula.calcula_nivel()
#     print(matricula)
#
# for inscripcion in Inscripcion.objects.filter(matricula__nivel__periodo__id__gt=110, matricula__retiradomatricula=False):
#     inscripcion.actualizar_nivel()
#     inscripcion.save()
#     print(inscripcion.id)
#

# for rubro in Rubro.objects.filter(cancelado=False, status=True):
#     if rubro.total_adeudado() <= 0:
#         rubro.cancelado = True
#         rubro.saldo = 0
#         rubro.save()
#         print(rubro)


# workbook = xlrd.open_workbook("RECIBOCAJA-2020.xlsx")
# sheet = workbook.sheet_by_index(0)
# linea = 1
# fecha = datetime.now()
# contador = 0
# for rowx in range(sheet.nrows):
#     if linea > 1:
#         cols = sheet.row_values(rowx)
#         persona = Persona.objects.get(cedula=cols[2])
#         valor = null_to_decimal(Rubro.objects.filter(persona=persona, cancelado=False).aggregate(valor=Sum('saldo'))['valor'], 2)
#         cantidad = Rubro.objects.filter(persona=persona, cancelado=False).count()
#         if cantidad == 1 and valor == float(cols[3]):
#             contador += 1
#             # print("# %s, cedula: %s, Nombre: %s, Valor pago: %s, valor rubro: %s, cant: %s" % (contador, cols[2], cols[1], cols[3], valor, cantidad))
#             # rubro = Rubro.objects.get(persona=persona, cancelado=False)
#             # if not PagoReciboCaja.objects.filter(persona=persona).exists():
#             #     pagorecibo = PagoReciboCaja(persona=persona,
#             #                                 fecha=fecha,
#             #                                 motivo='RECIBO CAJAS DEL 2020 POR CONCEPTO DE DEPOSITO',
#             #                                 valor=null_to_decimal(cols[3], 2))
#             #     pagorecibo.save()
#             #     pagorubro = Pago(fecha=fecha,
#             #                      subtotal0=pagorecibo.valor,
#             #                      subtotaliva=0,
#             #                      iva=0,
#             #                      valordescuento=0,
#             #                      valortotal=pagorecibo.valor,
#             #                      rubro=rubro,
#             #                      efectivo=False,
#             #                      sesion=None)
#             #     pagorubro.save()
#             #     pagorecibo.pagos.add(pagorubro)
#             #     rubro.save()
#             #     print("Se realizo pago con exito %s" % rubro)
#         else:
#             if valor == float(cols[3]):
#                 contador += 1
#                 # if not PagoReciboCaja.objects.filter(persona=persona).exists():
#                 #     contador += 1
#                 #     pagorecibo = PagoReciboCaja(persona=persona,
#                 #                                 fecha=fecha,
#                 #                                 motivo='RECIBO CAJAS DEL 2020 POR CONCEPTO DE DEPOSITO',
#                 #                                 valor=null_to_decimal(cols[3], 2))
#                 #     pagorecibo.save()
#                 #
#                 #     for rubro in Rubro.objects.filter(persona=persona, cancelado=False):
#                 #         pagorubro = Pago(fecha=fecha,
#                 #                          subtotal0=pagorecibo.valor,
#                 #                          subtotaliva=0,
#                 #                          iva=0,
#                 #                          valordescuento=0,
#                 #                          valortotal=pagorecibo.valor,
#                 #                          rubro=rubro,
#                 #                          efectivo=False,
#                 #                          sesion=None)
#                 #         pagorubro.save()
#                 #         pagorecibo.pagos.add(pagorubro)
#                 #         rubro.save()
#                 #         print("Se realizo pago con exito %s" % rubro)
#             else:
#                 if not PagoReciboCaja.objects.filter(persona=persona).exists():
#                     contador += 1
#                     print("# %s, cedula: %s, Nombre: %s, Valor pago: %s, valor rubro: %s, cant: %s" % (contador, cols[2], cols[1], cols[3], valor, cantidad))
#     linea += 1

# profesores = ProfesorDistributivoHoras.objects.filter(periodo_id=112, status=True).exclude(coordinacion_id=9)
#
# for listado in profesores:
#     profesorhora = ProfesorConfigurarHoras(periodo_id=119,
#                                            profesor=listado.profesor,
#                                            dedicacion=listado.dedicacion)
#     profesorhora.save()

# profesores = Profesor.objects.filter(status=True, activo=True).exclude(persona__apellido1__icontains='ADMISION')
#
# for pro in profesores:
#     if not ProfesorConfigurarHoras.objects.filter(periodo_id=119, profesor=pro).exists():
#         if pro.profesordistributivohoras_set.filter(status=True).exists():
#             distributivo = pro.profesordistributivohoras_set.filter(status=True).order_by("-periodo")[0]
#             profesorhora = ProfesorConfigurarHoras(periodo_id=119,
#                                                    profesor=pro,
#                                                    dedicacion=distributivo.dedicacion)
#             profesorhora.save()
#             print(pro)
#         else:
#             profesorhora = ProfesorConfigurarHoras(periodo_id=119,
#                                                    profesor=pro,
#                                                    dedicacion_id=1)
#             profesorhora.save()
#             print(pro)


# def calculo_modelo_evaluativo(ma):
#     T = ma.campo('T')
#     TF = ma.campo('TF')
#     N1 = ma.campo('N1')
#     N2 = ma.campo('N2')
#     EX = ma.campo('EX')
#     EXR = ma.campo('EXR')
#     T.valor = N1.valor + N2.valor + EX.valor
#     T.save()
#     TF.valor = T.valor
#     ma.notafinal = T.valor
#     if T.valor < 70:
#         if EXR.valor > 0:
#             ma.notafinal = (EXR.valor + float(ma.notafinal)) / 2
#             TF.valor = ma.notafinal
#     else:
#         EXR.valor = 0
#         EXR.save()
#     TF.save()
#     ma.save()



# for rubro in Rubro.objects.filter(epunemi=True, idrubroepunemi__gt=0):
#     cursor = connections['epunemi'].cursor()
#     cursor.execute("select r.valortotal from sagest_rubro r where r.id=%s" % rubro.idrubroepunemi)
#     rows = cursor.fetchall()
#     cursor.close()
#     if rows:
#         if rubro.valortotal != rows[0][0]:
#             print("%s, %s, %s, %s : %s" % (rubro.persona, rubro.id, rubro.idrubroepunemi,rubro, rubro.valortotal))
#
#


# for materia in Materia.objects.filter(status=True, nivel__periodo_id=99):
#     # materia.cerrado = True
#     # materia.fechacierre = datetime.now().date()
#     for asig in materia.asignados_a_esta_materia():
#         # asig.cerrado = True
#         # asig.save()
#         asig.actualiza_estado()
#         asig.cierre_materia_asignada()
#     # for asig in materia.asignados_a_esta_materia():
#     #     asig.cierre_materia_asignada()
#     # materia.save()
#     print(materia)
# from Moodle_Funciones import crearhtmlphpmoodle, crearhtmlphpmoodleadmision
#
# for materia in Materia.objects.values("id").filter(status=True, nivel__periodo_id=119, asignaturamalla__malla__carrera__coordinacion__id__in=[1, 2, 3, 4, 5]):
#     try:
#         crearhtmlphpmoodle(materia['id'])
#         print(materia['id'])
#     except Exception as ex:
#         print('Error al crear html %s ---- %s' % (ex, materia))

# for materia in Materia.objects.filter(status=True, nivel__periodo_id=136, asignaturamalla__malla__carrera__coordinacion__id=9):
#     try:
#         print("%s - %s" % (materia, materia.idcursomoodle))
#         crearhtmlphpmoodleadmision(materia)
#     except Exception as ex:
#         print('Error al crear html %s ---- %s' % (ex, materia))
#


# try:
#     moodlealumnocambio = 44578 # en moodle id de la materia
#     masignadamigrar = 1698210 # materiaasignada del alumno en el sga
#     materia = Materia.objects.get(pk=moodlealumnocambio, status=True)
#     alumno = MateriaAsignada.objects.get(pk=masignadamigrar, status=True, retiramateria=False)
#     if alumno.matricula.bloqueomatricula is False:
#         # Extraer datos de moodle
#         for notasmooc in materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#             campo = alumno.campo(notasmooc[1].upper())
#             # if not alumno.matricula.bloqueomatricula:
#             if type(notasmooc[0]) is Decimal:
#                 if null_to_decimal(campo.valor) != float(notasmooc[0]) or (
#                         alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
#                     actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
#                                                     calificacion=notasmooc[0])
#                     auditorianotas.save()
#             else:
#                 if null_to_decimal(campo.valor) != float(0) or (
#                         alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
#                     actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
#                     auditorianotas.save()
# except Exception as ex:
#     print(ex)
#     pass


### PROCESO QUE ELIMINA MATERIAS EN BLANCO DE ADMISION
count = 0
# for materia in Materia.objects.filter(status=True, nivel__periodo_id=136):
#     if not materia.materiaasignada_set.filter(status=True).count() > 0:
#         count += 1
#         print("%s.- %s" % (count, materia.materiaasignada_set.filter(status=True).count()))
#         materia.status = False
#         materia.save()
#     # print(materia)


import warnings



warnings.filterwarnings('ignore', message='Unverified HTTPS request')



# cant = 0
# for matricula in Matricula.objects.filter(nivel__periodo=periodo, status=True, materiaasignada__matriculas__gt=1).distinct():
#     cantidad = matricula.materiaasignada_set.filter(status=True).count()
#     valortotal = cantidad * 20
#     totalrubro = matricula.rubro_set.filter(status=True)[0].valortotal if matricula.rubro_set.filter(status=True).exists() else 0
#     if valortotal != totalrubro and totalrubro > 0:
#         cant += 1
#         print("Son diferentes %s valor real=%s - valor generado%s --- %s" % (cant, valortotal, totalrubro, matricula))

# from Moodle_Funciones import CrearVidMagistralMoodle
# for urlv in VideoMagistralSilaboSemanal.objects.filter(silabosemanal__silabo__materia__nivel__periodo_id=158).distinct():
#     CrearVidMagistralMoodle(urlv.id, persona=None)
#     print(urlv)


# # ####CORRIJE FECHAS DE LOS DIFERIDOS MAL PAGADOS
# def ajuste_fechas_rubros_pagados(ePeriodo):
#     fechas = [datetime(2022, 11, 5, 0, 0).date(), datetime(2022, 12, 5, 0, 0).date(), datetime(2023, 1, 5, 0, 0).date()]
#     eMatriculas = Matricula.objects.filter(rubro__isnull=False, status=True, nivel__periodo=ePeriodo).distinct()
#     total = eMatriculas.values("id").count()
#     c = 0
#     for eMatricula in eMatriculas:
#         c += 1
#         print(f"({total}/{c}) Matricula: {eMatricula.__str__()}")
#         eRubros = Rubro.objects.filter(matricula=eMatricula, status=True).exclude(observacion='INGLÉS NOVIEMBRE 2022 MARZO 2023')
#         print(f"( ---> Matricula: {eMatricula.__str__()} -> Total de rubros ({eRubros.values('id').count()})")
#         for eRubro in eRubros.filter(tipo_id=2924):
#             eRubro.fechavence = datetime(2022, 11, 5, 0, 0).date()
#             eRubro.cuota = 1
#             eRubro.save()
#         if eMatricula.aranceldiferido == 1 and eMatricula.actacompromiso is not None:
#             contador = 0
#             for eRubro in eRubros.filter(tipo_id=2923, cancelado=True):
#                 contador += 1
#                 if contador == 1:
#                     fechavence = datetime(2022, 11, 5, 0, 0).date()
#                 elif contador == 2:
#                     fechavence = datetime(2022, 12, 5, 0, 0).date()
#                 elif contador == 3:
#                     fechavence = datetime(2023, 1, 5, 0, 0).date()
#                 eRubro.fechavence = fechavence
#                 eRubro.cuota = 1
#                 eRubro.save()
#             cuota = 2
#             for eRubro in eRubros.filter(tipo_id=2923, cancelado=False).order_by('cuota'):
#                 contador += 1
#                 if contador == 1:
#                     fechavence = datetime(2022, 11, 5, 0, 0).date()
#                 elif contador == 2:
#                     fechavence = datetime(2022, 12, 5, 0, 0).date()
#                 elif contador == 3:
#                     fechavence = datetime(2023, 1, 5, 0, 0).date()
#                 eRubro.fechavence = fechavence
#                 eRubro.cuota = cuota
#                 eRubro.save()
#                 cuota += 1
#         else:
#             for eRubro in eRubros.filter(tipo_id=2923):
#                 eRubro.fechavence = datetime(2022, 11, 5, 0, 0).date()
#                 eRubro.cuota = 1
#                 eRubro.save()
#         print(u"* Matricula (ID: %s - %s)" % (eMatricula.id, eMatricula))
#         eMatricula.actualiza_matricula()
#
#
# ePeriodo = Periodo.objects.get(pk=153)
# ajuste_fechas_rubros_pagados(ePeriodo)
#

# periodo = Periodo.objects.get(pk=153)

""""
CREANDO LOS CURSOS
"""
# from moodle import moodle
# # excludemateria = Materia.objects.values_list('id', flat=True).filter(nivel__periodo=periodo, asignaturamalla__nivelmalla_id__in=[7, 8], asignaturamalla__malla__carrera__coordinacion__id__in=[1]).distinct()
# materias = Materia.objects.filter(nivel__periodo=periodo, idcursomoodle__gt=0).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
# tipourl = 1
# cont = 0
# for materia in materias:
#     coordinacion_id = materia.asignaturamalla.malla.carrera.coordinacion_carrera().id
#     idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%sP' % (periodo.idnumber(), coordinacion_id, materia.asignaturamalla.malla.carrera_id, materia.asignaturamalla.nivelmalla_id, materia.id)
#     bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
#     cursoid = 0
#     cont += 1
#     print("contador: %s" % cont)
#     if not bcurso:
#         bcurso = moodle.BuscarCursos(periodo, tipourl, 'idnumber', idnumber_curso)
#     if bcurso:
#         if bcurso['courses']:
#             # print(bcurso['courses'][0])
#             if 'id' in bcurso['courses'][0]:
#                 cursoid = bcurso['courses'][0]['id']
#                 if cursoid != materia.idcursomoodle:
#                     print('********Curso: %s' % materia)
#                     materia.idcursomoodle = cursoid
#                     materia.save()
#                     materia.crear_actualizar_estudiantes_curso(moodle ,1)
#                     # materia.crear_actualizar_docente_curso(moodle, 1)
#                 else:
#                     print("curso ok")
#         else:
#             print(bcurso['courses'])
#     else:
#         print("Fallo el Web service")





# # ##CORREGUIR PANELES DE MOODLE
# materias = Materia.objects.filter(nivel__periodo_id__in=[153], asignaturamalla__malla__carrera__coordinacion__id__in=[1, 2, 3, 4, 5]).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
# for materia in materias:
#     materia.poner_estilo_tarjeta_curso_moodle()


# def eliminar_lecciones_no_aperturada(periodo, fecha_hoy):
#     print(u"****************************************************************************************************")
#     print(f"Inicia proceso de eliminar lecciones no aperturadas a las {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} del periodo {periodo}")
#     eLeccionGrupos = LeccionGrupo.objects.filter(status=False, fecha__lte=fecha_hoy, lecciones__fecha__lte=fecha_hoy, lecciones__clase__materia__nivel__periodo=periodo)
#     with transaction.atomic():
#         try:
#             for eLeccionGrupo in eLeccionGrupos:
#                 eLecciones = eLeccionGrupo.lecciones.all()
#                 if eLecciones.values("id").filter(status=True).exists():
#                     for eLeccion in eLecciones:
#                         for eAsistenciaLeccion in eLeccion.asistencialeccion_set.all():
#                             eAsistenciaLeccion.status = True
#                             eAsistenciaLeccion.save()
#                             eMateriaAsignada = eAsistenciaLeccion.materiaasignada
#                             eMateriaAsignada.save(actualiza=True)
#                         eLeccion.status = True
#                         eLeccion.save()
#                     eLeccionGrupo.status = True
#                     eLeccionGrupo.save()
#                 else:
#                     eLeccionGrupo.delete()
#         except Exception as ex:
#             transaction.set_rollback(True)
#             print(f"Error al eliminar lección {ex.__str__()}")
#
#
# periodo = Periodo.objects.get(pk=153)
# fecha_hoy = datetime(2022, 11, 30, 23, 59)
# eliminar_lecciones_no_aperturada(periodo, fecha_hoy)


# from moodle import moodle
# # materias = Materia.objects.filter(idcursomoodle__in=[1206, 1190, 892], nivel__periodo_id__in=[202], asignaturamalla__malla__carrera__coordinacion__id__in=[1,2,3,4,5]).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
# materias = Materia.objects.filter(idcursomoodle__in=[1278], nivel__periodo_id__in=[153]).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
# tipourl = 1
# cont = 0
# from Moodle_Funciones import crearhtmlphpmoodle, crearhtmlphpmoodleadmision
# print(materias.count())
# from django.db import connections
# cursor = connections['moodle_db'].cursor()
#
# for materia in materias:
#     print(materia.urlhtml)
#     with open(materia.urlhtml) as f:
#         a = f.read()
#         print(a)
#     f.close()
#     if a == urlerror:
#         print('Listo si lo valido')
#     print('********Curso: %s, %s' % (materia, materia.idcursomoodle))
#     # crearhtmlphpmoodle(materia.id)


# #####MIGRAR NOTAS DE ADMISION
# try:
#     contador = 0
#     periodo = Periodo.objects.get(id=202)
#     for materia in Materia.objects.filter(nivel__periodo=periodo):
#         for alumno in materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
#             contador += 1
#             print("%s - %s" %(contador, alumno))
#             if materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#                 for notasmooc in materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#                     campo = alumno.campo(notasmooc[1].upper())
#                     if type(notasmooc[0]) is Decimal:
#                         if null_to_decimal(campo.valor) != float(notasmooc[0]) or (alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
#                             actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                             auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=notasmooc[0])
#                             auditorianotas.save()
#                     else:
#                         if null_to_decimal(campo.valor) != float(0) or (alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
#                             actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                             auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
#                             auditorianotas.save()
#             else:
#                 for detallemodelo in materia.modeloevaluativo.detallemodeloevaluativo_set.filter(migrarmoodle=True):
#                     campo = alumno.campo(detallemodelo.nombre)
#                     actualizar_nota_planificacion(alumno.id, detallemodelo.nombre, 0)
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
#                     auditorianotas.save()
# except Exception as ex:
#     print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
# #

# #####ACTUALIZAR ESTADOS DE NOTAS DE ADMISION ---- SOLO MEDICINA SE CONSIDERO PRESENCIAL EN ESTE PROCESO, LO IDEAL ES QUE SE CONSULTE POR MODALIDAD
# try:
#     contador = 0
#     periodo = Periodo.objects.get(id=202)
#     for materia in Materia.objects.filter(nivel__periodo=periodo):
#         carrera_id = materia.asignaturamalla.malla.carrera_id
#         for alumno in materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
#             contador += 1
#             print("%s - %s" %(contador, alumno))
#             if carrera_id != 223:
#                 if alumno.asistenciafinal != 100:
#                     alumno.asistenciafinal = 100
#                     alumno.save()
#             alumno.actualiza_estado()
# except Exception as ex:
#     print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))


#CERRAR ADMISION

# for materia in Materia.objects.filter(status=True, nivel__periodo_id=202):
#     for asig in materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
#         asig.cierre_materia_asignada()
#         print(asig)
#     print(materia)
#
#
# for inscripcion in Inscripcion.objects.filter(matricula__nivel__periodo__id__in=[202], matricula__retiradomatricula=False):
#     inscripcion.actualizar_nivel()
#     inscripcion.save()
#     print(inscripcion.id)

# for matricula in Matricula.objects.filter(nivel__periodo__id=202, retiradomatricula=False):
#     try:
#         matricula.calcula_nivel()
#         print(matricula)
#     except Exception as ex:
#         pass

# #####MIGRAR NOTAS DE PREGRADO
# periodo = Periodo.objects.get(id=153)
# try:
#     contador = 0
#     for materia in Materia.objects.filter(cerrado=False, tipomateria=3, nivel__periodo=periodo, asignaturamalla__malla__carrera__coordinacion__id__in=[1, 2, 3, 4, 5]):
#         for alumno in materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
#             contador += 1
#             print("%s - %s" %(contador, alumno))
#             if materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#                 try:
#                     for notasmooc in materia.notas_de_moodle(alumno.matricula.inscripcion.persona):
#                         campo = alumno.campo(notasmooc[1].upper())
#                         if type(notasmooc[0]) is Decimal:
#                             if null_to_decimal(campo.valor) != float(notasmooc[0]) or (alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
#                                 actualizar_nota_planificacion(alumno.id, notasmooc[1].upper().strip(), notasmooc[0])
#                                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False,
#                                                                 calificacion=notasmooc[0])
#                                 auditorianotas.save()
#                         else:
#                             if null_to_decimal(campo.valor) != float(0) or (
#                                     alumno.asistenciafinal < campo.detallemodeloevaluativo.modelo.asistenciaaprobar):
#                                 actualizar_nota_planificacion(alumno.id, notasmooc[1].upper(), notasmooc[0])
#                                 auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
#                                 auditorianotas.save()
#                 except Exception as ex:
#                     pass
#             else:
#                 for detallemodelo in materia.modeloevaluativo.detallemodeloevaluativo_set.filter(migrarmoodle=True):
#                     campo = alumno.campo(detallemodelo.nombre)
#                     actualizar_nota_planificacion(alumno.id, detallemodelo.nombre, 0)
#                     auditorianotas = AuditoriaNotas(evaluaciongenerica=campo, manual=False, calificacion=0)
#                     auditorianotas.save()
# except Exception as ex:
#     print('Error on line {} {}'.format(ex, sys.exc_info()[-1].tb_lineno))
#
# for materia in Materia.objects.filter(cerrado=False, tipomateria=3, status=True, nivel__periodo=periodo):
#     for asig in materia.materiaasignada_set.filter(status=True, retiramateria=False).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2','matricula__inscripcion__persona__nombres'):
#         asig.cierre_materia_asignada()
#         print(asig)
#     materia.cerrado = True
#     materia.save()
#     print(materia)

#
# for inscripcion in Inscripcion.objects.filter(matricula__nivel__periodo=periodo, matricula__retiradomatricula=False):
#     inscripcion.actualizar_nivel()
#     inscripcion.save()
#     print(inscripcion.id)

# eMatriculas = Matricula.objects.filter(rubro__isnull=False, status=True, nivel__periodo_id=177).distinct()
# total = eMatriculas.values("id").count()
# c = 0
# for eMatricula in eMatriculas:
#     c += 1
#     print(f"({total}/{c}) Matricula: {eMatricula.__str__()}")
#     eRubros = Rubro.objects.filter(matricula=eMatricula, status=True).exclude(observacion='INGLÉS NOVIEMBRE 2022 MARZO 2023').order_by("cuota")
#     print(f"( ---> Matricula: {eMatricula.__str__()} -> Total de rubros ({eRubros.values('id').count()})")
#     if eMatricula.aranceldiferido == 1 and eMatricula.actacompromiso is not None:
#         contador = 0
#         for eRubro in eRubros.filter(tipo_id=2923, status=True):
#             contador += 1
#             if contador == 1:
#                 fechavence = datetime(2023, 6, 5, 0, 0).date()
#             elif contador == 2:
#                 fechavence = datetime(2023, 7, 5, 0, 0).date()
#             elif contador == 3:
#                 fechavence = datetime(2023, 8, 5, 0, 0).date()
#             eRubro.fechavence = fechavence
#             eRubro.cuota = 1
#             eRubro.save()

# periodospregrado = [177]
# for materia in Materia.objects.filter(actualizarhtml=True, status=True, nivel__periodo_id__in=periodospregrado, asignaturamalla__malla__carrera__coordinacion__id__in=[9]):
#     try:
#         carrera_id = materia.asignaturamalla.malla.carrera_id
#         if materia.coordinacion().id == 9:
#             if carrera_id != 223:
#                 print(materia)
#                 materia.materiaasignada_set.filter(status=True).update(sinasistencia=True)
#
#     except Exception as ex:
#         print('Error al crear html %s ---- %s' % (ex, materia))

# bucket_name = 'admision_proctoring_unemi'
# from runback.arreglos.actualizar_bucket import upload_to_bucket
# source_file_name = f'/mnt/nfs/home/storage/servidoresunemi/Srv-IaaS-Unemi-OJS_1-flat.vmdk'
# destination_blob_name = f'servidoresunemi/Srv-IaaS-Unemi-OJS-flat.vmdk'
# upload_to_bucket(bucket_name, source_file_name, destination_blob_name)

# from moodle import moodle
# periodo = Periodo.objects.get(pk=224)
# eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
# cursos = Materia.objects.filter(nivel__periodo=periodo,
#                                 status=True, asignaturamalla__malla__carrera__coordinacion__id=9).exclude(
#     asignaturamalla__malla_id__in=eMallasIngles).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion',
#                                                                      'id')
# ano = '%s_%s-%s_%s' % (periodo.inicio.year, periodo.inicio.month, periodo.fin.year, periodo.fin.month)
#
# for curso in cursos:
#     if curso.coordinacion().id == 9:
#         idnumber_periodo = u'PER%s-%s' % (periodo.id, ano)
#         idnumber_curso = u'%s-COR%s-CARR%s-NIVEL%s-CURS%s' % (
#         idnumber_periodo, 9, curso.asignaturamalla.malla.carrera_id, curso.asignaturamalla.nivelmalla_id, curso.id)
#
#     cursoid = curso.buscar_cursomoodle(idnumber_curso)
#
#     if cursoid > 0:
#         if curso.idcursomoodle != cursoid:
#             curso.idcursomoodle = cursoid
#             curso.modelotarjeta = True
#             curso.save()
#         try:
#             # curso.crear_actualizar_docente_curso_admision(moodle, 2)
#             curso.crear_actualizar_estudiantes_curso(moodle, 1)
#         except Exception as ex:
#             print('Error al crear estudiante %s' % ex)
#     else:
#         print("Curso no encontrado (%s), (%s) - %s - %s" % (idnumber_curso, curso.asignatura, curso.id, curso.idcursomoodle))

# periodo = Periodo.objects.get(pk=224)
# from  Moodle_Funciones import CrearTestMoodleAdmision
# eMallasIngles = Malla.objects.filter(pk__in=[353, 22]).values_list('id', flat=True)
# cursos = Materia.objects.filter(asignatura_id=4881, nivel__periodo=periodo, status=True, asignaturamalla__malla__carrera__coordinacion__id=9).exclude(asignaturamalla__malla_id__in=eMallasIngles).distinct().order_by('asignatura__nombre', 'inicio', 'identificacion', 'id')
# for curso in cursos:
#     cursoid = curso.idcursomoodle
#     if cursoid > 0:
#         try:
#             profesor = curso.profesor_principal()
#             test = TestSilaboSemanalAdmision.objects.get(silabosemanal__numsemana=2, silabosemanal__silabo__status=True, silabosemanal__silabo__materia=curso, status=True, silabosemanal__status=True)
#             # test.titulo = 'TEST_1'
#             # test.detallemodelo_id = 110
#             # test.vecesintento = 1
#             # test.navegacion = 2
#             # test.esquemapregunta = 1
#             test.tiempoduracion = 30
#             test.save()
#             if profesor:
#                 value, msg = CrearTestMoodleAdmision(test.id, profesor.persona)
#                 if not value:
#                     raise NameError(msg)
#
#         except Exception as ex:
#             print('Error al crear test %s - %s - %s' % (ex, profesor, cursoid))

from Moodle_Funciones import crearhtmlphpmoodle, crearhtmlphpmoodleadmision
import sys
from django.db import transaction, connection, IntegrityError
periodospregrado = [317]
for materia in Materia.objects.filter(status=True, nivel__periodo_id__in=periodospregrado, asignaturamalla__malla__carrera__coordinacion__id__in=[1, 2, 3, 4, 5, 9]):
    try:
        if materia.coordinacion().id != 9:
            if materia.idcursomoodle > 0:
                cursoid = materia.idcursomoodle
                fecha = int(time.mktime(datetime.now().timetuple()))
                cursor = connections['moodle_db'].cursor()
                materia.namehtml = 'contruyendo_silabo.html'
                materia.actualizarhtml = True
                materia.save()

                if materia.fecha_modificacion:
                    version = '?v=%s' % materia.fecha_modificacion.strftime('%Y%m%d_%H%M%S')
                else:
                    version = '?v=%s' % materia.fecha_creacion.strftime('%Y%m%d_%H%M%S')
                summary = """
                                <iframe src="https://sga.unemi.edu.ec/static/contruyendo_silabo.html%s"  class="filter_hvp" id="hvp_4383" style="width:100%s; height:1000px; border:0;" frameborder="0" allowfullscreen="allowfullscreen"></iframe>
                            """ % (version, '%')
                sql = """UPDATE mooc_course_sections set summary='%s' WHERE course=%s AND SECTION='0' """ % (
                summary, cursoid)
                cursor.execute(sql)

                query = u"UPDATE mooc_course SET cacherev = %s WHERE id = %s" % (fecha, cursoid)
                cursor.execute(query)
                print(materia)

    except Exception as ex:
        print('Error al crear html %s ---- %s ----- %s' % (ex, materia,  sys.exc_info()[-1].tb_lineno))

