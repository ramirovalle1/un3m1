# -*- coding: latin-1 -*-
import random
import io
import os
import sys
from datetime import timedelta

import xlrd
import xlsxwriter
import xlwt
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction, connection, connections
from django.db.models import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *
from sga.excelbackground import reporte_matriculados_background, reporte_matrizestudiantes_anio_background, \
    reporte_matriculaperiodoacademico_background, reporte_matrizpracticaspreprofesionales_anio_background, \
    reporte_matrizestudiantesxfechaprimernivel_background, reporte_matrizmatrizgraduados_anio_background, \
    reporte_matrizprofesoresdistributivo_background, reporte_estudiantes_matricula_posgrado, \
    reporte_estudiantes_posgrado, reporte_graduados_posgrado
from decorators import secure_module, last_access
from sagest.models import PersonaContratos, datetime, DistributivoPersona, DenominacionPuesto
from settings import ARCHIVO_TIPO_GENERAL
from sga.commonviews import adduserdata, obtener_reporte, traerNotificaciones
from sga.forms import ImportarArchivoXLSForm, PeriodoMutipleForm
from sga.funciones import nivel_enletra_malla, paralelo_enletra_nivel, generar_nombre, log, ingreso_total_hogar_rangos
from sga.models import DescargaArchivo, Periodo, ProfesorDistributivoHoras, Titulacion, Graduado, \
    Matricula, Inscripcion, PracticasPreprofesionalesInscripcion, BecaAsignacion, Archivo, PeriodoMatrizAdmision, \
    MatrizAdmision, Carrera, CedulaCarrera, Coordinacion, RetiroMatricula, Materia, MateriaAsignada, Profesor, \
    NivelEscalafonDocente, ProfesorTipo, Titulo, Notificacion, Persona, NivelTitulacion, AsignaturaMalla, Malla, \
    ItinerarioMallaEspecilidad, RecordAcademico, InscripcionMalla, HistoricoRecordAcademico, TemaTitulacionPosgradoMatricula
from socioecon.models import FichaSocioeconomicaINEC
from settings import MEDIA_ROOT, MEDIA_URL
from posgrado.models import InscripcionCohorte, CohorteMaestria
from typing import Any, Hashable, Iterable, Optional
from collections import Counter
from django.db.models import Sum
from sga.funciones import null_to_numeric

def rango_anios():
    if DescargaArchivo.objects.exclude(anio=0).exists():
        inicio = DescargaArchivo.objects.exclude(anio=0).order_by('anio')[0].anio
        fin = DescargaArchivo.objects.exclude(anio=0).order_by('-anio')[0].anio
        return range(fin, inicio - 1, -1)
    return None


def rango_anios_periodo():
    if Periodo.objects.exclude(anio__isnull=True).exists():
        ano = Periodo.objects.values_list('anio', flat=False).exclude(anio__isnull=True).order_by('-anio').distinct()
        return ano
    return None

def rango_anios_primernivel_pre():
    if Inscripcion.objects.filter(status=True, coordinacion__excluir=False).exists():
        anomn = Inscripcion.objects.filter(status=True, coordinacion__excluir=False, fechainicioprimernivel__isnull=False).order_by('fechainicioprimernivel')[0]
        anomy = Inscripcion.objects.filter(status=True, coordinacion__excluir=False, fechainicioprimernivel__isnull=False).order_by('-fechainicioprimernivel')[0]
        return range(anomn.fechainicioprimernivel.year, anomy.fechainicioprimernivel.year + 1)
    return None

def retirado(maestrante):
    return True if RetiroMatricula.objects.filter(status=True, matricula=maestrante).exists() else False

def graduado2(maestrante):
    return True if Graduado.objects.filter(status=True, inscripcion=maestrante.inscripcion).exists() else False

def graduadofecha(maestrante):
    fecha = 'NO REGISTRA'
    if Graduado.objects.filter(status=True, inscripcion=maestrante.inscripcion).exists():
        gra = Graduado.objects.filter(status=True, inscripcion=maestrante.inscripcion).first()
        fecha = gra.fechagraduado
    return fecha

def malla_completa(maestrante):
    estado = False
    malla = Malla.objects.get(status=True, pk=InscripcionMalla.objects.get(status=True, inscripcion=maestrante.inscripcion).malla.id)
    asignaturamalla = AsignaturaMalla.objects.filter(status=True, malla=malla, opcional=False).values_list('id', flat=True)

    if InscripcionCohorte.objects.filter(status=True, inscripcion=maestrante.inscripcion).exists():
        inscor = InscripcionCohorte.objects.filter(status=True, inscripcion=maestrante.inscripcion).order_by('-id').first()
        # if inscor.itinerario != 0:
        #     mencion = ItinerarioMallaEspecilidad.objects.get(malla=malla, itinerario=inscor.itinerario, status=True)
        #     canti_malla = malla.asignaturamalla_set.filter(Q(status=True, itinerario_malla_especialidad__id=mencion.id) | Q(itinerario_malla_especialidad__id__isnull=True)).count()
        # else:
        canti_malla = malla.cantidad_materias()
    else:
        canti_malla = malla.cantidad_materias()

    aprobadas = RecordAcademico.objects.filter(status=True, inscripcion=maestrante.inscripcion, aprobada=True, asignaturamalla__id__in=asignaturamalla).count()

    if aprobadas >= int(canti_malla):
        estado = True
    if maestrante.inscripcion.es_graduado():
        estado = True

    return estado

def elemento_mas_comun(lista):
    contador = Counter(lista)
    elemento, repeticiones = contador.most_common(1)[0]
    return elemento

def curso_matriculado(maestrante):
    matricula = Matricula.objects.filter(status=True, inscripcion=maestrante.inscripcion).order_by('-id').first()
    if MateriaAsignada.objects.filter(status=True, matricula=matricula).exists():
        mi_lista = matricula.materiaasignada_set.filter(matricula__status=True, status=True).values_list('materia__paralelo', flat=True)
        return elemento_mas_comun(mi_lista)

def buscar_dicc(it: Iterable[dict], clave: Hashable, valor: Any) -> Optional[dict]:
    for dicc in it:
        if dicc[clave] == valor:
            return dicc
    return None

def total_creditos(inscripcion):
    inscripcionmalla = inscripcion.malla_inscripcion()
    # if inscripcionmalla.malla.tiene_itinerario_malla_especialidad():
    #     return null_to_numeric(AsignaturaMalla.objects.filter(status=True, malla=inscripcionmalla.malla, itinerario__in=[inscripcion.itinerario,0, None]).aggregate(creditos=Sum('creditos'))['creditos'])
    # else:
    return null_to_numeric(AsignaturaMalla.objects.filter(status=True, malla=inscripcionmalla.malla).aggregate(creditos=Sum('creditos'))['creditos'])

def total_horas_ma(inscripcion):
    inscripcionmalla = inscripcion.malla_inscripcion()
    # if inscripcionmalla.malla.tiene_itinerario_malla_especialidad():
    #     return null_to_numeric(AsignaturaMalla.objects.filter(status=True, malla=inscripcionmalla.malla, itinerario__in=[inscripcion.itinerario,0, None]).aggregate(horas=Sum('horas'))['horas'])
    # else:
    return null_to_numeric(AsignaturaMalla.objects.filter(status=True, malla=inscripcionmalla.malla).aggregate(horas=Sum('horas'))['horas'])

def total_creditos_aprobadas(inscripcion):
    return null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignaturamalla__isnull=False, noaplica=False, aprobada=True).aggregate(creditos=Sum('creditos'))['creditos'])

def total_horas_aprobadas(inscripcion):
    return null_to_numeric(inscripcion.recordacademico_set.filter(valida=True, status=True, asignaturamalla__isnull=False, noaplica=False, aprobada=True).aggregate(horas=Sum('horas'))['horas'])

def num_segunda_mat(matricula):
    try:
        cantidad = 0
        if MateriaAsignada.objects.filter(status=True, matriculas=2, matricula=matricula).exists():
            cantidad = MateriaAsignada.objects.filter(status=True, matriculas=2, matricula=matricula).distinct().count()
        return cantidad
    except Exception as ex:
        pass

def num_tercera_mat(matricula):
    try:
        cantidad = 0
        if MateriaAsignada.objects.filter(status=True, matriculas=3, matricula=matricula).exists():
            cantidad = MateriaAsignada.objects.filter(status=True, matriculas=3, matricula=matricula).distinct().count()
        return cantidad
    except Exception as ex:
        pass

def periodo_matricula(inscripcion):
    try:
        periodo = 'NO REGISTRA'
        if MateriaAsignada.objects.filter(status=True, matricula__inscripcion=inscripcion, matricula__inscripcion__status=True).exists():
            mate = MateriaAsignada.objects.filter(status=True, matricula__inscripcion=inscripcion, matricula__inscripcion__status=True).first()
            return mate.matricula.nivel.periodo
        return periodo
    except Exception as ex:
        pass

def mecanismo_titulacion(inscripcion):
    try:
        tema = ''
        if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula__inscripcion=inscripcion, mecanismotitulacionposgrado__status=True).exists():
            tema = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula__inscripcion=inscripcion, mecanismotitulacionposgrado__status=True).order_by('-id').first()
            return tema.mecanismotitulacionposgrado.nombre
    except Exception as ex:
        pass

def es_extranjero(persona):
    try:
        estado = 'NO'
        if persona.paisnacimiento:
            if persona.paisnacimiento.id != 1:
                estado = 'SI'
        return estado
    except Exception as ex:
        pass

def inicio_primer_modulo(matricula):
    try:
        fecha = ''
        if MateriaAsignada.objects.filter(status=True, matricula=matricula).exists():
            ma = MateriaAsignada.objects.filter(status=True, matricula=matricula).first()
            fecha = ma.materia.inicio
        return fecha
    except Exception as ex:
        pass

def fin_ultimo_modulo(matricula):
    try:
        fecha = ''
        inscripcionmalla = matricula.inscripcion.malla_inscripcion()
        canti = AsignaturaMalla.objects.filter(status=True, malla=inscripcionmalla.malla).count()

        if MateriaAsignada.objects.filter(status=True, matricula=matricula, materia__cerrado=True).exists():
            cantima = MateriaAsignada.objects.filter(status=True, matricula=matricula, materia__cerrado=True).count()
            if cantima >= canti:
                ma = MateriaAsignada.objects.filter(status=True, matricula=matricula, materia__cerrado=True).order_by('-id').first()
                fecha = ma.materia.inicio
        return fecha
    except Exception as ex:
        pass

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['coordinacion'] = Coordinacion.objects.filter(id__in=[1, 2, 3, 4, 5, 9, 7])
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'matrizestudiantes_anio':
            try:
                lista = []
                for anio in rango_anios_periodo():
                    lista.append([anio[0]])
                data['lista'] = lista
                data['action'] = 'matrizestudiantes_anio'
                template = get_template("descargaarchivo/consultaxano.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        elif action == 'buscacarrera':
            try:
                coordinacion = Coordinacion.objects.get(id=int(request.POST['id_facultad']))
                lista = []
                for carr in coordinacion.carreras():
                    lista.append([carr.id, carr.nombre_completo()])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al buscar carreras."})

        if action == 'estudiantesfechaprimernivel':
            try:
                lista = []
                for anio in rango_anios_primernivel_pre():
                    lista.append([anio])
                data['lista'] = lista
                data['action'] = 'reporteestudiantesxfechaprimernivel'
                template = get_template("descargaarchivo/consultaxano.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizprofesoresdistributivo_periodo':
            try:
                lista = []
                for periodo in Periodo.objects.filter(status=True, visible=True).exclude(tipo_id__in=[3]).order_by('-fin'):
                    lista.append([periodo.id, str(periodo)])
                data['lista'] = lista
                data['action'] = 'matrizprofesoresdistributivo_periodo'
                template = get_template("descargaarchivo/consultaxperiodo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar el periodo academico'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizestudiantes_periodo':
            try:
                lista = []
                for periodo in Periodo.objects.filter(status=True, visible=True).exclude(tipo_id__in=[3]).order_by('-fin'):
                    lista.append([periodo.id, str(periodo)])
                data['lista'] = lista
                data['listacoordinaciones'] = Coordinacion.objects.filter(status=True)
                data['action'] = 'matrizestudiantes_periodo'
                data['eCoordinaciones'] = Coordinacion.objects.filter(status=True)
                template = get_template("descargaarchivo/consultaxperiodo.html")
                json_content = template.render(data)
                return JsonResponse(
                    {"result": "ok", 'html': json_content, 'title': u'Seleccionar el periodo academico'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizgraduados_anio':
            try:
                lista = []
                # fi = Graduado.objects.filter(status=True, estadograduado=True, fechagraduado__isnull=False).order_by('fechagraduado')[0]
                # ff = Graduado.objects.filter(status=True, estadograduado=True, fechagraduado__isnull=False).order_by('-fechagraduado')[0]
                # for anio in range(int(fi.fechagraduado.year), int(ff.fechagraduado.year)+1):
                #     lista.append([anio])
                for anio in rango_anios_primernivel_pre():
                    lista.append([anio])
                data['lista'] = lista
                data['action'] = 'matrizgraduados_anio'
                template = get_template("descargaarchivo/consultaxano.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizpracticaspreprofesionales_anio':
            try:
                lista = []
                fi = PracticasPreprofesionalesInscripcion.objects.filter(status=True, fechadesde__isnull=False).order_by('fechadesde')[0]
                ff = PracticasPreprofesionalesInscripcion.objects.filter(status=True, fechadesde__isnull=False).order_by('-fechadesde')[0]
                for anio in range(int(fi.fechahasta.year), int(ff.fechadesde.year) + 1):
                    lista.append([anio])
                data['lista'] = lista
                data['action'] = 'matrizpracticaspreprofesionales_anio'
                template = get_template("descargaarchivo/consultaxano.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizprofesorescontrato_anio':
            try:
                lista = []
                for anio in rango_anios_periodo():
                    lista.append([anio[0]])
                data['lista'] = lista
                data['action'] = 'matrizprofesorescontrato_anio'
                template = get_template("descargaarchivo/consultaxano.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matriculadosposgrado_anio':
            try:
                lista = []
                for anio in rango_anios_periodo():
                    lista.append([anio[0]])
                data['lista'] = lista
                data['action'] = 'excelmatriculadosposgrado'
                template = get_template("descargaarchivo/posgradoxanio.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'estudiantesposgrado_anio':
            try:
                lista = []
                for anio in rango_anios_periodo():
                    lista.append([anio[0]])
                data['lista'] = lista
                data['action'] = 'excelestudiantesposgrado'
                template = get_template("descargaarchivo/posgradoxanio.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'periodosposgrado_anio':
            try:
                lista = []
                for anio in rango_anios_periodo():
                    lista.append([anio[0]])
                data['lista'] = lista
                data['action'] = 'excelperiodosposgrado'
                template = get_template("descargaarchivo/posgradoxanio.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'graduadosposgrado_anio':
            try:
                lista = []
                for anio in rango_anios_periodo():
                    lista.append([anio[0]])
                data['lista'] = lista
                data['action'] = 'excelgraduados'
                template = get_template("descargaarchivo/posgradoxanio.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizestudiantesipec_anio':
            try:
                lista = []
                matriculainicio = Matricula.objects.filter(status=True, inscripcion__coordinacion__id=7).order_by('fecha')[0]
                matriculafin = Matricula.objects.filter(status=True, inscripcion__coordinacion__id=7).order_by('-fecha')[0]
                for anio in range(int(matriculainicio.fecha.year), int(matriculafin.fecha.year) + 1):
                    lista.append([anio])
                data['lista'] = lista
                data['action'] = 'matrizestudiantesipec_anio'
                template = get_template("descargaarchivo/consultaxano.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar año'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizestudiantesprimernivel':
            try:
                lista = []
                inicio = Inscripcion.objects.filter(status=True, fechainicioprimernivel__isnull=False).order_by('fechainicioprimernivel')[0].fechainicioprimernivel
                fin = Inscripcion.objects.filter(status=True, fechainicioprimernivel__isnull=False).order_by('-fechainicioprimernivel')[0].fechainicioprimernivel
                data['periodoadmision'] = periodoadmision = PeriodoMatrizAdmision.objects.filter(status=True).order_by('id')
                for anio in range(int(inicio.year), int(fin.year) + 1):
                    lista.append([anio])
                data['lista'] = lista
                data['action'] = 'matrizestudiantesprimernivel'
                template = get_template("descargaarchivo/consultaxrango.html")
                json_content = template.render(data)
                return JsonResponse(
                    {"result": "ok", 'html': json_content, 'title': u'Seleccionar el periodo academico'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizanalisisestudiantes':
            try:
                lista = []
                for periodo in Periodo.objects.filter(status=True, visible=True).exclude(tipo_id__in=[3]).order_by('-fin'):
                    lista.append([periodo.id, str(periodo)])
                data['lista'] = lista
                data['action'] = 'matrizanalisisestudiantes'
                template = get_template("descargaarchivo/consultaxperiodo.html")
                json_content = template.render(data)
                return JsonResponse(
                    {"result": "ok", 'html': json_content, 'title': u'Seleccionar el periodo academico'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        if action == 'matrizanalisisperiodoacademico':
            try:
                lista = []
                for periodo in Periodo.objects.filter(status=True, visible=True).exclude(tipo_id__in=[3]).order_by('-fin'):
                    lista.append([periodo.id, str(periodo)])
                data['lista'] = lista
                data['action'] = 'matrizanalisisperiodoacademico'
                template = get_template("descargaarchivo/consultaxperiodo.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content, 'title': u'Seleccionar el periodo academico'})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar excel."})

        elif action == 'importar':
            mensaje = None
            try:
                form = ImportarArchivoXLSForm(request.POST, request.FILES)
                if form.is_valid():
                    nfile = request.FILES['archivo']
                    nfile._name = generar_nombre("matrizadmision_", nfile._name)
                    archivo = Archivo(nombre='MATRIZ ADMISION',
                                      fecha=datetime.now().date(),
                                      archivo=nfile,
                                      tipo_id=ARCHIVO_TIPO_GENERAL)
                    archivo.save(request)
                    workbook = xlrd.open_workbook(archivo.archivo.file.name)
                    sheet = workbook.sheet_by_index(0)
                    linea = 1
                    for rowx in range(sheet.nrows):
                        if linea >= 2:
                            cols = sheet.row_values(rowx)
                            if PeriodoMatrizAdmision.objects.filter(nombre=cols[6].strip()).exists():
                                periodomatrizadmision = PeriodoMatrizAdmision.objects.filter(nombre=cols[6].strip())[0]
                            else:
                                periodomatrizadmision = PeriodoMatrizAdmision(nombre=cols[6].strip())
                                periodomatrizadmision.save(request)
                            if cols[12].strip() == 'APROBADO':
                                estado = 0
                            else:
                                if cols[12].strip() == 'REPROBADO':
                                    estado = 1
                                else:
                                    if cols[12].strip() == 'NO MATRICULADO':
                                        estado = 2
                                    else:
                                        estado = 3
                            carreraadmision = Carrera.objects.get(pk=int(cols[8]))
                            if not MatrizAdmision.objects.filter(periodomatrizadmision=periodomatrizadmision, cedula=cols[1].strip(), carreraadmision=carreraadmision).exists():
                                matrizadmision = MatrizAdmision(periodomatrizadmision=periodomatrizadmision,
                                                                tipodocumento=cols[0].strip(),
                                                                cedula=cols[1].strip(),
                                                                apellidos=cols[2].strip(),
                                                                nombres=cols[3].strip(),
                                                                carreraadmision=carreraadmision,
                                                                estado=estado)
                            else:
                                matrizadmision = MatrizAdmision.objects.get(periodomatrizadmision=periodomatrizadmision, cedula=cols[1].strip(), carreraadmision=carreraadmision)
                                matrizadmision.apellidos = cols[2].strip()
                                matrizadmision.nombres = cols[3].strip()
                                matrizadmision.estado = estado
                            matrizadmision.save(request)
                        linea += 1
                    log(u'importo matriz admision: %s' % matrizadmision, request, "add")
                    return JsonResponse({'result': 'ok'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. linea %s" % linea})

        elif action == 'resumen_matricula_carrera':
            try:
                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('Hoja1')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=resumen' + random.randint(1, 10000).__str__() + '.xls'
                columns = [
                    (u"CARRERA", 6000),
                    (u"CANTIDAD", 6000),
                ]
                row_num = 0
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 1
                for carrera in Carrera.objects.filter(pk__in=Materia.objects.values_list('asignaturamalla__malla__carrera').filter(nivel__periodo__id__in=[112, 113]).distinct()).order_by('-nombre').distinct():
                    cant = 0
                    cant = Matricula.objects.values_list('inscripcion__persona__id').filter(status=True,
                                                                                            inscripcion__status=True,
                                                                                            estado_matricula__in=[2, 3],
                                                                                            retiradomatricula=False,
                                                                                            nivel__periodo__id__in=request.POST['periodo'],
                                                                                            inscripcion__carrera=carrera).order_by('inscripcion__persona__id').distinct('inscripcion__persona__id').count()
                    ws.write(row_num, 0, u'%s' % carrera, font_style2)
                    ws.write(row_num, 1, u'%s' % cant, font_style2)
                    print(u"%s" % carrera)
                    row_num += 1
                wb.save(response)
                return response
            except Exception as ex:
                pass

        elif action == 'selectperiodo':
            try:
                if 'id' in request.POST:
                    lista = []
                    idperiodos = Matricula.objects.filter(status=True, inscripcion__carrera__coordinacion__id=7, inscripcion__carrera__id=int(request.POST['id'])).values_list('nivel__periodo__id', flat=True).order_by('nivel__periodo__id').distinct()
                    periodos = Periodo.objects.filter(status=True, id__in=idperiodos).exclude(nombre__icontains='TITULA').order_by('-id')

                    for periodo in periodos:
                        lista.append([periodo.id, u'%s %s: %s a %s' % (periodo.tipo, periodo.nombre, periodo.inicio.strftime('%d-%m-%Y'), periodo.fin.strftime('%d-%m-%Y'))])
                    return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'descarga':
                try:
                    descargaarchivo = DescargaArchivo.objects.get(pk=request.GET['id'])
                    cursor = connection.cursor()
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=archivo.xls'
                    wb = xlwt.Workbook()
                    ws = wb.add_sheet('Sheetname')
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='dd/mm/yyyy')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    cabecera = descargaarchivo.cabecera.split(',')
                    c = 0
                    estilo = []
                    for cabeceras in cabecera:
                        ca = cabeceras.split('|')
                        ws.col(c).width = 4000
                        ws.write(0, c, ca[0])
                        if ca[1] == '0':
                            estilo.append(font_style2)
                        else:
                            estilo.append(style1)
                        c += 1
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    sql = descargaarchivo.select
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    f = 1
                    for per in results:
                        c1 = 0
                        while c1 < c:
                            ws.write(f, c1, per[c1], estilo[c1])
                            c1 += 1
                        f += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            if action == 'matrizestudiantes_anio':
                try:
                    if data['permiteWebPush']:
                        name_document = 'estudiantes_por_anio'
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo=name_document, destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matrizestudiantes_anio_background(request=request, data=data, notiid=noti.pk, name_document=name_document).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            if 'anio' in request.GET:
                                __author__ = 'Unemi'
                                directory = os.path.join(MEDIA_ROOT, 'reportes', 'matrices','estudiantes.xlsx')

                                output = io.BytesIO()
                                workbook = xlsxwriter.Workbook(directory)
                                ws = workbook.add_worksheet('estudiantes')

                                font_style2 = workbook.add_format(
                                    {'border': 1, 'text_wrap': True, 'align': 'center', 'font_size': 5, 'valign': 'vcenter',
                                     'font_name': 'Century Gothic'})
                                font_style = workbook.add_format(
                                    {'border': 1, 'text_wrap': True,'bold': 1, 'align': 'center', 'font_size': 5, 'valign': 'vcenter',
                                     'font_name': 'Century Gothic'})


                                coordinacion = None
                                carrera = None
                                if 'idcoor' in request.GET:
                                    idcoor = request.GET['idcoor']
                                    if int(idcoor) > 0:
                                        coordinacion = Coordinacion.objects.get(id=int(idcoor))
                                        nombbre = u"Estudiantes %s" % coordinacion.nombre
                                    else:
                                        nombbre = u"Estudiantes"
                                else:
                                    nombbre = u"Estudiantes"

                                if 'idcarr' in request.GET:
                                    idcarr = request.GET['idcarr']
                                    if idcarr != '':
                                        if int(idcarr) > 0:
                                            carrera = Carrera.objects.get(id=int(idcarr))
                                            nombbre += u" Carrera %s" % carrera.nombre_completo()
                                ws.write(0, 0,u"CODIGO_IES",font_style)
                                ws.write(0, 1,u"CODIGO_CARRERA",font_style)
                                ws.write(0, 2,u"CIUDAD_CARRERA",font_style)
                                ws.write(0, 3,u"TIPO_IDENTIFICACION",font_style)
                                ws.write(0, 4,u"IDENTIFICACION",font_style)
                                ws.write(0, 5,u"PRIMER_APELLIDO",font_style)
                                ws.write(0, 6,u"SEGUNDO_APELLIDO",font_style)
                                ws.write(0, 7,u"NOMBRES",font_style)
                                ws.write(0, 8,u"SEXO",font_style)
                                ws.write(0, 9,u"FECHA_NACIMIENTO",font_style)
                                ws.write(0, 10,u"PAIS_ORIGEN",font_style)
                                ws.write(0, 11,u"DISCAPACIDAD",font_style)
                                ws.write(0, 12,u"PORCENTAJE_DISCAPACIDAD",font_style)
                                ws.write(0, 13,u"NUMERO_CONADIS",font_style)
                                ws.write(0, 14,u"ETNIA",font_style)
                                ws.write(0, 15,u"NACIONALIDAD",font_style)
                                ws.write(0, 16,u"DIRECCION",font_style)
                                ws.write(0, 17,u"EMAIL_PERSONAL",font_style)
                                ws.write(0, 18,u"EMAIL_INSTITUCIONAL",font_style)
                                ws.write(0, 19,u"FECHA_INICIO_PRIMER_NIVEL",font_style)
                                ws.write(0, 20,u"FECHA_INGRESO_CONVALIDACION",font_style)
                                ws.write(0, 21,u"PAIS_RESIDENCIA",font_style)
                                ws.write(0, 22,u"PROVINCIA_RESIDENCIA",font_style)
                                ws.write(0, 23,u"CANTON_RESIDENCIA",font_style)
                                ws.write(0, 24,u"CELULAR",font_style)
                                ws.write(0, 25,u"NIVEL_FORMACION_PADRE",font_style)
                                ws.write(0, 26,u"NIVEL_FORMACION_MADRE",font_style)
                                ws.write(0, 27,u"CANTIDAD_MIEMBROS_HOGAR",font_style)
                                ws.write(0, 28,u"TIPO_COLEGIO",font_style)
                                ws.write(0, 29,u"POLITICA_CUOTA",font_style)
                                ws.write(0, 30,u"CARRERA",font_style)
                                ws.write(0, 31,u"FACULTAD",font_style)

                                cursor = connection.cursor()
                                listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                                                  "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                                                  "sga_asignatura asi, sga_inscripcion i, sga_periodo p where mat.estado_matricula in (2,3) and mat.status=true and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                                  "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=p.id and p.anio=%s  " \
                                                  "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                                                  "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                                                  "sga_materia mate, sga_asignatura asi, sga_periodo p where mat.estado_matricula in (2,3) and mat.status=true and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                                  "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=p.id and p.anio=%s  group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero)" % (int(request.GET['anio']), int(request.GET['anio']))
                                cursor.execute(listaestudiante)
                                results = cursor.fetchall()
                                respuestas = []
                                for per in results:
                                    respuestas.append(per[0])
                                listainscriciones = Inscripcion.objects.filter(id__in=Matricula.objects.values_list('inscripcion__id', flat=False).filter(status=True,
                                                                                                                                                          estado_matricula__in=[2, 3],
                                                                                                                                                          nivel__periodo__anio=int(request.GET['anio'])
                                                                                                                                                          ).exclude(retiromatricula__isnull=False
                                                                                                                                                                    ).exclude(pk__in=respuestas)).distinct()
                                if coordinacion:
                                    listainscriciones = listainscriciones.filter(carrera__coordinacion=coordinacion)
                                if carrera:
                                    listainscriciones = listainscriciones.filter(carrera=carrera)
                                row_num = 1
                                for r in listainscriciones:
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
                                            formacionpadre = r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion.nombrecaces if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion else ''
                                        if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2).exists():
                                            formacionmadre = r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion.nombrecaces if r.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion else ''
                                        cantidad = r.persona.personadatosfamiliares_set.filter(status=True).count()
                                    codigocarrera = ''
                                    espre = False
                                    fecha = r.fechainicioprimernivel.strftime("%d/%m/%Y") if r.fechainicioprimernivel else ''
                                    if r.coordinacion:
                                        if r.coordinacion.id == 9:
                                            espre = True
                                            fecha = r.matricula_set.filter(nivel__periodo__anio=int(request.GET['anio'])).order_by('id')[0].fecha.strftime("%d/%m/%Y") if r.matricula_set.filter(nivel__periodo__anio=int(request.GET['anio'])) else ''
                                    if espre:
                                        codigocarrera = '00098'
                                    else:
                                        codigocarrera = r.mi_malla().codigo if r.mi_malla() else ''

                                    if r.matricula_set.filter(nivel__periodo__anio=int(request.GET['anio'])):
                                        matricula = r.matricula_set.filter(nivel__periodo__anio=int(request.GET['anio'])).order_by('id')[0]
                                        if matricula.matriculagruposocioeconomico_set.filter(status=True).exists():
                                            mat_gruposocioecono = matricula.matriculagruposocioeconomico_set.filter(status=True)[0]
                                            if mat_gruposocioecono.gruposocioeconomico.id in [4, 5]:
                                                politicacuota = 'SOCIECONOMICA'

                                    # if BecaAsignacion.objects.filter(status=True, solicitud__inscripcion=r, solicitud__estado=2, solicitud__periodo__anio=int(request.GET['anio']), solicitud__becatipo__id__in=[4,7]).exists():
                                    #     politicacuota = BecaAsignacion.objects.filter(status=True, solicitud__inscripcion=r, solicitud__estado=2, solicitud__periodo__anio=int(request.GET['anio']), solicitud__becatipo__id__in=[4,7])[0]
                                    #     politicacuota = politicacuota.solicitud.becatipo.nombre.upper()
                                    tipocolegio = 'NO REGISTRA'
                                    if r.unidadeducativa:
                                        if r.unidadeducativa.tipocolegio:
                                            tipocolegio = r.unidadeducativa.tipocolegio.nombre.upper()
                                    ciudad_carrera = "MILAGRO"
                                    ws.write(row_num, 0, '1024', font_style2)
                                    ws.write(row_num, 1, codigocarrera, font_style2)
                                    ws.write(row_num, 2, ciudad_carrera, font_style2)
                                    ws.write(row_num, 3, tipoidentificacion if tipoidentificacion else '', font_style2)
                                    ws.write(row_num, 4, nidentificacion if nidentificacion else '', font_style2)
                                    ws.write(row_num, 5, r.persona.apellido1 if r.persona.apellido1 else '', font_style2)
                                    ws.write(row_num, 6, r.persona.apellido2 if r.persona.apellido2 else '', font_style2)
                                    ws.write(row_num, 7, r.persona.nombres if r.persona.nombres else '', font_style2)
                                    ws.write(row_num, 8, r.persona.sexo.nombre if r.persona.sexo else '', font_style2)
                                    ws.write(row_num, 9, r.persona.nacimiento.strftime("%d/%m/%Y") if r.persona.nacimiento else '', font_style2)
                                    ws.write(row_num, 10, r.persona.paisnacimiento.nombre if r.persona.paisnacimiento else '', font_style2)
                                    ws.write(row_num, 11, tipodiscapacidad if tipodiscapacidad else 'NINGUNA', font_style2)
                                    ws.write(row_num, 12, porcientodiscapacidad if porcientodiscapacidad else 0, font_style2)
                                    ws.write(row_num, 13, carnetdiscapacidad if carnetdiscapacidad else '', font_style2)
                                    ws.write(row_num, 14, raza, font_style2)
                                    ws.write(row_num, 15, nacionalidad, font_style2)
                                    ws.write(row_num, 16, r.persona.direccion if r.persona.direccion2 else 'DESCONOCIDO', font_style2)
                                    ws.write(row_num, 17, r.persona.email if r.persona.email else '', font_style2)
                                    ws.write(row_num, 18, r.persona.emailinst if r.persona.emailinst else '', font_style2)
                                    ws.write(row_num, 19, fecha, font_style2)
                                    ws.write(row_num, 20, r.fechainicioconvalidacion.strftime("%d/%m/%Y") if r.fechainicioconvalidacion else '', font_style2)
                                    ws.write(row_num, 21, r.persona.pais.nombre if r.persona.pais else '', font_style2)
                                    ws.write(row_num, 22, r.persona.provincia.nombre if r.persona.provincia else '', font_style2)
                                    ws.write(row_num, 23, r.persona.canton.nombre if r.persona.canton else '', font_style2)
                                    ws.write(row_num, 24, r.persona.telefono if r.persona.telefono else '0000000000', font_style2)
                                    ws.write(row_num, 25, formacionpadre if formacionpadre else 'NINGUNO', font_style2)
                                    # ws.write(row_num, 26, 'NINGUNO', font_style2)
                                    ws.write(row_num, 26, formacionmadre if formacionmadre else 'NINGUNO', font_style2)
                                    # ws.write(row_num, 28, 'NINGUNO', font_style2)
                                    ws.write(row_num, 27, cantidad if cantidad else 0, font_style2)
                                    ws.write(row_num, 28, tipocolegio, font_style2)
                                    ws.write(row_num, 29, politicacuota, font_style2)
                                    ws.write(row_num, 30, r.carrera.nombre_completo() if r.carrera else '', font_style2)
                                    ws.write(row_num, 31, r.coordinacion.nombre if r.coordinacion else '', font_style2)
                                    row_num += 1
                                # wb.save(response)
                                workbook.close()
                                output.seek(0)
                                filename = 'estudiantes' + random.randint(1, 10000).__str__() + '.xlsx'
                                response = HttpResponse(output,
                                                        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                                response['Content-Disposition'] = 'attachment; filename=%s' % filename

                                return response
                        except Exception as ex:
                            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                            pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            if action == 'reporteestudiantesxfechaprimernivel':
                try:
                    if data['permiteWebPush']:
                        name_document = 'estudiantes_fecha_primer_nivel'
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo= name_document, destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matrizestudiantesxfechaprimernivel_background(request=request, data=data, notiid=noti.pk, name_document=name_document).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            if 'anio' in request.GET:
                                __author__ = 'Unemi'
                                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                                font_style = XFStyle()
                                font_style.font.bold = True
                                font_style2 = XFStyle()
                                font_style2.font.bold = False
                                wb = Workbook(encoding='utf-8')
                                ws = wb.add_sheet('exp_xls_post_part')
                                response = HttpResponse(content_type="application/ms-excel")
                                coordinacion = None
                                carrera = None
                                if 'idcoor' in request.GET:
                                    idcoor = request.GET['idcoor']
                                    if int(idcoor) > 0:
                                        coordinacion = Coordinacion.objects.get(id=int(idcoor))
                                        nombbre = u"Estudiantes %s" % coordinacion.nombre
                                    else:
                                        nombbre = u"Estudiantes"
                                else:
                                    nombbre = u"Estudiantes"

                                if 'idcarr' in request.GET:
                                    idcarr = request.GET['idcarr']
                                    if idcarr != '':
                                        if int(idcarr) > 0:
                                            carrera = Carrera.objects.get(id=int(idcarr))
                                            nombbre += u" _ Carrera %s" % carrera.nombre_completo()

                                response['Content-Disposition'] = 'attachment; filename=' + nombbre + ' ' + request.GET[
                                    'anio'] + '-' + random.randint(1, 10000).__str__() + '.xls'
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
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                listainscriciones = Inscripcion.objects.filter(status=True, fechainicioprimernivel__year=int(request.GET['anio'])).exclude(coordinacion__id__in=[6, 7, 8, 9]).order_by('persona').distinct()
                                if coordinacion:
                                    listainscriciones = listainscriciones.filter(carrera__coordinacion=coordinacion)

                                if carrera:
                                    listainscriciones = listainscriciones.filter(carrera=carrera)

                                row_num = 1
                                for r in listainscriciones:
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

                                    if r.matricula_set.filter(nivel__periodo__anio=int(request.GET['anio'])):
                                        matricula = r.matricula_set.filter(nivel__periodo__anio=int(request.GET['anio'])).order_by('id')[0]
                                        if matricula.matriculagruposocioeconomico_set.filter(status=True).exists():
                                            mat_gruposocioecono = matricula.matriculagruposocioeconomico_set.filter(status=True)[0]
                                            if mat_gruposocioecono.gruposocioeconomico.id in [4, 5]:
                                                politicacuota = 'SOCIOECONÓMICO'
                                    # politicacuota = 'NINGUNA'
                                    # if BecaAsignacion.objects.filter(status=True, solicitud__inscripcion=r, solicitud__estado=2, solicitud__periodo__anio=int(request.GET['anio']), solicitud__becatipo__id__in=[4, 7]).exists():
                                    #     politicacuota = BecaAsignacion.objects.filter(status=True, solicitud__inscripcion=r, solicitud__estado=2, solicitud__periodo__anio=int(request.GET['anio']), solicitud__becatipo__id__in=[4, 7])[0]
                                    #     politicacuota = politicacuota.solicitud.becatipo.nombre.upper()
                                    ciudad_carrera = "MILAGRO"
                                    ws.write(row_num, 0, '1024', font_style2)
                                    ws.write(row_num, 1, codigocarrera, font_style2)
                                    ws.write(row_num, 2, ciudad_carrera, font_style2)
                                    ws.write(row_num, 3, tipoidentificacion if tipoidentificacion else '', font_style2)
                                    ws.write(row_num, 4, nidentificacion if nidentificacion else '', font_style2)
                                    ws.write(row_num, 5, r.persona.apellido1 if r.persona.apellido1 else '', font_style2)
                                    ws.write(row_num, 6, r.persona.apellido2 if r.persona.apellido2 else '', font_style2)
                                    ws.write(row_num, 7, r.persona.nombres if r.persona.nombres else '', font_style2)
                                    ws.write(row_num, 8, r.persona.sexo.nombre if r.persona.sexo else '', font_style2)
                                    ws.write(row_num, 9, r.persona.nacimiento.strftime("%d/%m/%Y") if r.persona.nacimiento else '', font_style2)
                                    ws.write(row_num, 10, r.persona.paisnacimiento.nombre if r.persona.paisnacimiento else '', font_style2)
                                    ws.write(row_num, 11, tipodiscapacidad if tipodiscapacidad else 'NINGUNA', font_style2)
                                    ws.write(row_num, 12, porcientodiscapacidad if porcientodiscapacidad else 0, font_style2)
                                    ws.write(row_num, 13, carnetdiscapacidad if carnetdiscapacidad else '', font_style2)
                                    ws.write(row_num, 14, raza, font_style2)
                                    ws.write(row_num, 15, nacionalidad, font_style2)
                                    ws.write(row_num, 16, r.persona.direccion if r.persona.direccion2 else '', font_style2)
                                    ws.write(row_num, 17, r.persona.email if r.persona.email else '', font_style2)
                                    ws.write(row_num, 18, r.persona.emailinst if r.persona.emailinst else '', font_style2)
                                    ws.write(row_num, 19, r.fechainicioprimernivel.strftime("%d/%m/%Y") if r.fechainicioprimernivel else '', font_style2)
                                    ws.write(row_num, 20, r.fechainicioconvalidacion.strftime("%d/%m/%Y") if r.fechainicioconvalidacion else '', font_style2)
                                    ws.write(row_num, 21, r.persona.pais.nombre if r.persona.pais else '', font_style2)
                                    ws.write(row_num, 22, r.persona.provincia.nombre if r.persona.provincia else '', font_style2)
                                    ws.write(row_num, 23, r.persona.canton.nombre if r.persona.canton else '', font_style2)
                                    ws.write(row_num, 24, r.persona.telefono if r.persona.telefono else '', font_style2)
                                    ws.write(row_num, 25, formacionpadre if formacionpadre else 'NINGUNO', font_style2)
                                    # ws.write(row_num, 24, 'NINGUNO', font_style2)
                                    ws.write(row_num, 26, formacionmadre if formacionmadre else 'NINGUNO', font_style2)
                                    # ws.write(row_num, 25, 'NINGUNO', font_style2)
                                    ws.write(row_num, 27, cantidad if cantidad else 0, font_style2)
                                    ws.write(row_num, 28, 'NO REGISTRA', font_style2)
                                    ws.write(row_num, 29, politicacuota, font_style2)
                                    ws.write(row_num, 30, r.carrera.nombre_completo() if r.carrera else '', font_style2)
                                    row_num += 1
                                wb.save(response)
                                return response
                        except Exception as ex:
                            pass
                except Exception as ex:
                    pass

            if action == 'matrizestudiantes_periodo':
                try:
                    if data['permiteWebPush']:
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo='Excel Estudiantes - Matrícula Periodo Académico', destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matriculaperiodoacademico_background(request=request, data=data, notiid=noti.pk).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            if 'id' in request.GET:
                                periodo = Periodo.objects.get(pk=int(request.GET['id']))
                                try:
                                    eCoordinacion = Coordinacion.objects.get(pk=int(request.GET.get('idc', '0')))
                                except ObjectDoesNotExist:
                                    eCoordinacion = None
                                __author__ = 'Unemi'
                                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                                font_style = XFStyle()
                                font_style.font.bold = True
                                font_style2 = XFStyle()
                                font_style2.font.bold = False
                                wb = Workbook(encoding='utf-8')
                                ws = wb.add_sheet('exp_xls_post_part')
                                response = HttpResponse(content_type="application/ms-excel")
                                nomperiodo = u'%s' % periodo
                                response['Content-Disposition'] = 'attachment; filename=Estudiantes ' + str(periodo) + ' ' + random.randint(1, 10000).__str__() + '.xls'
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
                                    (u"ESTADO", 6000)
                                ]
                                row_num = 0
                                for col_num in range(len(columns)):
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                cursor = connection.cursor()
                                listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                                                  "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                                                  "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                                  "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                                                  "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                                                  "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                                                  "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and ma.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                                  "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (periodo.id, periodo.id)
                                cursor.execute(listaestudiante)
                                results = cursor.fetchall()
                                respuestas = []
                                for per in results:
                                    respuestas.append(per[0])
                                filtro = Q(nivel__periodo=periodo) & Q(estado_matricula__in=[2, 3]) & Q(status=True)
                                if eCoordinacion:
                                    filtro = filtro & Q(inscripcion__coordinacion=eCoordinacion)
                                matriculados = Matricula.objects.filter(filtro).exclude(pk__in=respuestas).exclude(retiromatricula__isnull=False)
                                # matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2,3], status=True).exclude(pk__in=respuestas).exclude(retiromatricula__isnull=False)[:100]
                                row_num = 1
                                duracion = 0
                                resta = periodo.fin - periodo.inicio
                                wek, dias = divmod(resta.days, 7)
                                for mat in matriculados:
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
                                    total_ingreso = sum([x.ingresomensual for x in mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True)])
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
                                    if RetiroMatricula.objects.values('id').filter(status=True, matricula=mat).exists():
                                        estado = "RETIRADO"
                                        terminado_per = "NO"
                                    if FichaSocioeconomicaINEC.objects.values('id').filter(status=True, persona=mat.inscripcion.persona).exists():
                                        ficha = FichaSocioeconomicaINEC.objects.filter(status=True, persona=mat.inscripcion.persona).order_by('id').last()
                                        origen_recursos = u"%s" % ficha.personacubregasto if ficha.personacubregasto else "NO REGISTRA"

                                    ws.write(row_num, 0, '1024', font_style2)
                                    ws.write(row_num, 1, codigocarrera, font_style2)
                                    ws.write(row_num, 2, ciudad_carrera, font_style2)
                                    ws.write(row_num, 3, tipoidentificacion, font_style2)
                                    ws.write(row_num, 4, nidentificacion, font_style2)
                                    ws.write(row_num, 5, mat.inscripcion.total_creditos(), font_style2)
                                    ws.write(row_num, 6, mat.total_creditos_matricula(), font_style2)
                                    ws.write(row_num, 7, tipomatricula, font_style2)
                                    ws.write(row_num, 8, paralelo, font_style2)
                                    ws.write(row_num, 9, nivel, font_style2)
                                    ws.write(row_num, 10, u"%s" % (wek), font_style2)
                                    ws.write(row_num, 11, numsegundamat, font_style2)
                                    ws.write(row_num, 12, numterceramat, font_style2)
                                    ws.write(row_num, 13, 'SI' if mat.inscripcion.gratuidad else 'NO', font_style2)
                                    ws.write(row_num, 14, 'NO', font_style2)
                                    ws.write(row_num, 15, 'NO', font_style2)
                                    ws.write(row_num, 16, nombre_ingreso, font_style2)
                                    ws.write(row_num, 17, origen_recursos, font_style2)
                                    ws.write(row_num, 18, u"%s" % (terminado_per), font_style2)
                                    ws.write(row_num, 19, mat.inscripcion.total_horas(), font_style2)
                                    ws.write(row_num, 20, total_horasmat, font_style2)
                                    ws.write(row_num, 21, '0', font_style2)
                                    ws.write(row_num, 22, '0', font_style2)
                                    ws.write(row_num, 23, estado, font_style2)
                                    row_num += 1
                                wb.save(response)
                                return response
                        except Exception as ex:
                            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                            pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'matrizfuncionarios':
                try:
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 22, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Funcionarios ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CODIGO_IES", 6000),
                        (u"CODIGO_MATRIZ_EXTENSION", 6000),
                        (u"TIPO_IDENTIFICACION", 6000),
                        (u"IDENTIFICACION", 6000),
                        (u"PRIMER_APELLIDO", 6000),
                        (u"SEGUNDO_APELLIDO", 6000),
                        (u"NOMBRES", 6000),
                        (u"SEXO", 6000),
                        (u"FECHA_NACIMIENTO", 6000),
                        (u"PAIS_ORIGEN", 6000),
                        (u"DISCAPACIDAD", 6000),
                        (u"NUMERO_CONADIS", 6000),
                        (u"PORCENTAJE_DISCAPACIDAD", 6000),
                        (u"ETNIA", 6000),
                        (u"NACIONALIDAD", 6000),
                        (u"DIRECCION", 6000),
                        (u"EMAIL_PERSONAL", 6000),
                        (u"EMAIL_INSTITUCIONAL", 6000),
                        (u"NUMERO_DOCUMENTO", 6000),
                        (u"RELACION_IES", 6000),
                        (u"FECHA_INICIO", 6000),
                        (u"FECHA_FIN", 6000),
                        (u"INGRESO_POR_CONCURSO", 6000),
                        (u"REMUNERACION", 6000),
                        (u"TIPO_FUNCIONARIO", 6000),
                        (u"CARGO", 6000),
                        (u"TIPO_DOCENTE_LOSEP", 6000),
                        (u"CATEGORIA_DOCENTE_LOSEP", 6000),
                        (u"UNIDAD_ACADEMICA", 6000),
                        (u"PUESTO_JERARQUICO_SUPERIOR", 6000),
                        (u"HORAS_LABORABLES_SEMANA", 6000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    sql = "select distinct '1024' as CODIGO_IES, per.telefonoextension as CODIGO_MATRIZ_EXTENSION, (case substr(per.cedula,1,2) when 'VS' then 'PASAPORTE' else 'CEDULA' end) as TIPO_IDENTIFICACION, " \
                          "(case substr(per.cedula,1,2) when 'VS' then per.pasaporte else per.cedula end) as INDENTIFICACION, " \
                          "per.apellido1 as PRIMER_APELLIDO, per.apellido2 as SEGUNDO_APELLIDO, per.nombres as NOMBRES, sex.nombre as SEXO, " \
                          "COALESCE((CAST(to_char(per.nacimiento,'DD/MM/YYYY') as text) ),'') as FECHA_NACIMIENTO, COALESCE((pai.nombre),'') as PAIS_ORIGEN, " \
                          "COALESCE((select dis.nombre from sga_perfilinscripcion pin,sga_discapacidad dis where pin.persona_id=per.id and pin.tipodiscapacidad_id=dis.id),'NINGUNA') as DISCAPACIDAD, " \
                          "(select pin.carnetdiscapacidad from sga_perfilinscripcion pin where pin.persona_id=per.id) as NUMERO_CONADIS, " \
                          "COALESCE((select pin.porcientodiscapacidad from sga_perfilinscripcion pin,sga_discapacidad dis where pin.persona_id=per.id and pin.tipodiscapacidad_id=dis.id),'0') as PORCENTAJE_DISCAPACIDAD, " \
                          "COALESCE((select r.nombre from sga_perfilinscripcion pin, sga_raza r where pin.persona_id=per.id and pin.raza_id=r.id),'0') as ENIA, " \
                          "per.nacionalidad as NACIONALIDAD, per.direccion as DIRECCION, " \
                          "per.email as EMAIL_PERSONAL, per.emailinst as EMAIL_INSTITUCIONAL, '' as NUMERO_DOCUMENTO, '' as RELACION_IES, " \
                          "'' as FECHA_INICIO, '' as FECHA_FIN, '' as INGRESO_POR_CONCURSO, dper.rmupuesto as REMUNERACION, '' as TIPO_FUNCIONARIO, " \
                          "dpu.descripcion as CARGO, '' as TIPO_DOCENTE_LOSEP, " \
                          "'' as CATEGORIA_DOCENTE_LOSEP, '' as UNIDAD_ACADEMICA, '' as PUESTO_JERARQUICO_SUPERIOR, '' as HORAS_LABORABLES_SEMANA " \
                          "from sagest_distributivopersona dper " \
                          "inner join sga_persona per on per.id=dper.persona_id " \
                          "inner join sagest_regimenlaboral reg on reg.id=dper.regimenlaboral_id " \
                          "inner join sagest_estadopuesto est on est.id=dper.estadopuesto_id and est.id=1 " \
                          "inner join sga_sexo sex on sex.id=per.sexo_id " \
                          "inner join sga_pais pai on pai.id=per.paisnacimiento_id " \
                          "inner join sagest_denominacionpuesto dpu on dpu.id=dper.denominacionpuesto_id"
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 1
                    for r in results:
                        ws.write(row_num, 0, r[0] if r[0] else '', font_style2)
                        ws.write(row_num, 1, r[1] if r[1] else '', font_style2)
                        ws.write(row_num, 2, r[2] if r[2] else '', font_style2)
                        ws.write(row_num, 3, r[3] if r[3] else '', font_style2)
                        ws.write(row_num, 4, r[4] if r[4] else '', font_style2)
                        ws.write(row_num, 5, r[5] if r[5] else '', font_style2)
                        ws.write(row_num, 6, r[6] if r[6] else '', font_style2)
                        ws.write(row_num, 7, r[7] if r[7] else '', font_style2)
                        ws.write(row_num, 8, r[8] if r[8] else '', font_style2)
                        ws.write(row_num, 9, r[9] if r[9] else '', font_style2)
                        ws.write(row_num, 10, r[10] if r[10] else '', font_style2)
                        ws.write(row_num, 11, r[11] if r[11] else '', font_style2)
                        ws.write(row_num, 12, r[12] if r[12] else '', font_style2)
                        ws.write(row_num, 13, r[13] if r[13] else '', font_style2)
                        ws.write(row_num, 14, r[14] if r[14] else '', font_style2)
                        ws.write(row_num, 15, r[15] if r[15] else '', font_style2)
                        ws.write(row_num, 16, r[16] if r[16] else '', font_style2)
                        ws.write(row_num, 17, r[17] if r[17] else '', font_style2)
                        ws.write(row_num, 18, r[18] if r[18] else '', font_style2)
                        ws.write(row_num, 19, r[19] if r[19] else '', font_style2)
                        ws.write(row_num, 20, r[20] if r[20] else '', font_style2)
                        ws.write(row_num, 21, r[21] if r[21] else '', font_style2)
                        ws.write(row_num, 22, r[10] if r[22] else '', font_style2)
                        ws.write(row_num, 23, r[11] if r[23] else '', font_style2)
                        ws.write(row_num, 24, r[12] if r[24] else '', font_style2)
                        ws.write(row_num, 25, r[13] if r[25] else '', font_style2)
                        ws.write(row_num, 26, r[14] if r[26] else '', font_style2)
                        ws.write(row_num, 27, r[15] if r[27] else '', font_style2)
                        ws.write(row_num, 28, r[16] if r[28] else '', font_style2)
                        ws.write(row_num, 29, r[17] if r[29] else '', font_style2)
                        ws.write(row_num, 30, r[18] if r[30] else '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'matrizprofesoresdistributivo_periodo':
                try:
                    if data['permiteWebPush']:
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo='Excel - Distribucion Horas Periodo Academico', destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matrizprofesoresdistributivo_background(request=request, data=data, notiid=noti.pk).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            if 'id' in request.GET:
                                periodo = Periodo.objects.get(pk=int(request.GET['id']))
                                __author__ = 'Unemi'
                                title = easyxf(
                                    'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                                font_style = XFStyle()
                                font_style.font.bold = True
                                font_style2 = XFStyle()
                                font_style2.font.bold = False
                                wb = Workbook(encoding='utf-8')
                                ws = wb.add_sheet('exp_xls_post_part')
                                # ws.write_merge(0, 0, 0, 15, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                                response = HttpResponse(content_type="application/ms-excel")
                                response[
                                    'Content-Disposition'] = 'attachment; filename=Profesores_distribucionh ' + str(
                                    periodo) + ' ' + random.randint(1, 10000).__str__() + '.xls'
                                columns = [
                                    (u"CODIGO_IES", 6000),
                                    (u"TIPO_IDENTIFICACION", 6000),
                                    (u"IDENTIFICACION", 6000),
                                    (u"NUMERO_DE_DOCUMENTO", 6000),
                                    (u"FECHA_INICIO", 3000),
                                    (u"FECHA_FIN", 3000),
                                    (u"ACCION_NUMERO_DE_DOCUMENTO", 6000),
                                    (u"FECHA", 3000),
                                    (u"HORAS_CLASE", 6000),
                                    (u"HORAS_TUTORIA", 6000),
                                    (u"HORAS_ADMINISTRATIVAS", 6000),
                                    (u"HORAS_INVESTIGACION", 6000),
                                    (u"HORAS_VINCULACION", 6000),
                                    (u"HORAS_OTRAS_ACTIVIDADES", 6000),
                                    (u"HORAS_CLASE_NIVEL_TECNICO", 6000),
                                    (u"HORAS_CLASE_TERCER_NIVEL", 6000),
                                    (u"HORAS_CLASE_CUARTO_NIVEL", 6000),
                                    (u"CALIFICACION_ACTIVIDADES_DOCENCIA", 6000),
                                    (u"CALIFICACION_ACTIVIDADES_INVESTIGACION", 6000),
                                    (u"CALIFICACION_ACTIVIDADES_DIRECCION_GESTION_ACADEMICA", 6000),
                                    (u"APELLIDOS Y NOMBRES", 7000),
                                    (u"NIVEL CATEGORIA", 6000),
                                    (u"CATEGORIA", 6000),
                                    (u"DEDICACION", 6000)
                                ]
                                row_num = 0
                                date_format = xlwt.XFStyle()
                                date_format.num_format_str = 'yyyy/mm/dd'
                                for col_num in range(len(columns)):
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                cursor = connection.cursor()
                                sql = "select tabla1.CODIGO_IES , (case substr(per.cedula,1,2) when 'VS' then 'PASAPORTE' else 'CEDULA' end) as TIPO_IDENTIFICACION , per.cedula as IDENTIFICACION,  " \
                                      "COALESCE((select pc.numerodocumento from sagest_personacontratos pc, sga_periodo p where pc.persona_id=per.id and pc.fechainicio>=p.inicio and pc.fechainicio<=p.fin and p.id=%s ORDER BY pc.fechainicio desc LIMIT 1),'') as NUMERO_DOCUMENTO, " \
                                      "(select pc.fechainicio from sagest_personacontratos pc, sga_periodo p where pc.persona_id=per.id and pc.fechainicio>=p.inicio and pc.fechainicio<=p.fin and p.id=%s ORDER BY pc.fechainicio desc LIMIT 1) as FINI_DOCUMENTO, " \
                                      "(select pc.fechafin from sagest_personacontratos pc, sga_periodo p where pc.persona_id=per.id and pc.fechainicio>=p.inicio and pc.fechainicio<=p.fin and p.id=%s ORDER BY pc.fechainicio desc LIMIT 1) as FFIN_DOCUMENTO, " \
                                      "COALESCE((SELECT pacc.numerodocumento FROM sagest_personaacciones pacc, sga_periodo p WHERE pacc.persona_id=per.id AND pacc.fecharige<=p.fin AND p.id=%s ORDER BY pacc.fecharige desc LIMIT 1),'') AS NUMERO_DOCUMENTO_ACCION," \
                                      "(SELECT pacc.fecharige FROM sagest_personaacciones pacc, sga_periodo p WHERE pacc.persona_id=per.id AND pacc.fecharige<=p.fin AND p.id=%s ORDER BY pacc.fecharige desc LIMIT 1) AS FECHA_DOCUMENTO_ACCION," \
                                      "tabla1.HORA_CLASE,tabla1.HORA_TUTORIA,tabla1.HORA_ADMINISTRACION,tabla1.HORA_INVESTIGACION,tabla1.HORA_VINCULACION,  " \
                                      "(case when COALESCE((select tdd.horas from sga_profesordistributivohoras pdh, sga_tiempodedicaciondocente tdd, sga_profesor pro where pdh.periodo_id=%s and tdd.id=pdh.dedicacion_id and pro.id=pdh.profesor_id and pro.persona_id=per.id LIMIT 1),0) - tabla1.HORAS_OTRAS_ACTIVIDADES >= 0 then COALESCE((select tdd.horas from sga_profesordistributivohoras pdh, sga_tiempodedicaciondocente tdd, sga_profesor pro where pdh.periodo_id=%s and tdd.id=pdh.dedicacion_id and pro.id=pdh.profesor_id and pro.persona_id=per.id),0) - tabla1.HORAS_OTRAS_ACTIVIDADES else 0 end) as HORAS_OTRAS_ACTIVIDADES, " \
                                      "0 as HORAS_CLASE_NIVEL_TECNICO, " \
                                      "0 as HORAS_CLASE_TERCER_NIVEL, " \
                                      "0 as HORAS_CLASE_CUARTO_NIVEL, " \
                                      "COALESCE((select round((rfa.resultado_docencia*100/5),2) from sga_resumenfinalevaluacionacreditacion rfa where rfa.id=(select distinct ra.id  " \
                                      "from sga_profesordistributivohoras dh  " \
                                      "left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id=%s  " \
                                      "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id  " \
                                      "left join sga_coordinacion coor on coor.id=dh.coordinacion_id  " \
                                      "left join sga_carrera car on car.id=dh.carrera_id  " \
                                      "left join sga_profesor pro on pro.id=dh.profesor_id  " \
                                      "left join sga_persona per1 on per1.id=pro.persona_id and per1.id=per.id  " \
                                      "where dh.periodo_id=%s and per1.real=True and ra.promedio_docencia_hetero notnull order by 1)),0) as CALIFICACION_ACTIVIDADES_DOCENCIA,  " \
                                      "COALESCE((select round((rfa.resultado_investigacion*100/5),2) from sga_resumenfinalevaluacionacreditacion rfa where rfa.id=(select distinct ra.id  " \
                                      "from sga_profesordistributivohoras dh  " \
                                      "left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id=%s  " \
                                      "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id  " \
                                      "left join sga_coordinacion coor on coor.id=dh.coordinacion_id  " \
                                      "left join sga_carrera car on car.id=dh.carrera_id  " \
                                      "left join sga_profesor pro on pro.id=dh.profesor_id  " \
                                      "left join sga_persona per1 on per1.id=pro.persona_id and per1.id=per.id  " \
                                      "where dh.periodo_id=%s and per1.real=True and ra.promedio_docencia_hetero notnull order by 1)),0) as CALIFICACION_ACTIVIDADES_INVESTIGACION,  " \
                                      "COALESCE((select round((rfa.resultado_gestion*100/5),2) from sga_resumenfinalevaluacionacreditacion rfa where rfa.id=(select distinct ra.id from sga_profesordistributivohoras dh  " \
                                      "left join sga_respuestaevaluacionacreditacion rea on dh.profesor_id=rea.profesor_id and rea.proceso_id=%s  " \
                                      "left join sga_resumenfinalevaluacionacreditacion ra on ra.distributivo_id=dh.id  " \
                                      "left join sga_coordinacion coor on coor.id=dh.coordinacion_id  " \
                                      "left join sga_carrera car on car.id=dh.carrera_id  " \
                                      "left join sga_profesor pro on pro.id=dh.profesor_id  " \
                                      "left join sga_persona per1 on per1.id=pro.persona_id and per1.id=per.id  " \
                                      "where dh.periodo_id=%s and per1.real=True and ra.promedio_docencia_hetero notnull order by 1)),0) as CALIFICACION_ACTIVIDADES_DIRECCION_GESTION_ACADEMICA,per.apellido1||' '||per.apellido2||' '||per.nombres as nompersona,per.id " \
                                      "from  (select  tabla.id, '1024' as CODIGO_IES ,  " \
                                      "sum(tabla.horas_clases) as HORA_CLASE, " \
                                      "sum(tabla.horas_tutorias) as HORA_TUTORIA, " \
                                      "sum(tabla.horas_administracion) as HORA_ADMINISTRACION, " \
                                      "sum(tabla.horas_investigacion) as HORA_INVESTIGACION, " \
                                      "sum(tabla.horas_vinculacion) as HORA_VINCULACION, " \
                                      "sum(tabla.horas_clases)+sum(tabla.horas_tutorias)+sum(tabla.horas_administracion)+sum(tabla.horas_investigacion)+sum(tabla.horas_vinculacion) as HORAS_OTRAS_ACTIVIDADES " \
                                      "from  (select pe.id,  " \
                                      "sum((case cd.tipocriterioactividad when 1 then dd.horas else 0 end)) as horas_administracion, " \
                                      "sum((case cd.tipocriterioactividad when 2 then dd.horas else 0 end)) as horas_clases, " \
                                      "sum((case cd.tipocriterioactividad when 3 then dd.horas else 0 end)) as horas_tutorias, " \
                                      "sum((case cd.tipocriterioactividad when 4 then dd.horas else 0 end)) as horas_vinculacion, " \
                                      "sum((case cd.tipocriterioactividad when 5 then dd.horas else 0 end)) as horas_investigacion " \
                                      "from sga_profesordistributivohoras pdh, sga_detalledistributivo dd, sga_criteriodocenciaperiodo cdp,  " \
                                      "sga_criteriodocencia cd, sga_profesor p, sga_persona pe " \
                                      "where pdh.periodo_id in (%s) and dd.distributivo_id=pdh.id and cdp.id=dd.criteriodocenciaperiodo_id " \
                                      "and cdp.criterio_id=cd.id and cdp.periodo_id=pdh.periodo_id and p.id=pdh.profesor_id and pe.id=p.persona_id " \
                                      "GROUP BY pe.id " \
                                      "union " \
                                      "select pe.id,  " \
                                      "sum((case cd.tipocriterioactividad when 1 then dd.horas else 0 end)) as horas_administracion, " \
                                      "sum((case cd.tipocriterioactividad when 2 then dd.horas else 0 end)) as horas_clases, " \
                                      "sum((case cd.tipocriterioactividad when 3 then dd.horas else 0 end)) as horas_tutorias, " \
                                      "sum((case cd.tipocriterioactividad when 4 then dd.horas else 0 end)) as horas_vinculacion, " \
                                      "sum((case cd.tipocriterioactividad when 5 then dd.horas else 0 end)) as horas_investigacion " \
                                      "from sga_profesordistributivohoras pdh, sga_detalledistributivo dd, sga_criterioinvestigacionperiodo cdp,  " \
                                      "sga_criterioinvestigacion cd, sga_profesor p, sga_persona pe " \
                                      "where pdh.periodo_id in (%s) and dd.distributivo_id=pdh.id and cdp.id=dd.criterioinvestigacionperiodo_id " \
                                      "and cdp.criterio_id=cd.id and cdp.periodo_id=pdh.periodo_id and p.id=pdh.profesor_id and pe.id=p.persona_id " \
                                      "GROUP BY pe.id " \
                                      "union " \
                                      "select pe.id,  " \
                                      "sum((case cd.tipocriterioactividad when 1 then dd.horas else 0 end)) as horas_administracion, " \
                                      "sum((case cd.tipocriterioactividad when 2 then dd.horas else 0 end)) as horas_clases, " \
                                      "sum((case cd.tipocriterioactividad when 3 then dd.horas else 0 end)) as horas_tutorias, " \
                                      "sum((case cd.tipocriterioactividad when 4 then dd.horas else 0 end)) as horas_vinculacion, " \
                                      "sum((case cd.tipocriterioactividad when 5 then dd.horas else 0 end)) as horas_investigacion " \
                                      "from sga_profesordistributivohoras pdh, sga_detalledistributivo dd, sga_criteriogestionperiodo cdp,  " \
                                      "sga_criteriogestion cd, sga_profesor p, sga_persona pe " \
                                      "where pdh.periodo_id in (%s) and dd.distributivo_id=pdh.id and cdp.id=dd.criteriogestionperiodo_id " \
                                      "and cdp.criterio_id=cd.id and cdp.periodo_id=pdh.periodo_id and p.id=pdh.profesor_id and pe.id=p.persona_id " \
                                      "GROUP BY pe.id) as tabla GROUP BY tabla.id) as tabla1 " \
                                      "inner join sga_persona per on tabla1.id=per.id  " % (
                                      periodo.id, periodo.id, periodo.id, periodo.id, periodo.id, periodo.id,
                                      periodo.id, periodo.id, periodo.id, periodo.id, periodo.id, periodo.id,
                                      periodo.id, periodo.id, periodo.id, periodo.id)
                                cursor.execute(sql)
                                results = cursor.fetchall()
                                row_num = 1
                                for r in results:
                                    nivelcategoria = ''
                                    categoria = ''
                                    dedicacion = ''
                                    distri = ProfesorDistributivoHoras.objects.get(profesor__persona__id=int(r[21]),
                                                                                   periodo__id=periodo.id, status=True)
                                    if distri.nivelcategoria:
                                        nivelcategoria = distri.nivelcategoria.nombre
                                    if distri.categoria:
                                        categoria = distri.categoria.nombre
                                    if distri.dedicacion:
                                        dedicacion = distri.dedicacion.nombre
                                    ws.write(row_num, 0, r[0] if r[0] else '', font_style2)
                                    ws.write(row_num, 1, r[1] if r[1] else '', font_style2)
                                    ws.write(row_num, 2, str(r[2]) if r[2] else '', font_style2)
                                    ws.write(row_num, 3, r[3] if r[3] else '', font_style2)
                                    ws.write(row_num, 4, r[4], date_format)
                                    ws.write(row_num, 5, r[5], date_format)
                                    ws.write(row_num, 6, r[6] if r[6] else '', font_style2)
                                    ws.write(row_num, 7, r[7], date_format)
                                    ws.write(row_num, 8, r[8], font_style2)
                                    ws.write(row_num, 9, r[9], font_style2)
                                    ws.write(row_num, 10, r[10], font_style2)
                                    ws.write(row_num, 11, r[11], font_style2)
                                    ws.write(row_num, 12, r[12], font_style2)
                                    ws.write(row_num, 13, r[13], font_style2)
                                    ws.write(row_num, 14, r[14], font_style2)
                                    ws.write(row_num, 15, r[15], font_style2)
                                    ws.write(row_num, 16, r[16], font_style2)
                                    ws.write(row_num, 17, r[17], font_style2)
                                    ws.write(row_num, 18, r[18], font_style2)
                                    ws.write(row_num, 19, r[19], font_style2)
                                    ws.write(row_num, 20, r[20], font_style2)
                                    ws.write(row_num, 21, nivelcategoria, font_style2)
                                    ws.write(row_num, 22, categoria, font_style2)
                                    ws.write(row_num, 23, dedicacion, font_style2)
                                    row_num += 1
                                wb.save(response)
                                return response
                        except Exception as ex:
                            pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'matrizprofesorformacionencurso':
                try:
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 16, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Profesores_formacion_en_curso ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CODIGO_IES", 6000),
                        (u"TIPO_IDENTIFICACION", 6000),
                        (u"NUMERO_INDENTIFICACION", 6000),
                        (u"PAIS_ESTUDIO", 6000),
                        (u"CODIGO_IES_ESTUDIO", 6000),
                        (u"NOMBRE_IES", 6000),
                        (u"NIVEL", 6000),
                        (u"GRADO", 6000),
                        (u"NOMBRE_TITULO", 6000),
                        (u"CODIGO_SUBAREA_CONOCIMIENTO_ESPECIFICO_UNESCO", 6000),
                        (u"FECHA_INICIO_ESTUDIOS", 6000),
                        (u"POSEE_BECA", 6000),
                        (u"TIPO_BECA", 6000),
                        (u"MONTO_BECA", 6000),
                        (u"FINANCIAMIENTO_BECA", 6000),
                        (u"ESPECIFICAR_OTRO", 6000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    idpersonas = ProfesorDistributivoHoras.objects.values_list('profesor__persona__id', flat=False).filter(horasdocencia__gt=0, horasinvestigacion__gt=0, horasgestion__gt=0).distinct()
                    results = Titulacion.objects.filter(persona__in=idpersonas, cursando=True, titulo__nivel__id__in=[3, 4])
                    row_num = 1
                    for r in results:
                        nidentificacion = r.persona.cedula if r.persona.cedula else r.persona.pasaporte
                        tipoidentificacion = 'CEDULA' if r.persona.cedula else 'PASAPORTE'
                        ws.write(row_num, 0, '1024', font_style2)
                        ws.write(row_num, 1, tipoidentificacion, font_style2)
                        ws.write(row_num, 2, nidentificacion, font_style2)
                        ws.write(row_num, 3, r.pais.nombre if r.pais else '', font_style2)
                        ws.write(row_num, 4, r.institucion.codigo if r.institucion else '', font_style2)
                        ws.write(row_num, 5, r.institucion.nombre if r.institucion else '', font_style2)
                        ws.write(row_num, 6, r.titulo.nivel.nombre if r.titulo else '', font_style2)
                        ws.write(row_num, 7, r.titulo.grado.nombre if r.titulo.grado else '', font_style2)
                        ws.write(row_num, 8, r.titulo.nombre if r.titulo else '', font_style2)
                        ws.write(row_num, 9, '', font_style2)
                        ws.write(row_num, 10, r.fechainicio.strftime("%d/%m/%Y") if r.fechainicio else '', font_style2)
                        ws.write(row_num, 11, 'SI' if r.aplicobeca else 'NO', font_style2)
                        ws.write(row_num, 12, r.get_tipobeca_display() if r.tipobeca else '', font_style2)
                        ws.write(row_num, 13, r.valorbeca if r.aplicobeca else '', font_style2)
                        ws.write(row_num, 14, r.financiamientobeca.nombre if r.financiamientobeca else '', font_style2)
                        ws.write(row_num, 15, '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'matrizprofesorformacionterminada':
                try:
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    # ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=Profesores_formacion_terminada ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CODIGO_IES", 6000),
                        (u"TIPO_IDENTIFICACION", 6000),
                        (u"NUMERO_INDENTIFICACION", 6000),
                        (u"PAIS_ESTUDIO", 6000),
                        (u"CODIGO_IES_ESTUDIO", 6000),
                        (u"NOMBRE_IES", 6000),
                        (u"NIVEL", 6000),
                        (u"GRADO", 6000),
                        (u"NOMBRE_TITULO", 6000),
                        (u"CODIGO_SUBAREA_CONOCIMIENTO_ESPECIFICO_UNESCO", 6000),
                        (u"NUMERO_REGISTRO_SENESCYT ", 6000),
                        (u"FECHA_OBTUVO_TITULO", 6000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    idpersonas = ProfesorDistributivoHoras.objects.values_list('profesor__persona__id', flat=False).filter(horasdocencia__gt=0, horasinvestigacion__gt=0, horasgestion__gt=0).distinct()
                    results = Titulacion.objects.filter(Q(persona__in=idpersonas), Q(cursando=False), Q(titulo__nivel__id__in=[3, 4]), (Q(verificado=True) | Q(verisenescyt=True)))
                    row_num = 1
                    for r in results:
                        nidentificacion = r.persona.cedula if r.persona.cedula else r.persona.pasaporte
                        tipoidentificacion = 'CEDULA' if r.persona.cedula else 'PASAPORTE'
                        ws.write(row_num, 0, '1024', font_style2)
                        ws.write(row_num, 1, tipoidentificacion, font_style2)
                        ws.write(row_num, 2, nidentificacion, font_style2)
                        ws.write(row_num, 3, r.pais.nombre if r.pais else '', font_style2)
                        ws.write(row_num, 4, r.institucion.codigo if r.institucion else '', font_style2)
                        ws.write(row_num, 5, r.institucion.nombre if r.institucion else '', font_style2)
                        # ws.write(row_num, 6, r.titulo.nivel.nombre if r.titulo else '', font_style2)
                        ws.write(row_num, 6, '', font_style2)
                        ws.write(row_num, 7, r.titulo.grado.nombre if r.titulo.grado else '', font_style2)
                        ws.write(row_num, 8, r.titulo.nombre if r.titulo else '', font_style2)
                        ws.write(row_num, 9, '', font_style2)
                        ws.write(row_num, 10, r.registro if r.registro else '', font_style2)
                        ws.write(row_num, 11, r.fechaaprobaciontitulo.strftime("%d/%m/%Y") if r.fechaaprobaciontitulo else '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'matrizprofesorescontrato_anio ':
                try:
                    if 'anio' in request.GET:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('exp_xls_post_part')
                        # ws.write_merge(0, 0, 0, 31, 'UNIVERSIDAD ESTATAL DE MILAGRO '+ str(request.GET['anio']), title)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=Profesores_contrato-' + str(request.GET['anio']) + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"CODIGO_IES", 6000),
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
                            (u"TIPO_DOCUMENTO", 6000),
                            (u"NUMERO_DOCUMENTO", 6000),
                            (u"CONTRATO_RELACIONADO", 6000),
                            (u"INGRESO_POR_CONCURSO", 6000),
                            (u"RELACION_IES", 6000),
                            (u"TIPO_ESCALAFON_NOMBRAMIENTO", 6000),
                            (u"CATEGORIA", 6000),
                            (u"TIEMPO_DEDICACION", 6000),
                            (u"REMUNERACION_MES", 6000),
                            (u"REMUNERACION_HORA", 6000),
                            (u"FECHA_INGRESO_IES", 6000),
                            (u"FECHA_INICIO", 6000),
                            (u"FECHA_FIN", 6000),
                            (u"NIVEL", 6000),
                            (u"UNIDAD_ACADEMICA", 6000)
                        ]
                        row_num = 0
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        idpersonas = ProfesorDistributivoHoras.objects.values_list('profesor__persona__id', flat=False).filter(Q(status=True), (Q(horasdocencia__gt=0) | Q(horasinvestigacion__gt=0) | Q(horasgestion__gt=0)), Q(periodo__anio=int(request.GET['anio']))).distinct()
                        contratos = PersonaContratos.objects.filter(status=True, persona__id__in=idpersonas, fechainicio__year__gte=int(request.GET['anio']))
                        row_num = 1
                        for con in contratos:
                            nidentificacion = con.persona.cedula if con.persona.cedula else con.persona.pasaporte
                            tipoidentificacion = 'CEDULA' if con.persona.cedula else 'PASAPORTE'
                            tienediscapasidad = 'NO'
                            porcentajd = 0
                            carnetdiscapacidad = ''
                            etnia = ''
                            if con.persona.perfilinscripcion_set.filter(status=True).exists():
                                pinscripcion = con.persona.perfilinscripcion_set.filter(status=True)[0]
                                if pinscripcion.tienediscapacidad:
                                    if pinscripcion.tipodiscapacidad_id in [5, 1, 4, 8, 9, 7]:
                                        tienediscapasidad = pinscripcion.tienediscapacidad if pinscripcion.tienediscapacidad else 'NO'
                                        tipodiscapacidad = u'%s' % pinscripcion.tipodiscapacidad
                                        carnetdiscapacidad = pinscripcion.carnetdiscapacidad if pinscripcion.carnetdiscapacidad else ''
                                        porcentajd = pinscripcion.porcientodiscapacidad if pinscripcion.tienediscapacidad else 0
                                etnia = pinscripcion.raza.nombre if pinscripcion.raza else ''
                            ws.write(row_num, 0, '1024', font_style2)
                            ws.write(row_num, 1, tipoidentificacion, font_style2)
                            ws.write(row_num, 2, nidentificacion, font_style2)
                            ws.write(row_num, 3, con.persona.apellido1, font_style2)
                            ws.write(row_num, 4, con.persona.apellido2, font_style2)
                            ws.write(row_num, 5, con.persona.nombres, font_style2)
                            ws.write(row_num, 6, con.persona.sexo.nombre if con.persona.sexo else '', font_style2)
                            ws.write(row_num, 7, con.persona.nacimiento.strftime("%d-%m-%Y") if con.persona.nacimiento else '', font_style2)
                            ws.write(row_num, 8, con.persona.pais.nombre if con.persona.pais else '', font_style2)
                            ws.write(row_num, 9, tienediscapasidad, font_style2)
                            ws.write(row_num, 10, porcentajd, font_style2)
                            ws.write(row_num, 11, carnetdiscapacidad, font_style2)
                            ws.write(row_num, 12, etnia, font_style2)
                            ws.write(row_num, 13, con.persona.nacionalidad if con.persona.nacionalidad else '', font_style2)
                            ws.write(row_num, 14, con.persona.direccion if con.persona.direccion else con.persona.direccion2, font_style2)
                            ws.write(row_num, 15, con.persona.email if con.persona.email else '', font_style2)
                            ws.write(row_num, 16, con.persona.emailinst if con.persona.emailinst else '', font_style2)
                            ws.write(row_num, 17, '', font_style2)
                            ws.write(row_num, 18, con.numerodocumento if con.numerodocumento else '', font_style2)
                            ws.write(row_num, 19, con.contratacionrelacionada if con.contratacionrelacionada else '', font_style2)
                            ws.write(row_num, 20, 'SI' if con.persona.concursomeritos else 'NO', font_style2)
                            ws.write(row_num, 21, con.get_relacionies_display() if con.relacionies else '', font_style2)
                            ws.write(row_num, 22, '', font_style2)
                            ws.write(row_num, 23, '', font_style2)
                            ws.write(row_num, 24, '', font_style2)
                            ws.write(row_num, 25, con.remuneracion if con.remuneracion else '', font_style2)
                            ws.write(row_num, 26, '', font_style2)
                            ws.write(row_num, 27, con.persona.fechaingresoies.strftime("%d-%m-%Y") if con.persona.fechaingresoies else '', font_style2)
                            ws.write(row_num, 28, con.fechainicio.strftime("%d-%m-%Y") if con.fechainicio else '', font_style2)
                            ws.write(row_num, 29, con.fechafin.strftime("%d-%m-%Y") if con.fechafin else '', font_style2)
                            ws.write(row_num, 30, '', font_style2)
                            ws.write(row_num, 31, '', font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    pass

            elif action == 'matrizgraduados_anio':
                try:
                    if data['permiteWebPush']:
                        name_document = 'graduados_fecha_graduacion'
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo=name_document, destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matrizmatrizgraduados_anio_background(request=request, data=data, notiid=noti.pk, name_document=name_document).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            if 'anio' in request.GET:
                                __author__ = 'Unemi'
                                title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                                font_style = XFStyle()
                                font_style.font.bold = True
                                font_style2 = XFStyle()
                                font_style2.font.bold = False
                                wb = Workbook(encoding='utf-8')
                                ws = wb.add_sheet('exp_xls_post_part')
                                response = HttpResponse(content_type="application/ms-excel")
                                coordinacion = None
                                carrera = None
                                if 'idcoor' in request.GET:
                                    idcoor = request.GET['idcoor']
                                    if int(idcoor) > 0:
                                        coordinacion = Coordinacion.objects.get(id=int(idcoor))
                                        nombbre = u"Graduados %s" % coordinacion.nombre
                                    else:
                                        nombbre = u"Graduados"
                                else:
                                    nombbre = u"Graduados"

                                if 'idcarr' in request.GET:
                                    idcarr = request.GET['idcarr']
                                    if idcarr != '':
                                        if int(idcarr) > 0:
                                            carrera = Carrera.objects.get(id=int(idcarr))
                                            nombbre += u" _ Carrera %s" % carrera.nombre_completo()

                                response['Content-Disposition'] = 'attachment; filename=' + nombbre + ' - ' + str(request.GET['anio']) + random.randint(1, 10000).__str__() + '.xls'
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
                                    (u"NUMERO_CONADIS", 6000),
                                    (u"DIRECCION", 6000),
                                    (u"EMAIL_PERSONAL", 6000),
                                    (u"EMAIL_INSTITUCIONAL", 6000),
                                    (u"FECHA_INICIO_PRIMER_NIVEL", 6000),
                                    (u"FECHA_INGRESO_CONVALIDACION", 6000),
                                    (u"FECHA_GRADUACION", 6000),
                                    (u"MECANISMO_TITULACION", 6000),
                                    (u"CARRERA", 6000)
                                ]
                                row_num = 0
                                for col_num in range(len(columns)):
                                    ws.write(row_num, col_num, columns[col_num][0], font_style)
                                    ws.col(col_num).width = columns[col_num][1]
                                idinscripciones = Inscripcion.objects.values_list('id', flat=False).filter(status=True, fechainicioprimernivel__year=int(request.GET['anio'])).exclude(coordinacion__id__in=[6, 7, 8, 9]).order_by('persona').distinct()
                                graduados = Graduado.objects.filter(status=True, estadograduado=True, fechagraduado__year=int(request.GET['anio']))
                                # graduados = Graduado.objects.filter(status=True, estadograduado=True, inscripcion__id__in=idinscripciones)
                                if coordinacion:
                                    graduados = graduados.filter(inscripcion__carrera__coordinacion=coordinacion)

                                if carrera:
                                    graduados = graduados.filter(inscripcion__carrera=carrera)

                                row_num = 1
                                for g in graduados:
                                    nidentificacion = g.inscripcion.persona.cedula if g.inscripcion.persona.cedula else g.inscripcion.persona.pasaporte
                                    tipoidentificacion = 'CEDULA' if g.inscripcion.persona.cedula else 'PASAPORTE'
                                    tipodiscapacidad = 'NINGUNA'
                                    carnetdiscapacidad = ''
                                    if g.inscripcion.persona.perfilinscripcion_set.filter(status=True).exists():
                                        pinscripcion = g.inscripcion.persona.perfilinscripcion_set.filter(status=True)[0]
                                        tipodiscapacidad = pinscripcion.tipodiscapacidad.nombre if pinscripcion.tipodiscapacidad else 'NINGUNA'
                                        carnetdiscapacidad = pinscripcion.carnetdiscapacidad if pinscripcion.carnetdiscapacidad else ''
                                    mecanismot = ''
                                    if g.codigomecanismotitulacion:
                                        if g.codigomecanismotitulacion.mecanismotitulacion:
                                            mecanismot = g.codigomecanismotitulacion.mecanismotitulacion.nombre
                                    ciudad_carrera = "MILAGRO"
                                    ws.write(row_num, 0, '1024', font_style2)
                                    ws.write(row_num, 1, g.inscripcion.mi_malla().codigo if g.inscripcion.mi_malla() else '', font_style2)
                                    ws.write(row_num, 2, ciudad_carrera, font_style2)
                                    ws.write(row_num, 3, tipoidentificacion, font_style2)
                                    ws.write(row_num, 4, nidentificacion, font_style2)
                                    ws.write(row_num, 5, g.inscripcion.persona.apellido1, font_style2)
                                    ws.write(row_num, 6, g.inscripcion.persona.apellido2, font_style2)
                                    ws.write(row_num, 7, g.inscripcion.persona.nombres, font_style2)
                                    ws.write(row_num, 8, g.inscripcion.persona.sexo.nombre if g.inscripcion.persona.sexo else '', font_style2)
                                    ws.write(row_num, 9, g.inscripcion.persona.nacimiento.strftime("%d/%m/%Y") if g.inscripcion.persona.nacimiento else '', font_style2)
                                    ws.write(row_num, 10, g.inscripcion.persona.pais.nombre if g.inscripcion.persona.pais else '', font_style2)
                                    ws.write(row_num, 11, tipodiscapacidad, font_style2)
                                    ws.write(row_num, 12, carnetdiscapacidad, font_style2)
                                    ws.write(row_num, 13, g.inscripcion.persona.direccion if g.inscripcion.persona.direccion else g.inscripcion.persona.direccion2, font_style2)
                                    ws.write(row_num, 14, g.inscripcion.persona.email if g.inscripcion.persona.email else '', font_style2)
                                    ws.write(row_num, 15, g.inscripcion.persona.emailinst if g.inscripcion.persona.emailinst else '', font_style2)
                                    ws.write(row_num, 16, g.inscripcion.fechainicioprimernivel.strftime("%d/%m/%Y") if g.inscripcion.fechainicioprimernivel else '', font_style2)
                                    ws.write(row_num, 17, g.inscripcion.fechainicioconvalidacion.strftime("%d/%m/%Y") if g.inscripcion.fechainicioconvalidacion else '', font_style2)
                                    ws.write(row_num, 18, g.fechagraduado.strftime("%d/%m/%Y") if g.fechagraduado else '', font_style2)
                                    ws.write(row_num, 19, mecanismot if mecanismot else 'TRABAJO TITULACIÓN ', font_style2)
                                    ws.write(row_num, 20, g.inscripcion.carrera.nombre_completo(), font_style2)
                                    row_num += 1
                                wb.save(response)
                                return response
                        except Exception as ex:
                            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                            pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'matrizgraduados_anio2':
                try:
                    if 'anio' in request.GET:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('exp_xls_post_part')
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=Graduados-' + str(request.GET['anio']) + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"CODIGO_IES", 6000),
                            (u"CODIGO_CARRERA", 6000),
                            (u"TIPO_IDENTIFICACION", 6000),
                            (u"IDENTIFICACION", 6000),
                            (u"PRIMER_APELLIDO", 6000),
                            (u"SEGUNDO_APELLIDO", 6000),
                            (u"NOMBRES", 6000),
                            (u"SEXO", 6000),
                            (u"FECHA_NACIMIENTO", 6000),
                            (u"PAIS_ORIGEN", 6000),
                            (u"DISCAPACIDAD", 6000),
                            (u"NUMERO_CONADIS", 6000),
                            (u"DIRECCION", 6000),
                            (u"EMAIL_PERSONAL", 6000),
                            (u"EMAIL_INSTITUCIONAL", 6000),
                            (u"FECHA_INICIO_PRIMER_NIVEL", 6000),
                            (u"FECHA_INGRESO_CONVALIDACION", 6000),
                            (u"FECHA_GRADUACION", 6000),
                            (u"MECANISMO_TITULACION", 6000)
                        ]
                        row_num = 0
                        for col_num in range(len(columns)):
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        idinscripciones = Inscripcion.objects.values_list('id', flat=False).filter(status=True, fechainicioprimernivel__year=int(request.GET['anio'])).exclude(coordinacion__id__in=[6, 7, 8, 9]).order_by('persona').distinct()
                        graduados = Graduado.objects.filter(status=True, estadograduado=True, fechagraduado__year=int(request.GET['anio']))
                        # graduados = Graduado.objects.filter(status=True, estadograduado=True, fechagraduado__year=int(request.GET['anio']))
                        row_num = 1
                        for g in graduados:
                            nidentificacion = g.inscripcion.persona.cedula if g.inscripcion.persona.cedula else g.inscripcion.persona.pasaporte
                            tipoidentificacion = 'CEDULA' if g.inscripcion.persona.cedula else 'PASAPORTE'
                            tipodiscapacidad = 'NINGUNA'
                            carnetdiscapacidad = ''
                            if g.inscripcion.persona.perfilinscripcion_set.filter(status=True).exists():
                                pinscripcion = g.inscripcion.persona.perfilinscripcion_set.filter(status=True)[0]
                                tipodiscapacidad = pinscripcion.tipodiscapacidad.nombre if pinscripcion.tipodiscapacidad else 'NINGUNA'
                                carnetdiscapacidad = pinscripcion.carnetdiscapacidad if pinscripcion.carnetdiscapacidad else ''
                            mecanismot = ''
                            if g.codigomecanismotitulacion:
                                if g.codigomecanismotitulacion.mecanismotitulacion:
                                    mecanismot = g.codigomecanismotitulacion.mecanismotitulacion.nombre
                            ws.write(row_num, 0, '1024', font_style2)
                            ws.write(row_num, 1, g.inscripcion.mi_malla().codigo if g.inscripcion.mi_malla() else '', font_style2)
                            ws.write(row_num, 2, tipoidentificacion, font_style2)
                            ws.write(row_num, 3, nidentificacion, font_style2)
                            ws.write(row_num, 4, g.inscripcion.persona.apellido1, font_style2)
                            ws.write(row_num, 5, g.inscripcion.persona.apellido2, font_style2)
                            ws.write(row_num, 6, g.inscripcion.persona.nombres, font_style2)
                            ws.write(row_num, 7, g.inscripcion.persona.sexo.nombre if g.inscripcion.persona.sexo else '', font_style2)
                            ws.write(row_num, 8, g.inscripcion.persona.nacimiento.strftime("%d/%m/%Y") if g.inscripcion.persona.nacimiento else '', font_style2)
                            ws.write(row_num, 9, g.inscripcion.persona.pais.nombre if g.inscripcion.persona.pais else '', font_style2)
                            ws.write(row_num, 10, tipodiscapacidad, font_style2)
                            ws.write(row_num, 11, carnetdiscapacidad, font_style2)
                            ws.write(row_num, 12, g.inscripcion.persona.direccion if g.inscripcion.persona.direccion else g.inscripcion.persona.direccion2, font_style2)
                            ws.write(row_num, 13, g.inscripcion.persona.email if g.inscripcion.persona.email else '', font_style2)
                            ws.write(row_num, 14, g.inscripcion.persona.emailinst if g.inscripcion.persona.emailinst else '', font_style2)
                            ws.write(row_num, 15, g.inscripcion.fechainicioprimernivel.strftime("%d/%m/%Y") if g.inscripcion.fechainicioprimernivel else '', font_style2)
                            ws.write(row_num, 16, g.inscripcion.fechainicioconvalidacion.strftime("%d/%m/%Y") if g.inscripcion.fechainicioconvalidacion else '', font_style2)
                            ws.write(row_num, 17, g.fechagraduado.strftime("%d/%m/%Y") if g.fechagraduado else '', font_style2)
                            ws.write(row_num, 18, mecanismot if mecanismot else 'TRABAJO TITULACIÓN ', font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    pass

            elif action == 'matrizestudiantesipec_anio':
                try:
                    if 'anio' in request.GET:
                        __author__ = 'Unemi'
                        title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                        font_style = XFStyle()
                        font_style.font.bold = True
                        font_style2 = XFStyle()
                        font_style2.font.bold = False
                        wb = Workbook(encoding='utf-8')
                        ws = wb.add_sheet('exp_xls_post_part')
                        # ws.write_merge(0, 0, 0, 29, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                        response = HttpResponse(content_type="application/ms-excel")
                        response['Content-Disposition'] = 'attachment; filename=EstudiantesIPEC- ' + request.GET['anio'] + '-' + random.randint(1, 10000).__str__() + '.xls'
                        columns = [
                            (u"CODIGO_IES", 6000),
                            (u"CODIGO_CARRERA", 6000),
                            (u"TIPO_IDENTIFICACION", 6000),
                            (u"IDENTIFICACION", 6000),
                            (u"PRIMER_APELLIDO", 6000),
                            (u"SEGUNDO_APELLIDO", 6000),
                            (u"NOMBRES", 6000),
                            (u"SEXO", 6000),
                            (u"FECHA NACIMIENTO", 6000),
                            (u"PAIS ORIGEN", 6000),
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
                            ws.write(row_num, col_num, columns[col_num][0], font_style)
                            ws.col(col_num).width = columns[col_num][1]
                        listaestudiantes = Matricula.objects.filter(status=True, inscripcion__coordinacion__id=7, fecha__year=int(request.GET['anio'])).distinct()
                        row_num = 1
                        for r in listaestudiantes:
                            nidentificacion = r.inscripcion.persona.cedula if r.inscripcion.persona.cedula else r.inscripcion.persona.pasaporte
                            tipoidentificacion = 'CEDULA' if r.inscripcion.persona.cedula else 'PASAPORTE'
                            tipodiscapacidad = 'NINGUNA'
                            carnetdiscapacidad = ''
                            porcientodiscapacidad = ''
                            raza = 'NO REGISTRA'
                            if r.inscripcion.persona.perfilinscripcion_set.filter(status=True).exists():
                                pinscripcion = r.inscripcion.persona.perfilinscripcion_set.filter(status=True)[0]
                                if pinscripcion.tienediscapacidad:
                                    if pinscripcion.tipodiscapacidad_id in [5, 1, 4, 8, 9, 7]:
                                        tienediscapasidad = pinscripcion.tienediscapacidad if pinscripcion.tienediscapacidad else 'NO'
                                        tipodiscapacidad = u'%s' % pinscripcion.tipodiscapacidad
                                        carnetdiscapacidad = pinscripcion.carnetdiscapacidad if pinscripcion.carnetdiscapacidad else ''
                                        porcientodiscapacidad = pinscripcion.porcientodiscapacidad if pinscripcion.tienediscapacidad else ''
                                if pinscripcion.raza:
                                    raza = pinscripcion.raza.nombre
                                    if pinscripcion.raza.id == 1:
                                        nacionalidad = u"%s" % pinscripcion.nacionalidadindigena
                            formacionpadre = ''
                            formacionmadre = ''
                            cantidad = 0
                            if r.inscripcion.persona.personadatosfamiliares_set.filter(status=True).exists():
                                if r.inscripcion.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1).exists():
                                    formacionpadre = r.inscripcion.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion.nombrecaces if r.inscripcion.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=1)[0].niveltitulacion else ''
                                if r.inscripcion.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2).exists():
                                    formacionmadre = r.inscripcion.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion.nombrecaces if r.inscripcion.persona.personadatosfamiliares_set.filter(status=True, parentesco_id=2)[0].niveltitulacion else ''
                                cantidad = r.inscripcion.persona.personadatosfamiliares_set.filter(status=True).count()
                            ws.write(row_num, 0, '1024', font_style2)
                            ws.write(row_num, 1, r.inscripcion.mi_malla().codigo if r.inscripcion.mi_malla() else '', font_style2)
                            ws.write(row_num, 2, tipoidentificacion if tipoidentificacion else '', font_style2)
                            ws.write(row_num, 3, nidentificacion if nidentificacion else '', font_style2)
                            ws.write(row_num, 4, r.inscripcion.persona.apellido1 if r.inscripcion.persona.apellido1 else '', font_style2)
                            ws.write(row_num, 5, r.inscripcion.persona.apellido2 if r.inscripcion.persona.apellido2 else '', font_style2)
                            ws.write(row_num, 6, r.inscripcion.persona.nombres if r.inscripcion.persona.nombres else '', font_style2)
                            ws.write(row_num, 7, r.inscripcion.persona.sexo.nombre if r.inscripcion.persona.sexo else '', font_style2)
                            ws.write(row_num, 8, r.inscripcion.persona.nacimiento.strftime("%d/%m/%Y") if r.inscripcion.persona.nacimiento else '', font_style2)
                            ws.write(row_num, 9, r.inscripcion.persona.paisnacimiento.nombre if r.inscripcion.persona.paisnacimiento else '', font_style2)
                            ws.write(row_num, 10, tipodiscapacidad if tipodiscapacidad else 'NINGUNA', font_style2)
                            ws.write(row_num, 11, porcientodiscapacidad if porcientodiscapacidad else 0, font_style2)
                            ws.write(row_num, 12, carnetdiscapacidad if carnetdiscapacidad else '', font_style2)
                            ws.write(row_num, 13, raza if raza else 'NO REGISTRA', font_style2)
                            # ws.write(row_num, 14, r.inscripcion.persona.nacionalidad if r.inscripcion.persona.nacionalidad else '', font_style2)
                            ws.write(row_num, 14, 'NO REGISTRA', font_style2)
                            ws.write(row_num, 15, r.inscripcion.persona.direccion if r.inscripcion.persona.direccion2 else '', font_style2)
                            ws.write(row_num, 16, r.inscripcion.persona.email if r.inscripcion.persona.email else '', font_style2)
                            ws.write(row_num, 17, r.inscripcion.persona.emailinst if r.inscripcion.persona.emailinst else '', font_style2)
                            ws.write(row_num, 18, r.inscripcion.fechainicioprimernivel.strftime("%d/%m/%Y") if r.inscripcion.fechainicioprimernivel else '', font_style2)
                            ws.write(row_num, 19, r.inscripcion.fechainicioconvalidacion.strftime("%d/%m/%Y") if r.inscripcion.fechainicioconvalidacion else '', font_style2)
                            ws.write(row_num, 20, r.inscripcion.persona.pais.nombre if r.inscripcion.persona.pais else '', font_style2)
                            ws.write(row_num, 21, r.inscripcion.persona.provincia.nombre if r.inscripcion.persona.provincia else '', font_style2)
                            ws.write(row_num, 22, r.inscripcion.persona.canton.nombre if r.inscripcion.persona.canton else '', font_style2)
                            ws.write(row_num, 23, r.inscripcion.persona.telefono if r.inscripcion.persona.telefono else '', font_style2)
                            # ws.write(row_num, 24, formacionpadre if formacionpadre else '', font_style2)
                            ws.write(row_num, 24, 'NINGUNO', font_style2)
                            # ws.write(row_num, 25, formacionmadre if formacionmadre else '', font_style2)
                            ws.write(row_num, 25, 'NINGUNO', font_style2)
                            ws.write(row_num, 26, cantidad if cantidad else 0, font_style2)
                            ws.write(row_num, 27, 'NO REGISTRA', font_style2)
                            ws.write(row_num, 28, 'NINGUNA', font_style2)
                            ws.write(row_num, 29, r.inscripcion.carrera.nombre_completo() if r.inscripcion.carrera else '', font_style2)
                            row_num += 1
                        wb.save(response)
                        return response
                except Exception as ex:
                    pass

            elif action == 'matrizpracticaspreprofesionales_anio':
                try:
                    if data['permiteWebPush']:
                        name_document = 'estudiantePPP_sin_salud'
                        noti = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                            titulo=name_document, destinatario=persona,
                                            url='',
                                            prioridad=1, app_label='SGA',
                                            fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                            en_proceso=True)
                        noti.save(request)
                        reporte_matrizpracticaspreprofesionales_anio_background(request=request, data=data, notiid=noti.pk, name_document=name_document).start()
                        return JsonResponse({"result": True,
                                             "mensaje": u"El reporte se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                             "btn_notificaciones": traerNotificaciones(request, data, persona)})
                    else:
                        try:
                            if 'anio' in request.GET:
                                __author__ = 'Unemi'
                            title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                            font_style = XFStyle()
                            font_style.font.bold = True
                            font_style2 = XFStyle()
                            font_style2.font.bold = False
                            wb = Workbook(encoding='utf-8')
                            ws = wb.add_sheet('exp_xls_post_part')
                            response = HttpResponse(content_type="application/ms-excel")
                            response['Content-Disposition'] = 'attachment; filename=Practicas- ' + request.GET['anio'] + '-' + random.randint(1, 10000).__str__() + '.xls'
                            columns = [
                                (u"CODIGO_IES", 6000),
                                (u"CODIGO_CARRERA", 6000),
                                (u"CIUDAD_CARRERA", 6000),
                                (u"TIPO_IDENTIFICACION", 6000),
                                (u"IDENTIFICACION", 6000),
                                (u"NOMBRE_INSTITUCION", 6000),
                                (u"TIPO_INSTITUCION", 6000),
                                (u"FECHA_INICIO", 6000),
                                (u"FECHA_FIN", 6000),
                                (u"NUMERO_HORAS", 6000),
                                (u"CAMPO_ESPECIFICO", 6000),
                                (u"IDENTIFICACION_DOCENTE_TUTOR", 6000),
                                (u"TIPO", 6000)
                            ]
                            row_num = 0
                            for col_num in range(len(columns)):
                                ws.write(row_num, col_num, columns[col_num][0], font_style)
                                ws.col(col_num).width = columns[col_num][1]
                            listapracticas = PracticasPreprofesionalesInscripcion.objects.filter(status=True, culminada=True, fechadesde__year=int(request.GET['anio'])).exclude(inscripcion__coordinacion__id=1).distinct()
                            row_num = 1
                            for p in listapracticas.order_by('fechadesde'):
                                nidentificacion = p.inscripcion.persona.cedula if p.inscripcion.persona.cedula else p.inscripcion.persona.pasaporte
                                tipoidentificacion = 'CEDULA' if p.inscripcion.persona.cedula else 'PASAPORTE'
                                identificaciondocentetutor = ''
                                if p.tutorunemi:
                                    identificaciondocentetutor = p.tutorunemi.persona.cedula if p.tutorunemi else p.tutorunemi.persona.pasaporte
                                if p.tiposolicitud == 3:
                                    numerohoras = p.horahomologacion if p.horahomologacion else ''
                                else:
                                    numerohoras = p.numerohora if p.numerohora else ''
                                campo_Especifico = "NINGUNO"
                                if p.inscripcion.carrera.malla_set.values('id').all().exists():
                                    if p.inscripcion.carrera.malla_set.all()[0].campo_especifico:
                                        campo_Especifico = u"%s" % p.inscripcion.carrera.malla_set.all()[0].campo_especifico.codigo
                                ws.write(row_num, 0, '1024', font_style2)
                                ws.write(row_num, 1, p.inscripcion.mi_malla().codigo if p.inscripcion.mi_malla() else '', font_style2)
                                ws.write(row_num, 2, u"MILAGRO", font_style2)
                                ws.write(row_num, 3, tipoidentificacion if tipoidentificacion else '', font_style2)
                                ws.write(row_num, 4, nidentificacion if nidentificacion else '', font_style2)
                                ws.write(row_num, 5, p.traer_empresa(), font_style2)
                                ws.write(row_num, 6, p.get_tipoinstitucion_display() if p.tipoinstitucion else '', font_style2)
                                ws.write(row_num, 7, p.fechadesde.strftime("%d-%m-%Y") if p.fechadesde else '', font_style2)
                                ws.write(row_num, 8, p.fechahasta.strftime("%d-%m-%Y") if p.fechahasta else '', font_style2)
                                ws.write(row_num, 9, numerohoras, font_style2)
                                ws.write(row_num, 10, campo_Especifico, font_style2)
                                ws.write(row_num, 11, identificaciondocentetutor, font_style2)
                                ws.write(row_num, 12, p.get_tipo_display(), font_style2)
                                row_num += 1
                            wb.save(response)
                            return response
                        except Exception as ex:
                            print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                            pass
                except Exception as ex:
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    pass

            elif action == 'matrizestudiantesprimernivel':
                try:
                    # periodo = ""
                    # if int(request.GET['id'])>0:
                    #     periodo = Periodo.objects.get(pk=int(request.GET['id']))
                    fini = int(request.GET['inicio'])
                    ffin = int(request.GET['fin'])
                    pfini = int(request.GET['pinicio'])
                    pffin = int(request.GET['pfin'])
                    __author__ = 'Unemi'
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    # nomperiodo = u'%s' % periodo
                    response['Content-Disposition'] = 'attachment; filename=Estudiantes ' + str(fini) + ' a ' + str(ffin) + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"TIPO_DOCUMENTO", 6000),
                        (u"DOCUMENTO", 6000),
                        (u"APELLIDOS", 6000),
                        (u"NOMBRES", 6000),
                        (u"NOMBRE_IES", 6000),
                        (u"CODIGO_IES", 6000),
                        (u"SEMESTRE", 6000),
                        (u"PERIODO_OBT_CUPO", 6000),
                        (u"CARRERA_ADMISION", 6000),
                        (u"CARRERA_ACTUAL", 6000),
                        (u"CAMPUS", 6000),
                        (u"MODALIDAD", 6000),
                        (u"JORNADA", 6000),
                        (u"ULTIMO_SEMESTRE_MATRICULA", 6000),
                        (u"ULTIMO_AÑO_MATRICULA", 6000),
                        (u"ESTADO_ACTUAL", 6000),
                        (u"OBSERVACIONES", 6000),
                        (u"FECHA_PRIMER_NIVEL", 6000),
                        (u"FECHA_CONVALIDACIÓN", 6000)
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    # inscriciones_f_con = Inscripcion.objects.values_list('id', flat=False).filter(Q(status=True), Q(fechainicioprimernivel__isnull=True), Q(fechainicioconvalidacion__isnull=False), Q(fechainicioconvalidacion__year__gte=fini), Q(fechainicioconvalidacion__year__lte=ffin)).distinct().exclude(coordinacion__id__in=[6,7,8])
                    # inscriciones_f_pri = Inscripcion.objects.values_list('id', flat=False).filter(Q(status=True), Q(fechainicioprimernivel__isnull=False), Q(fechainicioconvalidacion__isnull=True), Q(fechainicioprimernivel__year__gte=fini), Q(fechainicioprimernivel__year__lte=ffin)).distinct().exclude(coordinacion__id__in=[6,7,8])
                    # inscriciones = Inscripcion.objects.filter(Q(id__in=inscriciones_f_con)|Q(id__in=inscriciones_f_pri)).distinct()
                    # row_num = 1
                    # for i in inscriciones:
                    #     tipoidentificacion = 'CEDULA' if i.persona.cedula else 'PASAPORTE'
                    #     nidentificacion = i.persona.cedula if i.persona.cedula else i.persona.pasaporte
                    #     ultima_matricula = Matricula.objects.filter(inscripcion=i, status=True).order_by('-nivel__periodo__inicio')[0] if i.matricula_set.filter(status=True) else ''
                    #     primera_matricula = Matricula.objects.filter(inscripcion=i, status=True).order_by('nivel__periodo__inicio')[0] if i.matricula_set.filter(status=True) else ''
                    #     ws.write(row_num, 0, tipoidentificacion, font_style2)
                    #     ws.write(row_num, 1, nidentificacion, font_style2)
                    #     ws.write(row_num, 2, i.persona.apellido1 + ' ' + i.persona.apellido2, font_style2)
                    #     ws.write(row_num, 3, i.persona.nombres, font_style2)
                    #     ws.write(row_num, 4, 'UNIVERSIDAD ESTATAL DE MILAGRO UNEMI', font_style2)
                    #     ws.write(row_num, 5, '1024', font_style2)
                    #     ws.write(row_num, 6, str(primera_matricula.nivel.periodo) if str(primera_matricula).__len__()>0 else '', font_style2)
                    #     ws.write(row_num, 7, i.fechainicioprimernivel.strftime("%d/%m/%Y") if i.fechainicioprimernivel else '', font_style2)
                    #     # ws.write(row_num, 7, str(primera_matricula.nivel.periodo) if str(primera_matricula).__len__()>0 else '', font_style2)
                    #     ws.write(row_num, 8, str(i.carrera) if i.carrera else '', font_style2)
                    #     ws.write(row_num, 9, 'CAMPUS UNEMI', font_style2)
                    #     ws.write(row_num, 10, ultima_matricula.inscripcion.modalidad.nombre if ultima_matricula else '', font_style2)
                    #     ws.write(row_num, 11, ultima_matricula.inscripcion.sesion.nombre if ultima_matricula else '', font_style2)
                    #     ws.write(row_num, 12, str(ultima_matricula.nivelmalla.nombre) if ultima_matricula else '', font_style2)
                    #     ws.write(row_num, 13, str(ultima_matricula.nivel.periodo.fin.year) if ultima_matricula else '', font_style2)
                    #     ws.write(row_num, 14, '', font_style2)#estado actual
                    #     ws.write(row_num, 15, '', font_style2)#observaciones
                    #     ws.write(row_num, 16, i.fechainicioprimernivel.strftime("%d/%m/%Y") if i.fechainicioprimernivel else '', font_style2)
                    #     ws.write(row_num, 17, i.fechainicioconvalidacion.strftime("%d/%m/%Y") if i.fechainicioconvalidacion else '', font_style2)
                    #     row_num += 1
                    # wb.save(response)
                    # return response
                    cedulacarrera = []
                    for cc in CedulaCarrera.objects.filter(status=True):
                        cedulacarrera.append([cc.cedula, cc.carrera.nombre])

                    row_num = 1
                    for matriz in MatrizAdmision.objects.filter(status=True, periodomatrizadmision__id__gte=pfini, periodomatrizadmision__id__lte=pffin):
                        carrera = ''
                        modalidad = ''
                        jornada = ''
                        orden = ''
                        anio = ''
                        estadoaux = 'NO MATRICULADO'
                        primernivel = ''
                        convalidacion = ''
                        carreraadmision = matriz.carreraadmision.nombre
                        if matriz.estado == 0:
                            matricula = Matricula.objects.filter(nivel__periodo__inicio__year__gte=fini, nivel__periodo__inicio__year__lte=ffin, inscripcion__persona__cedula=matriz.cedula, status=True, estado_matricula__in=[2, 3]).exclude(inscripcion__carrera__coordinacion__id__in=[6, 7, 8, 9]).order_by('-nivel__periodo__inicio')
                            if matricula:
                                inscripcion = matricula[0].inscripcion
                                carrera = matricula[0].inscripcion.carrera.nombre
                                for c in cedulacarrera:
                                    if matriz.cedula.strip() in c[0].strip():
                                        carrera = c[1]

                                modalidad = inscripcion.modalidad.nombre
                                jornada = inscripcion.sesion.nombre
                                orden = str(matricula[0].nivelmalla.orden)
                                anio = str(matricula[0].nivel.periodo.inicio.year)
                                estadoaux = 'MATRICULADO'
                                primernivel = ''
                                if inscripcion.fechainicioprimernivel:
                                    primernivel = str(inscripcion.fechainicioprimernivel.strftime("%d/%m/%Y"))
                                convalidacion = ''
                                if inscripcion.fechainicioconvalidacion:
                                    convalidacion = str(inscripcion.fechainicioconvalidacion.strftime("%d/%m/%Y"))
                        campo1 = 'CEDULA'
                        campo2 = matriz.cedula
                        campo3 = matriz.apellidos
                        campo4 = matriz.nombres
                        campo5 = 'UNIVERSIDAD ESTATAL DE MILAGRO'
                        campo6 = '59'
                        campo7 = matriz.periodomatrizadmision.nombre
                        campo8 = matriz.periodomatrizadmision.per
                        campo9 = carrera
                        campo10 = 'UNEMI'
                        campo11 = modalidad
                        campo12 = jornada
                        campo13 = orden
                        campo14 = anio
                        campo15 = estadoaux
                        campo16 = ''
                        campo17 = primernivel
                        campo18 = convalidacion
                        ws.write(row_num, 0, campo1, font_style2)
                        ws.write(row_num, 1, campo2, font_style2)
                        ws.write(row_num, 2, campo3, font_style2)
                        ws.write(row_num, 3, campo4, font_style2)
                        ws.write(row_num, 4, campo5, font_style2)
                        ws.write(row_num, 5, campo6, font_style2)
                        ws.write(row_num, 6, campo7, font_style2)
                        ws.write(row_num, 7, campo8, font_style2)
                        ws.write(row_num, 8, carreraadmision, font_style2)
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
                        row_num += 1
                    wb.save(response)
                    return response

                except Exception as ex:
                    pass

            elif action == 'matrizanalisisestudiantes':
                try:
                    periodo = Periodo.objects.get(pk=int(request.GET['id']))
                    __author__ = 'Unemi'
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    nomperiodo = u'%s' % periodo
                    response['Content-Disposition'] = 'attachment; filename=Analisis_estadudiantes ' + str(periodo) + ' ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CÓDIGO IES", 6000),
                        (u"CÓDIGO CARRERA", 6000),
                        (u"NUMERO IDENTIFICACION", 6000),
                        (u"ESTADO CIVÍL", 6000),
                        (u"TIPO DE VIVIENDA", 6000),
                        (u"PARA ACCEDER A EDUCACIÓN SUPERIOR TUVO QUE CAMBIAR SU LUGAR DE RESIDENCIA?", 6000),
                        (u"ESTUDIÓ ANTES DE SU ACTUAL CARRERA EN ALGUNA INSTITUCIÓN DE EDUCACIÓN SUPERIOR Y CAMBIÓ DE INSTITUCIÓN DE ESTUDIO PARA CURSAR LA MISMA CARRERA?", 6000),
                        (u"CUÁL FUE LA PRINCIPAL RAZÓN PARA EL CAMBIO DE INSTITUCIÓN PARA CURSAR LA MISMA CARRERA.", 6000),
                        (u"¿ESTUDIÓ ANTES DE SU ACTUAL CARRERA EN ALGUNA INSTITUCIÓN DE EDUCACIÓN SUPERIOR Y CAMBIÓ LA CARRERA DE ESTUDIO EN LA MISMA O EN OTRA UNIVERSIDAD?", 6000),
                        (u"CUÁL FUE LA PRINCIPAL RAZÓN PARA EL CAMBIO DE CARRERA EN LA MISMA O EN OTRA UNIVERSIDAD", 6000),
                        (u"AL MOMENTO DE INICIAR SUS ESTUDIOS DE EDUCACIÓN SUPERIOR CUÁNTAS PERSONAS REALIZABAN UNA ACTIVIDAD ECONÓMICA REMUNERADA EN EL HOGAR.", 6000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                                      "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and mat.status=True and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                                      "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and mat.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (
                                          periodo.id, periodo.id)
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    respuestas = []
                    for per in results:
                        respuestas.append(per[0])
                    matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2, 3], status=True).exclude(pk__in=respuestas).exclude(retiromatricula__isnull=False)
                    row_num = 1
                    for mat in matriculados:
                        tipoidentificacion = 'CEDULA' if mat.inscripcion.persona.cedula else 'PASAPORTE'
                        nidentificacion = mat.inscripcion.persona.cedula if mat.inscripcion.persona.cedula else mat.inscripcion.persona.pasaporte
                        espre = False
                        if mat.inscripcion.coordinacion:
                            if mat.inscripcion.coordinacion.id == 9:
                                espre = True
                        if espre:
                            codigocarrera = '00098'
                        else:
                            codigocarrera = mat.inscripcion.mi_malla().codigo if mat.inscripcion.mi_malla() else ''
                        tipovivienda = ''
                        if mat.inscripcion.persona.fichasocioeconomicainec_set.filter(status=True):
                            ficha = mat.inscripcion.persona.fichasocioeconomicainec_set.filter(status=True)[0]
                            if ficha.tipoviviendapro:
                                tipovivienda = ficha.tipoviviendapro.nombre
                        numero = 0
                        if mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True).exists():
                            numero = mat.inscripcion.persona.personadatosfamiliares_set.filter(status=True, ingresomensual__gt=0).count()
                        ws.write(row_num, 0, '1024', font_style2)
                        ws.write(row_num, 1, codigocarrera, font_style2)
                        ws.write(row_num, 2, nidentificacion if nidentificacion else '', font_style2)
                        ws.write(row_num, 3, str(mat.inscripcion.persona.estado_civil()) if mat.inscripcion.persona.estado_civil() else '', font_style2)
                        ws.write(row_num, 4, tipovivienda, font_style2)
                        ws.write(row_num, 5, '', font_style2)
                        ws.write(row_num, 6, '', font_style2)
                        ws.write(row_num, 7, '', font_style2)
                        ws.write(row_num, 8, '', font_style2)
                        ws.write(row_num, 9, '', font_style2)
                        ws.write(row_num, 10, numero, font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'matrizanalisisperiodoacademico':
                try:
                    periodo = Periodo.objects.get(pk=int(request.GET['id']))
                    __author__ = 'Unemi'
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('exp_xls_post_part')
                    response = HttpResponse(content_type="application/ms-excel")
                    nomperiodo = u'%s' % periodo
                    response['Content-Disposition'] = 'attachment; filename=Análisis_Periodo_Académico ' + str(periodo) + ' ' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CÓDIGO IES", 6000),
                        (u"CÓDIGO CARRERA", 6000),
                        (u"NUMERO IDENTIFICACION", 6000),
                        (u"TIPO DE PARROQUIA EN LA QUE VIVE", 6000),
                        (u"DURANTE EL TRANSCURSO DE LOS ESTUDIOS ¿CUÁLES ERAN LOS ORÍGENES PRINCIPALES DE LOS RECURSOS PARA SU ESTUDIO?", 6000),
                        (u"DURANTE EL TRANSCURSO DE LOS ESTUDIOS ¿CUÁLES ERAN LOS ORÍGENES PRINCIPALES DE LOS RECURSOS ECONÓMICOS PARA SU SUSTENTO?", 6000),
                        (u"DURANTE ESTE PERIODO. REALIZÓ ALGUNA ACTIVIDAD ECONÓMICA REMUNERADA DE MANERA PERIÓDICA.", 6000),
                        (u"LA ACTIVIDAD ECONÓMICA QUE REALIZÓ DURANTE ESTE PERIODO ESTABA RELACIONADA CON SU ÁREA DE ESTUDIO.", 6000),
                        (u"DURANTE ESTE PERIODO. CUÁNTAS HORAS DE DEDICACIÓN A LA SEMANA REQUERÍA ESTA ACTIVIDAD ECONÓMICA.", 6000),
                        (u"CUÁL ES LA MOTIVACIÓN PRINCIPAL POR LA QUE REALIZABA ESTA ACTIVIDAD ECONÓMICA DURANTE ESTE PERIODO.", 6000),
                        (u"DURANTE ESTE PERIODO. TUVO ACCESO A INTERNET EN SU HOGAR?", 6000),
                        (u"NÚMERO DE DEPENDIENTES.", 6000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connection.cursor()
                    listaestudiante = "(select ma.id from (select  mat.id as id,count(ma.materia_id)  as numero " \
                                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma,sga_materia mate, " \
                                      "sga_asignatura asi, sga_inscripcion i where mat.estado_matricula in (2,3) and mat.status=True and i.id=mat.inscripcion_id and i.carrera_id not in (7) and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s" \
                                      "and asi.modulo=True group by mat.id) ma,(select  mat.id as id, count(ma.materia_id) as numero " \
                                      "from sga_Matricula mat , sga_Nivel n,sga_materiaasignada ma, " \
                                      "sga_materia mate, sga_asignatura asi where mat.estado_matricula in (2,3) and mat.status=True and mat.nivel_id=n.id and mat.id=ma.matricula_id " \
                                      "and ma.materia_id=mate.id and mate.asignatura_id=asi.id and n.periodo_id=%s group by mat.id) mo where ma.id=mo.id and ma.numero=mo.numero);" % (
                                          periodo.id, periodo.id)
                    cursor.execute(listaestudiante)
                    results = cursor.fetchall()
                    respuestas = []
                    for per in results:
                        respuestas.append(per[0])
                    matriculados = Matricula.objects.filter(nivel__periodo=periodo, estado_matricula__in=[2, 3], status=True).exclude(pk__in=respuestas).exclude(retiromatricula__isnull=False)
                    row_num = 1
                    for mat in matriculados:
                        tipoidentificacion = 'CEDULA' if mat.inscripcion.persona.cedula else 'PASAPORTE'
                        nidentificacion = mat.inscripcion.persona.cedula if mat.inscripcion.persona.cedula else mat.inscripcion.persona.pasaporte
                        espre = False
                        if mat.inscripcion.coordinacion:
                            if mat.inscripcion.coordinacion.id == 9:
                                espre = True
                        if espre:
                            codigocarrera = '00098'
                        else:
                            codigocarrera = mat.inscripcion.mi_malla().codigo if mat.inscripcion.mi_malla() else ''
                        tieneinternet = ''
                        if mat.inscripcion.persona.fichasocioeconomicainec_set.filter(status=True):
                            ficha = mat.inscripcion.persona.fichasocioeconomicainec_set.filter(status=True)[0]
                            tieneinternet = 'NO'
                            if ficha.tieneinternet:
                                tieneinternet = 'SI'
                        ws.write(row_num, 0, '1024', font_style2)
                        ws.write(row_num, 1, codigocarrera, font_style2)
                        # ws.write(row_num, 2, tipoidentificacion if tipoidentificacion else '', font_style2)
                        ws.write(row_num, 2, nidentificacion if nidentificacion else '', font_style2)
                        # ws.write(row_num, 3, str(mat.inscripcion.persona.estado_civil()) if mat.inscripcion.persona.estado_civil() else '', font_style2)
                        ws.write(row_num, 3, '', font_style2)
                        ws.write(row_num, 4, '', font_style2)
                        ws.write(row_num, 5, '', font_style2)
                        ws.write(row_num, 6, '', font_style2)
                        ws.write(row_num, 7, '', font_style2)
                        ws.write(row_num, 8, '', font_style2)
                        ws.write(row_num, 9, '', font_style2)
                        ws.write(row_num, 10, tieneinternet, font_style2)
                        ws.write(row_num, 11, '', font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'importar':
                try:
                    data['title'] = u'Subir Archivo'
                    data['form'] = ImportarArchivoXLSForm()
                    return render(request, "descargaarchivo/importar.html", data)
                except Exception as ex:
                    pass

            elif action == 'formreporte':
                try:
                    form = PeriodoMutipleForm()
                    data['form2'] = form
                    template = get_template("descargaarchivo/formreporte.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'resumen_matricula_carrera':
                try:
                    periodos_filter = tuple(request.GET.getlist('periodo'))
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('Hoja1')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=resumen' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CARRERA", 6000),
                        (u"CANTIDAD", 6000),
                    ]
                    row_num = 0
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    row_num = 1
                    cursor = connection.cursor()
                    sql = f"""SELECT DISTINCT  carr1.nombre AS nombre_carrera,(
                        select COUNT(tabla.*) FROM(
                        SELECT DISTINCT ON (ins0.persona_id) ins0.persona_id
                        FROM sga_matricula matri0 
                        INNER JOIN sga_inscripcion ins0 ON matri0.inscripcion_id = ins0.id
                        INNER JOIN sga_nivel niv0 ON matri0.nivel_id = niv0.id
                        WHERE matri0.status = TRUE 
                        AND ins0.status = TRUE 
                        AND matri0.estado_matricula in (2,3) 
                        AND matri0.retiradomatricula = FALSE 
                        AND niv0.periodo_id IN {periodos_filter} 
                        AND ins0.carrera_id = carr1.id
                        AND matri0.id not IN(
                        SELECT DISTINCT "sga_matricula"."id"
                        FROM "sga_matricula"
                        INNER JOIN "sga_nivel" ON ("sga_matricula"."nivel_id" = "sga_nivel"."id")
                        INNER JOIN "sga_periodo" ON ("sga_nivel"."periodo_id" = "sga_periodo"."id")
                        INNER JOIN "sga_materiaasignada" ON ("sga_matricula"."id" = "sga_materiaasignada"."matricula_id")
                        INNER JOIN "sga_materia" ON ("sga_materiaasignada"."materia_id" = "sga_materia"."id")
                        INNER JOIN "sga_asignatura" ON ("sga_materia"."asignatura_id" = "sga_asignatura"."id")
                        INNER JOIN "sga_inscripcion" ON ("sga_matricula"."inscripcion_id" = "sga_inscripcion"."id")
                        WHERE ("sga_matricula"."estado_matricula" = 2 AND "sga_nivel"."periodo_id" in {periodos_filter}
                        AND "sga_matricula"."status" = TRUE AND "sga_asignatura"."modulo" = TRUE
                        AND ((SELECT COUNT(mta.id)
                        FROM sga_materiaasignada mta
                        WHERE mta.matricula_id=sga_matricula.id) = 1)
                        AND NOT ("sga_inscripcion"."carrera_id" IN (
                        SELECT U3."carrera_id" AS Col1
                        FROM "sga_coordinacion_carrera" U3
                        WHERE U3."coordinacion_id" = 9))
                        AND NOT ("sga_inscripcion"."carrera_id" = 7)
                        AND NOT ("sga_matricula"."retiradomatricula" = TRUE))
                        )
                        ORDER BY ins0.persona_id ASC
                        )AS tabla
                        )
                        FROM sga_carrera carr1
                        WHERE (carr1.id IN 
                        (SELECT DISTINCT U2."carrera_id" 
                        FROM "sga_materia" U0 
                        LEFT OUTER JOIN "sga_asignaturamalla" U1 ON (U0."asignaturamalla_id" = U1."id") 
                        LEFT OUTER JOIN "sga_malla" U2 ON (U1."malla_id" = U2."id") 
                        INNER JOIN "sga_nivel" U4 ON (U0."nivel_id" = U4."id") 
                        WHERE U4."periodo_id" IN {periodos_filter})) 
                        ORDER BY nombre_carrera ASC """
                    cursor.execute(sql)
                    for x in cursor.fetchall():
                        ws.write(row_num, 0, u'%s' % x[0], font_style2)
                        ws.write(row_num, 1, u'%s' % x[1], font_style2)
                        row_num += 1
                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            # ========= PESTAñA CACES / AUTH: ROALEX =========

            elif action == 'cargos_academicos_directivos':
                try:

                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 40)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'bold': True})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    ws.write(0, 0, 'TIPO DE IDENTIFICACIÓN', formatoceldagris)
                    ws.write(0, 1, 'IDENTIFICACIÓN', formatoceldagris)
                    ws.write(0, 2, 'NOMBRE COMPLETO', formatoceldagris)
                    ws.write(0, 3, 'SEXO', formatoceldagris)
                    ws.write(0, 4, 'FECHA INICIO', formatoceldagris)
                    ws.write(0, 5, 'FECHA FIN', formatoceldagris)
                    ws.write(0, 6, 'NÚMERO DE DOCUMENTO', formatoceldagris)
                    ws.write(0, 7, 'CARGO', formatoceldagris)

                    filtros = Q(descripcion__contains='DIRECTOR/A DE CARRERA') \
                              | Q(descripcion__contains='DIRECTOR DE CARRERA') \
                              | Q(descripcion__contains='VICERRECTOR/A ACADEMICO') \
                              | Q(descripcion__contains='DECANO/AS') \
                              | Q(descripcion__contains='DECANO') \
                              | Q(descripcion__contains='SUBDECANO/AS') \
                              | Q(descripcion__contains='COORDINADOR') \
                              | Q(descripcion__contains='COORDINADOR/A') \
                              | Q(descripcion__contains='JEFE/A') \
                              | Q(descripcion__contains='SECRETARIO/A') \
                              | Q(descripcion__contains='RECTOR/A')

                    sexo = int(request.GET['sexo'])
                    if sexo == 0:
                        cargos = DenominacionPuesto.objects.all()
                        cargos_filtrados = cargos.filter(filtros, status=True).values_list('id', flat=True)
                        distributivo = DistributivoPersona.objects.filter(status=True,
                                                                          estadopuesto=1,
                                                                          denominacionpuesto__in=cargos_filtrados).distinct().order_by('persona')
                    elif sexo == 1:
                        cargos = DenominacionPuesto.objects.all()
                        cargos_filtrados = cargos.filter(filtros, status=True).values_list('id', flat=True)
                        distributivo = DistributivoPersona.objects.filter(status=True,
                                                                          estadopuesto=1,
                                                                          denominacionpuesto__in=cargos_filtrados,
                                                                          persona__sexo_id=2).distinct().order_by('persona')
                    elif sexo == 2:
                        cargos = DenominacionPuesto.objects.all()
                        cargos_filtrados = cargos.filter(filtros, status=True).values_list('id', flat=True)
                        distributivo = DistributivoPersona.objects.filter(status=True,
                                                                          estadopuesto=1,
                                                                          denominacionpuesto__in=cargos_filtrados,
                                                                          persona__sexo_id=1).distinct().order_by('persona')

                    fila_directivo = 2

                    for directivo in distributivo:
                        ws.write('A%s' % fila_directivo, str(''), formatoceldaleft)
                        ws.write('B%s' % fila_directivo, str(directivo.persona.cedula), formatoceldaleft)
                        ws.write('C%s' % fila_directivo, str(directivo.persona), formatoceldaleft)
                        ws.write('D%s' % fila_directivo, str(directivo.persona.sexo), formatoceldaleft)
                        ws.write('E%s' % fila_directivo, str(''), formatoceldaleft)
                        ws.write('F%s' % fila_directivo, str(''), formatoceldaleft)
                        ws.write('G%s' % fila_directivo, str(''), formatoceldaleft)
                        ws.write('H%s' % fila_directivo, str(directivo.denominacionpuesto), formatoceldaleft)
                        fila_directivo += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'plantilla_cargos_academicos_directivos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'profesores_contratos':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 40)

                    formatoceldagris = workbook.add_format({'align': 'center', 'border': 1, 'text_wrap': True, 'bold': True})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    ws.write(0, 0, 'CODIGO_IES', formatoceldagris)
                    ws.write(0, 1, 'TIPO_IDENTIFICACION', formatoceldagris)
                    ws.write(0, 2, 'IDENTIFICACION', formatoceldagris)
                    ws.write(0, 3, 'NOMBRES COMPLETOS', formatoceldagris)
                    ws.write(0, 4, 'SEXO', formatoceldagris)
                    ws.write(0, 5, 'FECHA_NACIMIENTO', formatoceldagris)
                    ws.write(0, 6, 'PAIS_ORIGEN', formatoceldagris)
                    ws.write(0, 7, 'DISCAPACIDAD', formatoceldagris)
                    ws.write(0, 8, 'PORCENTAJE_DISCAPACIDAD', formatoceldagris)
                    ws.write(0, 9, 'NUMERO_CONADIS', formatoceldagris)
                    ws.write(0, 10, 'ETNIA', formatoceldagris)
                    ws.write(0, 11, 'NACIONALIDAD', formatoceldagris)
                    ws.write(0, 12, 'DIRECCION', formatoceldagris)
                    ws.write(0, 13, 'EMAIL_PERSONAL', formatoceldagris)
                    ws.write(0, 14, 'EMAIL_INSTITUCIONAL', formatoceldagris)
                    ws.write(0, 15, 'TIPO_DOCUMENTO', formatoceldagris)
                    ws.write(0, 16, 'NUMERO_DOCUMENTO', formatoceldagris)
                    ws.write(0, 17, 'CONTRATO_RELACIONADO', formatoceldagris)
                    ws.write(0, 18, 'INGRESO_POR_CONCURSO', formatoceldagris)
                    ws.write(0, 19, 'RELACION_IES', formatoceldagris)
                    ws.write(0, 20, 'TIPO_ESCALAFON_NOMBRAMIENTO', formatoceldagris)
                    ws.write(0, 21, 'CATEGORIA', formatoceldagris)
                    ws.write(0, 22, 'TIEMPO_DEDICACION', formatoceldagris)
                    ws.write(0, 23, 'REMUNERACION_MES', formatoceldagris)
                    ws.write(0, 24, 'REMUNERACION_HORA', formatoceldagris)
                    ws.write(0, 25, 'FECHA_INGRESO_IES', formatoceldagris)
                    ws.write(0, 26, 'FECHA_INICIO', formatoceldagris)
                    ws.write(0, 27, 'FECHA_FIN', formatoceldagris)
                    ws.write(0, 28, 'NIVEL', formatoceldagris)
                    ws.write(0, 29, 'UNIDAD_ACADEMICA', formatoceldagris)

                    categoria = ProfesorTipo.objects.filter(status=True).values_list('id', flat=True)
                    escalafon = NivelEscalafonDocente.objects.filter(status=True).values_list('id', flat=True)
                    docente = Profesor.objects.filter(status=True, nivelescalafon__in=escalafon, nivelcategoria__in=categoria).values_list('id', flat=True)
                    personacontrato = PersonaContratos.objects.filter(status=True, persona__in=docente).distinct()

                    fila_profesor = 2
                    for i in personacontrato:
                        docentecontrato = i.persona.profesor_set.filter(status=True)
                        perfil = i.persona.mi_perfil()

                        por_concurso = "NO"
                        if i.persona.concursomeritos:
                            por_concurso = "SI"

                        relacion_ies = "No registra"
                        if i.relacionies == 1:
                            relacion_ies = "NOMBRAMIENTO"
                        elif i.relacionies == 2:
                            relacion_ies = "CONTRATO CON RELACION DE DEPENDENCIA"
                        elif i.relacionies == 3:
                            relacion_ies = "CONTRATO SIN RELACION DE DEPENDENCIA"
                        elif i.relacionies == 4:
                            relacion_ies = "PROMETEO"

                        nidentificacion = i.persona.cedula if i.persona.cedula else i.persona.pasaporte
                        tipoidentificacion = 'CEDULA' if i.persona.cedula else 'PASAPORTE'

                        ws.write('A%s' % fila_profesor, str('1024'), formatoceldaleft)
                        ws.write('B%s' % fila_profesor, str(tipoidentificacion), formatoceldaleft)
                        ws.write('C%s' % fila_profesor, str(nidentificacion), formatoceldaleft)
                        ws.write('D%s' % fila_profesor, str(i.persona), formatoceldaleft)
                        ws.write('E%s' % fila_profesor, str(i.persona.sexo), formatoceldaleft)
                        ws.write('F%s' % fila_profesor, str(i.persona.nacimiento), formatoceldaleft)
                        ws.write('G%s' % fila_profesor, str(i.persona.pais), formatoceldaleft)
                        ws.write('H%s' % fila_profesor, str(perfil.tipodiscapacidad if perfil.tipodiscapacidad else 'No existe registro'), formatoceldaleft)
                        ws.write('I%s' % fila_profesor, str(perfil.porcientodiscapacidad if perfil.porcientodiscapacidad else 'No existe registro'), formatoceldaleft)
                        ws.write('J%s' % fila_profesor, str(perfil.carnetdiscapacidad if perfil.carnetdiscapacidad else 'No existe registro'), formatoceldaleft)
                        ws.write('K%s' % fila_profesor, str(perfil.raza if perfil.raza else 'No existe registro'), formatoceldaleft)
                        ws.write('L%s' % fila_profesor, str(i.persona.nacionalidad if i.persona.nacionalidad else 'No existe registro'), formatoceldaleft)
                        ws.write('M%s' % fila_profesor, str(i.persona.direccion if i.persona.direccion else 'No existe registro'), formatoceldaleft)
                        ws.write('N%s' % fila_profesor, str(i.persona.email if i.persona.email else 'No existe registro'), formatoceldaleft)
                        ws.write('O%s' % fila_profesor, str(i.persona.emailinst if i.persona.emailinst else 'No existe registro'), formatoceldaleft)
                        ws.write('P%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('Q%s' % fila_profesor, str(i.numerodocumento if i.numerodocumento else 'No existe registro'), formatoceldaleft)
                        ws.write('R%s' % fila_profesor, str(i.contratacionrelacionada if i.contratacionrelacionada else 'No existe registro'), formatoceldaleft)
                        ws.write('S%s' % fila_profesor, str(por_concurso), formatoceldaleft)
                        ws.write('T%s' % fila_profesor, str(relacion_ies), formatoceldaleft)
                        ws.write('U%s' % fila_profesor, str(docentecontrato[0].nivelescalafon if docentecontrato[0].nivelescalafon else 'No existe registro'), formatoceldaleft)
                        ws.write('V%s' % fila_profesor, str(docentecontrato[0].nivelcategoria if docentecontrato[0].nivelcategoria else 'No existe registro'), formatoceldaleft)
                        ws.write('W%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('X%s' % fila_profesor, str(i.remuneracion if i.remuneracion else 'No existe registro'), formatoceldaleft)
                        ws.write('Y%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('Z%s' % fila_profesor, str(i.persona.fechaingresoies if i.persona.fechaingresoies else 'No existe registro'), formatoceldaleft)
                        ws.write('AA%s' % fila_profesor, str(i.fechainicio if i.fechainicio else 'No existe registro'), formatoceldaleft)
                        ws.write('AB%s' % fila_profesor, str(i.fechafin if i.fechafin else 'No existe registro'), formatoceldaleft)
                        ws.write('AC%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('AD%s' % fila_profesor, str(''), formatoceldaleft)

                        fila_profesor += 1

                    workbook.close()
                    output.seek(0)
                    filename = 'profesores_contratos.xlsx'
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelgraduados':
                try:
                    anio = int(request.GET['anio'])
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('graduadosposgrado_hoja')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=graduadosposgrado' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CODIGO_IES", 2000),
                        (u"CODIGO_CARRERA", 4000),
                        (u"NOMBRE_CARRERA", 8000),
                        (u"TIPO_IDENTIFICACIÓN", 5000),
                        (u"IDENTIFICACION", 4000),
                        (u"PRIMER_APELLIDO", 6000),
                        (u"SEGUNDO_APELLIDO", 6000),
                        (u"NOMBRES", 6000),
                        (u"SEXO", 6000),
                        (u"FECHA_NACIMIENTO", 5000),
                        (u"PAIS_ORIGEN", 5000),
                        (u"DISCAPACIDAD", 6000),
                        (u"NUMERO_CONADIS", 4000),
                        (u"DIRECCION", 8000),
                        (u"EMAIL_PERSONAL", 6000),
                        (u"EMAIL_INSTITUCIONAL", 6000),
                        (u"FECHA_INICIO_PRIMER_NIVEL", 6000),
                        (u"FECHA_INGRESO_CONVALIDACION", 6000),
                        (u"FECHA_GRADUACION", 5000),
                        (u"MECANISMO_TITULACION", 8000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connections['sga_select'].cursor()
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    sql = f"""
                                                    SELECT
'1024' AS CODIGO_IES,
carr.codigo AS CODIGO_CARRERA,
carr.nombre AS NOMBRE_CARRERA,
(CASE WHEN pers0.pasaporte != '' AND pers0.pasaporte IS NOT NULL THEN 'PASAPORTE' ELSE 'CEDULA' END) AS TIPO_IDENTIFICACION, 
(CASE WHEN pers0.pasaporte != '' AND pers0.pasaporte IS NOT NULL THEN pers0.pasaporte ELSE pers0.cedula END) AS IDENTIFICACION,
pers0.apellido1 AS PRIMER_APELLIDO,
pers0.apellido2 AS SEGUNDO_APELLIDO,
pers0.nombres AS NOMBRES,
sex.nombre AS sexo, TO_CHAR(pers0.nacimiento, 'DD-MM-YYYY') AS FECHA_NACIMIENTO, (
SELECT pa.nombre
FROM sga_pais pa
WHERE pa.id=pers0.paisnacimiento_id) PAIS_ORIGEN,
(
SELECT (CASE WHEN perf.tienediscapacidad = TRUE THEN 'SI' ELSE 'NO' END)
FROM sga_perfilinscripcion AS perf
WHERE perf.persona_id = pers0.id) AS DISCAPACIDAD,
(
SELECT perf.carnetdiscapacidad
FROM sga_perfilinscripcion AS perf
WHERE perf.persona_id = pers0.id) AS NUMERO_CONADIS,
pers0.direccion AS DIRECCION,
pers0.email AS EMAIL_PERSONAL,
pers0.emailinst AS EMAIL_INSTITUCIONAL, 
(
SELECT TO_CHAR(mt.inicio, 'DD-MM-YYYY')
FROM sga_materiaasignada maa
INNER JOIN sga_materia mt ON mt.id=maa.materia_id
INNER JOIN sga_matricula matricula ON matricula.id=maa.matricula_id
WHERE matricula.inscripcion_id=ins0.id AND mt.status = TRUE AND maa."status"= TRUE AND matricula.inscripcion_id = ins0.id AND maa.retiramateria= FALSE
ORDER BY mt.inicio
LIMIT 1

) AS FECHA_INICIO_PRIMER_NIVEL,
'NO' AS FECHA_INGRESO_CONVALIDACION, TO_CHAR(graduado.fechagraduado, 'DD-MM-YYYY') AS FECHA_GRADUACION,
(
SELECT array_to_string(array_agg(DISTINCT mcti.nombre),',')
FROM sga_matricula matr
INNER JOIN sga_tematitulacionposgradomatricula tma ON tma.matricula_id = matr.id
INNER JOIN sga_mecanismotitulacion mcti ON tma.mecanismotitulacionposgrado_id = mcti.id
WHERE matr.inscripcion_id = ins0.id AND tma.status= TRUE AND mcti.status = TRUE
) AS MECANISMO_TITULACION
FROM sga_graduado graduado
INNER JOIN sga_inscripcion ins0 ON graduado.inscripcion_id = ins0.id
INNER JOIN sga_persona pers0 ON pers0.id=ins0.persona_id
LEFT JOIN sga_sexo sex ON sex.id=pers0.sexo_id
INNER JOIN sga_carrera carr ON carr.id=ins0.carrera_id
INNER JOIN sga_coordinacion_carrera cc ON cc.carrera_id=carr.id
INNER JOIN sga_coordinacion coor ON coor.id=cc.coordinacion_id
WHERE coor.id=7 AND ins0.status = TRUE AND pers0."status"= TRUE AND graduado.status= TRUE AND (EXTRACT(YEAR
FROM graduado.fechagraduado) = {anio} OR EXTRACT(YEAR
FROM graduado.fecharefrendacion) = {anio})
ORDER BY graduado.fechagraduado
                                                """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0
                        campo0 = r[0]
                        campo1 = r[1]
                        campo2 = r[2]
                        campo3 = r[3]
                        campo4 = r[4]
                        campo5 = r[5]
                        campo6 = r[6]
                        campo7 = r[7]
                        campo8 = r[8]
                        campo9 = r[9]
                        campo10 = r[10]
                        campo11 = r[11]
                        campo12 = r[12]
                        campo13 = r[13]
                        campo14 = r[14]
                        campo15 = r[15]
                        campo16 = r[16]
                        campo17 = r[17]
                        campo18 = r[18]
                        campo19 = r[19]

                        ws.write(row_num, 0, campo0, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
                        ws.write(row_num, 8, campo8, font_style2)
                        ws.write(row_num, 9, campo9, date_format)
                        ws.write(row_num, 10, campo10, font_style2)
                        ws.write(row_num, 11, campo11, font_style2)
                        ws.write(row_num, 12, campo12, font_style2)
                        ws.write(row_num, 13, campo13, font_style2)
                        ws.write(row_num, 14, campo14, font_style2)
                        ws.write(row_num, 15, campo15, font_style2)
                        ws.write(row_num, 16, campo16, date_format)
                        ws.write(row_num, 17, campo17, font_style2)
                        ws.write(row_num, 18, campo18, date_format)
                        ws.write(row_num, 19, campo19, font_style2)

                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelgraduados2':
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Graduados Posgrado', destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_graduados_posgrado(request=request, notiid=notifi.id).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de Graduados Posgrado se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'excelestudiantesposgrado':
                try:
                    anio = int(request.GET['anio'])
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('estudiantesposgrado_hoja')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=estudiantesposgrado' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"PERIODO", 2000),
                        (u"DESDE", 7000),
                        (u"HASTA", 4000),
                        (u"CODIGO_CARRERA", 8000),
                        (u"TIPO_IDENTIFICACION", 8000),
                        (u"IDENTIFICACION", 8000),
                        (u"PRIMER_APELLIDO", 10000),
                        (u"SEGUNDO_APELLIDO", 3000),
                        (u"NOMBRES", 5000),
                        (u"SEXO", 5000),
                        (u"FECHA_NACIMIENTO", 3000),
                        (u"PAIS_ORIGEN", 4000),
                        (u"DISCAPACIDAD", 3000),
                        (u"PORCENTAJE_DISCAPACIDAD", 3000),
                        (u"NUMERO_CONADIS", 4000),
                        (u"ETNIA", 6000),
                        (u"NACIONALIDAD", 6000),
                        (u"DIRECCION", 5000),
                        (u"EMAIL_PERSONAL", 8000),
                        (u"EMAIL_INSTITUCIONAL", 8000),
                        (u"FECHA_INICIO_PRIMER_NIVEL", 7000),
                        (u"PAIS_RESIDENCIA", 7000),
                        (u"PROVINCIA_RESIDENCIA", 5000),
                        (u"CANTON_RESIDENCIA", 5000),
                        (u"CELULAR", 3000),
                        (u"NIVEL_FORMACION_PADRE", 2000),
                        (u"NIVEL_FORMACION_MADRE", 2000),
                        (u"CANTIDAD_MIEMBROS_HOGAR", 2000),
                        (u"TIPO_COLEGIO", 5000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connections['sga_select'].cursor()
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    sql = f"""
SELECT
per0.nombre AS periodo,
TO_CHAR(per0.inicio, 'DD-MM-YYYY') AS desde, TO_CHAR(per0.fin, 'DD-MM-YYYY') AS hasta,
carr.codigo AS CODIGO_CARRERA,
(CASE WHEN pers0.pasaporte != '' AND pers0.pasaporte != NULL THEN 'PASAPORTE' ELSE 'CEDULA' END) AS TIPO_IDENTIFICACION, 
(CASE WHEN pers0.pasaporte != '' AND pers0.pasaporte != NULL THEN pers0.pasaporte ELSE pers0.cedula END) AS IDENTIFICACION, 
pers0.apellido1 AS PRIMER_APELLIDO,
pers0.apellido2 AS SEGUNDO_APELLIDO,
pers0.nombres AS NOMBRES,
sex.nombre AS sexo,
TO_CHAR(pers0.nacimiento, 'DD-MM-YYYY') AS FECHA_NACIMIENTO, (
SELECT pa.nombre
FROM sga_pais pa
WHERE pa.id=pers0.paisnacimiento_id) PAIS_ORIGEN,
(
SELECT (CASE WHEN perf.tienediscapacidad = True THEN 'SI' ELSE 'NO' END)
FROM sga_perfilinscripcion AS perf
WHERE perf.persona_id = pers0.id) AS DISCAPACIDAD,
(
SELECT perf.porcientodiscapacidad
FROM sga_perfilinscripcion AS perf
WHERE perf.persona_id = pers0.id) AS PORCENTAJE_DISCAPACIDAD,
(
SELECT perf.carnetdiscapacidad
FROM sga_perfilinscripcion AS perf
WHERE perf.persona_id = pers0.id) AS NUMERO_CONADIS,
(
SELECT raza.nombre
FROM sga_perfilinscripcion perf
INNER JOIN sga_raza raza ON raza.id=perf.raza_id
WHERE perf.persona_id=pers0.id) AS ETNIA,
pers0.nacionalidad AS NACIONALIDAD,
pers0.direccion||' '||pers0.direccion2||' '||pers0.referencia AS DIRECCION,

pers0.email AS EMAIL_PERSONAL,
pers0.emailinst AS EMAIL_INSTITUCIONAL, 
(SELECT TO_CHAR(mt.inicio, 'DD-MM-YYYY') 
FROM sga_materiaasignada maa
INNER JOIN sga_materia mt ON mt.id=maa.materia_id
WHERE  maa.matricula_id=matri0.id AND   mt.status = TRUE AND maa."status"=TRUE
AND maa.retiramateria= False
ORDER BY mt.inicio LIMIT 1
)  AS FECHA_INICIO_PRIMER_NIVEL
,
(
SELECT pa.nombre
FROM sga_pais pa
WHERE pa.id=pers0.pais_id) AS PAIS_RESIDENCIA,
(
SELECT prov.nombre
FROM sga_provincia prov
WHERE prov.id=pers0.provincia_id) AS PROVINCIA_RESIDENCIA,
(
SELECT cant.nombre
FROM sga_canton cant
WHERE cant.id=pers0.canton_id) AS CANTON_RESIDENCIA,
pers0.telefono AS CELULAR,
(
SELECT niv.nombre
FROM sga_personadatosfamiliares datfam
INNER JOIN sga_niveltitulacion niv ON datfam.niveltitulacion_id = niv.id
WHERE datfam.persona_id=pers0.id AND datfam.parentesco_id=1 AND datfam.status =TRUE LIMIT 1) AS NIVEL_FORMACION_PADRE,
(
SELECT niv.nombre
FROM sga_personadatosfamiliares datfam
INNER JOIN sga_niveltitulacion niv ON datfam.niveltitulacion_id = niv.id
WHERE datfam.persona_id=pers0.id AND datfam.parentesco_id=2 AND datfam.status =TRUE LIMIT 1) AS NIVEL_FORMACION_MADRE,
(
SELECT COUNT(datfam.id)
FROM sga_personadatosfamiliares datfam
WHERE datfam.persona_id=pers0.id AND datfam.status=TRUE) AS CANTIDAD_MIEMBROS_HOGAR,
(SELECT (CASE WHEN colg.tipo = 1 THEN 'FISCAL' 
					WHEN colg.tipo = 2 THEN 'FISCOMISIONAL' 
					WHEN colg.tipo = 3 THEN 'MUNICIPAL'
					WHEN colg.tipo = 4 THEN 'PARTICULAR'
					WHEN colg.tipo = 5 THEN 'EXTRANJERO'
					WHEN colg.tipo = 6 THEN 'NO REGISTRA'
					ELSE 'NO REGISTRA'
					END) FROM sga_titulacion titu
INNER JOIN  sga_colegio colg ON titu.colegio_id = colg.id
WHERE titu.persona_id = pers0.id AND titu.status = TRUE AND colg."status" = TRUE LIMIT 1 ) AS TIPO_COLEGIO
FROM sga_matricula matri0
INNER JOIN sga_inscripcion ins0 ON matri0.inscripcion_id = ins0.id
INNER JOIN sga_nivel niv0 ON matri0.nivel_id = niv0.id
INNER JOIN sga_periodo per0 ON per0.id=niv0.periodo_id
INNER JOIN sga_persona pers0 ON pers0.id=ins0.persona_id
INNER JOIN sga_sexo sex ON sex.id=pers0.sexo_id
INNER JOIN sga_modalidad moda ON moda.id=ins0.modalidad_id
INNER JOIN sga_carrera carr ON carr.id=ins0.carrera_id
INNER JOIN sga_coordinacion_carrera cc ON cc.carrera_id=carr.id
INNER JOIN sga_coordinacion coor ON coor.id=cc.coordinacion_id
WHERE matri0.status = TRUE AND ins0.status = TRUE AND matri0.retiradomatricula = FALSE AND coor.id=7
AND per0.anio = {anio} ORDER BY per0.nombre

   """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0

                        campo0 = r[0]
                        campo1 = r[1]
                        campo2 = r[2]
                        campo3 = r[3]
                        campo4 = r[4]
                        campo5 = r[5]
                        campo6 = r[6]
                        campo7 = r[7]
                        campo8 = r[8]
                        campo9 = r[9]
                        campo10 = r[10]
                        campo11 = r[11]
                        campo12 = r[12]
                        campo13 = r[13]
                        campo14 = r[14]
                        campo15 = r[15]
                        campo16 = r[16]
                        campo17 = r[17]
                        campo18 = r[18]
                        campo19 = r[19]
                        campo20 = r[20]
                        campo21 = r[21]
                        campo22 = r[22]
                        campo23 = r[23]
                        campo24 = r[24]
                        campo25 = r[25]
                        campo26 = r[26]
                        campo27 = r[27]
                        campo28 = r[28]

                        ws.write(row_num, 0, campo0, font_style2)
                        ws.write(row_num, 1, campo1, date_format)
                        ws.write(row_num, 2, campo2, date_format)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
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
                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelestudiantesposgrado2':
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de Estudiantes Posgrado', destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_estudiantes_posgrado(request=request, notiid=notifi.id).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de Estudiantes Posgrado se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'excelmatriculadosposgrado':
                try:
                    anio = int(request.GET['anio'])
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off',
                                    num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on',
                                      num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf(
                        'font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('matriculadosposgrado_hoja')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=matriculadosposgrado' + random.randint(1,
                                                                                                                  10000).__str__() + '.xls'
                    columns = [
                        (u"PERIODO", 2000),
                        (u"DESDE", 7000),
                        (u"HASTA", 4000),
                        (u"CODIGO_IES", 4000),
                        (u"CODIGO_CARRERA", 8000),
                        (u"TIPO_IDENTIFICACION", 8000),
                        (u"IDENTIFICACION", 8000),
                        (u"TOTAL_CREDITOS_APROBADOS", 5000),
                        (u"CREDITOS_APROBADOS", 5000),
                        (u"TIPO_MATRICULA", 5000),
                        (u"PARALELO", 5000),
                        (u"NIVEL_ACADEMICO", 5000),
                        (u"DURACION_PERIODO_ACADEMICO", 5000),
                        (u"NUM_MATERIAS_SEGUNDA_MATRICULA", 5000),
                        (u"NUM_MATERIAS_TERCERA_MATRICULA", 5000),
                        (u"PERDIDA_GRATUIDAD", 5000),
                        (u"PENSION_DIFERENCIADA", 5000),
                        (u"PLAN_CONTINGENCIA", 5000),
                        (u"INGRESO_TOTAL_HOGAR", 5000),
                        (u"ORIGEN_RECURSOS_ESTUDIO", 5000),
                        (u"TERMINO_PERIODO", 5000),
                        (u"TOTAL_HORAS_APROBADAS", 5000),
                        (u"HORAS_APROBADAS", 5000),
                        (u"MONTO_AYUDA_ECONOMICA", 5000),
                        (u"MONTO_CREDITO_EDUCATIVO", 5000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connections['sga_select'].cursor()
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    sql = f"""
       SELECT
per0.nombre AS periodo,
TO_CHAR(per0.inicio, 'DD-MM-YYYY') AS inicio,
TO_CHAR(per0.fin, 'DD-MM-YYYY') AS fin,
'1024' AS CODIGO_IES,
carr.codigo AS CODIGO_CARRERA,
(CASE WHEN pers0.pasaporte != '' AND pers0.pasaporte != NULL THEN 'PASAPORTE' ELSE 'CEDULA' END) AS TIPO_IDENTIFICACION, 
(CASE WHEN pers0.pasaporte != '' AND pers0.pasaporte != NULL THEN pers0.pasaporte ELSE pers0.cedula END) AS IDENTIFICACION,
(
SELECT ROUND(SUM(recd.creditos), 2)
FROM sga_recordacademico recd
WHERE recd.valida = TRUE AND recd.status = TRUE AND recd.inscripcion_id=ins0.id AND recd.aprobada=True) AS TOTAL_CREDITOS_APROBADOS,

(
SELECT mall.creditos_completar
FROM sga_inscripcionmalla insmall
INNER JOIN sga_malla mall ON mall.id=insmall.malla_id
WHERE insmall.inscripcion_id=ins0.id
) AS CREDITOS_APROBADOS,
'TIPO_MATRICULA',
(
SELECT array_to_string(array_agg(distinct mate.paralelo),',') 
FROM sga_materiaasignada maa
INNER JOIN sga_materia mate ON maa.materia_id=mate.id 
INNER JOIN sga_matricula matri ON matri.id=maa.matricula_id
WHERE matri0.id=matri.id) AS PARALELO,
'1' AS NIVEL_ACADEMICO,
(
SELECT COUNT(matasig.id)
FROM sga_materiaasignada matasig
WHERE matasig.matricula_id = matri0.id AND matasig.status = TRUE) AS DURACION_PERIODO_ACADEMICO,
(
SELECT COUNT(matasig.id)
FROM sga_materiaasignada matasig
WHERE matasig.matricula_id = matri0.id AND matasig.matriculas = 2 AND matasig.status = TRUE) AS NUM_MATERIAS_SEGUNDA_MATRICULA,
(
SELECT COUNT(matasig.id)
FROM sga_materiaasignada matasig
WHERE matasig.matricula_id = matri0.id AND matasig.matriculas = 3 AND matasig.status = TRUE) AS NUM_MATERIAS_TERCERA_MATRICULA,
'NO' AS PERDIDA_GRATUIDAD,
'NO APLICA' AS PENSION_DIFERENCIADA,
'NO APLICA' AS PLAN_CONTINGENCIA,
'NO REGISTRA' AS INGRESO_TOTAL_HOGAR,
'NO REGISTRA' AS ORIGEN_RECURSOS_ESTUDIO,
'NO' AS TERMINO_PERIODO,
(
SELECT SUM(recd.horas)
FROM sga_recordacademico recd
WHERE recd.valida = TRUE AND recd.status = TRUE AND recd.inscripcion_id=ins0.id AND recd.aprobada=True) AS TOTAL_HORAS_APROBADAS,
(SELECT matr.totalhoras FROM sga_matricula matr WHERE matr.id = matri0.id) AS HORAS_APROBADAS,
'0' AS MONTO_AYUDA_ECONOMICA,
'0' AS MONTO_CREDITO_EDUCATIVO


FROM sga_matricula matri0
INNER JOIN sga_inscripcion ins0 ON matri0.inscripcion_id = ins0.id
INNER JOIN sga_nivel niv0 ON matri0.nivel_id = niv0.id
INNER JOIN sga_periodo per0 ON per0.id=niv0.periodo_id
INNER JOIN sga_persona pers0 ON pers0.id=ins0.persona_id
INNER JOIN sga_sexo sex ON sex.id=pers0.sexo_id
INNER JOIN sga_modalidad moda ON moda.id=ins0.modalidad_id
INNER JOIN sga_carrera carr ON carr.id=ins0.carrera_id
INNER JOIN sga_coordinacion_carrera cc ON cc.carrera_id=carr.id
INNER JOIN sga_coordinacion coor ON coor.id=cc.coordinacion_id
WHERE matri0.status = TRUE AND ins0.status = TRUE AND matri0.retiradomatricula = FALSE 
AND coor.id=7 AND per0.anio={anio} ORDER BY per0.nombre
           """
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0

                        campo0 = r[0]
                        campo1 = r[1]
                        campo2 = r[2]
                        campo3 = r[3]
                        campo4 = r[4]
                        campo5 = r[5]
                        campo6 = r[6]
                        campo7 = r[7]
                        campo8 = r[8]
                        campo9 = r[9]
                        campo10 = r[10]
                        campo11 = r[11]
                        campo12 = r[12]
                        campo13 = r[13]
                        campo14 = r[14]
                        campo15 = r[15]
                        campo16 = r[16]
                        campo17 = r[17]
                        campo18 = r[18]
                        campo19 = r[19]
                        campo20 = r[20]
                        campo21 = r[21]
                        campo22 = r[22]
                        campo23 = r[23]
                        campo24 = r[24]


                        ws.write(row_num, 0, campo0, font_style2)
                        ws.write(row_num, 1, campo1, date_format)
                        ws.write(row_num, 2, campo2, date_format)
                        ws.write(row_num, 3, campo3, font_style2)
                        ws.write(row_num, 4, campo4, font_style2)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)
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

                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelmatriculadosposgrado2':
                try:
                    notifi = Notificacion(cuerpo='Generación de reporte de excel en progreso',
                                          titulo='Reporte de Estudiantes - Matrícula Periodo Académico (Posgrado)', destinatario=persona,
                                          url='',
                                          prioridad=1, app_label='SGA',
                                          fecha_hora_visible=datetime.now() + timedelta(days=1), tipo=2,
                                          en_proceso=True)
                    notifi.save(request)
                    reporte_estudiantes_matricula_posgrado(request=request, notiid=notifi.id).start()
                    return JsonResponse({"result": True,
                                         "mensaje": u"El reporte de  Estudiantes - Matrícula Periodo Académico (Posgrado) se está realizando. Verifique su apartado de notificaciones después de unos minutos.",
                                         "btn_notificaciones": traerNotificaciones(request, data, persona)})
                except Exception as ex:
                    pass

            elif action == 'excelperiodosposgrado':
                try:
                    anio = int(request.GET['anio'])
                    __author__ = 'Unemi'
                    style0 = easyxf('font: name Times New Roman, color-index blue, bold off', num_format_str='#,##0.00')
                    style_nb = easyxf('font: name Times New Roman, color-index blue, bold on', num_format_str='#,##0.00')
                    style_sb = easyxf('font: name Times New Roman, color-index blue, bold on')
                    title = easyxf('font: name Times New Roman, color-index blue, bold on , height 350; alignment: horiz centre')
                    style1 = easyxf(num_format_str='D-MMM-YY')
                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('periodosposgrado_hoja')
                    ws.write_merge(0, 0, 0, 6, 'UNIVERSIDAD ESTATAL DE MILAGRO', title)
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=periodosposgrado' + random.randint(1, 10000).__str__() + '.xls'
                    columns = [
                        (u"CODIGO", 3000),
                        (u"MAESTRIA", 7000),
                        (u"COHORTE", 4000),
                        (u"FECHA_INICIO", 6000),
                        (u"FECHA_FIN", 6000),
                        (u"TIPO_PERIODO", 4000),
                        (u"ORGANIZACIÓN", 8000),
                        (u"ESPECIFICAR_OTRA_ORGANIZACIÓN", 8000)
                    ]
                    row_num = 3
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], font_style)
                        ws.col(col_num).width = columns[col_num][1]
                    cursor = connections['sga_select'].cursor()
                    date_format = xlwt.XFStyle()
                    date_format.num_format_str = 'yyyy/mm/dd'
                    sql = f"""
                                                   SELECT per.id AS CODIGO, mae.descripcion AS MAESTRIA, 
per.nombre AS COHORTE, 
TO_CHAR(pco.fechainiciocohorte, 'DD-MM-YYYY') AS FECHA_INICIO, 
TO_CHAR(pco.fechafincohorte, 'DD-MM-YYYY') AS FECHA_FIN,
(CASE when pco.tipo = 1 THEN 'EXAMEN Y ENTREVISTA'
		WHEN pco.tipo = 2 THEN 'EXAMEN' 
		WHEN pco.tipo = 3 THEN 'APROBACIÓN DE REQUISITOS' END) AS TIPO_PERIODO,
'' AS ORGANIZACION,
'' AS ESPECIFICAR_OTRA_ORGANIZACIÓN

FROM sga_periodo per
JOIN posgrado_cohortemaestria pco ON per.id = pco.periodoacademico_id
JOIN posgrado_maestriasadmision mae ON pco.maestriaadmision_id = mae.id
WHERE per.status=TRUE AND pco.status=TRUE AND mae.status=TRUE AND (per.anio = {anio} OR per.nombre ILIKE '%{anio}%') 
ORDER BY per.nombre
"""
                    cursor.execute(sql)
                    results = cursor.fetchall()
                    row_num = 4
                    for r in results:
                        i = 0
                        campo0 = r[0]
                        campo1 = r[1]
                        campo2 = r[2]
                        campo3 = r[3]
                        campo4 = r[4]
                        campo5 = r[5]
                        campo6 = r[6]
                        campo7 = r[7]
                        ws.write(row_num, 0, campo0, font_style2)
                        ws.write(row_num, 1, campo1, font_style2)
                        ws.write(row_num, 2, campo2, font_style2)
                        ws.write(row_num, 3, campo3, date_format)
                        ws.write(row_num, 4, campo4, date_format)
                        ws.write(row_num, 5, campo5, font_style2)
                        ws.write(row_num, 6, campo6, font_style2)
                        ws.write(row_num, 7, campo7, font_style2)

                        row_num += 1
                    wb.save(response)
                    connection.close()
                    return response
                except Exception as ex:
                    pass

            elif action == 'excelperiodosposgrado2':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('periodos_posgrado')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 60)
                    ws.set_column(2, 2, 20)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 15)
                    ws.set_column(5, 5, 15)
                    ws.set_column(6, 6, 20)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '#,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '#,##0.0', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    anio = maestria = 0

                    if 'maestria' in request.GET:
                        maestria = request.GET['maestria']

                    if 'anio' in request.GET:
                        anio = request.GET['anio']

                    ws.merge_range('A1:G1', 'TABLA DE ARANCELES, MATRÍCULAS Y DERECHOS POR PROGRAMA, CORRESPONDIENTE A LOS PERIODOS ACADÉMICOS)', formatotitulo_filtros)
                    ws.merge_range('C2:G2', 'ARANCELES)', formatotitulo_filtros)
                    ws.merge_range('A2:B2', '', formatotitulo_filtros)

                    ws.write(2, 0, 'AÑO', formatoceldacab)
                    ws.write(2, 1, 'NOMBRE DEL PROGRAMA DE MAESTRÍA', formatoceldacab)
                    ws.write(2, 2, 'COHORTE', formatoceldacab)
                    ws.write(2, 3, 'ADMISIÓN', formatoceldacab)
                    ws.write(2, 4, 'MATRÍCULA', formatoceldacab)
                    ws.write(2, 5, 'COLEGIATURA', formatoceldacab)
                    ws.write(2, 6, 'COSTO TOTAL DEL PROGRAMA', formatoceldacab)

                    filtro = Q(status=True)

                    if maestria != "":
                        if eval(request.GET['maestria'])[0] != "0":
                            filtro = filtro & Q(maestriaadmision__carrera__id__in=eval(request.GET['maestria']))

                    if anio != "":
                        if eval(request.GET['anio'])[0] != "0":
                            filtro = filtro & Q(fecha_creacion__year__in=eval(request.GET['anio']))

                    cohortes = CohorteMaestria.objects.filter(filtro).order_by('maestriaadmision__fecha_creacion',
                                                                               'maestriaadmision__carrera__nombre')

                    filas_recorridas = 4
                    cont = 1
                    for cohorte in cohortes:
                        ws.write('A%s' % filas_recorridas, str(cohorte.maestriaadmision.fecha_creacion.date().year), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(cohorte.maestriaadmision.carrera.nombre + ' MODALIDAD ' + cohorte.maestriaadmision.carrera.get_modalidad_display()), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(cohorte.descripcion), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str('0.00'), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str('0.00'), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str('0.00'), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, cohorte.valorprogramacertificado, decimalformat)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Periodos_Académicos_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'prof_formacion_terminada':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('plantilla_')
                    ws.set_column(0, 100, 60)

                    formatoceldagris = workbook.add_format(
                        {'align': 'center', 'border': 1, 'text_wrap': True, 'bold': True})
                    formatoceldaleft = workbook.add_format({'text_wrap': True, 'align': 'left'})

                    ws.write(0, 0, 'CODIGO_IES', formatoceldagris)
                    ws.write(0, 1, 'TIPO_IDENTIFICACION', formatoceldagris)
                    ws.write(0, 2, 'IDENTIFICACION', formatoceldagris)
                    ws.write(0, 3, 'PAIS_ESTUDIO', formatoceldagris)
                    ws.write(0, 4, 'CODIGO_IES_ESTUDIO', formatoceldagris)
                    ws.write(0, 5, 'NOMBRE_IES', formatoceldagris)
                    ws.write(0, 6, 'NIVEL', formatoceldagris)
                    ws.write(0, 7, 'GRADO', formatoceldagris)
                    ws.write(0, 8, 'NOMBRE_TITULO', formatoceldagris)
                    ws.write(0, 9, 'CODIGO_SUBAREA_CONOCIMIENTO_ESPECIFICO_UNESCO', formatoceldagris)
                    ws.write(0, 10, 'NUMERO_REGISTRO_SENESCYT', formatoceldagris)
                    ws.write(0, 11, 'FECHA_OBTUVO_TITULO', formatoceldagris)

                    profesor = Profesor.objects.filter(status=True).values_list('id', flat=True)
                    personatitulacion = Titulacion.objects.filter(status=True, cursando=False, persona__in=profesor, titulo__nivel_id__in=[3, 4]).distinct()

                    fila_profesor = 2
                    for dato_titulacion in personatitulacion:
                        ws.write('A%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('B%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('C%s' % fila_profesor, str(dato_titulacion.persona.cedula), formatoceldaleft)
                        ws.write('D%s' % fila_profesor, str(dato_titulacion.pais), formatoceldaleft)
                        ws.write('E%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('F%s' % fila_profesor, str(''), formatoceldaleft)
                        ws.write('G%s' % fila_profesor, str(dato_titulacion.titulo.nivel), formatoceldaleft)
                        ws.write('H%s' % fila_profesor, str(dato_titulacion.titulo.grado), formatoceldaleft)
                        ws.write('I%s' % fila_profesor, str(dato_titulacion.titulo), formatoceldaleft)
                        ws.write('J%s' % fila_profesor, str(dato_titulacion.titulo.subareaconocimiento), formatoceldaleft)
                        ws.write('K%s' % fila_profesor, str(dato_titulacion.registro), formatoceldaleft)
                        ws.write('L%s' % fila_profesor, str(dato_titulacion.fechaobtencion), formatoceldaleft)
                        fila_profesor += 1

                    # cont=1
                    # for datoti in personatitulacion:
                    #     print(cont,
                    #             " | ",datoti.persona.cedula,
                    #           " | ",datoti.persona,
                    #           " | ",datoti.pais,
                    #           " | ",datoti.titulo.nivel,
                    #           " | ",datoti.titulo.grado,
                    #           " | ",datoti.titulo,
                    #           " | ",datoti.titulo.subareaconocimiento,
                    #           " | ",datoti.registro,
                    #           " | ",datoti.fechaobtencion)
                    #     cont+=1

                    workbook.close()
                    output.seek(0)
                    filename = 'profesores_formacion_profesional.xlsx'  # % (contrato.descripcion)
                    response = HttpResponse(output,
                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'reportematriculadoscohortes':
                try:
                    __author__ = 'Unemi'

                    output = io.BytesIO()
                    workbook = xlsxwriter.Workbook(output)
                    ws = workbook.add_worksheet('listado_matriculados')
                    ws.set_column(0, 0, 10)
                    ws.set_column(1, 1, 10)
                    ws.set_column(2, 2, 15)
                    ws.set_column(3, 3, 15)
                    ws.set_column(4, 4, 40)
                    ws.set_column(5, 5, 40)
                    ws.set_column(6, 6, 50)
                    ws.set_column(7, 7, 15)
                    ws.set_column(8, 8, 15)
                    ws.set_column(9, 9, 30)
                    ws.set_column(10, 10, 30)
                    ws.set_column(11, 11, 25)
                    ws.set_column(12, 12, 30)
                    ws.set_column(13, 13, 15)
                    ws.set_column(14, 14, 15)
                    ws.set_column(15, 15, 15)
                    ws.set_column(16, 16, 15)
                    ws.set_column(17, 17, 15)
                    ws.set_column(18, 18, 15)

                    formatotitulo_filtros = workbook.add_format(
                        {'bold': 1, 'text_wrap': True, 'border': 1, 'align': 'center', 'font_size': 14})

                    formatoceldacab = workbook.add_format(
                        {'align': 'center', 'bold': 1, 'border': 1, 'text_wrap': True, 'fg_color': '#1C3247', 'font_color': 'white'})
                    formatoceldaleft = workbook.add_format(
                        {'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    formatoceldaleft2 = workbook.add_format(
                        {'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    formatoceldaleft3 = workbook.add_format(
                        {'text_wrap': True, 'align': 'right', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    decimalformat = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1})

                    decimalformat2 = workbook.add_format({'num_format': '$ #,##0.00', 'text_wrap': True, 'align': 'center', 'valign': 'vcenter', 'border': 1, 'bold': 1})

                    maestria = period = 0

                    if 'maestria' in request.GET:
                        maestria = request.GET['maestria']
                    if 'periodo' in request.GET:
                        period = request.GET['periodo']

                    ws.merge_range('A1:S1', 'Reporte general de matriculados', formatotitulo_filtros)

                    ws.write(2, 0, 'N°', formatoceldacab)
                    ws.write(2, 1, 'Id', formatoceldacab)
                    ws.write(2, 2, 'Fecha de matrícula', formatoceldacab)
                    ws.write(2, 3, 'Cédula', formatoceldacab)
                    ws.write(2, 4, 'Maestrante', formatoceldacab)
                    ws.write(2, 5, 'Maestría', formatoceldacab)
                    ws.write(2, 6, 'Cohorte', formatoceldacab)
                    ws.write(2, 7, 'Paralelo', formatoceldacab)
                    ws.write(2, 8, 'Teléfono', formatoceldacab)
                    ws.write(2, 9, 'Correo personal', formatoceldacab)
                    ws.write(2, 10, 'Correo institucional', formatoceldacab)
                    ws.write(2, 11, 'Cantón', formatoceldacab)
                    ws.write(2, 12, 'Dirección', formatoceldacab)
                    ws.write(2, 13, '¿Matriculado?', formatoceldacab)
                    ws.write(2, 14, '¿Retirado?', formatoceldacab)
                    ws.write(2, 15, '¿Graduado?', formatoceldacab)
                    ws.write(2, 16, '¿Malla completa?', formatoceldacab)
                    ws.write(2, 17, '¿Malla incompleta?', formatoceldacab)
                    ws.write(2, 18, 'Fecha de graduación', formatoceldacab)

                    filtro = Q(status=True, inscripcion__carrera__coordinacion__id=7)

                    if maestria != "":
                        filtro = filtro & Q(inscripcion__carrera__id=int(request.GET['maestria']))

                    if period != "":
                       filtro = filtro & Q(nivel__periodo__id=int(request.GET['periodo']))

                    matriculados = Matricula.objects.filter(filtro).order_by('inscripcion__persona__apellido1',
                                                                             'inscripcion__persona__apellido2',
                                                                             'inscripcion__persona__nombres')

                    filas_recorridas = 4
                    cont = 1

                    for matriculado in matriculados:
                        ws.write('A%s' % filas_recorridas, str(cont), formatoceldaleft)
                        ws.write('B%s' % filas_recorridas, str(matriculado.id), formatoceldaleft)
                        ws.write('C%s' % filas_recorridas, str(matriculado.fecha), formatoceldaleft)
                        ws.write('D%s' % filas_recorridas, str(matriculado.inscripcion.persona.identificacion()), formatoceldaleft)
                        ws.write('E%s' % filas_recorridas, str(matriculado.inscripcion.persona.nombre_completo_inverso()), formatoceldaleft)
                        ws.write('F%s' % filas_recorridas, str(matriculado.inscripcion.carrera.nombre), formatoceldaleft)
                        ws.write('G%s' % filas_recorridas, str(matriculado.nivel.periodo), formatoceldaleft)
                        ws.write('H%s' % filas_recorridas, str(curso_matriculado(matriculado)), formatoceldaleft)
                        ws.write('I%s' % filas_recorridas, str(matriculado.inscripcion.persona.telefono if matriculado.inscripcion.persona.telefono else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('J%s' % filas_recorridas, str(matriculado.inscripcion.persona.email if matriculado.inscripcion.persona.email else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('K%s' % filas_recorridas, str(matriculado.inscripcion.persona.emailinst if matriculado.inscripcion.persona.emailinst else 'NO REGISTRA'), formatoceldaleft)
                        ws.write('L%s' % filas_recorridas, str(matriculado.inscripcion.persona.canton.nombre if matriculado.inscripcion.persona.canton else 'POR ASIGNAR'), formatoceldaleft)
                        ws.write('M%s' % filas_recorridas, str(matriculado.inscripcion.persona.direccion if matriculado.inscripcion.persona.direccion else 'POR ASIGNAR'), formatoceldaleft)
                        ws.write('N%s' % filas_recorridas, str('NO' if retirado(matriculado) else 'SI'), formatoceldaleft)
                        ws.write('O%s' % filas_recorridas, str('SI' if retirado(matriculado) else 'NO'), formatoceldaleft)
                        ws.write('P%s' % filas_recorridas, str('SI' if graduado2(matriculado) else 'NO'), formatoceldaleft)
                        ws.write('Q%s' % filas_recorridas, str('SI' if malla_completa(matriculado) else 'NO'), formatoceldaleft)
                        ws.write('R%s' % filas_recorridas, str('NO' if malla_completa(matriculado) else 'SI'), formatoceldaleft)
                        ws.write('S%s' % filas_recorridas, str(graduadofecha(matriculado)), formatoceldaleft)

                        filas_recorridas += 1
                        cont += 1

                    workbook.close()
                    output.seek(0)
                    fecha_hora_actual = datetime.now().date()
                    filename = 'Listado_matriculados_' + str(fecha_hora_actual) + '.xlsx'
                    response = HttpResponse(output,

                                            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    response['Content-Disposition'] = 'attachment; filename=%s' % filename
                    return response
                except Exception as ex:
                    pass

            elif action == 'cargar_carrera':
                try:
                    lista = []
                    carreras = Carrera.objects.filter(status=True, coordinacion__id=7).order_by('-id')

                    for carrera in carreras:
                        namecarrer = f'{carrera.nombre} MODALIDAD {carrera.get_modalidad_display()}'
                        if carrera.mencion:
                            namecarrer = f'{carrera.nombre} CON MENCIÓN EN {carrera.mencion} MODALIDAD {carrera.get_modalidad_display()}'
                        if not buscar_dicc(lista, 'id', carrera.id):
                            lista.append({'id': carrera.id, 'nombre': namecarrer})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'cargar_periodo':
                try:
                    lista = []
                    periodos = Periodo.objects.filter(status=True, tipo__id=3).exclude(nombre__icontains='TITU').order_by('nombre')

                    for periodo in periodos:
                        if not buscar_dicc(lista, 'id', periodo.id):
                            lista.append({'id': periodo.id, 'nombre': periodo.__str__()})
                    return JsonResponse({'result': 'ok', 'lista': lista})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Descarga de Archivos'

                data['anios'] = anios = rango_anios()
                if 'anio' in request.GET:
                    request.session['anioarchivo'] = int(request.GET['anio'])
                if 'anioarchivo' not in request.session:
                    request.session['anioarchivo'] = anios[0]
                data['anioselect'] = anioselect = request.session['anioarchivo']
                data['descargaarchivoceaaces'] = DescargaArchivo.objects.filter(tipo=1, anio=anioselect)
                data['descargaarchivosnieser'] = DescargaArchivo.objects.filter(tipo=2, anio=anioselect)
                data['reporte_cumplimiento'] = obtener_reporte('cumplimiento_proyectos')
                data['reporte_proyectos'] = obtener_reporte('docentes_que_participan_en_proyectos_investigacion')
                data['reporte_publicaciones'] = obtener_reporte('docentes_que_participan_en_publicaciones')
                data['reporte_ponencias'] = obtener_reporte('ponencias_realizadas_por_docentes')
                data['eAnios'] = Matricula.objects.filter(status=True, inscripcion__carrera__coordinacion__id=7, retiradomatricula=False, inscripcion__status=True).values_list('fecha__year', flat=True).order_by(
                    '-fecha__year').distinct()
                return render(request, "descargaarchivo/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect("/?info=Error. %s" % ex)
