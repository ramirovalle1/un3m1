#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
import sys

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
from sga.funciones import calculate_username, generar_usuario, fechatope

# for inscripcion in Inscripcion.objects.filter(matricula__nivel__periodo__id=82, matricula__retiradomatricula=False):
#     inscripcion.actualizar_nivel()
#     inscripcion.save()
#     print(inscripcion.id)



# for materias in Materia.objects.filter(nivel__periodo_id=82).exclude(nivel__sesion_id__in=[12, 13]).distinct('asignaturamalla__malla').order_by('asignaturamalla__malla'):
#     print('%s' % materias.asignaturamalla.malla)

# ARREGLA SALDOS DEL KARDEX
# arregla kardex ay que poner al comienzo un id menor para que funcione
# producto = Producto.objects.get(pk=100)
# idanterior = 21757
# idnormal = 21799
# arregloid = KardexInventario.objects.values_list('id', flat=True).filter(producto=producto, id__gte=idanterior, status=True).order_by('id')
# i = 0
# for k in KardexInventario.objects.filter(producto=producto, id__gte=idnormal, status=True).order_by('id'):
#     print (k.id)
#     saldoanterior = KardexInventario.objects.get(pk=arregloid[i]).saldofinalvalor
#     cantidadanterior = KardexInventario.objects.get(pk=arregloid[i]).saldofinalcantidad
#     print (saldoanterior)
#     k.saldoinicialvalor = saldoanterior
#     k.saldoinicialcantidad = cantidadanterior
#     k.costo = Decimal(0.5728849557522124).quantize(Decimal('.0000000000000001'))
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


# while True:
#     #do some serial sending here
#     sleep(60)
#     print("hola")

# # SOLICITAR CAMBIO DE CLAVE
# for ins in Inscripcion.objects.all():
#     ins.persona.cambiar_clave()
#     print(ins.persona)


# for adm in Administrativo.objects.all():
#     adm.persona.cambiar_clave()
#     print(adm.persona)

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


# ## COPIA DE BACKCUP ASISTENCIA
try:
    linea = 1
    cursorbackup = connections['backup'].cursor()
    cursor = connections['default'].cursor()
    sql="""
            SELECT l.id, l.clase_id, l.fecha, l.horaentrada, l.horasalida, l.abierta, l.contenido, l.observaciones,
            l.estrategiasmetodologicas, l.status, l.usuario_creacion_id, l.fecha_creacion, l.usuario_modificacion_id,
            l.fecha_modificacion, l.ipingreso, l.ipexterna, l.motivoapertura, l.origen_movil, l.origen_coordinador, l.automatica,
            l.solicitada, l.aperturaleccion
            FROM sga_leccion l
            INNER JOIN sga_clase cl ON cl.id=l.clase_id
            INNER JOIN sga_materia ma ON ma.id=cl.materia_id
            INNER JOIN sga_nivel ni ON ni.id=ma.nivel_id AND ni.periodo_id=82
    """
    cursorbackup.execute(sql)
    results = cursorbackup.fetchall()
    for r in results:
        if not Leccion.objects.values("id").filter(status=True, pk=r[0]).exists():
            Leccion.objects.filter(clase_id=r[1], fecha=r[2]).delete()
            leccion = Leccion(id=r[0],
                              clase_id=r[1], fecha=r[2], horaentrada=r[3], horasalida=r[4],
                              abierta=r[5], contenido=r[6], observaciones=r[7], estrategiasmetodologicas=r[8], status=r[9], usuario_creacion_id=r[10],
                              fecha_creacion=r[11], usuario_modificacion_id=r[12],fecha_modificacion=r[13],
                              ipingreso=r[14], ipexterna=r[15], motivoapertura=r[16], origen_movil=r[17],
                              origen_coordinador=r[18], automatica=r[19], solicitada=r[20], aperturaleccion=r[21])
            leccion.save()
        else:
            leccion = Leccion.objects.get(status=True, pk=r[0])
        ############ verificar si estan todas las asistencias cargadas
        sqlasi = """
                    SELECT id, leccion_id, asistio, materiaasignada_id, status, usuario_creacion_id,
                    fecha_creacion,usuario_modificacion_id,fecha_modificacion,asistenciajustificada
                    FROM sga_asistencialeccion a
                    WHERE a.leccion_id=%s
            """ % r[0]
        cursorbackup.execute(sqlasi)
        resultsasi = cursorbackup.fetchall()
        for ra in resultsasi:
            if MateriaAsignada.objects.filter(pk=ra[3]).exists():
                if not leccion.asistencialeccion_set.values("id").filter(materiaasignada_id=ra[3]).exists():
                    asistencialeccion = AsistenciaLeccion(id=ra[0],leccion_id=ra[1],asistio=ra[2],materiaasignada_id=ra[3],
                                                          status=ra[4],usuario_creacion_id=ra[5],
                                                          fecha_creacion=ra[6],usuario_modificacion_id=ra[7],fecha_modificacion=ra[8],asistenciajustificada=ra[9])
                    asistencialeccion.save()

        ############ verificar si estan todas las evaluaciones lecciones cargadas
        sqleva = """
                    SELECT id, leccion_id, evaluacion, materiaasignada_id, status, usuario_creacion_id, fecha_creacion, usuario_modificacion_id, fecha_modificacion
                    FROM sga_evaluacionleccion
                    WHERE leccion_id=%s
            """ % r[0]
        cursorbackup.execute(sqleva)
        resultseva = cursorbackup.fetchall()
        for re in resultseva:
            if not leccion.evaluacionleccion_set.values("id").filter(materiaasignada_id=re[3]).exists():
                evaluacionleccion = EvaluacionLeccion(id=re[0], leccion_id=re[1], evaluacion=re[2], materiaasignada_id=re[3], status=re[4], usuario_creacion_id=re[5],
                                                      fecha_creacion=re[6], usuario_modificacion_id=re[7], fecha_modificacion=re[8])
                evaluacionleccion.save()

        ############ verificar si estan todos los silabos cargadas
        sqltem = """
                    SELECT id, status, usuario_creacion_id, fecha_creacion, usuario_modificacion_id, fecha_modificacion,
                    leccion_id, tema_id, fecha
                    FROM sga_temaasistencia
                    WHERE leccion_id=%s
            """ % r[0]
        cursorbackup.execute(sqltem)
        resultstem = cursorbackup.fetchall()
        for rt in resultstem:
            if TemaAsistencia.objects.values("id").filter(pk=rt[0]).exists():
                temaasistencia = TemaAsistencia.objects.get(pk=rt[0])
                temaasistencia.leccion_id = r[0]
                temaasistencia.save()

        ############ verificar si estan todas las leccionesGrupo cargadas
        sqllgr = """
                    SELECT id, lecciongrupo_id, leccion_id FROM sga_lecciongrupo_lecciones
                    WHERE leccion_id=%s
            """ % r[0]
        cursorbackup.execute(sqllgr)
        resultslgr = cursorbackup.fetchall()
        for rlg in resultslgr:
            sqlgr = """
                        SELECT id, profesor_id, turno_id, aula_id, dia, fecha, horaentrada, horasalida, abierta, contenido, observaciones,
                        estrategiasmetodologicas,origen_movil,motivoapertura,automatica,origen_coordinador,solicitada,
                        status,usuario_creacion_id,fecha_creacion,usuario_modificacion_id,fecha_modificacion,ipingreso,ipexterna
                        FROM sga_lecciongrupo
                        WHERE id=%s
                    """ % rlg[1]

            cursorbackup.execute(sqlgr)
            resultsgr = cursorbackup.fetchall()
            for rg in resultsgr:
                if not LeccionGrupo.objects.values("id").filter(status=True, pk=rg[0]).exists():
                    LeccionGrupo.objects.filter(profesor_id=rg[1], fecha=rg[5], turno_id=rg[2]).delete()
                    lecciongrupo = LeccionGrupo(id=rg[0],
                                                profesor_id=rg[1], turno_id=rg[2], aula_id=rg[3], dia=rg[4],
                                                fecha=rg[5], horaentrada=rg[6], horasalida=rg[7], abierta=rg[8],
                                                contenido=rg[9], observaciones=rg[10],
                                                estrategiasmetodologicas=rg[11], origen_movil=rg[12], motivoapertura=rg[13],
                                                automatica=rg[14], origen_coordinador=rg[15], solicitada=rg[16], status=rg[17],
                                                usuario_creacion_id=rg[18], fecha_creacion=rg[19], usuario_modificacion_id=rg[20], fecha_modificacion=rg[21],
                                                ipingreso=rg[22], ipexterna=rg[23])
                    lecciongrupo.save()
                else:
                    lecciongrupo = LeccionGrupo.objects.get(status=True, pk=rg[0])

                sqlunemi = """
                            SELECT id, lecciongrupo_id, leccion_id FROM sga_lecciongrupo_lecciones
                            WHERE leccion_id=%s and lecciongrupo_id=%s
                            """ % (rlg[2], rlg[1])
                cursor.execute(sqlunemi)
                resultsunemi = cursor.fetchall()
                if not resultsunemi:
                    sqlune = """
                            INSERT INTO sga_lecciongrupo_lecciones(id, leccion_id, lecciongrupo_id) values(%s, %s, %s)
                            """ % (rlg[0], rlg[2], rlg[1])
                    cursor.execute(sqlune)
        linea += 1
        print("%s - %s" % (linea, leccion))
except Exception as ex:
    print('error: %s' % ex)

### FIN DE COPIA DE ASISTENCIA BACKCUP
