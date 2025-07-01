#!/usr/bin/env python

import sys
import os
SITE_ROOT = os.path.dirname(os.path.realpath(__file__))
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)
from django.core.wsgi import get_wsgi_application
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from datetime import datetime
from sga.models import Periodo, ProfesorDistributivoHoras, CoordinadorCarrera, ProfesorMateria
from sga.templatetags.sga_extras import listado_bitacora_docente, listado_colectivos_academicos
from settings import SITE_STORAGE
from sga.funciones import  convertir_fecha
from datetime import timedelta
from django.db.models import F, ExpressionWrapper, DurationField, Q

def calcularPorcentajeInformeMensual(codigo,fechainiinforme,fechafininforme):
    from sga.funcionesxhtml2pdf import html_to_pdfsave_informemensualdocente
    from inno.models import InformeMensualDocente, HistorialInforme, HistorialInformeMensual
    try:
        # cron_activo = variable_valor('CRON_INFORME_MENSUAL')
        # if cron_activo:
        qsdistributivo = ProfesorDistributivoHoras.objects.filter(pk=codigo)
        for distributivo in qsdistributivo:
            periodo = distributivo.periodo
            profesor = distributivo.profesor
            count, count1, count2, count3, count4 = 0, 0, 0, 0, 0
            totalporcentaje, totalhdocentes, totalhinvestigacion, totalhgestion, totalhvinculacion = 0, 0, 0, 0, 0
            fechames = datetime.now().date()
            now = datetime.now()



            fini = fechainiinforme

            ffin = fechafininforme

            fechainiresta = datetime.strptime(fini, '%d-%m-%Y') - timedelta(days=5)
            fechafinresta = datetime.strptime(ffin, '%d-%m-%Y') - timedelta(days=5)
            finicresta = fechainiresta
            ffincresta = fechafinresta

            print(f"Calculando: {profesor} {fini} - {ffin}")
            # DETALLE HORAS DOCENTES

            finiinicio = convertir_fecha(fechainiinforme)
            ffinal = convertir_fecha(fechafininforme)

            adicional_lista = []
            listDocencia = []
            # print(f'--------------DOCENTES--------------')
            horasdocencia = distributivo.detalle_horas_docencia(finiinicio, ffinal)
            if horasdocencia:
                dicDocencia = {'tipo': 'Horas Docencia'}
                listDocencia.append([0, 'ACTIVIDADES DE DOCENCIA'])
                for actividad in horasdocencia:
                    if actividad.criteriodocenciaperiodo.nombrehtmldocente():
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'impartirclase':
                            profesormateria = ProfesorMateria.objects.filter(profesor=distributivo.profesor, materia__nivel__periodo=periodo, tipoprofesor__imparteclase=True, activo=True, materia__status=True).distinct().order_by('desde', 'materia__asignatura__nombre')
                            if periodo.clasificacion == 1:
                                asignaturas = profesormateria.filter(((Q(desde__gte=finiinicio) & Q(hasta__lte=ffinal)) |
                                                                      (Q(desde__lte=finiinicio) & Q(hasta__gte=ffinal)) |
                                                                      (Q(desde__lte=finiinicio) & Q(desde__gte=ffinal)) |
                                                                      (Q(hasta__gte=finiinicio) & Q(hasta__lte=ffinal)))).distinct().exclude(tipoprofesor_id__in=[15, 5]).order_by('desde',
                                                                                                                                                                           'materia__asignatura__nombre')
                                # asignaturas = asignaturas.exclude(materia__modeloevaluativo_id__in = [27])
                            else:
                                asignaturas = profesormateria.filter(((Q(desde__gte=finiinicio) & Q(hasta__lte=ffinal)) |
                                                                      (Q(desde__lte=finiinicio) & Q(hasta__gte=ffinal)) |
                                                                      (Q(desde__lte=finiinicio) & Q(desde__gte=ffinal)) |
                                                                      (Q(hasta__gte=finiinicio) & Q(hasta__lte=ffinal)))).exclude(tipoprofesor_id__in=[5]).distinct().order_by('desde',
                                                                                                                                                                       'materia__asignatura__nombre')

                            totalimpartir = actividad.criteriodocenciaperiodo.totalimparticlase(distributivo.profesor, finiinicio, ffinal, asignaturas, None, True)
                            if totalimpartir[2]:
                                count += 1
                                totalhdocentes += totalimpartir[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, totalimpartir[0], totalimpartir[1]])
                            # print(f" 2 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'evidenciamoodle':
                            listadoevidencias = actividad.criteriodocenciaperiodo.horario_evidencia_moodle(distributivo.profesor, finicresta, ffincresta, True)
                            if listadoevidencias[2]:
                                count += 1
                                totalhdocentes += listadoevidencias[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, listadoevidencias[0], listadoevidencias[1]])
                            # print(f" 3 cres - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'materialsilabo':
                            actividadhor = actividad.criteriodocenciaperiodo.horarios_actividad_profesor(distributivo.profesor, finiinicio, ffinal, True)
                            count += 1
                            totalhdocentes += actividadhor[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadhor[0], actividadhor[1]])
                            # print(f" 4 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'cursonivelacion':
                            actividadnivelacioncarrera = actividad.criteriodocenciaperiodo.horarios_nivelacioncarrera_profesor(distributivo.profesor, finiinicio, ffinal)
                            totitem4 = 0
                            if actividadnivelacioncarrera:
                                totitem4 += 100
                                totalhdocentes += 100
                                count += 1

                                # listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem4))
                            # print(f" 5 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem4}")
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'planificarcontenido':
                            contenidohor = actividad.criteriodocenciaperiodo.horarios_contenido_profesor(distributivo.profesor, finiinicio, ffinal, True)
                            if contenidohor == 0:
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, '-', '-'])
                            else:
                                count += 1
                                totalhdocentes += contenidohor[1]
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, contenidohor[0], contenidohor[1]])
                            # print(f" 6 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'tutoriaacademica':
                            tutoriasacademicas = actividad.criteriodocenciaperiodo.horarios_tutoriasacademicas_profesor(distributivo.profesor, finiinicio, ffinal, True)
                            count += 1
                            totalhdocentes += tutoriasacademicas[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, tutoriasacademicas[0], tutoriasacademicas[1]])
                            # print(f" 7 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'seguimientoplataforma':
                            listadoseguimientos = actividad.criteriodocenciaperiodo.horario_seguimiento_tutor_fecha(distributivo.profesor, finiinicio, ffinal, True)
                            if listadoseguimientos[2]:
                                count += 1
                                totalhdocentes += listadoseguimientos[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, listadoseguimientos[0], listadoseguimientos[1]])
                            # print(f" 8 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'nivelacioncarrera':
                            actividadgestion = actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, finiinicio, ffinal, True)
                            count += 1
                            totalhdocentes += actividadgestion[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                            # print(f" 9 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'seguimientotransversal':
                            listadoseguimientos = actividad.criteriodocenciaperiodo.horario_seguimiento_transaversal_fecha(distributivo.profesor, finiinicio, ffinal, True)
                            if listadoseguimientos[2]:
                                count += 1
                                totalhdocentes += listadoseguimientos[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, listadoseguimientos[0], listadoseguimientos[1]])
                            # print(f" transversal - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'apoyovicerrectorado':
                            actividadapoyo = actividad.criteriodocenciaperiodo.horarios_apoyo_profesor(distributivo.profesor, finiinicio, ffinal)
                            totitem10 = 0
                            if actividadapoyo:
                                totitem10 += 100
                                totalhdocentes += 100
                                count += 1

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividaddocente':
                            actividaddocente1 = actividad.criteriodocenciaperiodo.horarios_actividaddocente_profesor(distributivo.profesor, finiinicio, ffinal, True)
                            # print(actividaddocente1)
                            if actividaddocente1:
                                count += 1
                                totalhdocentes += 100
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividaddocente1[0], actividaddocente1[1]])
                            else:
                                count += 1
                                totalhdocentes += 0
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, '-', '0.00'])
                            # print(f" 11 docencia - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'criterioperiodoadmision':
                            actividaddocente1 = actividad.criteriodocenciaperiodo.horario_criterio_nivelacion(distributivo.profesor, finiinicio, ffinal, True)
                            count += 1
                            totalhdocentes += actividaddocente1[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividaddocente1[0], actividaddocente1[1]])
                            # print(f" 11 docencia - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")
                                # listDocencia.append((actividad.criteriodocenciaperiodo.criterio.nombre, totitem10))
                            # print(f" 12 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{totitem10}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadbitacora':
                            actividaddocente1 = listado_bitacora_docente(0, actividad, ffinal, True)
                            count += 1
                            hmes = actividaddocente1[0]
                            totalhdocentes += actividaddocente1[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, hmes, actividaddocente1[1]])
                            # print(f" 12 bitacora - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadcolectivosacademicos':
                            hmes, porcentaje = '-', '-'
                            if actividaddocente1 := listado_colectivos_academicos(0, actividad, finiinicio, ffinal, True):
                                count += 1
                                hmes = actividaddocente1[0]
                                porcentaje = actividaddocente1[1]
                                totalhdocentes += actividaddocente1[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, hmes, porcentaje])
                            # print(f" 12 bitacora - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                # dicDocencia['actividades'] = listDocencia
                # adicional_lista.append(dicDocencia)
                adicional_lista.append(listDocencia)
            # DETALLE HORAS DE INVESTIGACIÓN
            # print(f'--------------INVESTIGACIÓN--------------')
            if distributivo.detalle_horas_investigacion():
                docInvestigacion = {'tipo': 'Horas Investigación'}
                listDocencia.append([0, 'ACTIVIDADES DE INVESTIGACIÓN'])
                listInvestigacion = []
                for actividad in distributivo.detalle_horas_investigacion():
                    if actividad.criterioinvestigacionperiodo.nombrehtmldocente():
                        if actividad.criterioinvestigacionperiodo.nombrehtmldocente() == 'actividadinvestigacion':
                            actividadgestion = actividad.criterioinvestigacionperiodo.horarios_informesinvestigacion_profesor(distributivo, finiinicio, ffinal, True)
                            count1 += 1
                            totalhinvestigacion += actividadgestion[1]
                            listDocencia.append([actividad.criterioinvestigacionperiodo.id, actividad.criterioinvestigacionperiodo.criterio.nombre, actividad.horas, '', actividadgestion[1]])
                            # print(f" 13 - {actividad.criterioinvestigacionperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criterioinvestigacionperiodo.nombrehtmldocente() == 'actividadbitacora':
                            actividadgestion = listado_bitacora_docente(0, actividad, ffinal, True)
                            count1 += 1
                            hmes = actividadgestion[0]
                            totalhinvestigacion += actividadgestion[1]
                            listDocencia.append([actividad.criterioinvestigacionperiodo.id, actividad.criterioinvestigacionperiodo.criterio.nombre, actividad.horas, hmes, actividadgestion[1]])
                            # print(f" 13 inv-bitacora - {actividad.criterioinvestigacionperiodo.criterio.nombre}", f"{actividad.horas}")
                docInvestigacion['actividades'] = listInvestigacion
                adicional_lista.append(listDocencia)
            # DETALLE HORAS DE GESTIÓN
            # print(f'--------------GESTIÓN--------------')
            horasgestion = distributivo.detalle_horas_gestion(finiinicio, ffinal)
            if horasgestion:
                docGestion = {'tipo': 'Horas Gestión'}
                listGestion = []
                listDocencia.append([0, 'ACTIVIDADES DE GESTIÓN EDUCATIVA'])
                for actividad in horasgestion:
                    if actividad.criteriogestionperiodo.nombrehtmldocente():
                        if actividad.criteriogestionperiodo.nombrehtmldocente() == 'actividadgestion':
                            actividadgestion = actividad.criteriogestionperiodo.horarios_actividadgestion_profesor(distributivo.profesor, finiinicio, ffinal, True)
                            if actividadgestion:
                                count2 += 1
                                totalhgestion += 100
                                listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                            else:
                                count2 += 1
                                totalhgestion += 0
                                listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, '-', '0.00'])
                            # print(f" 14 - {actividad.criteriogestionperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriogestionperiodo.nombrehtmldocente() == 'actividadinformegestion':
                            actividadgestion = actividad.criteriogestionperiodo.horarios_informesgestion_profesor(distributivo, finiinicio, ffinal, True)
                            count2 += 1
                            totalhgestion += actividadgestion[1]
                            listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, '', actividadgestion[1]])
                            # print(f" 15 - {actividad.criteriogestionperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriogestionperiodo.nombrehtmldocente() == 'actividadbitacora':
                            actividadgestion = listado_bitacora_docente(0, actividad, ffinal, True)
                            count2 += 1
                            totalhgestion += actividadgestion[1]
                            listDocencia.append([actividad.criteriogestionperiodo.id, actividad.criteriogestionperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                            # print(f" 16 - {actividad.criteriogestionperiodo.criterio.nombre}", f"{actividad.horas}")
                docGestion['actividades'] = listGestion
                adicional_lista.append(listDocencia)
            # DETALLE HORAS DE VINCULACIÓN
            # print(f'--------------VINCULACIÓN--------------')
            if distributivo.detalle_horas_vinculacion():
                docVinculacion = {'tipo': 'Horas Vinculacion'}
                listVinculacion = []
                listDocencia.append([0, 'ACTIVIDADES DE VINCULACIÓN CON LA SOCIEDAD'])
                for actividad in distributivo.detalle_horas_vinculacion():
                    if actividad.criteriodocenciaperiodo.nombrehtmldocente():
                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadvinculacion':
                            actividadgestion = actividad.criteriodocenciaperiodo.horarios_informesdocencia_profesor(distributivo, finiinicio, ffinal, True)
                            if actividadgestion:
                                count3 += 1
                                totalhvinculacion += actividadgestion[1]
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, actividadgestion[0], actividadgestion[1]])
                            else:
                                count3 += 1
                                totalhvinculacion += 0
                                listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas, '-', '0.00'])
                            # print(f" 16 - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")

                        if actividad.criteriodocenciaperiodo.nombrehtmldocente() == 'actividadbitacora':
                            actividadgestion = listado_bitacora_docente(0, actividad, ffinal, True)
                            count3 += 1
                            totalhvinculacion += actividadgestion[1]
                            listDocencia.append([actividad.criteriodocenciaperiodo.id, actividad.criteriodocenciaperiodo.criterio.nombre, actividad.horas,  actividadgestion[0], actividadgestion[1]])
                            # print(f" 13 inv-bitacora - {actividad.criteriodocenciaperiodo.criterio.nombre}", f"{actividad.horas}")
                docVinculacion['actividades'] = listVinculacion
                adicional_lista.append(listDocencia)
            # TOTALES INFORME
            # print(adicional_lista)
            totalporcentaje = totalhdocentes + totalhinvestigacion + totalhgestion + totalhvinculacion
            count4 = count + count1 + count2 + count3
            total_porcentaje = round(totalporcentaje / count4 if count4 else totalporcentaje, 2)
            # print(f"--- DOCENTES: {round(totalhdocentes / count if count else totalhdocentes, 2)}%")
            # print(f"--- INVESTIGACIÓN: {round(totalhinvestigacion / count1 if count1 else totalhinvestigacion, 2)}%")
            # print(f"--- GESTIÓN: {round(totalhgestion / count2 if count2 else totalhgestion, 2)}%")
            # print(f"--- VINCULACIÓN: {round(totalhvinculacion / count3 if count3 else totalhvinculacion, 2)}%")
            # print(f"--- TOTAL: {total_porcentaje}%")
            listDocencia.append(['total', total_porcentaje])
            # qrname = 'informemensual_' + str(distributivo.id) + '_' + str(fechafininforme.month)
            fechamesini = convertir_fecha(fechainiinforme)
            fechames = convertir_fecha(fechafininforme)
            qrname = 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_2'
            generaautomatico =False
            if not InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, fechafin__month=fechames.month, status=True):
                generaautomatico = True
            else:
                if InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, fechafin__month=fechames.month, estado=1, status=True):
                    informedelete = InformeMensualDocente.objects.filter(distributivo__profesor=profesor, distributivo__periodo=periodo, fechafin__month=fechames.month, estado=1, status=True)[0]
                    informedelete.delete()
                    generaautomatico = True

            if generaautomatico:
                tienefirmas = False
                if distributivo.carrera:
                    if CoordinadorCarrera.objects.values('id').filter(carrera=distributivo.carrera, periodo=periodo, sede_id=1, tipo=3).exists():
                        personadirectorcarrera = CoordinadorCarrera.objects.filter(carrera=distributivo.carrera, periodo=periodo, sede_id=1, tipo=3)[0]
                        if distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True).exists():
                            personadirectorcoordinacion = distributivo.coordinacion.responsablecoordinacion_set.filter(periodo=periodo, tipo=1, status=True)[0]
                            tienefirmas = True

                if tienefirmas:
                    # elimino el pdf 1 es generado y 2 es firmado, por si existan esos pdf
                    folder = os.path.join(SITE_STORAGE, 'media', 'informemensualdocente', '')
                    rutainformepdf1 = folder + 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_1.pdf'
                    if os.path.isfile(rutainformepdf1):
                        os.remove(rutainformepdf1)

                    rutainformepdf = folder + 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_2.pdf'
                    if os.path.isfile(rutainformepdf):
                        os.remove(rutainformepdf)

                    if not HistorialInformeMensual.objects.values('id').filter(distributivo=distributivo, status=True, finicioreporte__month=fechames.month).exists():
                        instance = HistorialInformeMensual(distributivo=distributivo, finicioreporte=fechamesini, ffinreporte=fechames, total_porcentaje=total_porcentaje)
                        instance.datos_lista = adicional_lista
                        instance.save()
                    else:
                        instance = HistorialInformeMensual.objects.filter(distributivo=distributivo, finicioreporte=fechamesini, ffinreporte=fechames, total_porcentaje=total_porcentaje)[0]
                        instance.datos_lista = adicional_lista
                        instance.save()

                    generainforme = html_to_pdfsave_informemensualdocente('adm_criteriosactividadesdocente/informe_actividad_docentev4_pdf.html',
                                                                          {'pagesize': 'A4',
                                                                           'data': profesor.informe_actividades_mensual_docente_v4(periodo, fechainiinforme, fechafininforme, 'FACULTAD', adicional_lista, 1)
                                                                           }, qrname + '.pdf', 'informemensualdocente'
                                                                          )
                    nombrepdf = 'informemensual_' + str(distributivo.id) + '_' + str(fechames.month) + '_2'
                    folder_save = os.path.join('informemensualdocente', '').replace('\\', '/')
                    informe = InformeMensualDocente(distributivo_id=distributivo.id,
                                                    fechainicio=fechamesini,
                                                    fechafin=fechames,
                                                    archivo=f'{folder_save}{nombrepdf}.pdf',
                                                    promedio=total_porcentaje,
                                                    estado=2,
                                                    automatico=True)
                    informe.save()


                    if not HistorialInforme.objects.values('id').filter(informe=informe, estado=2).exists():

                        url_file_generado = f'{folder_save}{nombrepdf}.pdf'
                        historial = HistorialInforme(informe=informe,
                                                     archivo=url_file_generado,
                                                     estado=2,
                                                     fechafirma=datetime.now().date(),
                                                     firmado=True,
                                                     personafirmas=informe.distributivo.profesor.persona)
                        historial.save()
                    if not HistorialInforme.objects.values('id').filter(informe=informe, estado=3).exists():
                        historial = HistorialInforme(informe=informe,
                                                     personafirmas=personadirectorcarrera.persona,
                                                     estado=3)
                        historial.save()
                    if not HistorialInforme.objects.values('id').filter(informe=informe, estado=4).exists():
                        historial = HistorialInforme(informe=informe,
                                                     personafirmas=personadirectorcoordinacion.persona,
                                                     estado=4)
                        historial.save()
            else:
                if not HistorialInformeMensual.objects.values('id').filter(distributivo=distributivo, status=True, finicioreporte__month=fechames.month).exists():
                    instance = HistorialInformeMensual(distributivo=distributivo, finicioreporte=fechamesini, ffinreporte=fechames, total_porcentaje=total_porcentaje)
                    instance.datos_lista = adicional_lista
                    instance.save()
                else:
                    instance = HistorialInformeMensual.objects.filter(distributivo=distributivo, finicioreporte=fechamesini, ffinreporte=fechames, total_porcentaje=total_porcentaje)[0]
                    instance.datos_lista = adicional_lista
                    instance.save()

    except Exception as ex:
        msg_ex = 'Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, str(ex))
        print(msg_ex)



# fecha_str = "2023-12-05"
# fecha_obj = datetime.strptime(fecha_str, "%Y-%m-%d")
# fechaactual = fecha_obj
fechaactual = datetime.now().date()
fechafininforme = fechaactual.replace(day=1) - timedelta(days=1)
fechainiinforme = fechafininforme.replace(day=1)

fechainiinforme = fechainiinforme.strftime('%d-%m-%Y')
fechafininforme = fechafininforme.strftime('%d-%m-%Y')

print(fechainiinforme)
print(fechafininforme)

# escojo el period que este en la fecha actual, sea regular y minomo tenga 4 meses
# entre la fecha inicio y fin para que no se choque con un periodo regular intermedio que por lo general crean
periodolectivo = Periodo.objects.annotate(duracion_meses=ExpressionWrapper(F('fin') - F('inicio'), output_field=DurationField())). \
    filter(tipo_id=2,
           inicio__lte=fechaactual,
           fin__gte=fechaactual,
           duracion_meses__gte=timedelta(days=120),  # 4 meses
           status=True)
print(periodolectivo)
# listadodistributivo = ProfesorDistributivoHoras.objects.filter(profesor__persona__cedula='1310297393', carrera_id__isnull=False, periodo_id=224, status=True)
listadodistributivo = ProfesorDistributivoHoras.objects.filter(carrera_id__isnull=False, periodo_id__in=periodolectivo.values_list('id', flat=True), status=True)
totaldocente = listadodistributivo.count()
lcontado = 0
print(listadodistributivo)
for lprofe in listadodistributivo:
    lcontado = lcontado + 1
    calcularPorcentajeInformeMensual(lprofe.id, fechainiinforme, fechafininforme)
    print(str(lcontado) + ' docentes de ' + str(totaldocente))


