# coding=utf-8
# !/usr/bin/env python

import os
import sys

from django.http import HttpResponse

YOUR_PATH = os.path.dirname(os.path.realpath(__file__))
SITE_ROOT = os.path.dirname(os.path.dirname(YOUR_PATH))
SITE_ROOT = os.path.join(SITE_ROOT, '')
your_djangoproject_home = os.path.split(SITE_ROOT)[0]
sys.path.append(your_djangoproject_home)

from webpush import send_user_notification
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "settings")
application = get_wsgi_application()
from settings import SITE_STORAGE
import xlwt
from xlwt import easyxf, XFStyle
from sga.models import Inscripcion, AsignaturaMalla, Persona, Matricula, MateriaAsignada
from xlwt import *
import io
import xlsxwriter


def mtfaci(anio):
    cadena = ''
    linea, excluidos, conexito = 0, 0, 0
    try:
        archivo_ = f'MT_FACI_{anio}'
        url_archivo = "{}/media/{}.xlsx".format(SITE_STORAGE, archivo_)

        __author__ = 'Unemi'
        workbook = xlsxwriter.Workbook(url_archivo, {'constant_memory': True})
        ws = workbook.add_worksheet('resultados')
        fuentecabecera = workbook.add_format({
            'align': 'center',
            'bg_color': 'silver',
            'border': 1,
            'bold': 1
        })
        formatoceldacenter = workbook.add_format({
            'border': 1,
            'valign': 'vcenter',
            'align': 'center'})




        columns = [
            (u"AÑO", 0, 2),
            (u"PERIODO", 1, 2),
            (u"CARRERA", 2, 2),
            (u"DOCUMENTO_ESTUDIANTE", 3, 0),
            (u"APELLIDOS_NOMBRES", 4, 1),
            (u"EMAIL", 5, 2),
            (u"TELEFONO", 6, 3),
            (u"SEXO_ESTUDIANTE", 7, 3),
            (u"FECHA_NACIMIENTO", 8, 3),
            (u"EDAD", 9, 3),
            (u"VARIABLE_SOCIOECONOMICA", 10, 4),
            (u"TRABAJA", 11, 4),
            (u"COLEGIO_FISCAL/PARTICULAR", 12, 4),
            (u"NIVEL", 13, 4),
            (u"MATERIA", 14, 6),
            (u"VECES_MATERIA", 15, 6),
            (u"ESTADO_MATERIA", 16, 6),
            (u"PROFESOR", 17, 6),
            (u"SEXO_PROFESOR", 18, 6),
            (u"PHD", 19, 6),
            (u"MAESTRIA", 20, 6),
        ]

        row_num, numcolum = 0, 0
        for col_num in range(len(columns)):
            ws.write(row_num, numcolum, columns[col_num][0], fuentecabecera)
            ws.set_column(row_num, numcolum, columns[col_num][1])
            numcolum += 1
        row_num, leido = 1, 1
        qsmateria = MateriaAsignada.objects.filter(status=True, matricula__nivel__periodo__anio=anio,  matricula__nivel__periodo__tipo=2, matricula__inscripcion__coordinacion=4)
        tot_ = len(qsmateria)
        for materia in qsmateria:
            print(f"{leido}/{tot_} {materia}")
            matricula = materia.matricula
            inscripcion = materia.matricula.inscripcion
            persona = materia.matricula.inscripcion.persona
            profesor = materia.materia.profesor_principal()
            fischasocio = persona.mi_ficha()
            experiencia_vigente = persona.experiencialaboral_set.filter(status=True, fechafin__isnull=True)
            colegio = persona.titulacion_set.filter(status=True, colegio__isnull=False).order_by('-fechaobtencion')
            titulos_docente_phd = None
            titulos_docente_maestria = None
            if profesor:
                titulos_docente_phd = profesor.persona.titulacion_set.filter(status=True, titulo__nivel__nivel__in=[5])
                titulos_docente_maestria = profesor.persona.titulacion_set.filter(status=True, titulo__nivel__nivel__in=[4])
            ws.write(row_num, 0, matricula.nivel.periodo.anio, formatoceldacenter)
            ws.write(row_num, 1, matricula.nivel.periodo.__str__(), formatoceldacenter)
            ws.write(row_num, 2, inscripcion.carrera.__str__(), formatoceldacenter)
            ws.write(row_num, 3, persona.documento(), formatoceldacenter)
            ws.write(row_num, 4, f"{persona.apellido1} {persona.apellido2} {persona.nombres}", formatoceldacenter)
            ws.write(row_num, 5, persona.emailinst, formatoceldacenter)
            ws.write(row_num, 6, persona.telefono, formatoceldacenter)
            ws.write(row_num, 7, persona.sexo.__str__() if persona.sexo else '', formatoceldacenter)
            ws.write(row_num, 8, str(persona.nacimiento), formatoceldacenter)
            ws.write(row_num, 9, persona.edad(), formatoceldacenter)
            if fischasocio:
                ws.write(row_num, 10, fischasocio.grupoeconomico.__str__(), formatoceldacenter)
            else:
                ws.write(row_num, 10, '', formatoceldacenter)
            if colegio:
                colegio_ = colegio.first().colegio
                ws.write(row_num, 11, colegio_.get_tipo_display() if colegio_.tipo else '', formatoceldacenter)
            else:
                ws.write(row_num, 11, '', formatoceldacenter)
            ws.write(row_num, 12, 'SI' if experiencia_vigente.exists() else 'NO', formatoceldacenter)
            ws.write(row_num, 13, inscripcion.nivelmatriculamalla().__str__(), formatoceldacenter)
            ws.write(row_num, 14, materia.materia.__str__(), formatoceldacenter)
            ws.write(row_num, 15, materia.matriculas, formatoceldacenter)
            ws.write(row_num, 16, materia.estado.__str__(), formatoceldacenter)
            if profesor:
                ws.write(row_num, 17, profesor.__str__(), formatoceldacenter)
                ws.write(row_num, 18, profesor.persona.sexo.__str__() if profesor.persona.sexo else '', formatoceldacenter)
            else:
                ws.write(row_num, 17, '', formatoceldacenter)
                ws.write(row_num, 18, '', formatoceldacenter)
            if titulos_docente_phd:
                titulo_phd = ''
                for titulo in titulos_docente_phd:
                    titulo_phd += f"{titulo},"
                ws.write(row_num, 19, titulo_phd, formatoceldacenter)
            else:
                ws.write(row_num, 19, '', formatoceldacenter)
            if titulos_docente_maestria:
                titulo_maestria = ''
                for titulo in titulos_docente_maestria:
                    titulo_maestria += f"{titulo},"
                ws.write(row_num, 20, titulo_maestria, formatoceldacenter)
            else:
                ws.write(row_num, 20, '', formatoceldacenter)
            row_num += 1
            leido += 1

        # wb.save(url_archivo)
        print(url_archivo)
        workbook.close()
    except Exception as ex:
        textoerror = '{} Linea:{}'.format(str(ex), sys.exc_info()[-1].tb_lineno)
        print(textoerror)


mtfaci(2021)
