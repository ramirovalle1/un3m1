import os
import sys
# import io
# import xlsxwriter
# import xlwt
# import openpyxl
# import xlwt
# from xlwt import *
# from django.http import HttpResponse
# from xlwt import *
#
YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from settings import DEBUG
# from django.http import HttpResponse
# from settings import MEDIA_ROOT, BASE_DIR
# from xlwt import easyxf, XFStyle
# from sga.adm_criteriosactividadesdocente import asistencia_tutoria
# from inno.models import *
# from sga.models import *
# from sagest.models import *
# from inno.funciones import *
# import concurrent.futures
# from balcon.models import *
# from Moodle_Funciones import crearhtmlphpmoodle


def masivo_duplicar_programa_analitico():
    try:
        from django.db.models import Exists, OuterRef
        from sga.models import Malla, Materia, AsignaturaMalla, ProgramaAnaliticoAsignatura, ResultadoAprendizajeRai, ResultadoAprendizajeRac, ObjetivoProgramaAnaliticoAsignatura, MetodologiaProgramaAnaliticoAsignatura, BibliografiaProgramaAnaliticoAsignatura, ContenidoResultadoProgramaAnalitico, UnidadResultadoProgramaAnalitico, TemaUnidadResultadoProgramaAnalitico, SubtemaUnidadResultadoProgramaAnalitico
        ePeriodo = 317

        # listado_carreras = [133, 146, 140, 187, 132, 170, 143, 129, 137, 131, 126, 158, 128, 141, 138, 135, 150, 175, 225, 224, 134, 127, 142, 130, 149, 156, 157, 110, 188, 111, 112, 153, 139, 151, 133, 160]
        listado_carreras = [133]

        for c in listado_carreras:

            eMalla = Malla.objects.filter(carrera=c, vigente=True, status=True).annotate(enusoperiodo=Exists(Materia.objects.filter(status=True, nivel__periodo_id=ePeriodo, asignaturamalla__malla_id=OuterRef('id')))).filter(enusoperiodo=True).first()
            if not eMalla:
                print(f'carrera {c} - Sin malla vigente en el periodo(317)')
                pass
            listado_asignaturamalla = AsignaturaMalla.objects.filter(malla=eMalla, transversal=False, status=True).exclude(unidad_organizacion_curricular_id__in=[3, 8])
            if c in [126, 133]:
                listado_asignaturamalla = listado_asignaturamalla.filter(asignaturapracticas=False)
            _count, forloop = listado_asignaturamalla.count(), 0
            print(f'CANTIDAD DE ASIGNATURAS: {_count}')
            for asignaturamalla in listado_asignaturamalla.order_by('nivelmalla__orden'):
                forloop += 1
                programasananalitico = ProgramaAnaliticoAsignatura.objects.filter(asignaturamalla=asignaturamalla, status=True)
                programaa_activo = programasananalitico.filter(activo=True).first()
                if not programaa_activo:
                    print(f'{forloop} - {asignaturamalla.asignatura.nombre} - Sin plan analítico activo ')
                    continue
                programa = programaa_activo
                if programaa_activo and not ProgramaAnaliticoAsignatura.objects.values_list('id', flat=True).filter(status=True, asignaturamalla=programa.asignaturamalla, procedimientoeva_id=6):
                    proanalitico = ProgramaAnaliticoAsignatura(asignaturamalla=programa.asignaturamalla,
                                                               descripcion=programa.descripcion,
                                                               compromisos=programa.compromisos,
                                                               integranteuno=programa.integranteuno,
                                                               integrantedos=programa.integrantedos,
                                                               integrantetres=programa.integrantetres,
                                                               activo=False)
                    proanalitico.save()
                    #ASIGNAR procedimiento de evaluación
                    proanalitico.procedimientoeva_id = 6
                    proanalitico.save()
                    #FIN ASIGNAR

                    if programa.resultadoaprendizajerai_set.filter(status=True).exists():
                        rai = programa.resultadoaprendizajerai_set.filter(status=True)[0]
                        ri = ResultadoAprendizajeRai(programaanaliticoasignatura=proanalitico, descripcion=rai.descripcion)
                        ri.save()
                    if programa.resultadoaprendizajerac_set.filter(status=True).exists():
                        rac = programa.resultadoaprendizajerac_set.filter(status=True)[0]
                        rc = ResultadoAprendizajeRac(programaanaliticoasignatura=proanalitico, descripcion=rac.descripcion)
                        rc.save()
                    if programa.objetivoprogramaanaliticoasignatura_set.filter(status=True).exists():
                        obj = programa.objetivoprogramaanaliticoasignatura_set.filter(status=True)[0]
                        objt = ObjetivoProgramaAnaliticoAsignatura(programaanaliticoasignatura=proanalitico, descripcion=obj.descripcion)
                        objt.save()
                    if programa.metodologiaprogramaanaliticoasignatura_set.filter(status=True).exists():
                        met = programa.metodologiaprogramaanaliticoasignatura_set.filter(status=True)[0]
                        mt = MetodologiaProgramaAnaliticoAsignatura(programaanaliticoasignatura=proanalitico, descripcion=met.descripcion)
                        mt.save()
                    if programa.bibliografiaprogramaanaliticoasignatura_set.filter(status=True).exists():
                        for bli in programa.bibliografiaprogramaanaliticoasignatura_set.filter(status=True):
                            blio = BibliografiaProgramaAnaliticoAsignatura(programaanaliticoasignatura=proanalitico, librokohaprogramaanaliticoasignatura=bli.librokohaprogramaanaliticoasignatura)
                            blio.save()
                    if programa.contenidoresultadoprogramaanalitico_set.filter(status=True).exists():
                        for cont in programa.contenidoresultadoprogramaanalitico_set.filter(status=True):
                            con = ContenidoResultadoProgramaAnalitico(programaanaliticoasignatura=proanalitico, descripcion=cont.descripcion, orden=cont.orden)
                            con.save()
                            if cont.unidadresultadoprogramaanalitico_set.filter(status=True).exists():
                                for uni in cont.unidadresultadoprogramaanalitico_set.filter(status=True):
                                    un = UnidadResultadoProgramaAnalitico(contenidoresultadoprogramaanalitico=con, descripcion=uni.descripcion, orden=uni.orden)
                                    un.save()
                                    if uni.temaunidadresultadoprogramaanalitico_set.filter(status=True).exists():
                                        for tem in uni.temaunidadresultadoprogramaanalitico_set.filter(status=True):
                                            t = TemaUnidadResultadoProgramaAnalitico(unidadresultadoprogramaanalitico=un, descripcion=tem.descripcion, orden=tem.orden)
                                            t.save()
                                            if tem.subtemaunidadresultadoprogramaanalitico_set.filter(status=True).exists():
                                                for sub in tem.subtemaunidadresultadoprogramaanalitico_set.filter(status=True):
                                                    s = SubtemaUnidadResultadoProgramaAnalitico(temaunidadresultadoprogramaanalitico=t, descripcion=sub.descripcion, orden=sub.orden)
                                                    s.save()
                    print(f'{forloop} - {asignaturamalla.asignatura.nombre} - OK ')
                else:
                    print(f'{forloop} - {asignaturamalla.asignatura.nombre} - YA ESTABA CREADO ')
        print('FIN PROCESO ')
    except Exception as ex:
        print(ex.__str__())


masivo_duplicar_programa_analitico()


# def actualiza_criterios_actividades_tecnico_transversal():
#     ePeriodo = 317
#     listado_materias = ProfesorMateria.objects.filter(status=True, tipoprofesor_id=22, materia__nivel__periodo=ePeriodo)
#     listado_docentes = listado_materias.values_list('profesor', flat=True).order_by('profesor__persona__apellido1').distinct()
#     print(f'Total_materias: {listado_materias.count()}')
#     print(f'Total_docentes: {listado_docentes.count()}')
#     for iddocente in listado_docentes:
#         listado_materias_docente = listado_materias.filter(profesor_id=iddocente)
#         eProfesor = listado_materias_docente[0].profesor
#
#         print(f' --------------------------------      {eProfesor} - {eProfesor.persona.cedula}      ---------------------------------')
#         print(f'Cantidad materias docente: {listado_materias_docente.count()}')
#         distributivo = ProfesorDistributivoHoras.objects.filter(status=True, periodo_id=ePeriodo, profesor=eProfesor).first()
#         print(f'Distributivo: {distributivo.profesor} - periodo: {distributivo.periodo.nombre}')
#         print(f'Horas Docencia: {distributivo.horasdocencia}')
#
#         totalhoras_materias_docente = sum(materia.hora for materia in listado_materias_docente)
#         print(f'total_horas_materias_docente: {totalhoras_materias_docente}')
#
#         estado_bloqueo_distributivo = distributivo.bloqueardistributivo
#         if distributivo.bloqueardistributivo:
#             distributivo.bloqueardistributivo = False
#             distributivo.save()
#
#         # ACTUALIZA CRITERIO Y ACTIVIDAD DE TECNICO TRANSVERSAL
#         criterio_tecnico_transversal = CriterioDocenciaPeriodo.objects.filter(criterio_id=185, periodo_id=ePeriodo).last()
#         if criterio_tecnico_transversal:
#             eDetalle = DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=criterio_tecnico_transversal).first()
#             if totalhoras_materias_docente > 0:
#                 if not eDetalle:
#                     print(f'Detalle Criterio Tecnico Transversal creado')
#                     eDetalle = DetalleDistributivo(distributivo=distributivo,
#                                                    criteriodocenciaperiodo=criterio_tecnico_transversal,
#                                                    criterioinvestigacionperiodo=None,
#                                                    criteriogestionperiodo=None,
#                                                    criteriovinculacionperiodo=None,
#                                                    horas=totalhoras_materias_docente)
#                     eDetalle.save()
#                 else:
#                     eDetalle.horas = totalhoras_materias_docente
#                     eDetalle.save()
#                 eDetalle.verifica_actividades(horas=eDetalle.horas)
#
#                 tecnicotransversal_horas = eDetalle.horas
#                 print(f'Detalle distributivo transversal: {eDetalle.criteriodocenciaperiodo.criterio.nombre}')
#                 print(f'Técnico transversal horas: {tecnicotransversal_horas}')
#             else:
#                 print(f'Sin horas para crear criterio transversal')
#
#             # ACTUALIZA CRITERIO  IMPARTIR CLASE
#             criterio_impartir_clase = CriterioDocenciaPeriodo.objects.filter(criterio_id=118, periodo_id=ePeriodo).last()
#             if criterio_impartir_clase:
#                 eDetalle2 = DetalleDistributivo.objects.filter(distributivo=distributivo, criteriodocenciaperiodo=criterio_impartir_clase).first()
#                 if eDetalle2:
#                     horas_restantes = eDetalle2.horas - totalhoras_materias_docente
#                     if horas_restantes > 0:
#                         eDetalle2.horas = horas_restantes
#                         eDetalle2.save()
#                         eDetalle2.verifica_actividades(horas=eDetalle2.horas)
#                         print(f'Detalle distributivo Impartir: {eDetalle2.criteriodocenciaperiodo.criterio.nombre}')
#                         print(f'Impartir clase horas: {eDetalle2.horas}')
#                     else:
#                         print(f'Detalle Criterio Impartir clase eliminado')
#                         print(f'Impartir clase horas: {eDetalle2.horas}')
#                         eDetalle2.delete()
#                         distributivo.actualiza_hijos()
#
#                 else:
#                     print(f'No existe el Criterio Impartir Clase')
#
#         distributivo.resumen_evaluacion_acreditacion().actualizar_resumen()
#         if estado_bloqueo_distributivo:
#             distributivo.bloqueardistributivo = True
#         distributivo.save()
#
#     print(' --------------------------------------------------------------------------------------------------------------------------------- ')
#
#
# actualiza_criterios_actividades_tecnico_transversal()


# def reporte_estudiantes_matriculados_asignaturas_PPP():
#     try:
#         # libre_origen = "/reporte_estudiantes_matriculados_asignaturas_PPP_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#         libre_origen = "/reporte_estudiantes_matriculados_asignaturas_PPP.xls"
#         fuentecabecera = easyxf(
#             'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
#         fuentenormal = easyxf(
#             'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
#         output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
#         libdestino = xlwt.Workbook()
#         hojadestino = libdestino.add_sheet('Sheet1')
#         fil = 0
#         lin = 0
#         columnas = [(u"ESTUDIANTE", 9500),
#                     (u"IDENTIFICACIÓN", 4000),
#                     (u"CARRERA", 12000),
#                     (u"ASIGNATURA", 12000),
#                     (u"DOCENTE", 9500),
#                     (u"PARALELO", 4000),
#                     (u"NIVEL ACADÉMICO", 5000),
#                     (u"CORREO ELECTRÓNICO", 7000),
#                     (u"CORREO INSTITUCIONAL", 7000),
#                     (u"TELÉFONOS", 6000),
#                     (u"PAÍS", 4000),
#                     (u"PROVINCIA", 6000),
#                     (u"CANTÓN", 6000),
#                     (u"PARROQUIA", 6000),
#                     (u"CIUDADELA", 7000),
#                     (u"SECTOR", 8000),
#                     (u"DIRECCIÓN", 12000),
#                     (u"¿TIENE DISCAPACIDAD?", 6000),
#                     (u"TIPO DISCAPACIDAD", 10000),
#                     (u"¿PPL?", 2000),
#                     (u"DETALLE PPL", 10000),
#         ]
#         for col_num in range(len(columnas)):
#             hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
#             hojadestino.col(col_num).width = columnas[col_num][1]
#         fila = 1
#         eListadoEstudiantes = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo_id=317,
#                                                              matricula__status=True, matricula__retiradomatricula=False,
#                                                              retiromanual=False, retiramateria=False,
#                                                              materia__status=True, materia__asignaturamalla__status=True,
#                                                              matricula__inscripcion__coordinacion_id__in=[1, 2, 3, 4, 5],
#                                                              materia__asignaturamalla__malla__validamatricula=True,
#                                                              materia__asignaturamalla__asignaturapracticas=True
#                                                              ).order_by('matricula__inscripcion__coordinacion_id',
#                                                                         'matricula__inscripcion__carrera_id',
#                                                                         'matricula__inscripcion__persona__apellido1').distinct()
#         for e in eListadoEstudiantes:
#             estudinate = e.matricula.inscripcion.persona
#             hojadestino.write(fila, 0, '%s' % estudinate.nombre_completo_inverso(), fuentenormal)
#             hojadestino.write(fila, 1, '%s' % estudinate.identificacion(), fuentenormal)
#             hojadestino.write(fila, 2, '%s' % e.matricula.inscripcion.carrera, fuentenormal)
#             hojadestino.write(fila, 3, '%s' % e.materia.asignatura.nombre, fuentenormal)
#             eProfesor = ''
#             if e.materia.asignaturamalla.malla.modalidad.es_enlinea(): profesor_principal = e.materia.profesor_principal_virtual()
#             else: profesor_principal = e.materia.profesor_principal()
#             if profesor_principal: eProfesor = profesor_principal.persona.nombre_completo()
#             hojadestino.write(fila, 4, '%s' % eProfesor, fuentenormal)
#             hojadestino.write(fila, 5, '%s' % e.materia.paralelo, fuentenormal)
#             hojadestino.write(fila, 6, '%s' % e.materia.asignaturamalla.nivelmalla.orden, fuentenormal)
#             hojadestino.write(fila, 7, '%s' % estudinate.email, fuentenormal)
#             hojadestino.write(fila, 8, '%s' % estudinate.emailinst, fuentenormal)
#             hojadestino.write(fila, 9, '%s' % estudinate.telefonos(), fuentenormal)
#             hojadestino.write(fila, 10, '%s' % estudinate.pais, fuentenormal)
#             hojadestino.write(fila, 11, '%s' % estudinate.provincia, fuentenormal)
#             hojadestino.write(fila, 12, '%s' % estudinate.canton, fuentenormal)
#             hojadestino.write(fila, 13, '%s' % estudinate.parroquia, fuentenormal)
#             hojadestino.write(fila, 14, '%s' % estudinate.ciudadela, fuentenormal)
#             hojadestino.write(fila, 15, '%s' % estudinate.sector, fuentenormal)
#             hojadestino.write(fila, 16, '%s' % estudinate.direccion_corta(), fuentenormal)
#             tienediscapacidad = 'NO'
#             tipodiscapacidad = 'NINGUNA'
#             ppl = 'NO'
#             pplobs = 'NINIGUNA'
#             if estudinate.tiene_discapasidad():
#                 tienediscapacidad = 'SI'
#                 if estudinate.tiene_discapasidad().filter(tipodiscapacidad__isnull=False).exists():
#                     tipodiscapacidad = estudinate.tiene_discapasidad().first().tipodiscapacidad.nombre
#                 else: tipodiscapacidad = 'NO DETERMINADA'
#             hojadestino.write(fila, 17, '%s' % tienediscapacidad, fuentenormal)
#             hojadestino.write(fila, 18, '%s' % tipodiscapacidad, fuentenormal)
#             if estudinate.ppl:
#                 ppl = 'SI'
#                 pplobs = estudinate.observacionppl
#             hojadestino.write(fila, 19, '%s' % ppl, fuentenormal)
#             hojadestino.write(fila, 20, '%s' % pplobs, fuentenormal)
#             fila += 1
#         lin += 1
#         libdestino.save(output_folder + libre_origen)
#         print("Proceso finalizado. . .")
#     except Exception as ex:
#         transaction.set_rollback(True)
#         print('error: %s' % ex)
#         hojadestino.write(fila, 3, str(ex))
#         fila += 1
#
# reporte_estudiantes_matriculados_asignaturas_PPP()
#
#
#


###########NUEVOOO  IMPORTA
# def reporte_estudiantes_matriculados_asignaturas_PPP():
#     import xlwt
#     from xlwt import easyxf
#     import os
#     import sys
#     from django.db import transaction
#     from settings import SITE_STORAGE
#     from sga.models import MateriaAsignada
#     try:
#         # libre_origen = "/reporte_estudiantes_matriculados_asignaturas_PPP_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#         libre_origen = "/reporte_estudiantes_matriculados_asignaturas_PPP.xls"
#         fuentecabecera = easyxf(
#             'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
#         fuentenormal = easyxf(
#             'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
#         output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
#         libdestino = xlwt.Workbook()
#         hojadestino = libdestino.add_sheet('Sheet1')
#         fil = 0
#         lin = 0
#         columnas = [(u"ESTUDIANTE", 9500),
#                     (u"IDENTIFICACIÓN", 4000),
#                     (u"CARRERA", 12000),
#                     (u"ASIGNATURA", 12000),
#                     (u"DOCENTE", 9500),
#                     (u"PARALELO", 4000),
#                     (u"NIVEL ACADÉMICO", 5000),
#                     (u"CORREO ELECTRÓNICO", 7000),
#                     (u"CORREO INSTITUCIONAL", 7000),
#                     (u"TELÉFONOS", 6000),
#                     (u"PAÍS", 4000),
#                     (u"PROVINCIA", 6000),
#                     (u"CANTÓN", 6000),
#                     (u"PARROQUIA", 6000),
#                     (u"CIUDADELA", 7000),
#                     (u"SECTOR", 8000),
#                     (u"DIRECCIÓN", 12000),
#                     (u"¿TIENE DISCAPACIDAD?", 6000),
#                     (u"TIPO DISCAPACIDAD", 10000),
#                     (u"¿PPL?", 2000),
#                     (u"DETALLE PPL", 10000),
#                     ]
#         for col_num in range(len(columnas)):
#             hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
#             hojadestino.col(col_num).width = columnas[col_num][1]
#         fila = 1
#         eListadoEstudiantes = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo_id=317,
#                                                              matricula__status=True, matricula__retiradomatricula=False,
#                                                              retiromanual=False, retiramateria=False,
#                                                              materia__status=True,
#                                                              materia__asignaturamalla__status=True,
#                                                              matricula__inscripcion__coordinacion_id__in=[1, 2, 3, 4,
#                                                                                                           5],
#                                                              materia__asignaturamalla__malla__validamatricula=True,
#                                                              materia__asignaturamalla__asignaturapracticas=True
#                                                              ).order_by('matricula__inscripcion__coordinacion_id',
#                                                                         'matricula__inscripcion__carrera_id',
#                                                                         'matricula__inscripcion__persona__apellido1').distinct()
#         for e in eListadoEstudiantes:
#             estudinate = e.matricula.inscripcion.persona
#             hojadestino.write(fila, 0, '%s' % estudinate.nombre_completo_inverso(), fuentenormal)
#             hojadestino.write(fila, 1, '%s' % estudinate.identificacion(), fuentenormal)
#             hojadestino.write(fila, 2, '%s' % e.matricula.inscripcion.carrera, fuentenormal)
#             hojadestino.write(fila, 3, '%s' % e.materia.asignatura.nombre, fuentenormal)
#             eProfesor = ''
#             if e.materia.asignaturamalla.malla.modalidad.es_enlinea():
#                 profesor_principal = e.materia.profesor_principal_virtual()
#             else:
#                 profesor_principal = e.materia.profesor_principal()
#             if profesor_principal: eProfesor = profesor_principal.persona.nombre_completo()
#             hojadestino.write(fila, 4, '%s' % eProfesor, fuentenormal)
#             hojadestino.write(fila, 5, '%s' % e.materia.paralelo, fuentenormal)
#             hojadestino.write(fila, 6, '%s' % e.materia.asignaturamalla.nivelmalla.orden, fuentenormal)
#             hojadestino.write(fila, 7, '%s' % estudinate.email, fuentenormal)
#             hojadestino.write(fila, 8, '%s' % estudinate.emailinst, fuentenormal)
#             hojadestino.write(fila, 9, '%s' % estudinate.telefonos(), fuentenormal)
#             hojadestino.write(fila, 10, '%s' % estudinate.pais, fuentenormal)
#             hojadestino.write(fila, 11, '%s' % estudinate.provincia, fuentenormal)
#             hojadestino.write(fila, 12, '%s' % estudinate.canton, fuentenormal)
#             hojadestino.write(fila, 13, '%s' % estudinate.parroquia, fuentenormal)
#             hojadestino.write(fila, 14, '%s' % estudinate.ciudadela, fuentenormal)
#             hojadestino.write(fila, 15, '%s' % estudinate.sector, fuentenormal)
#             hojadestino.write(fila, 16, '%s' % estudinate.direccion_corta(), fuentenormal)
#             tienediscapacidad = 'NO'
#             tipodiscapacidad = 'NINGUNA'
#             ppl = 'NO'
#             pplobs = 'NINIGUNA'
#             if estudinate.tiene_discapasidad():
#                 tienediscapacidad = 'SI'
#                 if estudinate.tiene_discapasidad().filter(tipodiscapacidad__isnull=False).exists():
#                     tipodiscapacidad = estudinate.tiene_discapasidad().first().tipodiscapacidad.nombre
#                 else:
#                     tipodiscapacidad = 'NO DETERMINADA'
#             hojadestino.write(fila, 17, '%s' % tienediscapacidad, fuentenormal)
#             hojadestino.write(fila, 18, '%s' % tipodiscapacidad, fuentenormal)
#             if estudinate.ppl:
#                 ppl = 'SI'
#                 pplobs = estudinate.observacionppl
#             hojadestino.write(fila, 19, '%s' % ppl, fuentenormal)
#             hojadestino.write(fila, 20, '%s' % pplobs, fuentenormal)
#             fila += 1
#         lin += 1
#         libdestino.save(output_folder + libre_origen)
#         print("Proceso finalizado. . .")
#     except Exception as ex:
#         transaction.set_rollback(True)
#         err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
#         msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
#         print('%s' % msg_err)
#         hojadestino.write(fila, 3, str(ex))
#         fila += 1
#
#
# funcionlocal.get("reporte_estudiantes_matriculados_asignaturas_PPP")()


# def reporte_estudiantes_matriculados_asignaturas_PPP():
#     import xlwt
#     from xlwt import easyxf
#     import os
#     import sys
#     from django.db import transaction
#     # from settings import SITE_STORAGE
#     from sga.models import MateriaAsignada
#     try:
#         # libre_origen = "/reporte_estudiantes_matriculados_asignaturas_PPP_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
#         libre_origen = "/reporte_estudiantes_matriculados_asignaturas_PPP.xls"
#         fuentecabecera = easyxf(
#             'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
#         fuentenormal = easyxf(
#             'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
#         output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
#         libdestino = xlwt.Workbook()
#         hojadestino = libdestino.add_sheet('Sheet1')
#         fil = 0
#         lin = 0
#         columnas = [(u"ESTUDIANTE", 9500),
#                     (u"IDENTIFICACIÓN", 4000),
#                     (u"CARRERA", 12000),
#                     (u"ASIGNATURA", 12000),
#                     (u"DOCENTE", 9500),
#                     (u"PARALELO", 4000),
#                     (u"NIVEL ACADÉMICO", 5000),
#                     (u"CORREO ELECTRÓNICO", 7000),
#                     (u"CORREO INSTITUCIONAL", 7000),
#                     (u"TELÉFONOS", 6000),
#                     (u"PAÍS", 4000),
#                     (u"PROVINCIA", 6000),
#                     (u"CANTÓN", 6000),
#                     (u"PARROQUIA", 6000),
#                     (u"CIUDADELA", 7000),
#                     (u"SECTOR", 8000),
#                     (u"DIRECCIÓN", 12000),
#                     (u"¿TIENE DISCAPACIDAD?", 6000),
#                     (u"TIPO DISCAPACIDAD", 10000),
#                     (u"¿PPL?", 2000),
#                     (u"DETALLE PPL", 10000),
#                     ]
#         for col_num in range(len(columnas)):
#             hojadestino.write(fil, col_num, columnas[col_num][0], fuentecabecera)
#             hojadestino.col(col_num).width = columnas[col_num][1]
#         fila = 1
#         # eListadoEstudiantes = MateriaAsignada.objects.values_list(
#         #     'matricula__inscripcion__persona__apellido1',
#         #     'matricula__inscripcion__persona__apellido2',
#         #     'matricula__inscripcion__persona__nombres',
#         #     'matricula__inscripcion__persona__cedula',
#         #     'matricula__inscripcion__persona__pasaporte',
#         #     'matricula__inscripcion__persona__emailinst',
#         #     'matricula__inscripcion__carrera__nombre',
#         #     'materia__asignatura__nombre',
#         #     'materia__paralelo',
#         #     'materia__asignaturamalla__nivelmalla__orden',
#         #
#         # ).filter(status=True, matricula__nivel__periodo_id=317,
#         #          matricula__status=True, matricula__retiradomatricula=False,
#         #          retiromanual=False, retiramateria=False,
#         #          materia__status=True,
#         #          materia__asignaturamalla__status=True,
#         #          matricula__inscripcion__carrera_id__in=[126],
#         #          materia__asignaturamalla__malla__validamatricula=True,
#         #          materia__asignaturamalla_id__in=[10634, 10636]
#         #          ).order_by('matricula__inscripcion__carrera_id',
#         #                     'matricula__inscripcion__persona__apellido1').distinct()
#         #
#         eListadoEstudiantes = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo_id=317,
#                                                              matricula__status=True, matricula__retiradomatricula=False,
#                                                              retiromanual=False, retiramateria=False,
#                                                              materia__status=True,
#                                                              materia__asignaturamalla__status=True,
#                                                              matricula__inscripcion__coordinacion_id__in=[1, 2, 3, 4,
#                                                                                                           5],
#                                                              materia__asignaturamalla__malla__validamatricula=True,
#                                                              materia__asignaturamalla__asignaturapracticas=True
#                                                              ).order_by('matricula__inscripcion__coordinacion_id',
#                                                                         'matricula__inscripcion__carrera_id',
#                                                                         'matricula__inscripcion__persona__apellido1').distinct()
#         for e in eListadoEstudiantes:
#             estudinate = e.matricula.inscripcion.persona
#             hojadestino.write(fila, 0, '%s' % estudinate.nombre_completo_inverso(), fuentenormal)
#             hojadestino.write(fila, 1, '%s' % estudinate.identificacion(), fuentenormal)
#             hojadestino.write(fila, 2, '%s' % e.matricula.inscripcion.carrera, fuentenormal)
#             hojadestino.write(fila, 3, '%s' % e.materia.asignatura.nombre, fuentenormal)
#             eProfesor = ''
#             if e.materia.asignaturamalla.malla.modalidad.es_enlinea():
#                 profesor_principal = e.materia.profesor_principal_virtual()
#             else:
#                 profesor_principal = e.materia.profesor_principal()
#             if profesor_principal: eProfesor = profesor_principal.persona.nombre_completo()
#             hojadestino.write(fila, 4, '%s' % eProfesor, fuentenormal)
#             hojadestino.write(fila, 5, '%s' % e.materia.paralelo, fuentenormal)
#             hojadestino.write(fila, 6, '%s' % e.materia.asignaturamalla.nivelmalla.orden, fuentenormal)
#             hojadestino.write(fila, 7, '%s' % estudinate.email, fuentenormal)
#             hojadestino.write(fila, 8, '%s' % estudinate.emailinst, fuentenormal)
#             hojadestino.write(fila, 9, '%s' % estudinate.telefonos(), fuentenormal)
#             hojadestino.write(fila, 10, '%s' % estudinate.pais, fuentenormal)
#             hojadestino.write(fila, 11, '%s' % estudinate.provincia, fuentenormal)
#             hojadestino.write(fila, 12, '%s' % estudinate.canton, fuentenormal)
#             hojadestino.write(fila, 13, '%s' % estudinate.parroquia, fuentenormal)
#             hojadestino.write(fila, 14, '%s' % estudinate.ciudadela, fuentenormal)
#             hojadestino.write(fila, 15, '%s' % estudinate.sector, fuentenormal)
#             hojadestino.write(fila, 16, '%s' % estudinate.direccion_corta(), fuentenormal)
#             tienediscapacidad = 'NO'
#             tipodiscapacidad = 'NINGUNA'
#             ppl = 'NO'
#             pplobs = 'NINIGUNA'
#             if estudinate.tiene_discapasidad():
#                 tienediscapacidad = 'SI'
#                 if estudinate.tiene_discapasidad().filter(tipodiscapacidad__isnull=False).exists():
#                     tipodiscapacidad = estudinate.tiene_discapasidad().first().tipodiscapacidad.nombre
#                 else:
#                     tipodiscapacidad = 'NO DETERMINADA'
#             hojadestino.write(fila, 17, '%s' % tienediscapacidad, fuentenormal)
#             hojadestino.write(fila, 18, '%s' % tipodiscapacidad, fuentenormal)
#             if estudinate.ppl:
#                 ppl = 'SI'
#                 pplobs = estudinate.observacionppl
#             hojadestino.write(fila, 19, '%s' % ppl, fuentenormal)
#             hojadestino.write(fila, 20, '%s' % pplobs, fuentenormal)
#             fila += 1
#         lin += 1
#         libdestino.save(output_folder + libre_origen)
#         print("Proceso finalizado. . .")
#     except Exception as ex:
#         transaction.set_rollback(True)
#         err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
#         msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
#         print('%s' % msg_err)
#         hojadestino.write(fila, 3, str(ex))
#         fila += 1
#
#
# funcionlocal.get("reporte_estudiantes_matriculados_asignaturas_PPP")()