import os
import statistics
import sys
import xlwt
import openpyxl
import xlsxwriter
from xlwt import *

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
# print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from webpush import send_user_notification
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from settings import SITE_STORAGE, MEDIA_ROOT, MEDIA_URL
from sga.models import *

from django.db import transaction, connections

from sga.funciones import null_to_decimal


# def reporte_matricular_estudiantes_regulares(ePeriodoActual,ePeriodoAnterior):
#     # ESTUDIANTES REGULARES : APROBARON TODAS LAS MATERIAS ANTERIORES
#     # SI VOY A 4TO TODAS LAS DE 3RO DEBEN ESTAR APROBADAS Y NO TENER MATERIAS DE OTROS NIVELES MAYORES AL QUE VA
#     # SI EL NIVEL AL QUE VOY TIENE MATERIAS DE PRACTICA EXCLUYO A ESA CARRERA




#descomentar_enelreporte y en result: cuando se matriculen y    quitar  eMatriculasAnterior[600:800]:
ePeriodoActual = Periodo.objects.get(pk=336)
ePeriodoAnterior = Periodo.objects.get(pk=317)
# reporte_matricular_estudiantes_regulares(ePeriodoActual,ePeriodoAnterior)

try:
    ePeriodoMatricula = ePeriodoActual.periodomatricula_set.filter(status=True).first()
    ePersona = Persona.objects.get(pk=38453)
    usernotify = ePersona.usuario
    eNotificacion = Notificacion(cuerpo=f'{ePeriodoMatricula}',
                                 titulo=f'(En proceso) {ePeriodoMatricula}',
                                 destinatario=ePersona,
                                 url='',
                                 prioridad=1,
                                 app_label='SGA',
                                 fecha_hora_visible=datetime.now() + timedelta(days=5),
                                 tipo=2,
                                 en_proceso=True)

    EJE_FORMATIVO_PRACTICAS = 9
    EJE_FORMATIVO_VINCULACION = 11
    EXCLUDE_EJE_FORMATIVO = [EJE_FORMATIVO_PRACTICAS, EJE_FORMATIVO_VINCULACION]

    if not ePeriodoMatricula:
        raise NameError(u"Periodo académico de matricula no existe")

    print(f"PERIODO ACTUAL: {ePeriodoMatricula}")
    print(f"PERIODO ANTERIOR: {ePeriodoAnterior}")
    eCoordinaciones = Coordinacion.objects.filter(id__in=[1, 2, 3, 4, 5])
    eMatriculasAnterior = Matricula.objects.filter(status=True, retiradomatricula=False, bloqueomatricula=False, nivel__periodo=ePeriodoAnterior, inscripcion__carrera__coordinacion__in=eCoordinaciones)
    eMatriculasAnterior = eMatriculasAnterior.filter(cerrada=True)

    total_matriculas = eMatriculasAnterior.values("id").distinct().count()

    print(f"Total matriculas periodo {ePeriodoAnterior}: {total_matriculas}")
    contador_matricula = 0
    contador_lectura_proceso = 0
    resultados = []
    errores = []
    for eMatriculaAnterior in eMatriculasAnterior:
        contador_lectura_proceso += 1
        with transaction.atomic():
            eInscripcion = eMatriculaAnterior.inscripcion
            eInscripcionMalla = eInscripcion.malla_inscripcion()
            eMalla = eInscripcionMalla.malla
            eInscripcionNivel = eInscripcion.mi_nivel()
            if eInscripcionNivel.nivel_id >= 5:
                continue
            itinerario = []
            itinerario.append(0)
            eAsignaturasMalla = eMalla.asignaturamalla_set.select_related().filter(status=True).exclude(Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO)).order_by('nivelmalla', 'ejeformativo').filter(itinerario__in=itinerario)
            if eInscripcion.itinerario:
                if eInscripcion.itinerario > 0:
                    itinerario.append(eInscripcion.itinerario)
                    eAsignaturasMalla = eAsignaturasMalla.filter(itinerario__in=itinerario)
                    print(f"{eInscripcion.persona.cedula} - itinerario: {eInscripcion.itinerario}")

            eModulosMalla = ModuloMalla.objects.filter(malla=eInscripcionMalla.malla)

            eNivelMallaAprobadoActual = eInscripcionNivel.nivel
            eNivelMallaMatriculaAnterior = eMatriculaAnterior.nivelmalla
            eAsignaturasMallaquedebeaprobar = eAsignaturasMalla.filter(nivelmalla__orden__lte=eNivelMallaAprobadoActual.orden).exclude(Q(asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)) | Q(asignatura__in=AsignaturaMalla.objects.values_list("asignatura__id", flat=True).filter(malla=eMalla)))
            eAsignaturasRecord = eInscripcion.recordacademico_set.filter(asignaturamalla__in=eAsignaturasMalla, status=True)

            if eAsignaturasRecord.values("id").filter(aprobada=False).exists():
                errores.append("Tiene asignaturas en el record reprobadas")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            eAsignaturasAprobadashastanivel = eAsignaturasRecord.filter(asignaturamalla__in=eAsignaturasMallaquedebeaprobar, aprobada=True, status=True)

            if eAsignaturasAprobadashastanivel.values("id").count() < eAsignaturasMallaquedebeaprobar.values("id").count():
                errores.append("Tiene asignaturas en el record reprobadas")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            eAsignaturasAprobadasAdelantada = eAsignaturasRecord.filter(asignaturamalla__in=eAsignaturasMalla.filter(nivelmalla__orden__gte=eNivelMallaAprobadoActual.orden + 1).exclude(Q(asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)) | Q(asignatura__in=AsignaturaMalla.objects.values_list("asignatura__id", flat=True).filter(malla=eMalla))), aprobada=True, status=True)
            if eAsignaturasAprobadasAdelantada.values("id").exists():
                errores.append("Tiene asignaturas en el record que ha adelantado")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            # -----------------------------------------------------Verificar si hay asignaturas sin aprobar hasta el nivel actual
            eAsignaturasMallaHastaNivelActualTodas = eMalla.asignaturamalla_set.select_related().filter(status=True, itinerario=0, nivelmalla__orden__lte=eNivelMallaAprobadoActual.orden).exclude(Q(nivelmalla_id=NIVEL_MALLA_CERO) | Q(opcional=True) | Q(ejeformativo_id__in=EXCLUDE_EJE_FORMATIVO))
            asignaturas_sin_aprobar = eAsignaturasMallaHastaNivelActualTodas.exclude(id__in=eAsignaturasRecord.values_list("asignaturamalla_id", flat=True))
            if asignaturas_sin_aprobar.exists():
                errores.append(f"Tiene asignaturas sin aprobar hasta el nivel actual {eNivelMallaAprobadoActual.orden}")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            eMateriaAsignadasAnterior = MateriaAsignada.objects.filter(matricula=eMatriculaAnterior, status=True).exclude(Q(materia__inglesepunemi=True) | Q(materia__asignatura__id__in=eModulosMalla.values_list('asignatura__id', flat=True)))

            # if eMateriaAsignadasAnterior.values("id").filter(Q(cerrado=False) | Q(estado_id__in=[2, 3, 4]) | Q(retiromanual=True)).exists():
            #     errores.append("Tiene asignaturas en la matricula anterior con estado cerrado=False | estado en [EN CURSO, REPROBADO] | retiromanual=True")

            ids_paralelo = eMateriaAsignadasAnterior.values_list('materia__paralelomateria__id', flat=True).distinct()
            # if len(ids_paralelo) > 1:
            #     errores.append(f"Tiene materias con paralelos de más de {len(ids_paralelo)}")

            if Matricula.objects.values("id").filter(inscripcion=eInscripcion, nivel__periodo=ePeriodoActual).exists():
                errores.append(f"Ya existe una matricula en el periodo {ePeriodoActual.__str__()}")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            eAsignaturasMallaNivelSiguiente = eAsignaturasMalla.filter(nivelmalla__orden=eNivelMallaAprobadoActual.orden + 1)
            if eAsignaturasMallaNivelSiguiente.values("id").filter(practicas=True).exists():
                errores.append(f"Existe asignarturas de practicas en el nivel de malla {eNivelMallaAprobadoActual.orden + 1} a matricular")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            if eAsignaturasMallaNivelSiguiente.values("id").filter(asignaturapracticas=True).exists():
                errores.append(f"Existe asignarturas de practicas preprofesionales en el nivel de malla {eNivelMallaAprobadoActual.orden + 1} a matricular")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            if eAsignaturasMallaNivelSiguiente.values("id").filter(itinerario__gt=0).exists():
                errores.append(f"Existe asignarturas con itinerario en el nivel de malla {eNivelMallaAprobadoActual.orden + 1} a matricular")
                if errores:
                    print("---------------------------------")
                    print(f"{eMatriculaAnterior} - {eNivelMallaAprobadoActual}")
                    for error in errores:
                        print(error)
                    errores.clear()
                    print("---------------------------------")
                continue

            eNivel = Nivel.objects.filter(periodo=ePeriodoActual,
                                          nivellibrecoordinacion__coordinacion__carrera=eInscripcion.carrera,
                                          nivellibrecoordinacion__coordinacion__sede=eInscripcion.sede,
                                          sesion=eMatriculaAnterior.nivel.sesion, cerrado=False,
                                          fin__gte=datetime.now().date()).first()
            if not eNivel:
                errores.append(f"No existe nivel en el periodo {ePeriodoActual.__str__()}")
            #
            eParalelo = Paralelo.objects.filter(pk__in=ids_paralelo).first()
            # eMateriasAbiertas = Materia.objects.filter(asignaturamalla__in=eAsignaturasMallaNivelSiguiente,
            #                                            inicio__gte=datetime.now(), nivel__cerrado=False,
            #                                            nivel__periodo=eNivel.periodo, paralelomateria=eParalelo,
            #                                            status=True).order_by('id')
            # eMateriasAbiertas = eMateriasAbiertas.annotate(numasignadados=Count('materiaasignada__id', distinct=True)).filter(cupo__gt=F('numasignadados'))
            # if not eMateriasAbiertas.values("id").exists():
            #     errores.append(f"No existe materias aperturadas del paralelo ({eParalelo.__str__()}) para el periodo {ePeriodoActual.__str__()}")
            # if eAsignaturasMallaNivelSiguiente.values("id").count() != eMateriasAbiertas.values("id").count():
            #     errores.append(f"No existe suficiente materias aperturadas para el periodo {ePeriodoActual.__str__()}")

            if not errores:
                contador_matricula += 1
                print(f"({total_matriculas}/{contador_matricula}) - {eMatriculaAnterior.__str__()}")

                # AQUI inicio MATRICULA .---------------------------------

                # AQUI fin MATRICULA .---------------------------------
                resultados.append({'eInscripcion': eInscripcion,
                                   'eNivelMallaAprobadoActual': eNivelMallaAprobadoActual,
                                   'eMatriculaAnterior': eMatriculaAnterior,
                                   'eParaleloAnterior': eParalelo,
                                   'eMateriaAsignadasAnterior': eMateriaAsignadasAnterior,
                                   'eAsignaturasMallaNivelSiguiente': eAsignaturasMallaNivelSiguiente,
                                   # 'eMatriculaActual': eMatriculaActual,
                                   # 'eMateriaAsignadasActual': eMateriaAsignadasActual,
                                   # 'eParaleloActual': eParaleloActual,
                                   })
            itinerario.clear()
        print(f"{total_matriculas}/{contador_lectura_proceso}")
    if len(resultados) > 0:
        nombre_archivo = "reporte_automaricula_2s_2024"
        # fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
        # fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
        style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
        style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
        style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
        title = easyxf(
            'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
        style1 = easyxf(num_format_str='D-MMM-YY')
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = xlwt.Workbook()
        ws = wb.add_sheet('Sheetname')
        estilo = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        output_folder = os.path.join(os.path.join(SITE_STORAGE, 'media'))
        nombre = nombre_archivo + "_" + datetime.now().strftime('%Y%m%d_%H%M%S') + ".xls"
        filename = os.path.join(output_folder, nombre)

        columnas = [
            (u"#", 7000),
            (u"documento", 7000),
            (u"alumno", 7000),
            (u"facultad", 7000),
            (u"carrera", 7000),
            (u"nivelmallaaprobado", 7000),
            (u"matriculaanterior", 7000),
            (u"nivelmallamatriculaanterior", 7000),
            (u"paraleloanterior", 7000),
            (u"materiasanterior", 7000),
            (u"asignaturasdebetomar", 7000),
            (u"matriculaactual", 7000),
            (u"materiasactual", 7000),
            (u"paraleloactual", 7000),
        ]
        row_num = 0
        for col_num in range(len(columnas)):
            ws.write(row_num, col_num, columnas[col_num][0], font_style)
            ws.col(col_num).width = columnas[col_num][1]
        total = len(resultados)
        cont = 0
        row_num = 1
        i = 0
        for r in resultados:
            cont += 1
            i += 1
            eInscripcion = r.get('eInscripcion')
            ePersona = eInscripcion.persona
            eNivelMallaAprobadoActual = r.get('eNivelMallaAprobadoActual')
            eMatriculaAnterior = r.get('eMatriculaAnterior')
            eParaleloAnterior = r.get('eParaleloAnterior')
            eMateriaAsignadasAnterior = r.get('eMateriaAsignadasAnterior')
            eAsignaturasMallaNivelSiguiente = r.get('eAsignaturasMallaNivelSiguiente')
            eMatriculaActual = r.get('eMatriculaActual')
            eMateriaAsignadasActual = r.get('eMateriaAsignadasActual')
            eParaleloActual = r.get('eParaleloActual')
            eFacultad = eInscripcion.coordinacion
            eCarrera = eInscripcion.carrera
            ws.write(row_num, 0, i, font_style2)  #
            ws.write(row_num, 1, "%s" % ePersona.documento(), font_style2)  # documento
            ws.write(row_num, 2, "%s (%s)" % (ePersona.nombre_completo_inverso(), eInscripcion.id), font_style2)  # alumno
            ws.write(row_num, 3, "%s" % eFacultad.__str__(), font_style2)  # facultad
            ws.write(row_num, 4, "%s" % eCarrera.__str__(), font_style2)  # carrera
            ws.write(row_num, 5, "%s" % eNivelMallaAprobadoActual.__str__(), font_style2)  # nivelmallaaprobado
            ws.write(row_num, 6, "ID_MATRICULA: %s - PERIODO: %s" % (eMatriculaAnterior.id, eMatriculaAnterior.nivel.periodo.__str__()), font_style2)  # matriculaanterior
            ws.write(row_num, 7, "%s" % eMatriculaAnterior.nivelmalla.__str__(), font_style2)  # nivelmallamatriculaanterior
            ws.write(row_num, 8, "%s" % eParaleloAnterior.__str__(), font_style2)  # paraleloanterior
            ws.write(row_num, 9, "%s" % ', '.join([x.materia.asignatura.nombre for x in eMateriaAsignadasAnterior]), font_style2)  # materiasanterior
            ws.write(row_num, 10, "%s" % ', '.join([x.asignatura.nombre for x in eAsignaturasMallaNivelSiguiente]), font_style2)  # asignaturasdebetomar
            # ws.write(row_num, 11, "ID_MATRICULA: %s - PERIODO: %s" % ( eMatriculaActual.id, eMatriculaActual.nivel.periodo.__str__()), font_style2)  # matriculaactual
            # ws.write(row_num, 12,"%s" % ', '.join([x.materia.asignatura.nombre for x in eMateriaAsignadasActual]),font_style2)  # materiasactual
            # ws.write(row_num, 13, "%s" % eParaleloActual.__str__(), font_style2)  # paraleloactual
            row_num += 1
            print(f"({total}/{cont}) Procesando . . .")
        wb.save(filename)
        print("ARCHIVO: ", filename)
        eNotificacion.url = "{}/{}".format(MEDIA_URL, nombre)
        eNotificacion.titulo = f'(Finalizado) Generación de automatricula 2S 2024 PREGRADO'
        eNotificacion.save()
        print("Proceso finalizado . . .")
except Exception as ex:
    print('Error al crear html %s ---- %s' % (ex, sys.exc_info()[-1].tb_lineno))
