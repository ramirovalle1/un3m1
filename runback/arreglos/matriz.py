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

import xlsxwriter

from sga.models import *
from sagest.models import *
from sga.funciones import nivel_enletra_malla, paralelo_enletra_nivel, ingreso_total_hogar_rangos

periododescarga=2021

with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/estudiantes2021.xlsx') as workbook:
    ws = workbook.add_worksheet(f"Hoja1")
    coordinacion = None
    carrera = None

    nombbre = u"Estudiantes"

    # response['Content-Disposition'] = 'attachment; filename=' + nombbre + ' 2021 -' + random.randint(1, 10000).__str__() + '.xls'
    columns = [
        (u"CODIGO_IES", 6000),
        (u"CODIGO_CARRERA", 6000),
        (u"CIUDAD_CARRERA", 6000),
        (u"TIPO_IDENTIFICACION", 6000),
        (u"IDENTIFICACION", 6000),
        (u"PRIMER_APELLIDO", 6000),
        (u"SEGUNDO_APELLIDO", 6000),
        (u"NOMBRES", 6000),
        (u"SEXO", 6000),
        (u"FECHA_NACIMIENTO", 6000),
        (u"PAIS_ORIGEN", 6000),
        (u"DISCAPACIDAD", 6000),
        (u"PORCENTAJE_DISCAPACIDAD", 6000),
        (u"NUMERO_CONADIS", 6000),
        (u"ETNIA", 6000),
        (u"NACIONALIDAD", 6000),
        (u"DIRECCION", 6000),
        (u"EMAIL_PERSONAL", 6000),
        (u"EMAIL_INSTITUCIONAL", 6000),
        (u"FECHA_INICIO_PRIMER_NIVEL", 6000),
        (u"FECHA_INGRESO_CONVALIDACION", 6000),
        (u"PAIS_RESIDENCIA", 6000),
        (u"PROVINCIA_RESIDENCIA", 6000),
        (u"CANTON_RESIDENCIA", 6000),
        (u"CELULAR", 6000),
        (u"NIVEL_FORMACION_PADRE", 6000),
        (u"NIVEL_FORMACION_MADRE", 6000),
        (u"CANTIDAD_MIEMBROS_HOGAR", 6000),
        (u"TIPO_COLEGIO", 6000),
        (u"POLITICA_CUOTA", 6000),
        (u"CARRERA", 6000),
        (u"FACULTAD", 6000)
    ]
    row_num = 0
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0])
        ws.set_column(col_num, col_num, columns[col_num][1])
    cursor = connection.cursor()
    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                      "sga_asignatura asi, sga_inscripcion i, sga_periodo p where mat.estado_matricula in (2,3) and mat.status=true and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=p.id and p.anio=%s  " \
                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                      "sga_materia mate, sga_asignatura asi, sga_periodo p where mat.estado_matricula in (2,3) and mat.status=true and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=p.id and p.anio=%s   group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero)" % (
                      periododescarga, periododescarga)
    cursor.execute(listaestudiante)
    results = cursor.fetchall()
    respuestas = []
    for per in results:
        respuestas.append(per[0])
    listainscriciones = Inscripcion.objects.filter(
        id__in=Matricula.objects.values_list('inscripcion__id', flat=False).filter(status=True,
                                                                                   estado_matricula__in=[2, 3],
                                                                                   nivel__periodo__anio=periododescarga
                                                                                   ).exclude(
            retiromatricula__isnull=False
            ).exclude(pk__in=respuestas)).distinct()
    if coordinacion:
        listainscriciones = listainscriciones.filter(carrera__coordinacion=coordinacion)
    if carrera:
        listainscriciones = listainscriciones.filter(carrera=carrera)
    row_num = 1
    for r in listainscriciones:
        print("Matriz 1 %s" % row_num)
        tipoidentificacion = 'CEDULA' if r.persona.cedula else 'PASAPORTE'
        nidentificacion = r.persona.cedula if r.persona.cedula else r.persona.pasaporte
        tipodiscapacidad = 'NINGUNA'
        carnetdiscapacidad = ''
        porcientodiscapacidad = ''
        nacionalidad = 'NO APLICA'
        raza = 'NO REGISTRA'
        politicacuota = 'NINGUNA'
        if r.persona.perfilinscripcion_set.filter(status=True).exists():
            pinscripcion = r.persona.perfilinscripcion_set.filter(status=True)[0]
            if pinscripcion.tienediscapacidad:
                if pinscripcion.tipodiscapacidad_id in [5, 1, 4, 8, 9, 7]:
                    tipodiscapacidad = u'%s' % pinscripcion.tipodiscapacidad
                    carnetdiscapacidad = pinscripcion.carnetdiscapacidad if pinscripcion.carnetdiscapacidad else ''
                    porcientodiscapacidad = pinscripcion.porcientodiscapacidad if pinscripcion.tienediscapacidad else 0
                    politicacuota = 'DISCAPACIDAD'
            if pinscripcion.raza:
                raza = pinscripcion.raza.nombre
                if pinscripcion.raza.id == 1:
                    nacionalidad = u"%s" % pinscripcion.nacionalidadindigena
                    politicacuota = 'PUEBLOS Y NACIONALIDADES'

        formacionpadre = ''
        formacionmadre = ''
        cantidad = 0
        if r.persona.personadatosfamiliares_set.filter(status=True).exists():
            if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1).exists():
                formacionpadre = r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[
                    0].niveltitulacion.nombrecaces if \
                r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion else ''
            if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2).exists():
                formacionmadre = r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[
                    0].niveltitulacion.nombrecaces if \
                r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion else ''
            cantidad = r.persona.personadatosfamiliares_set.filter(status=True).count()
        codigocarrera = ''
        espre = False
        fecha = r.fechainicioprimernivel.strftime("%d/%m/%Y") if r.fechainicioprimernivel else ''
        if r.coordinacion:
            if r.coordinacion.id == 9:
                espre = True
                fecha = r.matricula_set.filter(nivel__periodo__anio=periododescarga).order_by('id')[
                    0].fecha.strftime("%d/%m/%Y") if r.matricula_set.filter(
                    nivel__periodo__anio=periododescarga) else ''
        if espre:
            codigocarrera = '00098'
        else:
            codigocarrera = r.mi_malla().codigo if r.mi_malla() else ''

        if r.matricula_set.filter(nivel__periodo__anio=periododescarga):
            matricula = r.matricula_set.filter(nivel__periodo__anio=periododescarga).order_by('id')[0]
            if matricula.matriculagruposocioeconomico_set.filter(status=True).exists():
                mat_gruposocioecono = matricula.matriculagruposocioeconomico_set.filter(status=True)[0]
                if mat_gruposocioecono.gruposocioeconomico.id in [4, 5]:
                    politicacuota = 'SOCIECONOMICA'

        tipocolegio = 'NO REGISTRA'
        if r.unidadeducativa:
            if r.unidadeducativa.tipocolegio:
                tipocolegio = r.unidadeducativa.tipocolegio.nombre.upper()
        ciudad_carrera = "MILAGRO"
        ws.write(row_num, 0, '1024')
        ws.write(row_num, 1, codigocarrera)
        ws.write(row_num, 2, ciudad_carrera)
        ws.write(row_num, 3, tipoidentificacion if tipoidentificacion else '')
        ws.write(row_num, 4, nidentificacion if nidentificacion else '')
        ws.write(row_num, 5, r.persona.apellido1 if r.persona.apellido1 else '')
        ws.write(row_num, 6, r.persona.apellido2 if r.persona.apellido2 else '')
        ws.write(row_num, 7, r.persona.nombres if r.persona.nombres else '')
        ws.write(row_num, 8, r.persona.sexo.nombre if r.persona.sexo else '')
        ws.write(row_num, 9, r.persona.nacimiento.strftime("%d/%m/%Y") if r.persona.nacimiento else '')
        ws.write(row_num, 10, r.persona.paisnacimiento.nombre if r.persona.paisnacimiento else '')
        ws.write(row_num, 11, tipodiscapacidad if tipodiscapacidad else 'NINGUNA')
        ws.write(row_num, 12, porcientodiscapacidad if porcientodiscapacidad else 0)
        ws.write(row_num, 13, carnetdiscapacidad if carnetdiscapacidad else '')
        ws.write(row_num, 14, raza)
        ws.write(row_num, 15, nacionalidad)
        ws.write(row_num, 16, r.persona.direccion if r.persona.direccion2 else '')
        ws.write(row_num, 17, r.persona.email if r.persona.email else '')
        ws.write(row_num, 18, r.persona.emailinst if r.persona.emailinst else '')
        ws.write(row_num, 19, fecha)
        ws.write(row_num, 20, r.fechainicioconvalidacion.strftime("%d/%m/%Y") if r.fechainicioconvalidacion else '')
        ws.write(row_num, 21, r.persona.pais.nombre if r.persona.pais else '')
        ws.write(row_num, 22, r.persona.provincia.nombre if r.persona.provincia else '')
        ws.write(row_num, 23, r.persona.canton.nombre if r.persona.canton else '')
        ws.write(row_num, 24, r.persona.telefono if r.persona.telefono else '')
        ws.write(row_num, 25, formacionpadre if formacionpadre else '')
        # ws.write(row_num, 26, 'NINGUNO', font_style2)
        ws.write(row_num, 26, formacionmadre if formacionmadre else '')
        # ws.write(row_num, 28, 'NINGUNO', font_style2)
        ws.write(row_num, 27, cantidad if cantidad else 0)
        ws.write(row_num, 28, tipocolegio)
        ws.write(row_num, 29, politicacuota)
        ws.write(row_num, 30, r.carrera.nombre_completo() if r.carrera else '')
        ws.write(row_num, 31, r.coordinacion.nombre if r.coordinacion else '')
        row_num += 1

with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/estudiantesprimer2021.xlsx') as workbook:
    ws = workbook.add_worksheet(f"Hoja1")
    coordinacion = None
    carrera = None

    nombbre = u"Estudiantes"

    columns = [
        (u"CODIGO_IES", 6000),
        (u"CODIGO_CARRERA", 6000),
        (u"CIUDAD_CARRERA", 6000),
        (u"TIPO_IDENTIFICACION", 6000),
        (u"IDENTIFICACION", 6000),
        (u"PRIMER_APELLIDO", 6000),
        (u"SEGUNDO_APELLIDO", 6000),
        (u"NOMBRES", 6000),
        (u"SEXO", 6000),
        (u"FECHA_NACIMIENTO", 6000),
        (u"PAIS_ORIGEN", 6000),
        (u"DISCAPACIDAD", 6000),
        (u"PORCENTAJE_DISCAPACIDAD", 6000),
        (u"NUMERO_CONADIS", 6000),
        (u"ETNIA", 6000),
        (u"NACIONALIDAD", 6000),
        (u"DIRECCION", 6000),
        (u"EMAIL_PERSONAL", 6000),
        (u"EMAIL_INSTITUCIONAL", 6000),
        (u"FECHA_INICIO_PRIMER_NIVEL", 6000),
        (u"FECHA_INGRESO_CONVALIDACION", 6000),
        (u"PAIS_RESIDENCIA", 6000),
        (u"PROVINCIA_RESIDENCIA", 6000),
        (u"CANTON_RESIDENCIA", 6000),
        (u"CELULAR", 6000),
        (u"NIVEL_FORMACION_PADRE", 6000),
        (u"NIVEL_FORMACION_MADRE", 6000),
        (u"CANTIDAD_MIEMBROS_HOGAR", 6000),
        (u"TIPO_COLEGIO", 6000),
        (u"POLITICA_CUOTA", 6000),
        (u"CARRERA", 6000)
    ]
    row_num = 0
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0])
        ws.set_column(col_num, col_num, columns[col_num][1])
    listainscriciones = Inscripcion.objects.filter(status=True, fechainicioprimernivel__year=periododescarga).exclude(coordinacion__id__in=[6,7,8,9]).order_by('persona').distinct()

    row_num = 1
    for r in listainscriciones:
        print("Matriz 2 %s" % row_num)
        tipoidentificacion = 'CEDULA' if r.persona.cedula else 'PASAPORTE'
        nidentificacion = r.persona.cedula if r.persona.cedula else r.persona.pasaporte
        tipodiscapacidad = 'NINGUNA'
        carnetdiscapacidad = ''
        porcientodiscapacidad = ''
        nacionalidad = 'NO REGISTRA'
        raza = 'NO REGISTRA'
        politicacuota = 'NINGUNA'
        if r.persona.perfilinscripcion_set.filter(status=True).exists():
            pinscripcion = r.persona.perfilinscripcion_set.filter(status=True)[0]
            if pinscripcion.tienediscapacidad:
                if pinscripcion.tipodiscapacidad_id in [5,1,4,8,9,7]:
                    tipodiscapacidad = u'%s' % pinscripcion.tipodiscapacidad
                    carnetdiscapacidad = pinscripcion.carnetdiscapacidad if pinscripcion.carnetdiscapacidad else ''
                    porcientodiscapacidad = pinscripcion.porcientodiscapacidad if pinscripcion.tienediscapacidad else 0
                    politicacuota = 'DISCAPACIDAD'
            if pinscripcion.raza:
                raza = pinscripcion.raza.nombre
                if pinscripcion.raza.id == 1:
                    nacionalidad = u"%s" % pinscripcion.nacionalidadindigena
                    politicacuota = 'PUEBLOS Y NACIONALIDADES'
        formacionpadre = ''
        formacionmadre = ''
        cantidad = 0
        if r.persona.personadatosfamiliares_set.filter(status=True).exists():
            if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1).exists():
                formacionpadre = r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion.nombrecaces if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion else ''
            if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2).exists():
                formacionmadre = r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion.nombrecaces if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion else ''
            cantidad = r.persona.personadatosfamiliares_set.filter(status=True).count()
        codigocarrera = ''
        espre = False
        if r.coordinacion:
            if r.coordinacion.id == 9:
                espre = True
        if espre:
            codigocarrera = '00098'
        else:
            codigocarrera = r.mi_malla().codigo if r.mi_malla() else ''

        if r.matricula_set.filter(nivel__periodo__anio=periododescarga):
            matricula= r.matricula_set.filter(nivel__periodo__anio=periododescarga).order_by('id')[0]
            if matricula.matriculagruposocioeconomico_set.filter(status=True).exists():
                mat_gruposocioecono=matricula.matriculagruposocioeconomico_set.filter(status=True)[0]
                if mat_gruposocioecono.gruposocioeconomico.id in [4,5]:
                    politicacuota = 'SOCIOECONÓMICO'
        ciudad_carrera = "MILAGRO"
        ws.write(row_num, 0, '1024')
        ws.write(row_num, 1, codigocarrera)
        ws.write(row_num, 2, ciudad_carrera)
        ws.write(row_num, 3, tipoidentificacion if tipoidentificacion else '')
        ws.write(row_num, 4, nidentificacion if nidentificacion else '')
        ws.write(row_num, 5, r.persona.apellido1 if r.persona.apellido1 else '')
        ws.write(row_num, 6, r.persona.apellido2 if r.persona.apellido2 else '')
        ws.write(row_num, 7, r.persona.nombres if r.persona.nombres else '')
        ws.write(row_num, 8, r.persona.sexo.nombre if r.persona.sexo else '')
        ws.write(row_num, 9, r.persona.nacimiento.strftime("%d/%m/%Y") if r.persona.nacimiento else '')
        ws.write(row_num, 10, r.persona.paisnacimiento.nombre if r.persona.paisnacimiento else '')
        ws.write(row_num, 11, tipodiscapacidad if tipodiscapacidad else 'NINGUNA')
        ws.write(row_num, 12, porcientodiscapacidad if porcientodiscapacidad else 0)
        ws.write(row_num, 13, carnetdiscapacidad if carnetdiscapacidad else '')
        ws.write(row_num, 14, raza)
        ws.write(row_num, 15, nacionalidad)
        ws.write(row_num, 16, r.persona.direccion if r.persona.direccion2 else '')
        ws.write(row_num, 17, r.persona.email if r.persona.email else '')
        ws.write(row_num, 18, r.persona.emailinst if r.persona.emailinst else '')
        ws.write(row_num, 19, r.fechainicioprimernivel.strftime("%d/%m/%Y") if r.fechainicioprimernivel else '')
        ws.write(row_num, 20, r.fechainicioconvalidacion.strftime("%d/%m/%Y") if r.fechainicioconvalidacion else '')
        ws.write(row_num, 21, r.persona.pais.nombre if r.persona.pais else '')
        ws.write(row_num, 22, r.persona.provincia.nombre if r.persona.provincia else '')
        ws.write(row_num, 23, r.persona.canton.nombre if r.persona.canton else '')
        ws.write(row_num, 24, r.persona.telefono if r.persona.telefono else '')
        ws.write(row_num, 25, formacionpadre if formacionpadre else 'NINGUNO')
        ws.write(row_num, 26, formacionmadre if formacionmadre else 'NINGUNO')
        ws.write(row_num, 27, cantidad if cantidad else 0)
        ws.write(row_num, 28, 'NO REGISTRA')
        ws.write(row_num, 29, politicacuota)
        ws.write(row_num, 30, r.carrera.nombre_completo() if r.carrera else '')
        row_num += 1


with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/estudiantes2021mayosep.xlsx') as workbook:
    from socioecon.models import FichaSocioeconomicaINEC
    ws = workbook.add_worksheet(f"Hoja1")
    periodo = Periodo.objects.get(pk=113)
    nomperiodo = u'%s' % periodo
    columns = [
        (u"CODIGO_IES", 6000),
        (u"CODIGO_CARRERA", 6000),
        (u"CIUDAD_CARRERA", 6000),
        (u"TIPO_IDENTIFICACION", 6000),
        (u"IDENTIFICACION", 6000),
        (u"TOTAL_CREDITOS_APROBADOS", 6000),
        (u"CREDITOS_APROBADOS", 6000),
        (u"TIPO_MATRICULA", 6000),
        (u"NIVEL_ACADEMICO", 6000),
        (u"PARALELO", 6000),
        (u"DURACION_PERIODO_ACADEMICO", 6000),
        (u"NUM_MATERIAS_SEGUNDA_MATRICULA", 6000),
        (u"NUM_MATERIAS_TERCERA_MATRICULA", 6000),
        (u"PERDIDA_GRATUIDAD", 6000),
        (u"PENSION_DIFERENCIADA", 6000),
        (u"PLAN_CONTINGENCIA", 6000),
        (u"INGRESO_TOTAL_HOGAR", 6000),
        (u"ORIGEN_RECURSOS_ESTUDIOS", 6000),
        (u"TERMINO_PERIODO", 6000),
        (u"TOTAL_HORAS_APROBADAS", 6000),
        (u"HORAS_APROBADAS_PERIODO", 6000),
        (u"MONTO_AYUDA_ECONOMICA", 6000),
        (u"MONTO_CREDITO_EDUCATIVO", 6000),
        (u"ESTADO", 6000),
        (u"CARRERA", 8000)
    ]
    row_num = 0
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0])
        ws.set_column(col_num, col_num, columns[col_num][1])
    cursor = connection.cursor()
    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                      "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                      "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and ma.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (
                      periodo.id, periodo.id)
    cursor.execute(listaestudiante)
    results = cursor.fetchall()
    respuestas = []
    for per in results:
        respuestas.append(per[0])
    matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2, 3], status=True).exclude(
        pk__in=respuestas).exclude(retiromatricula__isnull=False)
    row_num = 1
    duracion = 0
    print(matriculados)
    resta = periodo.fin - periodo.inicio
    wek, dias = divmod(resta.days, 7)
    for mat in matriculados:
        print("Matriz 3 %s" % row_num)
        espre = False
        if mat.inscripcion.coordinacion:
            if mat.inscripcion.coordinacion.id == 9:
                espre = True
        if espre:
            codigocarrera = '00098'
        else:
            codigocarrera = mat.inscripcion.mi_malla().codigo if mat.inscripcion.mi_malla() else ''
        tipoidentificacion = 'CEDULA' if mat.inscripcion.persona.cedula else 'PASAPORTE'
        nidentificacion = mat.inscripcion.persona.cedula if mat.inscripcion.persona.cedula else mat.inscripcion.persona.pasaporte
        if mat.inscripcion.coordinacion.id == 9:
            paralelo = 'NO APLICA'
            nivel = 'NIVELACION'
        else:
            paralelo = nivel_enletra_malla(mat.nivelmalla.orden)
            nivel = paralelo_enletra_nivel(mat.nivelmalla.orden)
        numsegundamat = mat.materiaasignada_set.filter(status=True, matriculas=2).count()
        numterceramat = mat.materiaasignada_set.filter(status=True, matriculas=3).count()
        total_ingreso = sum(
            [x.ingresomensual for x in mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True)])
        nombre_ingreso = ingreso_total_hogar_rangos(total_ingreso)
        total_horasmat = mat.total_horas_matricula()
        tipomatricula = ''
        if mat.tipomatricula:
            tipomatricula = mat.tipomatricula.nombre
            if mat.tipomatricula.id == 1:
                tipomatricula = 'ORDINARIA'
            if mat.tipomatricula.id == 4:
                tipomatricula = 'ESPECIAL'

        ciudad_carrera = "MILAGRO"
        estado = ""
        terminado_per = ""
        if mat.cantidad_materias_aprobadas(periodo) > 0:
            estado = "APROBADO"
            terminado_per = "SI"
        else:
            estado = "NO APROBADO"
            terminado_per = "SI"
        if RetiroMatricula.objects.filter(status=True, matricula=mat).exists():
            estado = "RETIRADO"
            terminado_per = "NO"
        if FichaSocioeconomicaINEC.objects.values('id').filter(status=True, persona=mat.inscripcion.persona).exists():
            ficha = FichaSocioeconomicaINEC.objects.filter(status=True, persona=mat.inscripcion.persona).order_by(
                'id').last()
            origen_recursos = u"%s" % ficha.personacubregasto if ficha.personacubregasto else "NO REGISTRA"
        ws.write(row_num, 0, '1024')
        ws.write(row_num, 1, codigocarrera)
        ws.write(row_num, 2, ciudad_carrera)
        ws.write(row_num, 3, tipoidentificacion)
        ws.write(row_num, 4, nidentificacion)
        ws.write(row_num, 5, mat.inscripcion.total_creditos())
        ws.write(row_num, 6, mat.total_creditos_matricula())
        ws.write(row_num, 7, tipomatricula)
        ws.write(row_num, 8, nivel)
        ws.write(row_num, 9, paralelo)
        ws.write(row_num, 10, u"%s" % (wek))
        ws.write(row_num, 11, numsegundamat)
        ws.write(row_num, 12, numterceramat)
        ws.write(row_num, 13, 'SI' if mat.inscripcion.gratuidad else 'NO')
        ws.write(row_num, 14, 'NO')
        ws.write(row_num, 15, 'NO')
        ws.write(row_num, 16, nombre_ingreso)
        ws.write(row_num, 17, origen_recursos)
        ws.write(row_num, 18, u"%s" % (terminado_per))
        ws.write(row_num, 19, mat.inscripcion.total_horas())
        ws.write(row_num, 20, total_horasmat)
        ws.write(row_num, 21, '0')
        ws.write(row_num, 22, '0')
        ws.write(row_num, 23, estado)
        ws.write(row_num, 24, mat.inscripcion.carrera.nombre_completo())
        row_num += 1

with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/estudiantes2021novmarzo.xlsx') as workbook:
    from socioecon.models import FichaSocioeconomicaINEC
    ws = workbook.add_worksheet(f"Hoja1")
    periodo = Periodo.objects.get(pk=119)
    nomperiodo = u'%s' % periodo
    columns = [
        (u"CODIGO_IES", 6000),
        (u"CODIGO_CARRERA", 6000),
        (u"CIUDAD_CARRERA", 6000),
        (u"TIPO_IDENTIFICACION", 6000),
        (u"IDENTIFICACION", 6000),
        (u"TOTAL_CREDITOS_APROBADOS", 6000),
        (u"CREDITOS_APROBADOS", 6000),
        (u"TIPO_MATRICULA", 6000),
        (u"NIVEL_ACADEMICO", 6000),
        (u"PARALELO", 6000),
        (u"DURACION_PERIODO_ACADEMICO", 6000),
        (u"NUM_MATERIAS_SEGUNDA_MATRICULA", 6000),
        (u"NUM_MATERIAS_TERCERA_MATRICULA", 6000),
        (u"PERDIDA_GRATUIDAD", 6000),
        (u"PENSION_DIFERENCIADA", 6000),
        (u"PLAN_CONTINGENCIA", 6000),
        (u"INGRESO_TOTAL_HOGAR", 6000),
        (u"ORIGEN_RECURSOS_ESTUDIOS", 6000),
        (u"TERMINO_PERIODO", 6000),
        (u"TOTAL_HORAS_APROBADAS", 6000),
        (u"HORAS_APROBADAS_PERIODO", 6000),
        (u"MONTO_AYUDA_ECONOMICA", 6000),
        (u"MONTO_CREDITO_EDUCATIVO", 6000),
        (u"ESTADO", 6000),
        (u"CARRERA", 8000)
    ]
    row_num = 0
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0])
        ws.set_column(col_num, col_num, columns[col_num][1])
    cursor = connection.cursor()
    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                      "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                      "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and ma.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (
                      periodo.id, periodo.id)
    cursor.execute(listaestudiante)
    results = cursor.fetchall()
    respuestas = []
    for per in results:
        respuestas.append(per[0])
    matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2, 3], status=True).exclude(
        pk__in=respuestas).exclude(retiromatricula__isnull=False)
    row_num = 1
    duracion = 0
    print(matriculados)
    resta = periodo.fin - periodo.inicio
    wek, dias = divmod(resta.days, 7)
    for mat in matriculados:
        print("Matriz 4 %s" % row_num)
        espre = False
        if mat.inscripcion.coordinacion:
            if mat.inscripcion.coordinacion.id == 9:
                espre = True
        if espre:
            codigocarrera = '00098'
        else:
            codigocarrera = mat.inscripcion.mi_malla().codigo if mat.inscripcion.mi_malla() else ''
        tipoidentificacion = 'CEDULA' if mat.inscripcion.persona.cedula else 'PASAPORTE'
        nidentificacion = mat.inscripcion.persona.cedula if mat.inscripcion.persona.cedula else mat.inscripcion.persona.pasaporte
        if mat.inscripcion.coordinacion.id == 9:
            paralelo = 'NO APLICA'
            nivel = 'NIVELACION'
        else:
            paralelo = nivel_enletra_malla(mat.nivelmalla.orden)
            nivel = paralelo_enletra_nivel(mat.nivelmalla.orden)
        numsegundamat = mat.materiaasignada_set.filter(status=True, matriculas=2).count()
        numterceramat = mat.materiaasignada_set.filter(status=True, matriculas=3).count()
        total_ingreso = sum(
            [x.ingresomensual for x in mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True)])
        nombre_ingreso = ingreso_total_hogar_rangos(total_ingreso)
        total_horasmat = mat.total_horas_matricula()
        tipomatricula = ''
        if mat.tipomatricula:
            tipomatricula = mat.tipomatricula.nombre
            if mat.tipomatricula.id == 1:
                tipomatricula = 'ORDINARIA'
            if mat.tipomatricula.id == 4:
                tipomatricula = 'ESPECIAL'

        ciudad_carrera = "MILAGRO"
        estado = ""
        terminado_per = ""
        if mat.cantidad_materias_aprobadas(periodo) > 0:
            estado = "APROBADO"
            terminado_per = "SI"
        else:
            estado = "NO APROBADO"
            terminado_per = "SI"
        if RetiroMatricula.objects.filter(status=True, matricula=mat).exists():
            estado = "RETIRADO"
            terminado_per = "NO"
        if FichaSocioeconomicaINEC.objects.values('id').filter(status=True, persona=mat.inscripcion.persona).exists():
            ficha = FichaSocioeconomicaINEC.objects.filter(status=True, persona=mat.inscripcion.persona).order_by(
                'id').last()
            origen_recursos = u"%s" % ficha.personacubregasto if ficha.personacubregasto else "NO REGISTRA"
        ws.write(row_num, 0, '1024')
        ws.write(row_num, 1, codigocarrera)
        ws.write(row_num, 2, ciudad_carrera)
        ws.write(row_num, 3, tipoidentificacion)
        ws.write(row_num, 4, nidentificacion)
        ws.write(row_num, 5, mat.inscripcion.total_creditos())
        ws.write(row_num, 6, mat.total_creditos_matricula())
        ws.write(row_num, 7, tipomatricula)
        ws.write(row_num, 8, nivel)
        ws.write(row_num, 9, paralelo)
        ws.write(row_num, 10, u"%s" % (wek))
        ws.write(row_num, 11, numsegundamat)
        ws.write(row_num, 12, numterceramat)
        ws.write(row_num, 13, 'SI' if mat.inscripcion.gratuidad else 'NO')
        ws.write(row_num, 14, 'NO')
        ws.write(row_num, 15, 'NO')
        ws.write(row_num, 16, nombre_ingreso)
        ws.write(row_num, 17, origen_recursos)
        ws.write(row_num, 18, u"%s" % (terminado_per))
        ws.write(row_num, 19, mat.inscripcion.total_horas())
        ws.write(row_num, 20, total_horasmat)
        ws.write(row_num, 21, '0')
        ws.write(row_num, 22, '0')
        ws.write(row_num, 23, estado)
        ws.write(row_num, 24, mat.inscripcion.carrera.nombre_completo())
        row_num += 1

with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/estudiantes2021admijuniosept1s.xlsx') as workbook:
    from socioecon.models import FichaSocioeconomicaINEC
    ws = workbook.add_worksheet(f"Hoja1")
    periodo = Periodo.objects.get(pk=123)
    nomperiodo = u'%s' % periodo
    columns = [
        (u"CODIGO_IES", 6000),
        (u"CODIGO_CARRERA", 6000),
        (u"CIUDAD_CARRERA", 6000),
        (u"TIPO_IDENTIFICACION", 6000),
        (u"IDENTIFICACION", 6000),
        (u"TOTAL_CREDITOS_APROBADOS", 6000),
        (u"CREDITOS_APROBADOS", 6000),
        (u"TIPO_MATRICULA", 6000),
        (u"PARALELO", 6000),
        (u"NIVEL_ACADEMICO", 6000),
        (u"DURACION_PERIODO_ACADEMICO", 6000),
        (u"NUM_MATERIAS_SEGUNDA_MATRICULA", 6000),
        (u"NUM_MATERIAS_TERCERA_MATRICULA", 6000),
        (u"PERDIDA_GRATUIDAD", 6000),
        (u"PENSION_DIFERENCIADA", 6000),
        (u"PLAN_CONTINGENCIA", 6000),
        (u"INGRESO_TOTAL_HOGAR", 6000),
        (u"ORIGEN_RECURSOS_ESTUDIOS", 6000),
        (u"TERMINO_PERIODO", 6000),
        (u"TOTAL_HORAS_APROBADAS", 6000),
        (u"HORAS_APROBADAS_PERIODO", 6000),
        (u"MONTO_AYUDA_ECONOMICA", 6000),
        (u"MONTO_CREDITO_EDUCATIVO", 6000),
        (u"ESTADO", 6000),
        (u"CARRERA", 8000)
    ]
    row_num = 0
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0])
        ws.set_column(col_num, col_num, columns[col_num][1])
    cursor = connection.cursor()
    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                      "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                      "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and ma.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (
                      periodo.id, periodo.id)
    cursor.execute(listaestudiante)
    results = cursor.fetchall()
    respuestas = []
    for per in results:
        respuestas.append(per[0])
    matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2, 3], status=True).exclude(
        pk__in=respuestas).exclude(retiromatricula__isnull=False)
    row_num = 1
    duracion = 0
    print(matriculados)
    resta = periodo.fin - periodo.inicio
    wek, dias = divmod(resta.days, 7)
    for mat in matriculados:
        print("Matriz 5 %s" % row_num)
        espre = False
        if mat.inscripcion.coordinacion:
            if mat.inscripcion.coordinacion.id == 9:
                espre = True
        if espre:
            codigocarrera = '00098'
        else:
            codigocarrera = mat.inscripcion.mi_malla().codigo if mat.inscripcion.mi_malla() else ''
        tipoidentificacion = 'CEDULA' if mat.inscripcion.persona.cedula else 'PASAPORTE'
        nidentificacion = mat.inscripcion.persona.cedula if mat.inscripcion.persona.cedula else mat.inscripcion.persona.pasaporte
        if mat.inscripcion.coordinacion.id == 9:
            paralelo = 'NO APLICA'
            nivel = 'NIVELACION'
        else:
            paralelo = nivel_enletra_malla(mat.nivelmalla.orden)
            nivel = paralelo_enletra_nivel(mat.nivelmalla.orden)
        numsegundamat = mat.materiaasignada_set.filter(status=True, matriculas=2).count()
        numterceramat = mat.materiaasignada_set.filter(status=True, matriculas=3).count()
        total_ingreso = sum(
            [x.ingresomensual for x in mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True)])
        nombre_ingreso = ingreso_total_hogar_rangos(total_ingreso)
        total_horasmat = mat.total_horas_matricula()
        tipomatricula = ''
        if mat.tipomatricula:
            tipomatricula = mat.tipomatricula.nombre
            if mat.tipomatricula.id == 1:
                tipomatricula = 'ORDINARIA'
            if mat.tipomatricula.id == 4:
                tipomatricula = 'ESPECIAL'

        ciudad_carrera = "MILAGRO"
        estado = ""
        terminado_per = ""
        if mat.cantidad_materias_aprobadas(periodo) > 0:
            estado = "APROBADO"
            terminado_per = "SI"
        else:
            estado = "NO APROBADO"
            terminado_per = "SI"
        if RetiroMatricula.objects.filter(status=True, matricula=mat).exists():
            estado = "RETIRADO"
            terminado_per = "NO"
        if FichaSocioeconomicaINEC.objects.values('id').filter(status=True, persona=mat.inscripcion.persona).exists():
            ficha = FichaSocioeconomicaINEC.objects.filter(status=True, persona=mat.inscripcion.persona).order_by(
                'id').last()
            origen_recursos = u"%s" % ficha.personacubregasto if ficha.personacubregasto else "NO REGISTRA"
        ws.write(row_num, 0, '1024')
        ws.write(row_num, 1, codigocarrera)
        ws.write(row_num, 2, ciudad_carrera)
        ws.write(row_num, 3, tipoidentificacion)
        ws.write(row_num, 4, nidentificacion)
        ws.write(row_num, 5, mat.inscripcion.total_creditos())
        ws.write(row_num, 6, mat.total_creditos_matricula())
        ws.write(row_num, 7, tipomatricula)
        ws.write(row_num, 8, paralelo)
        ws.write(row_num, 9, nivel)
        ws.write(row_num, 10, u"%s" % (wek))
        ws.write(row_num, 11, numsegundamat)
        ws.write(row_num, 12, numterceramat)
        ws.write(row_num, 13, 'SI' if mat.inscripcion.gratuidad else 'NO')
        ws.write(row_num, 14, 'NO')
        ws.write(row_num, 15, 'NO')
        ws.write(row_num, 16, nombre_ingreso)
        ws.write(row_num, 17, origen_recursos)
        ws.write(row_num, 18, u"%s" % (terminado_per))
        ws.write(row_num, 19, mat.inscripcion.total_horas())
        ws.write(row_num, 20, total_horasmat)
        ws.write(row_num, 21, '0')
        ws.write(row_num, 22, '0')
        ws.write(row_num, 23, estado)
        ws.write(row_num, 24, mat.inscripcion.carrera.nombre_completo())
        row_num += 1

with xlsxwriter.Workbook(f'{SITE_STORAGE}/media/estudiantes2021adminovmarzo2s.xlsx') as workbook:
    from socioecon.models import FichaSocioeconomicaINEC
    ws = workbook.add_worksheet(f"Hoja1")
    periodo = Periodo.objects.get(pk=136)
    nomperiodo = u'%s' % periodo
    columns = [
        (u"CODIGO_IES", 6000),
        (u"CODIGO_CARRERA", 6000),
        (u"CIUDAD_CARRERA", 6000),
        (u"TIPO_IDENTIFICACION", 6000),
        (u"IDENTIFICACION", 6000),
        (u"TOTAL_CREDITOS_APROBADOS", 6000),
        (u"CREDITOS_APROBADOS", 6000),
        (u"TIPO_MATRICULA", 6000),
        (u"PARALELO", 6000),
        (u"NIVEL_ACADEMICO", 6000),
        (u"DURACION_PERIODO_ACADEMICO", 6000),
        (u"NUM_MATERIAS_SEGUNDA_MATRICULA", 6000),
        (u"NUM_MATERIAS_TERCERA_MATRICULA", 6000),
        (u"PERDIDA_GRATUIDAD", 6000),
        (u"PENSION_DIFERENCIADA", 6000),
        (u"PLAN_CONTINGENCIA", 6000),
        (u"INGRESO_TOTAL_HOGAR", 6000),
        (u"ORIGEN_RECURSOS_ESTUDIOS", 6000),
        (u"TERMINO_PERIODO", 6000),
        (u"TOTAL_HORAS_APROBADAS", 6000),
        (u"HORAS_APROBADAS_PERIODO", 6000),
        (u"MONTO_AYUDA_ECONOMICA", 6000),
        (u"MONTO_CREDITO_EDUCATIVO", 6000),
        (u"ESTADO", 6000),
        (u"GRADUADO", 8000)
    ]
    row_num = 0
    for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num][0])
        ws.set_column(col_num, col_num, columns[col_num][1])
    cursor = connection.cursor()
    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                      "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                      "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and ma.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (
                      periodo.id, periodo.id)
    cursor.execute(listaestudiante)
    results = cursor.fetchall()
    respuestas = []
    for per in results:
        respuestas.append(per[0])
    matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2, 3], status=True).exclude(
        pk__in=respuestas).exclude(retiromatricula__isnull=False)
    row_num = 1
    duracion = 0
    print(matriculados)
    resta = periodo.fin - periodo.inicio
    wek, dias = divmod(resta.days, 7)
    for mat in matriculados:
        print("Matriz 6 %s" % row_num)
        espre = False
        if mat.inscripcion.coordinacion:
            if mat.inscripcion.coordinacion.id == 9:
                espre = True
        if espre:
            codigocarrera = '00098'
        else:
            codigocarrera = mat.inscripcion.mi_malla().codigo if mat.inscripcion.mi_malla() else ''
        tipoidentificacion = 'CEDULA' if mat.inscripcion.persona.cedula else 'PASAPORTE'
        nidentificacion = mat.inscripcion.persona.cedula if mat.inscripcion.persona.cedula else mat.inscripcion.persona.pasaporte
        if mat.inscripcion.coordinacion.id == 9:
            paralelo = 'NO APLICA'
            nivel = 'NIVELACION'
        else:
            paralelo = nivel_enletra_malla(mat.nivelmalla.orden)
            nivel = paralelo_enletra_nivel(mat.nivelmalla.orden)
        numsegundamat = mat.materiaasignada_set.filter(status=True, matriculas=2).count()
        numterceramat = mat.materiaasignada_set.filter(status=True, matriculas=3).count()
        total_ingreso = sum(
            [x.ingresomensual for x in mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True)])
        nombre_ingreso = ingreso_total_hogar_rangos(total_ingreso)
        total_horasmat = mat.total_horas_matricula()
        tipomatricula = ''
        if mat.tipomatricula:
            tipomatricula = mat.tipomatricula.nombre
            if mat.tipomatricula.id == 1:
                tipomatricula = 'ORDINARIA'
            if mat.tipomatricula.id == 4:
                tipomatricula = 'ESPECIAL'

        ciudad_carrera = "MILAGRO"
        estado = ""
        terminado_per = ""
        if mat.cantidad_materias_aprobadas(periodo) > 0:
            estado = "APROBADO"
            terminado_per = "SI"
        else:
            estado = "NO APROBADO"
            terminado_per = "SI"
        if RetiroMatricula.objects.filter(status=True, matricula=mat).exists():
            estado = "RETIRADO"
            terminado_per = "NO"
        if FichaSocioeconomicaINEC.objects.values('id').filter(status=True, persona=mat.inscripcion.persona).exists():
            ficha = FichaSocioeconomicaINEC.objects.filter(status=True, persona=mat.inscripcion.persona).order_by(
                'id').last()
            origen_recursos = u"%s" % ficha.personacubregasto if ficha.personacubregasto else "NO REGISTRA"
        ws.write(row_num, 0, '1024')
        ws.write(row_num, 1, codigocarrera)
        ws.write(row_num, 2, ciudad_carrera)
        ws.write(row_num, 3, tipoidentificacion)
        ws.write(row_num, 4, nidentificacion)
        ws.write(row_num, 5, mat.inscripcion.total_creditos())
        ws.write(row_num, 6, mat.total_creditos_matricula())
        ws.write(row_num, 7, tipomatricula)
        ws.write(row_num, 8, paralelo)
        ws.write(row_num, 9, nivel)
        ws.write(row_num, 10, u"%s" % (wek))
        ws.write(row_num, 11, numsegundamat)
        ws.write(row_num, 12, numterceramat)
        ws.write(row_num, 13, 'SI' if mat.inscripcion.gratuidad else 'NO')
        ws.write(row_num, 14, 'NO')
        ws.write(row_num, 15, 'NO')
        ws.write(row_num, 16, nombre_ingreso)
        ws.write(row_num, 17, origen_recursos)
        ws.write(row_num, 18, u"%s" % (terminado_per))
        ws.write(row_num, 19, mat.inscripcion.total_horas())
        ws.write(row_num, 20, total_horasmat)
        ws.write(row_num, 21, '0')
        ws.write(row_num, 22, '0')
        ws.write(row_num, 23, estado)
        ws.write(row_num, 24, mat.inscripcion.carrera.nombre_completo())
        row_num += 1
