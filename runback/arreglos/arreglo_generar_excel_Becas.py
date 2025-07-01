#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import os
import sys

# SITE_ROOT = os.path.dirname(os.path.realpath(__file__))

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
print(f"YOUR_PATH: {YOUR_PATH}")
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
# print(f"SITE_ROOT: {SITE_ROOT}")
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
# print(f"your_djangoproject_home: {your_djangoproject_home}")
sys.path.append(your_djangoproject_home)

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from django.db import transaction
from django.db.models import F, Count, Q
from certi.models import Carnet
from sga.models import Periodo, PreInscripcionBeca, MateriaAsignada, PreInscripcionBecaRequisito, InscripcionNivel, MatriculaGrupoSocioEconomico
from settings import SITE_STORAGE

import xlwt
from xlwt import XFStyle, Workbook

from sga.models import BecaTipo, Matricula


def generar_etnias(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=21)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()
        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_etnias'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR PERTENCER A PUEBLOS Y NACIONALIDADES DEL ECUADOR'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_etnias_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR PERTENCER A PUEBLOS Y NACIONALIDADES DEL ECUADOR'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_etnias_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR PERTENCER A PUEBLOS Y NACIONALIDADES DEL ECUADOR'

        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)

        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        # periodoactual = Periodo.objects.get(id=int(request.POST['periodoactual']))
        # periodovalida = Periodo.objects.get(id=int(request.POST['periodovalida']))
        # modalidad = int(request.POST['modalidad'])
        ws = wb.add_sheet('alumnos_etnias')
        #response = HttpResponse(content_type="application/ms-excel")
        #response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1, 10000).__str__() + '.xls'
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN.", 1000),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 8000),
            (u"MODALIDAD", 8000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"ETNIA", 3000),
            (u"PROMEDIO", 3000),
            (u"ASISTENCIA", 3000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION", 3000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 5000),
            (u"PROVINCIA", 5000),
            (u"CANTON", 5000),
            (u"DIRECCION 1", 5000),
            (u"DIRECCION 2", 5000),
            (u"SECTOR", 5000),
            (u"GRUPO SOCIOECONOMICO", 5000),
            (u"PERIODO ACTUAL", 8000),
            (u"PERIDOO VALIDA", 8000),
            (u"TIPO/ESTADO", 2500),
        ]

        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title_2)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, font_style)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
            discapacitados = periodoactual.objects.values_list('inscripcion__id', flat=True).filter(status=True,
                                                                                                nivel__periodo=periodoactual,
                                                                                                estado_matricula__in=[
                                                                                                    2, 3],
                                                                                                retiradomatricula=False,
                                                                                                inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                                                                                inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                                                                                matriculagruposocioeconomico__tipomatricula=1).exclude(
                inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by("inscripcion__persona")
            matriculados = Matricula.objects.filter(status=True, nivel__periodo=periodovalida,
                                                    estado_matricula__in=[2, 3],
                                                    retiradomatricula=False,
                                                    matriculagruposocioeconomico__tipomatricula=1,
                                                    inscripcion__id__in=discapacitados).exclude(
                inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by("inscripcion__persona")
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual,
                                                              becatipo_id=21).values_list('inscripcion_id',
                                                                                          flat=True)
            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()

            matriculados = Matricula.objects.filter(inscripcion__id__in=inscripciones.values_list('inscripcion_id', flat=True), nivel__periodo__id=periodoactual.id).distinct().order_by("inscripcion__persona")
        row_num = 4
        i = 0
        print('Cantidad de Registros etnias', matriculados.count())
        contador  = 0
        for numero, x in enumerate(matriculados):
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.inscripcion, periodo=periodoactual, becatipo_id=21).first()
            asignaturas = MateriaAsignada.objects.filter(status=True,
                                                         matricula__inscripcion__id=x.inscripcion.id,
                                                         matricula__nivel__periodo__id=periodovalida.id,
                                                         materiaasignadaretiro__isnull=True)
            verifica = 0
            suma = 0
            promedio = 0
            sumasis = 0
            total = asignaturas.count()
            for m in asignaturas:
                suma += m.notafinal
                sumasis += m.asistenciafinal
                if m.estado.id != 1:
                    verifica = 1
                    break
            if suma > 0 and verifica == 0:
                promedio = round(suma / total, 2)
                asistencia = round(sumasis / total, 2)

            #if verifica == 0:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.inscripcion.persona.nombre_completo_inverso()
            if x.inscripcion.carrera.mencion:
                campo4 = x.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.inscripcion.carrera.mencion
            else:
                campo4 = x.inscripcion.carrera.nombre
            campo5 = x.inscripcion.modalidad.__str__()
            campo6 = x.inscripcion.persona.cedula
            campo7 = x.inscripcion.persona.nacimiento
            if periodoactual.id >= 119:
                campo8 = preinscripcion.raza.nombre if preinscripcion.raza else ''  # x.inscripcion.persona.mi_perfil().raza.nombre
            else:
                campo8 = x.inscripcion.persona.mi_perfil().raza.nombre
            campo9 = promedio
            campo10 = asistencia
            campo11 = x.inscripcion.sesion.nombre
            if x.nivelmalla:
                campo12 = x.nivelmalla.nombre
            else:
                campo12 = 'Ninguno'
            if x.paralelo:
                campo13 = x.paralelo.nombre
            else:
                campo13 = 'Ninguno'
            campo14 = x.inscripcion.persona.direccion_completa()
            campo15 = x.inscripcion.persona.telefono
            campo16 = x.inscripcion.persona.telefono_conv
            campo17 = x.inscripcion.persona.email
            campo18 = x.inscripcion.persona.emailinst
            campo19 = x.inscripcion.persona.sexo.nombre
            campo20 = x.inscripcion.persona.pais.nombre if x.inscripcion.persona.pais else ""
            campo21 = x.inscripcion.persona.provincia.nombre if x.inscripcion.persona.provincia else ""
            campo22 = x.inscripcion.persona.canton.nombre if x.inscripcion.persona.canton else ""
            campo23 = x.inscripcion.persona.direccion if x.inscripcion.persona.direccion else ""
            campo24 = x.inscripcion.persona.direccion2 if x.inscripcion.persona.direccion2 else ""
            campo25 = x.inscripcion.persona.sector if x.inscripcion.persona.sector else ""
            campo26 = str(
                x.matriculagruposocioeconomico().nombre) if x.matriculagruposocioeconomico() else ""
            campo27 = x.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, date_format)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, str(periodoactual), font_style2)
            ws.write(row_num, 28, str(periodovalida), font_style2)
            ws.write(row_num, 29, campo27, font_style2)

            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)

                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            contador = numero + 1
            print(f'{contador}.-', x.inscripcion, preinscripcion)
            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', contador)
        print('Url etnias: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)

def generar_extranjeros(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=22)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()

        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_extranjeros'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR SER ECUATORIANO EN EL EXTERIOR'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_extranjeros_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR SER ECUATORIANO EN EL EXTERIOR'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_extranjeros_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR SER ECUATORIANO EN EL EXTERIOR'
        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        # periodoactual = Periodo.objects.get(id=int(request.POST['periodoactual']))
        # periodovalida = Periodo.objects.get(id=int(request.POST['periodovalida']))

        # modalidad = int(request.POST['modalidad'])
        ws = wb.add_sheet('alumnos_extranjeros')
        # response = HttpResponse(content_type="application/ms-excel")
        # response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1,
        #                                                                                             10000).__str__() + '.xls'
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN", 1500),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 8000),
            (u"MODALIDAD", 8000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"PAIS EXTERIOR", 3000),
            (u"PROMEDIO", 3000),
            (u"ASISTENCIA", 3000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION", 3000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 5000),
            (u"PROVINCIA", 5000),
            (u"CANTON", 5000),
            (u"DIRECCION 1", 5000),
            (u"DIRECCION 2", 5000),
            (u"SECTOR", 5000),
            (u"GRUPO SOCIOECONOMICO", 5000),
            (u"PERIODO ACTUAL", 8000),
            (u"PERIDOO VALIDA", 8000),
            (u"TIPO/ESTADO", 2500),
        ]

        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
            matriculados = Matricula.objects.filter(pk=None)
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual,
                                                              becatipo_id=22).values_list('inscripcion_id',
                                                                                          flat=True)

            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()

            matriculados = Matricula.objects.filter(~Q(inscripcion__persona__pais_id=1),
                                                    inscripcion__id__in=inscripciones.values_list('inscripcion_id', flat=True),
                                                    nivel__periodo__id=periodoactual.id).distinct().order_by(
                "inscripcion__persona")
        row_num = 4
        i = 0
        becatipo = BecaTipo.objects.get(pk=22)
        print('Cantidad de Registros extranjeros', matriculados.count())
        contador = 0
        for numero, x in enumerate(matriculados):
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.inscripcion, periodo=periodoactual, becatipo_id=22).first()
            asignaturas = MateriaAsignada.objects.filter(status=True,
                                                         matricula__inscripcion__id=x.inscripcion.id,
                                                         matricula__nivel__periodo__id=periodovalida.id,
                                                         materiaasignadaretiro__isnull=True)
            verifica = 0
            suma = 0
            promedio = 0
            sumasis = 0
            total = asignaturas.count()
            for m in asignaturas:
                suma += m.notafinal
                sumasis += m.asistenciafinal
                if m.estado.id != 1:
                    verifica = 1
                    break
            if suma > 0 and verifica == 0:
                promedio = round(suma / total, 2)
                asistencia = round(sumasis / total, 2)
            #if verifica == 0:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.inscripcion.persona.nombre_completo_inverso()
            if x.inscripcion.carrera.mencion:
                campo4 = x.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.inscripcion.carrera.mencion
            else:
                campo4 = x.inscripcion.carrera.nombre
            campo5 = x.inscripcion.modalidad.__str__()
            campo6 = x.inscripcion.persona.cedula
            campo7 = x.inscripcion.persona.nacimiento
            campo8 = x.inscripcion.persona.pais.nombre
            campo9 = promedio
            campo10 = asistencia
            campo11 = x.inscripcion.sesion.nombre
            if x.nivelmalla:
                campo12 = x.nivelmalla.nombre
            else:
                campo12 = 'Ninguno'
            if x.paralelo:
                campo13 = x.paralelo.nombre
            else:
                campo13 = 'Ninguno'
            campo14 = x.inscripcion.persona.direccion_completa()
            campo15 = x.inscripcion.persona.telefono
            campo16 = x.inscripcion.persona.telefono_conv
            campo17 = x.inscripcion.persona.email
            campo18 = x.inscripcion.persona.emailinst
            campo19 = x.inscripcion.persona.sexo.nombre
            campo20 = x.inscripcion.persona.pais.nombre if x.inscripcion.persona.pais else ""
            campo21 = x.inscripcion.persona.provincia.nombre if x.inscripcion.persona.provincia else ""
            campo22 = x.inscripcion.persona.canton.nombre if x.inscripcion.persona.canton else ""
            campo23 = x.inscripcion.persona.direccion if x.inscripcion.persona.direccion else ""
            campo24 = x.inscripcion.persona.direccion2 if x.inscripcion.persona.direccion2 else ""
            campo25 = x.inscripcion.persona.sector if x.inscripcion.persona.sector else ""
            campo26 = str(
                x.matriculagruposocioeconomico().nombre) if x.matriculagruposocioeconomico() else ""
            campo27 = x.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, date_format)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, str(periodoactual), font_style2)
            ws.write(row_num, 28, str(periodovalida), font_style2)
            ws.write(row_num, 29, campo27, font_style2)

            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)
                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            contador = numero + 1
            print(f'{contador}.-', x.inscripcion, preinscripcion)

            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', contador)
        print('Url extranjero: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'

def generar_migrantes(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=22)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()
        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_migrantes'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR SER ECUATORIANO MIGRANTE RETORNADO O DEPORTADO'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_migrantes_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR SER ECUATORIANO MIGRANTE RETORNADO O DEPORTADO'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_migrantes_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR SER ECUATORIANO MIGRANTE RETORNADO O DEPORTADO'

        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)

        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        # periodoactual = Periodo.objects.get(id=int(request.POST['periodoactual']))
        # periodovalida = Periodo.objects.get(id=int(request.POST['periodovalida']))
        # periodoactual = periodosesion
        # periodovalida = anterior
        # modalidad = int(request.POST['modalidad'])
        ws = wb.add_sheet('alumnos_migrantes')
        # response = HttpResponse(content_type="application/ms-excel")
        # response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1,
        #                                                                                             10000).__str__() + '.xls'
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN", 1500),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 8000),
            (u"MODALIDAD", 8000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"PAIS RETORNO", 3000),
            (u"AÑOS/MESES", 3000),
            (u"FECHA DE RETORNO", 3000),
            (u"PROMEDIO", 3000),
            (u"ASISTENCIA", 3000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION", 3000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 5000),
            (u"PROVINCIA", 5000),
            (u"CANTON", 5000),
            (u"DIRECCION 1", 5000),
            (u"DIRECCION 2", 5000),
            (u"SECTOR", 5000),
            (u"GRUPO SOCIOECONOMICO", 5000),
            (u"PERIODO ACTUAL", 8000),
            (u"PERIDOO VALIDA", 8000),
            (u"TIPO/ESTADO", 2500),
        ]

        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
            discapacitados = Matricula.objects.values_list('inscripcion__id', flat=True).filter(status=True,
                                                                                                nivel__periodo=periodoactual,
                                                                                                estado_matricula__in=[
                                                                                                    2, 3],
                                                                                                retiradomatricula=False,
                                                                                                inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                                                                                inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                                                                                matriculagruposocioeconomico__tipomatricula=1).exclude(
                inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by("inscripcion__persona")
            matriculados = Matricula.objects.filter(status=True, nivel__periodo=periodovalida,
                                                    estado_matricula__in=[2, 3],
                                                    retiradomatricula=False,
                                                    matriculagruposocioeconomico__tipomatricula=1,
                                                    inscripcion__id__in=discapacitados).exclude(
                inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by("inscripcion__persona")
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual,
                                                              becatipo_id=22).values_list('inscripcion_id',
                                                                                          flat=True)
            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()

            matriculados = Matricula.objects.filter(inscripcion__persona__migrantepersona__isnull=False,
                                                    inscripcion__id__in=inscripciones.values_list('inscripcion_id', flat=True),
                                                    nivel__periodo__id=periodoactual.id).distinct().order_by(
                "inscripcion__persona")
        row_num = 4
        i = 0
        print('Cantidad Estudiantes Migrantes', matriculados.count())
        contador = 0
        for numero, x in enumerate(matriculados):
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.inscripcion, periodo=periodoactual, becatipo_id=22).first()
            asignaturas = MateriaAsignada.objects.filter(status=True,
                                                         matricula__inscripcion__id=x.inscripcion.id,
                                                         matricula__nivel__periodo__id=periodovalida.id,
                                                         materiaasignadaretiro__isnull=True)
            verifica = 0
            suma = 0
            promedio = 0
            sumasis = 0
            total = asignaturas.count()
            for m in asignaturas:
                suma += m.notafinal
                sumasis += m.asistenciafinal
                if m.estado.id != 1:
                    verifica = 1
                    break
            if suma > 0 and verifica == 0:
                promedio = round(suma / total, 2)
                asistencia = round(sumasis / total, 2)
            #if verifica == 0:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.inscripcion.persona.nombre_completo_inverso()
            if x.inscripcion.carrera.mencion:
                campo4 = x.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.inscripcion.carrera.mencion
            else:
                campo4 = x.inscripcion.carrera.nombre
            campo5 = x.inscripcion.modalidad.__str__()
            campo6 = x.inscripcion.persona.cedula
            campo7 = x.inscripcion.persona.nacimiento
            campo8 = x.inscripcion.persona.registro_migrante().paisresidencia.nombre
            campo9 = u"%s - %s" % (x.inscripcion.persona.registro_migrante().anioresidencia,
                                   x.inscripcion.persona.registro_migrante().mesresidencia)
            campo10 = x.inscripcion.persona.registro_migrante().fecharetorno
            campo11 = promedio
            campo12 = asistencia
            campo13 = x.inscripcion.sesion.nombre
            if x.nivelmalla:
                campo14 = x.nivelmalla.nombre
            else:
                campo14 = 'Ninguno'
            if x.paralelo:
                campo15 = x.paralelo.nombre
            else:
                campo15 = 'Ninguno'
            campo16 = x.inscripcion.persona.direccion_completa()
            campo17 = x.inscripcion.persona.telefono
            campo18 = x.inscripcion.persona.telefono_conv
            campo19 = x.inscripcion.persona.email
            campo20 = x.inscripcion.persona.emailinst
            campo21 = x.inscripcion.persona.sexo.nombre
            campo22 = x.inscripcion.persona.pais.nombre if x.inscripcion.persona.pais else ""
            campo23 = x.inscripcion.persona.provincia.nombre if x.inscripcion.persona.provincia else ""
            campo24 = x.inscripcion.persona.canton.nombre if x.inscripcion.persona.canton else ""
            campo25 = x.inscripcion.persona.direccion if x.inscripcion.persona.direccion else ""
            campo26 = x.inscripcion.persona.direccion2 if x.inscripcion.persona.direccion2 else ""
            campo27 = x.inscripcion.persona.sector if x.inscripcion.persona.sector else ""
            campo28 = str(
                x.matriculagruposocioeconomico().nombre) if x.matriculagruposocioeconomico() else ""
            campo29 = x.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, font_style2)
            ws.write(row_num, 7, campo7, date_format)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, date_format)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, campo27, font_style2)
            ws.write(row_num, 28, campo28, font_style2)
            ws.write(row_num, 29, str(periodovalida), font_style2)
            ws.write(row_num, 30, str(periodoactual), font_style2)
            ws.write(row_num, 31, campo29, font_style2)

            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)
                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            contador = numero + 1
            print(f'{contador}.-', x.inscripcion, preinscripcion)
            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', contador)
        print('Url migrante: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)

def generar_discapacitados(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=19)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()
        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_discapacitados'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR DISCAPACIDAD'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_discapacitados_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR DISCAPACIDAD'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_discapacitados_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR DISCAPACIDAD'

        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)

        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        # periodoactual = Periodo.objects.get(id=int(request.POST['periodoactual']))
        # periodovalida = Periodo.objects.get(id=int(request.POST['periodovalida']))
        # modalidad = int(request.POST['modalidad'])
        ws = wb.add_sheet('alumnos_discapacitados')
        # response = HttpResponse(content_type="application/ms-excel")
        # response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1, 10000).__str__() + '.xls'
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN", 1500),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 8000),
            (u"MODALIDAD", 8000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"DISCAPACIDAD", 3000),
            (u"PORCENTAJE", 3000),
            (u"CARNET", 3000),
            (u"PROMEDIO", 3000),
            (u"ASISTENCIA", 3000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION", 3000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 5000),
            (u"PROVINCIA", 5000),
            (u"CANTON", 5000),
            (u"DIRECCION 1", 5000),
            (u"DIRECCION 2", 5000),
            (u"SECTOR", 5000),
            (u"GRUPO SOCIOECONOMICO", 5000),
            (u"PERIODO ACTUAL", 8000),
            (u"PERIDOO VALIDA", 8000),
            (u"TIPO/ESTADO", 2500),
        ]

        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
            discapacitados = Matricula.objects.values_list('inscripcion__id', flat=True).filter(status=True,
                                                                                                nivel__periodo=periodoactual,
                                                                                                estado_matricula__in=[
                                                                                                    2, 3],
                                                                                                retiradomatricula=False,
                                                                                                inscripcion__persona__perfilinscripcion__tienediscapacidad=True,
                                                                                                inscripcion__persona__perfilinscripcion__verificadiscapacidad=True,
                                                                                                matriculagruposocioeconomico__tipomatricula=1).exclude(
                inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by("inscripcion__persona")
            matriculados = Matricula.objects.filter(status=True, nivel__periodo=periodovalida,
                                                    estado_matricula__in=[2, 3],
                                                    retiradomatricula=False,
                                                    matriculagruposocioeconomico__tipomatricula=1,
                                                    inscripcion__id__in=discapacitados).exclude(
                inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by("inscripcion__persona")
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=19)

            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()

            matriculados = Matricula.objects.filter(inscripcion__id__in=inscripciones.values_list('inscripcion_id', flat=True),
                                                    nivel__periodo__id=periodoactual.id).distinct().order_by(
                "inscripcion__persona")
        row_num = 4
        i = 0
        print('Cantidad Estudiantes Discapacitados', matriculados.count())
        for numero, x in enumerate(matriculados):
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.inscripcion, periodo=periodoactual, becatipo_id=19).first()
            x1 = InscripcionNivel.objects.filter(inscripcion=x.inscripcion, nivel__orden=1)
            isPrimerNivel = False
            verifica = 0
            suma = 0
            promedio = 0
            sumasis = 0
            asistencia = 0
            if x1.exists():
                isPrimerNivel = True
            if not isPrimerNivel:
                asignaturas = MateriaAsignada.objects.filter(status=True,
                                                             matricula__inscripcion__id=x.inscripcion.id,
                                                             matricula__nivel__periodo__id=periodovalida.id,
                                                             materiaasignadaretiro__isnull=True).exclude(
                    materia__asignaturamalla__malla_id__in=[353, 22])

                total = asignaturas.count()
                for m in asignaturas:
                    suma += m.notafinal
                    sumasis += m.asistenciafinal
                    if m.estado.id != 1:
                        verifica = 1
                        break
                if suma > 0 and verifica == 0:
                    promedio = round(suma / total, 2)
                    asistencia = round(sumasis / total, 2)
            # if verifica == 0:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.inscripcion.persona.nombre_completo_inverso()
            if x.inscripcion.carrera.mencion:
                campo4 = x.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.inscripcion.carrera.mencion
            else:
                campo4 = x.inscripcion.carrera.nombre
            campo5 = x.inscripcion.modalidad.__str__()
            campo6 = x.inscripcion.persona.cedula
            campo7 = x.inscripcion.persona.nacimiento
            if periodoactual.id >= 119:
                campo8 = preinscripcion.tipodiscapacidad.nombre if preinscripcion.tipodiscapacidad else ""
                campo9 = preinscripcion.porcientodiscapacidad
                campo10 = preinscripcion.carnetdiscapacidad
            else:
                campo8 = x.inscripcion.persona.mi_perfil().tipodiscapacidad.nombre if x.inscripcion.persona.mi_perfil().tipodiscapacidad else ""
                campo9 = x.inscripcion.persona.mi_perfil().porcientodiscapacidad
                campo10 = x.inscripcion.persona.mi_perfil().carnetdiscapacidad
            campo11 = promedio if not isPrimerNivel and promedio > 0 else 'NO APLICA'
            campo12 = asistencia if not isPrimerNivel and asistencia > 0 else 'NO APLICA'
            campo13 = x.inscripcion.sesion.nombre
            if x.nivelmalla:
                campo14 = x.nivelmalla.nombre
            else:
                campo14 = 'Ninguno'
            if x.paralelo:
                campo15 = x.paralelo.nombre
            else:
                campo15 = 'Ninguno'
            campo16 = x.inscripcion.persona.direccion_completa()
            campo17 = x.inscripcion.persona.telefono if x.inscripcion.persona.telefono else ""
            campo18 = x.inscripcion.persona.telefono_conv if x.inscripcion.persona.telefono_conv else ""
            campo19 = x.inscripcion.persona.email if x.inscripcion.persona.email else ""
            campo20 = x.inscripcion.persona.emailinst if x.inscripcion.persona.emailinst else ""
            campo21 = x.inscripcion.persona.sexo.nombre if x.inscripcion.persona.sexo else ""
            campo22 = x.inscripcion.persona.pais.nombre if x.inscripcion.persona.pais else ""
            campo23 = x.inscripcion.persona.provincia.nombre if x.inscripcion.persona.provincia else ""
            campo24 = x.inscripcion.persona.canton.nombre if x.inscripcion.persona.canton else ""
            campo25 = x.inscripcion.persona.direccion if x.inscripcion.persona.direccion else ""
            campo26 = x.inscripcion.persona.direccion2 if x.inscripcion.persona.direccion2 else ""
            campo27 = x.inscripcion.persona.sector if x.inscripcion.persona.sector else ""
            campo28 = str(
                x.matriculagruposocioeconomico().nombre) if x.matriculagruposocioeconomico() else ""
            campo29 = x.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, date_format)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, campo27, font_style2)
            ws.write(row_num, 28, campo28, font_style2)
            ws.write(row_num, 29, str(periodoactual), font_style2)
            ws.write(row_num, 30, str(periodovalida), font_style2)
            ws.write(row_num, 31, campo29, font_style2)

            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)

                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            print(f'{i}.-', x.inscripcion, preinscripcion)
            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', i)
        print('Url migrante: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)

def generar_deportes(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=20)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()

        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_deporte'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR ALTO RENDIMIENTO EN DEPORTES'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_deporte_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR ALTO RENDIMIENTO EN DEPORTES'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_deporte_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR ALTO RENDIMIENTO EN DEPORTES'
        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('alumnos_deporte')
        # response = HttpResponse(content_type="application/ms-excel")
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN", 1500),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 3000),
            (u"MODALIDAD", 3000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"PROMEDIO", 2000),
            (u"ASISTENCIA", 2000),
            (u"AMERITA", 2000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION COMPLETA", 4000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 8000),
            (u"PROVINCIA", 8000),
            (u"CANTON", 8000),
            (u"DIRECCION 1", 8000),
            (u"DIRECCION 2", 8000),
            (u"SECTOR", 8000),
            (u"GRUPO SOCIO ECONÓMICO", 8000),
            (u"TIPO/ESTADO", 2500),
        ]

        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        #response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1, 10000).__str__() + '.xls'
        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
            matriculados = Matricula.objects.filter(pk=None)
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=20).values_list(
                'inscripcion_id', flat=True)

            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(
                    preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(
                    preinscripcionbecarequisito__cumplerequisito=False).exclude(
                    id__in=pendientes).distinct()

            matriculados = Matricula.objects.filter(inscripcion__id__in=inscripciones.values_list('inscripcion_id', flat=True),
                                                    nivel__periodo__id=periodoactual.id).distinct().order_by("inscripcion__persona")
        row_num = 4
        i = 0
        continua = False
        print('Cantidad Estudiantes Deportes', matriculados.count())
        for x in matriculados:
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.inscripcion, periodo=periodoactual, becatipo_id=20).first()
            amerita = None
            verifica = 0
            suma = 0
            sumasis = 0
            promedio = 0
            materias = MateriaAsignada.objects.filter(status=True,
                                                      matricula__inscripcion__id=x.inscripcion.id,
                                                      matricula__nivel__periodo__id=periodovalida.id,
                                                      materiaasignadaretiro__isnull=True)
            total = materias.count()
            if total < 4:
                amerita = "<4: " + str(total)
            for m in materias:
                suma += m.notafinal
                sumasis += m.asistenciafinal
                if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
                    if m.estado.id != 1:
                        verifica = 1
                        break
            if suma > 0 and sumasis > 0:
                promedio = round(suma / total, 2)
                asistencia = round(sumasis / total, 2)

            if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
                if verifica == 0 and promedio >= 85:
                    continua = True
            elif periodoactual.versionbeca == 2:
                if verifica == 0 and promedio >= 70:
                    continua = True
            #if continua:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.inscripcion.persona.nombre_completo_inverso()
            if x.inscripcion.carrera.mencion:
                campo4 = x.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.inscripcion.carrera.mencion
            else:
                campo4 = x.inscripcion.carrera.nombre
            campo5 = x.inscripcion.modalidad.__str__()
            campo6 = x.inscripcion.persona.cedula
            campo7 = x.inscripcion.persona.nacimiento
            campo8 = promedio
            campo9 = asistencia
            campo10 = amerita
            campo11 = x.inscripcion.sesion.nombre
            campo12 = x.nivelmalla.nombre
            if x.paralelo:
                campo13 = x.paralelo.nombre
            else:
                campo13 = 'Ninguno'
            campo14 = x.inscripcion.persona.direccion_completa()
            campo15 = x.inscripcion.persona.telefono
            campo16 = x.inscripcion.persona.telefono_conv
            campo17 = x.inscripcion.persona.email
            campo18 = x.inscripcion.persona.emailinst
            campo19 = x.inscripcion.persona.sexo.nombre
            campo20 = x.inscripcion.persona.pais.nombre if x.inscripcion.persona.pais else ""
            campo21 = x.inscripcion.persona.provincia.nombre if x.inscripcion.persona.provincia else ""
            campo22 = x.inscripcion.persona.canton.nombre if x.inscripcion.persona.canton else ""
            campo23 = x.inscripcion.persona.direccion if x.inscripcion.persona.direccion else ""
            campo24 = x.inscripcion.persona.direccion2 if x.inscripcion.persona.direccion2 else ""
            campo25 = x.inscripcion.persona.sector if x.inscripcion.persona.sector else ""
            campo26 = str(
                x.matriculagruposocioeconomico().nombre) if x.matriculagruposocioeconomico() else ""
            campo27 = x.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, date_format)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, campo27, font_style2)

            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)
                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            print(f'{i}.-', x.inscripcion, preinscripcion)
            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes procesados', i)
        print('Url Deporte: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)

def generar_primernivel(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=16)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()

        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_primernivel'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR PRIMER NIVEL'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_primernivel_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR PRIMER NIVEL'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_primernivel_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR PRIMER NIVEL'
        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('alumnos_primernivel')
        #response = HttpResponse(content_type="application/ms-excel")
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN", 1000),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 3000),
            (u"MODALIDAD", 3000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION COMPLETA", 4000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 8000),
            (u"PROVINCIA", 8000),
            (u"CANTON", 8000),
            (u"DIRECCION 1", 8000),
            (u"DIRECCION 2", 8000),
            (u"SECTOR", 8000),
            (u"GRUPO SOCIO ECONÓMICO", 8000),
            (u"TÍTULO", 20000),
            (u"COLEGIO", 20000),
            (u"FECHA INICIO", 3000),
            (u"FECHA OBTENCIÓN", 3000),
            (u"FECHA EGRESADO", 3000),
            (u"CALIFICACIÓN", 2000),
            (u"AÑO INICIO", 2000),
            (u"AÑO FIN", 2000),
            (u"ACTA DE GRADO", 20000),
        ]

        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        #response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1, 10000).__str__() + '.xls'
        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        preinscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual,
                                                             becatipo=becatipo,
                                                             inscripcion__matricula__estado_matricula__in=[2, 3],
                                                             status=True,
                                                             inscripcion__matricula__status=True,
                                                             inscripcion__matricula__retiradomatricula=False,
                                                             inscripcion__matricula__matriculagruposocioeconomico__tipomatricula=1).distinct()

        if action_extra == 'requisitos_completos':
            preinscripciones = preinscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                .filter(total_requisitos=cantidad_total_requisitos)
        elif action_extra == 'requisitos_incompletos':
            pendientes = preinscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
            preinscripciones = preinscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()

        row_num = 4
        print('Cantidad Estudiantes Primer Nivel', preinscripciones.count())
        contador = 0
        for i, preinscripcion in enumerate(preinscripciones):
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = preinscripcion.inscripcion.persona.nombre_completo_inverso()
            if preinscripcion.inscripcion.carrera.mencion:
                campo4 = preinscripcion.inscripcion.carrera.nombre + ' CON MENCION EN  ' + preinscripcion.inscripcion.carrera.mencion
            else:
                campo4 = preinscripcion.inscripcion.carrera.nombre
            campo5 = preinscripcion.inscripcion.modalidad.__str__()
            campo6 = preinscripcion.inscripcion.persona.cedula
            campo7 = preinscripcion.inscripcion.persona.nacimiento
            campo8 = preinscripcion.inscripcion.sesion.nombre
            matricula = preinscripcion.inscripcion.matricula_set.filter(nivel__periodo=periodoactual, retiradomatricula=False, status=True).first()
            campo9 = matricula.nivelmalla.nombre
            campo10 = matricula.paralelo.nombre if matricula.paralelo else "Ninguno"
            campo11 = preinscripcion.inscripcion.persona.direccion_completa()
            campo12 = preinscripcion.inscripcion.persona.telefono
            campo13 = preinscripcion.inscripcion.persona.telefono_conv
            campo14 = preinscripcion.inscripcion.persona.email
            campo15 = preinscripcion.inscripcion.persona.emailinst
            campo16 = preinscripcion.inscripcion.persona.sexo.nombre
            campo17 = preinscripcion.inscripcion.persona.pais.nombre if preinscripcion.inscripcion.persona.pais else ""
            campo18 = preinscripcion.inscripcion.persona.provincia.nombre if preinscripcion.inscripcion.persona.provincia else ""
            campo19 = preinscripcion.inscripcion.persona.canton.nombre if preinscripcion.inscripcion.persona.canton else ""
            campo20 = preinscripcion.inscripcion.persona.direccion if preinscripcion.inscripcion.persona.direccion else ""
            campo21 = preinscripcion.inscripcion.persona.direccion2 if preinscripcion.inscripcion.persona.direccion2 else ""
            campo22 = preinscripcion.inscripcion.persona.sector if preinscripcion.inscripcion.persona.sector else ""
            campo23 = str(matricula.matriculagruposocioeconomico().nombre) if matricula.matriculagruposocioeconomico() else ""
            campo24 = ""
            campo25 = ""
            campo26 = ""
            campo27 = ""
            campo28 = ""
            campo29 = ""
            campo30 = ""
            campo31 = ""
            campo32 = ""
            titulo_bachiller = preinscripcion.inscripcion.persona.titulo_bachiller()
            if titulo_bachiller:
                campo24 = titulo_bachiller.titulo.__str__()  # titulo
                campo25 = titulo_bachiller.colegio.nombre if titulo_bachiller.colegio else "Sin Colegio"  # colegio
                campo26 = titulo_bachiller.fechainicio  # fechainicio
                campo27 = titulo_bachiller.fechaobtencion  # fechaobtencion
                campo28 = titulo_bachiller.fechaegresado  # fechaegresado
                detalle = titulo_bachiller.detalletitulacion()
                if detalle:
                    campo29 = detalle.calificacion  # calificacion
                    campo30 = detalle.anioinicioperiodograduacion  # anioinicio
                    campo31 = detalle.aniofinperiodograduacion  # aniofin
                    campo32 = detalle.actagrado.url if detalle.actagrado else ""  # actagrado
            ws.write(row_num, 0, i + 1, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, date_format)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, date_format)
            ws.write(row_num, 27, campo27, date_format)
            ws.write(row_num, 28, campo28, date_format)
            ws.write(row_num, 29, campo29, font_style2)
            ws.write(row_num, 30, campo30, font_style2)
            ws.write(row_num, 31, campo31, font_style2)
            ws.write(row_num, 32, campo32, font_style2)

            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)
                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            contador += 1
            print(f'{contador}.-', preinscripcion.inscripcion, preinscripcion)
            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', contador)
        print('Url Primer Nivel: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)

def generar_promedio(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=17)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=perioactual).first()
        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_promedio'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR ALTO PROMEDIO Y DISTINCIÓN ACADÉMICA'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_promedio_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR ALTO PROMEDIO Y DISTINCIÓN ACADÉMICA'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_promedio_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR ALTO PROMEDIO Y DISTINCIÓN ACADÉMICA'

        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('alumnos_promedio')
        #response = HttpResponse(content_type="application/ms-excel")
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN.", 1000),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 3000),
            (u"MODALIDAD", 3000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"PROMEDIO", 2000),
            (u"PROMEDIO CARRERA", 2000),
            (u"DESVIACIÓN ESTANDAR", 3000),
            (u"ASISTENCIA", 2000),
            (u"AMERITA", 2000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION COMPLETA", 4000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 8000),
            (u"PROVINCIA", 8000),
            (u"CANTON", 8000),
            (u"DIRECCION 1", 8000),
            (u"DIRECCION 2", 8000),
            (u"SECTOR", 8000),
            (u"GRUPO SOCIO ECONÓMICO", 8000),
            (u"TIPO/ESTADO", 2500),
        ]
        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        #response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1, 10000).__str__() + '.xls'
        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        if perioactual.versionbeca is None or perioactual.versionbeca == 1:
            inscripcionesactuales = Matricula.objects.values_list('inscripcion__id', flat=True).filter(
                status=True, nivel__periodo__id=perioactual.id,
                estado_matricula__in=[2, 3],
                retiradomatricula=False,
                matriculagruposocioeconomico__tipomatricula=1).exclude(
                inscripcion__persona__rubro__cancelado=False,
                inscripcion__persona__rubro__status=True,
                inscripcion__persona__rubro__fecha__lte=periodovalida.fin).distinct().order_by(
                "inscripcion__persona")
            matriculados = Matricula.objects.filter(status=True,
                                                    nivel__periodo__id=periodovalida.id,
                                                    estado_matricula__in=[2, 3],
                                                    retiradomatricula=False,
                                                    matriculagruposocioeconomico__tipomatricula=1,
                                                    inscripcion__id__in=inscripcionesactuales).exclude(
                inscripcion__persona__rubro__cancelado=False,
                inscripcion__persona__rubro__status=True,
                inscripcion__persona__rubro__fecha__lte=periodovalida.fin).distinct().order_by(
                "inscripcion__persona")
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=17).values_list('inscripcion_id', flat=True)

            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()

            matriculados = Matricula.objects.filter(inscripcion__id__in=inscripciones.values_list('inscripcion_id', flat=True),
                                                    nivel__periodo__id=periodoactual.id).distinct().order_by("inscripcion__persona")

        row_num = 4
        i = 0
        continua = False
        print('Cantidad Estudiantes Academico', matriculados.count())
        for x in matriculados:
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.inscripcion, periodo=periodoactual, becatipo_id=17).first()
            amerita = None
            verifica = 0
            suma = 0
            sumasis = 0
            promedio = 0

            materias = MateriaAsignada.objects.filter(status=True,
                                                      matricula__inscripcion__id=x.inscripcion.id,
                                                      matricula__nivel__periodo__id=periodovalida.id,
                                                      materiaasignadaretiro__isnull=True)
            total = materias.count()
            if total < 4:
                amerita = "<4: " + str(total)
            for m in materias:
                suma += m.notafinal
                sumasis += m.asistenciafinal
                if m.estado.id != 1:
                    verifica = 1
                    break
            if suma > 0 and sumasis > 0:
                promedio = round(suma / total, 2)
                asistencia = round(sumasis / total, 2)

            if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
                if verifica == 0 and promedio >= 85:
                    continua = True
            elif periodoactual.versionbeca == 2:
                continua = True
                promedio = x.inscripcion.promedio
            # if continua:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.inscripcion.persona.nombre_completo_inverso()
            if x.inscripcion.carrera.mencion:
                campo4 = x.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.inscripcion.carrera.mencion
            else:
                campo4 = x.inscripcion.carrera.nombre
            campo5 = x.inscripcion.modalidad.__str__()
            campo6 = x.inscripcion.persona.cedula
            campo7 = x.inscripcion.persona.nacimiento
            campo8 = preinscripcion.promedio
            campo9 = preinscripcion.promedio_carrera
            campo10 = preinscripcion.desviacion_estandar
            campo11 = asistencia
            campo12 = amerita
            campo13 = x.inscripcion.sesion.nombre
            campo14 = x.nivelmalla.nombre
            if x.paralelo:
                campo15 = x.paralelo.nombre
            else:
                campo15 = 'Ninguno'
            campo16 = x.inscripcion.persona.direccion_completa()
            campo17 = x.inscripcion.persona.telefono
            campo18 = x.inscripcion.persona.telefono_conv
            campo19 = x.inscripcion.persona.email
            campo20 = x.inscripcion.persona.emailinst
            campo21 = x.inscripcion.persona.sexo.nombre
            campo22 = x.inscripcion.persona.pais.nombre if x.inscripcion.persona.pais else ""
            campo23 = x.inscripcion.persona.provincia.nombre if x.inscripcion.persona.provincia else ""
            campo24 = x.inscripcion.persona.canton.nombre if x.inscripcion.persona.canton else ""
            campo25 = x.inscripcion.persona.direccion if x.inscripcion.persona.direccion else ""
            campo26 = x.inscripcion.persona.direccion2 if x.inscripcion.persona.direccion2 else ""
            campo27 = x.inscripcion.persona.sector if x.inscripcion.persona.sector else ""
            campo28 = str(
                x.matriculagruposocioeconomico().nombre) if x.matriculagruposocioeconomico() else ""
            campo29 = x.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, font_style2)
            ws.write(row_num, 6, campo6, date_format)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, campo27, font_style2)
            ws.write(row_num, 28, campo28, font_style2)
            ws.write(row_num, 29, campo29, font_style2)
            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)
                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1
            print(f'{i}.-', x.inscripcion, preinscripcion)
            row_num += 1
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', i)
        print('Url promedios: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)
def generar_quintil(periodoactual, periodovalida,  action_extra='', dev=True):
    try:
        becatipo = BecaTipo.objects.get(pk=18)
        configuracion = becatipo.becatipoconfiguracion_set.filter(becaperiodo__periodo=periodoactual).first()
        cantidad_total_requisitos = 0
        nombre_archivo = 'alumnos_quintil'
        titulo_archivo = 'LISTADO DE ESTUDIANTE PRESELECCIONADO POR SITUACION ECONOMICA VULNERABLE'
        if configuracion:
            if action_extra:
                cantidad_total_requisitos = configuracion.requisitosbecas.count() if configuracion.requisitosbecas else 0
                if action_extra == 'requisitos_completos':
                    nombre_archivo = 'alumnos_quintil_OCAS'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES SELECCIONADOS POR SITUACION ECONOMICA VULNERABLE'
                elif action_extra == 'requisitos_incompletos':
                    nombre_archivo = 'alumnos_quintil_rechazados'
                    titulo_archivo = 'LISTADO DE ESTUDIANTES NO SELECCIONADOS POR SITUACION ECONOMICA VULNERABLE'
        url_archivo = "{}/media/{}.xls".format(SITE_STORAGE, nombre_archivo)
        if dev:
            url_archivo = "{}/media/{}.xls".format(SITE_ROOT, nombre_archivo)
        font_style = XFStyle()
        font_style.font.bold = True
        font_style2 = XFStyle()
        font_style2.font.bold = False
        wb = Workbook(encoding='utf-8')
        ws = wb.add_sheet('alumnos_quintil')
        # periodoactual = Periodo.objects.get(id=int(request.POST['periodoactual']))
        # periodovalida = Periodo.objects.get(id=int(request.POST['periodovalida']))
        # modalidad = int(request.POST['modalidad'])
        #response = HttpResponse(content_type="application/ms-excel")
        # response['Content-Disposition'] = f'attachment; filename={nombre_archivo}' + random.randint(1,
        #                                                                                             10000).__str__() + '.xls'
        columns = [
            (u"N.", 1500),
            (u"ID_PREINSCRIPCION.", 1500),
            (u"ORDEN", 1500),
            (u"APELLIDOS Y NOMBRES", 12000),
            (u"CARRERA", 3000),
            (u"MODALIDAD", 3000),
            (u"CEDULA", 3000),
            (u"FECHA NACIMIENTO", 3000),
            (u"DIRECCION", 3000),
            (u"PROMEDIO GENERAL", 3000),
            (u"PROMEDIO VERIFICADOR", 3000),
            (u"ASISTENCIA", 3000),
            (u"CODIGO", 3000),
            (u"NOMBRE", 3000),
            (u"SESION", 3000),
            (u"NIVEL", 3000),
            (u"PARALELO", 3000),
            (u"DIRECCION COMPLETA", 3000),
            (u"TELEFONO", 4000),
            (u"TELEFONO CONVENCIONAL", 4000),
            (u"EMAIL", 5000),
            (u"EMAIL INSTITUCIONAL", 5000),
            (u"SEXO", 5000),
            (u"PAIS", 5000),
            (u"PROVINCIA", 5000),
            (u"CANTON", 5000),
            (u"DIRECCION 1", 5000),
            (u"DIRECCION 2", 5000),
            (u"SECTOR", 5000),
            (u"PERIODO ACTUAL", 8000),
            (u"PERIDOO VALIDA", 8000),
            (u"TIPO/ESTADO", 2500),
        ]
        requisitos = []
        if configuracion:
            # Requisitos de tipos de becas
            requisitos = configuracion.requisitosbecas.filter(status=True)
            for detallerequisitobeca in requisitos:
                columns.append((f'({detallerequisitobeca.pk}) {detallerequisitobeca.requisitobeca.__str__()}', 10000))
                if not action_extra:
                    columns.append((f'({detallerequisitobeca.pk}) OBSERVACIÓN', 5000))

        style_title = xlwt.easyxf(
            'font: height 350, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        style_title_2 = xlwt.easyxf(
            'font: height 250, name Arial, colour_index black, bold on, italic on; align: wrap on, vert centre, horiz center;')
        ws.write_merge(0, 0, 0, len(columns), 'UNIVERSIDAD ESTATAL DE MILAGRO', style_title)
        ws.write_merge(1, 1, 0, len(columns), titulo_archivo, style_title_2)
        row_num = 3
        for col_num in range(len(columns)):
            ws.write(row_num, col_num, columns[col_num][0], font_style)
            ws.col(col_num).width = columns[col_num][1]
        date_format = xlwt.XFStyle()
        date_format.num_format_str = 'yyyy/mm/dd'
        matriculados = None
        if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
            listaquintil = MatriculaGrupoSocioEconomico.objects.values_list('matricula__inscripcion__id',
                                                                            flat=True).filter(
                Q(gruposocioeconomico__codigo='D') | Q(gruposocioeconomico__codigo='C-'),
                matricula__estado_matricula__in=[2, 3], matricula__status=True,
                matricula__retiradomatricula=False,
                matricula__nivel__periodo__id=periodoactual.id,
                matricula__matriculagruposocioeconomico__tipomatricula=1,
                matricula__inscripcion__carrera__coordinacion__excluir=False
            ).exclude(matricula__inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by(
                "puntajetotal")
            matriculados = MatriculaGrupoSocioEconomico.objects.filter(
                Q(gruposocioeconomico__codigo='D') | Q(gruposocioeconomico__codigo='C-'),
                matricula__estado_matricula__in=[2, 3], matricula__status=True,
                matricula__retiradomatricula=False,
                matricula__nivel__periodo__id=periodovalida.id,
                matricula__matriculagruposocioeconomico__tipomatricula=1,
                matricula__inscripcion__carrera__coordinacion__excluir=False,
                matricula__inscripcion__id__in=listaquintil).exclude(
                matricula__inscripcion__carrera__coordinacion__id__in=[7, 9]).distinct().order_by(
                "puntajetotal")
        elif periodoactual.versionbeca == 2:
            inscripciones = PreInscripcionBeca.objects.filter(periodo=periodoactual, becatipo_id=18)

            if action_extra == 'requisitos_completos':
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=True) \
                    .annotate(total_requisitos=Count('preinscripcionbecarequisito', filter=Q(status=True), distinct=True)) \
                    .filter(total_requisitos=cantidad_total_requisitos)
            elif action_extra == 'requisitos_incompletos':
                pendientes = inscripciones.values_list('id', flat=True).filter(preinscripcionbecarequisito__cumplerequisito__isnull=True)
                inscripciones = inscripciones.filter(preinscripcionbecarequisito__cumplerequisito=False).exclude(id__in=pendientes).distinct()
            matriculados = MatriculaGrupoSocioEconomico.objects.filter(
                Q(gruposocioeconomico__codigo='D') | Q(gruposocioeconomico__codigo='C-'),
                matricula__retiradomatricula=False,
                matricula__nivel__periodo=periodoactual,
                matricula__matriculagruposocioeconomico__tipomatricula=1,
                matricula__inscripcion__in=inscripciones.values_list('inscripcion_id', flat=True),
                matricula__inscripcion__carrera__coordinacion__excluir=False
            ).distinct().order_by("gruposocioeconomico__codigo")
        row_num = 4
        i = 0
        for x in matriculados:
            preinscripcion = PreInscripcionBeca.objects.filter(inscripcion=x.matricula.inscripcion, periodo=periodoactual, becatipo_id=18).first()
            asignatura = MateriaAsignada.objects.filter(status=True,
                                                        matricula__inscripcion__id=x.matricula.inscripcion.id,
                                                        matricula__nivel__periodo__id=periodovalida.id,
                                                        materiaasignadaretiro__isnull=True)
            verifica = 0
            suma = 0
            promedio = 0
            sumasis = 0
            total = asignatura.count()
            for m in asignatura:
                suma += m.notafinal
                sumasis += m.asistenciafinal
                if periodoactual.versionbeca is None or periodoactual.versionbeca == 1:
                    if m.estado.id != 1:
                        verifica = 1
                        break
            if suma > 0 and sumasis > 0 and verifica == 0:
                promedio = round(suma / total, 2)
                asistencia = round(sumasis / total, 2)
            if periodoactual.versionbeca > 1:
                verifica = 0
                promedio = x.matricula.inscripcion.promedio

            #if verifica == 0:
            campo1 = preinscripcion.id
            campo2 = preinscripcion.orden
            campo3 = x.matricula.inscripcion.persona.nombre_completo_inverso()
            if (x.matricula.inscripcion.carrera.mencion and x.matricula.inscripcion.carrera.nombre != ''):
                campo4 = x.matricula.inscripcion.carrera.nombre + ' CON MENCION EN  ' + x.matricula.inscripcion.carrera.mencion
            elif (x.matricula.inscripcion.carrera.nombre != ''):
                campo4 = x.matricula.inscripcion.carrera.nombre
            campo5 = x.matricula.inscripcion.modalidad.__str__()
            campo6 = x.matricula.inscripcion.persona.cedula
            campo7 = x.matricula.inscripcion.persona.nacimiento
            campo8 = x.matricula.inscripcion.persona.direccion_completa()
            campo9 = promedio
            campo10 = preinscripcion.promedio
            campo11 = asistencia
            campo12 = x.gruposocioeconomico.codigo
            campo13 = x.gruposocioeconomico.nombre
            campo14 = x.matricula.inscripcion.sesion.nombre
            if x.matricula.nivelmalla.nombre:
                campo15 = x.matricula.nivelmalla.nombre
            else:
                campo15 = 'Ninguno'
            if x.matricula.paralelo:
                campo16 = x.matricula.paralelo.nombre
            else:
                campo16 = 'Ninguno'
            campo17 = x.matricula.inscripcion.persona.direccion_completa()
            campo18 = x.matricula.inscripcion.persona.telefono
            campo19 = x.matricula.inscripcion.persona.telefono_conv
            campo20 = x.matricula.inscripcion.persona.email
            campo21 = x.matricula.inscripcion.persona.emailinst
            campo22 = x.matricula.inscripcion.persona.sexo.nombre if x.matricula.inscripcion.persona.sexo else ""
            campo23 = x.matricula.inscripcion.persona.pais.nombre if x.matricula.inscripcion.persona.pais else ""
            campo24 = x.matricula.inscripcion.persona.provincia.nombre if x.matricula.inscripcion.persona.provincia else ""
            campo25 = x.matricula.inscripcion.persona.canton.nombre if x.matricula.inscripcion.persona.canton else ""
            campo26 = x.matricula.inscripcion.persona.direccion if x.matricula.inscripcion.persona.direccion else ""
            campo27 = x.matricula.inscripcion.persona.direccion2 if x.matricula.inscripcion.persona.direccion2 else ""
            campo28 = x.matricula.inscripcion.persona.sector if x.matricula.inscripcion.persona.sector else ""
            campo29 = x.matricula.estado_renovacion_beca(becatipo, periodovalida)
            i += 1
            ws.write(row_num, 0, i, font_style2)
            ws.write(row_num, 1, campo1, font_style2)
            ws.write(row_num, 2, campo2, font_style2)
            ws.write(row_num, 3, campo3, font_style2)
            ws.write(row_num, 4, campo4, font_style2)
            ws.write(row_num, 5, campo5, date_format)
            ws.write(row_num, 6, campo6, font_style2)
            ws.write(row_num, 7, campo7, font_style2)
            ws.write(row_num, 8, campo8, font_style2)
            ws.write(row_num, 9, campo9, font_style2)
            ws.write(row_num, 10, campo10, font_style2)
            ws.write(row_num, 11, campo11, font_style2)
            ws.write(row_num, 12, campo12, font_style2)
            ws.write(row_num, 13, campo13, font_style2)
            ws.write(row_num, 14, campo14, font_style2)
            ws.write(row_num, 15, campo15, font_style2)
            ws.write(row_num, 16, campo16, font_style2)
            ws.write(row_num, 17, campo17, font_style2)
            ws.write(row_num, 18, campo18, font_style2)
            ws.write(row_num, 19, campo19, font_style2)
            ws.write(row_num, 20, campo20, font_style2)
            ws.write(row_num, 21, campo21, font_style2)
            ws.write(row_num, 22, campo22, font_style2)
            ws.write(row_num, 23, campo23, font_style2)
            ws.write(row_num, 24, campo24, font_style2)
            ws.write(row_num, 25, campo25, font_style2)
            ws.write(row_num, 26, campo26, font_style2)
            ws.write(row_num, 27, campo27, font_style2)
            ws.write(row_num, 28, campo28, font_style2)
            ws.write(row_num, 29, str(periodoactual), font_style2)
            ws.write(row_num, 30, str(periodovalida), font_style2)
            ws.write(row_num, 31, campo29, font_style2)
            if requisitos:
                col_num = len(columns) - requisitos.count() * (2 if not action_extra else 1)
                for detallerequisitobeca in requisitos:
                    preinscriocionrequisitos = PreInscripcionBecaRequisito.objects.filter(preinscripcion=preinscripcion, detallerequisitobeca=detallerequisitobeca, status=True)
                    for preinsrequisito in preinscriocionrequisitos:
                        cumple = ''
                        cumplerequisito = preinsrequisito.cumplerequisito
                        if cumplerequisito:
                            cumple = 'SI'
                        elif cumplerequisito == False:
                            cumple = 'NO'
                        ws.write(row_num, col_num, cumple, font_style2)
                        if not action_extra:
                            col_num += 1
                            ws.write(row_num, col_num, '', font_style2)  # Observación por columna
                    col_num += 1

            row_num += 1
            print(f'{i}.-', x.matricula.inscripcion, preinscripcion)
            # else:
            #     verifica =123
        wb.save(url_archivo)
        print('Cantidad de Estudiantes prcesados', i)
        print('Url quintil: ', url_archivo)
    except Exception as ex:
        err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
        msg = ex.__str__()
        msg = f'{msg} {err}'
        print(msg)

perioactual = Periodo.objects.get(pk=126)
periovalida = Periodo.objects.get(pk=119)
generar_etnias(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_extranjeros(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_migrantes(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_discapacitados(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_deportes(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_primernivel(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_promedio(periodoactual=perioactual, periodovalida=periovalida, dev=False)
generar_quintil(periodoactual=perioactual, periodovalida=periovalida, dev=False)


