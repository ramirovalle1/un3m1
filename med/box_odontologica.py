# -*- coding: latin-1 -*-
import json
import os
import random
import glob
from datetime import datetime, time
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from xlwt import easyxf, Workbook, XFStyle

from decorators import secure_module, last_access
from med.forms import PersonaConsultaOdontologicaForm, AntecedenteOdontologicoForm, AlergiaForm, Alergia2Form, \
    FechaFichaMedicaForm, AccionConsultaForm
from med.models import Odontograma, PersonaConsultaOdontologica, ProximaCita, TIPO_PACIENTE, CatalogoEnfermedad, \
    PersonaExamenFisico, AntecedenteOdontologico, PersonaFichaMedica, AccionConsulta
from sagest.models import DistributivoPersona
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, calcula_edad, calcula_edad_fn_fc, grafica_barra
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, Matricula, Coordinacion, Carrera, NivelMalla, PALETA_COLORES


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'afd':
            try:
                odontrograma = Odontograma.objects.get(pk=request.POST['id'])
                diente = request.POST['iid']
                mv = request.POST['mv']
                valor_actual = odontrograma.__getattribute__("pieza_" + diente)
                if mv == '0':
                    odontrograma.__setattr__("pieza_" + diente, "00000")
                if mv == '1':
                    sid = int(request.POST['sid'])
                    valor_final = valor_actual[:sid] + "1" + valor_actual[sid + 1:]
                    odontrograma.__setattr__("pieza_" + diente, valor_final)
                if mv == '5':
                    sid = int(request.POST['sid'])
                    valor_final = valor_actual[:sid] + "5" + valor_actual[sid + 1:]
                    odontrograma.__setattr__("pieza_" + diente, valor_final)
                if mv == '2':
                    odontrograma.__setattr__("pieza_" + diente, "22222")
                if mv == '3':
                    odontrograma.__setattr__("pieza_" + diente, "33333")
                if mv == '4':
                    sid = int(request.POST['sid'])
                    valor_final = valor_actual[:sid] + "4" + valor_actual[sid + 1:]
                    odontrograma.__setattr__("pieza_" + diente, valor_final)
                odontrograma.save(request)
                log(u'Adiciono odontograma: %s' % odontrograma.fichamedica.personaextension.persona, request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificar_atenciones':
            try:
                persona = request.session['persona']
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'],
                                                                                             '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    tipopaciente = int(request.POST['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    atenciones = PersonaConsultaOdontologica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True)

                    if atenciones:
                        # if esdirectordbu is False:
                        #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                        if atenciones:
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_atencionesfc':
            try:
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'],
                                                                                             '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    facultad = int(request.POST['facultad'])
                    carrera = int(request.POST['carrera'])
                    tipopaciente = int(request.POST['tipopaciente'])

                    atenciones = PersonaConsultaOdontologica.objects.filter(fecha__range=(desde, hasta), status=True)

                    if atenciones:
                        if tipopaciente == 3:
                            atenciones = atenciones.filter(tipopaciente=3)
                            if facultad != 0:
                                fac = Coordinacion.objects.get(pk=facultad)
                                atenciones = atenciones.filter(matricula__inscripcion__coordinacion=fac)
                                if carrera != 0:
                                    carr = Carrera.objects.get(pk=carrera)
                                    atenciones = atenciones.filter(matricula__inscripcion__carrera=carr)

                        # if esdirectordbu is False:
                        #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                        if atenciones:
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse(
                        {"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'resumengeneralareaodontologica':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área Odontológica'
                atenciones = PersonaConsultaOdontologica.objects.filter(fecha__range=(desde, hasta), status=True)

                # if not esdirectordbu:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                totaladminf = atenciones.filter(tipopaciente=1, persona__sexo_id=1).count()
                totaladminm = atenciones.filter(tipopaciente=1, persona__sexo_id=2).count()
                totaldocenf = atenciones.filter(tipopaciente=2, persona__sexo_id=1).count()
                totaldocenm = atenciones.filter(tipopaciente=2, persona__sexo_id=2).count()
                totalestuf = atenciones.filter(tipopaciente=3, persona__sexo_id=1).count()
                totalestum = atenciones.filter(tipopaciente=3, persona__sexo_id=2).count()
                totalpartf = atenciones.filter(tipopaciente=4, persona__sexo_id=1).count()
                totalpartm = atenciones.filter(tipopaciente=4, persona__sexo_id=2).count()
                totalepunf = atenciones.filter(tipopaciente=5, persona__sexo_id=1).count()
                totalepunm = atenciones.filter(tipopaciente=5, persona__sexo_id=2).count()
                totaltrabf = atenciones.filter(tipopaciente=6, persona__sexo_id=1).count()
                totaltrabm = atenciones.filter(tipopaciente=6, persona__sexo_id=2).count()
                totalnivf = atenciones.filter(tipopaciente=7, persona__sexo_id=1).count()
                totalnivm = atenciones.filter(tipopaciente=7, persona__sexo_id=2).count()
                totalgeneral = atenciones.count()

                data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                titulos = persona.titulo3y4nivel()
                data['titulo1'] = titulos['tit1']
                data['titulo2'] = titulos['tit2']
                data['medico'] = persona
                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['totaladminf'] = totaladminf
                data['totaladminm'] = totaladminm
                data['totaldocenf'] = totaldocenf
                data['totaldocenm'] = totaldocenm
                data['totalestuf'] = totalestuf
                data['totalestum'] = totalestum
                data['totalpartf'] = totalpartf
                data['totalpartm'] = totalpartm
                data['totalepunf'] = totalepunf
                data['totalepunm'] = totalepunm
                data['totaltrabf'] = totaltrabf
                data['totaltrabm'] = totaltrabm
                data['totalnivf'] = totalnivf
                data['totalnivm'] = totalnivm
                data['totalfemenino'] = totalfemenino = totaladminf + totaldocenf + totalestuf + totalpartf + totalepunf + totaltrabf + totalnivf
                data['totalmasculino'] = totalmasculino = totaladminm + totaldocenm + totalestum + totalpartm + totalepunm + totaltrabm + totalnivm
                data['totalgeneral'] = totalgeneral
                data['fecha'] = datetime.now().date()
                data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''

                nusuario = str(persona.usuario)
                area = "odon"
                filename = "ge_" + area + "_" + nusuario + "_"

                path_to_save = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar')) + '/'

                for filenameremove in glob.glob(path_to_save + "/" + filename + "*"):
                    os.remove(filenameremove)

                titulografica = "ATENCIONES POR TIPO DE PACIENTE"
                totaladmin = totaladminf + totaladminm
                totaldocen = totaldocenf + totaldocenm
                totalestu = totalestuf + totalestum
                totalpart = totalpartf + totalpartm
                totalepun = totalepunf + totalepunm
                totaltrab = totaltrabf + totaltrabm
                totalniv = totalnivf + totalnivm

                padmin = round((totaladmin * 100) / totalgeneral, 2)
                pdocen = round((totaldocen * 100) / totalgeneral, 2)
                pestu = round((totalestu * 100) / totalgeneral, 2)
                ppart = round((totalpart * 100) / totalgeneral, 2)
                pepun = round((totalepun * 100) / totalgeneral, 2)
                ptrab = round((totaltrab * 100) / totalgeneral, 2)
                pniv = round((totalniv * 100) / totalgeneral, 2)

                valores = [[padmin, pdocen, pestu, ppart, pepun, ptrab, pniv]]
                categorias = ['ADMINISTRATIVOS', 'DOCENTES', 'ESTUDIANTES',
                              'PARTICULARES', 'PARTICULARES/EPUNEMI', 'TRABAJADORES', 'NIVELACION']
                mostrarsimboloporcentaje = True
                tieneleyenda = False
                barrasagrupadas = False
                coloresindividual = [PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3],
                                     PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3]]
                coloresagrupado = []
                leyenda = []

                imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
                                       leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                data['imagen1'] = path_to_save + filename + ".png"

                titulografica = "ATENCIONES POR TIPO DE GÉNERO"
                porcfem = round((totalfemenino * 100) / totalgeneral, 2)
                porcmasc = round((totalmasculino * 100) / totalgeneral, 2)
                valores = [[porcfem, porcmasc]]
                categorias = ['FEMENINO', 'MASCULINO']
                mostrarsimboloporcentaje = True
                tieneleyenda = False
                barrasagrupadas = False
                coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[5]]
                coloresagrupado = []
                leyenda = []

                imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
                                       leyenda,
                                       barrasagrupadas, coloresindividual, coloresagrupado)

                filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                data['imagen2'] = path_to_save + filename + ".png"

                return conviert_html_to_pdf(
                    'box_medical/resumengeneral_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )
            except Exception as ex:
                pass

        elif action == 'resumengeneralareaodontologicatipocita':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                tipopaciente = int(request.POST['tipopaciente'])
                facultad = int(request.POST['facultad'])
                carrera = int(request.POST['carrera'])

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área Odontológica por Tipo de Cita'
                atenciones = PersonaConsultaOdontologica.objects.filter(fecha__range=(desde, hasta), status=True)

                datos = []
                # if not esdirectordbu:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                if facultad != 0 and carrera != 0:
                    fac = Coordinacion.objects.get(pk=facultad)
                    carr = Carrera.objects.get(pk=carrera)
                    atenciones = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                   matricula__inscripcion__carrera=carr).order_by(
                        'matricula__inscripcion__coordinacion', 'matricula__inscripcion__carrera',
                        'matricula__nivelmalla_id')
                elif facultad != 0:
                    fac = Coordinacion.objects.get(pk=facultad)
                    atenciones = atenciones.filter(matricula__inscripcion__coordinacion=fac).order_by(
                        'matricula__inscripcion__coordinacion', 'matricula__inscripcion__carrera',
                        'matricula__nivelmalla_id')

                nusuario = str(persona.usuario)
                area = "odon"
                filename = "ge_" + area + "_" + nusuario + "_"

                path_to_save = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar')) + '/'

                for filenameremove in glob.glob(path_to_save + "/" + filename + "*"):
                    os.remove(filenameremove)

                if tipopaciente != 3:
                    total1vez = atenciones.filter(tipopaciente=1, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=1, primeravez=False).count()
                    datos.append(['ADMINISTRATIVO', total1vez, totalsubsec])

                    total1vez = atenciones.filter(tipopaciente=2, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=2, primeravez=False).count()
                    datos.append(['DOCENTE', total1vez, totalsubsec])

                    total1vez = atenciones.filter(tipopaciente=3, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=3, primeravez=False).count()
                    datos.append(['ESTUDIANTE', total1vez, totalsubsec])

                    total1vez = atenciones.filter(tipopaciente=4, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=4, primeravez=False).count()
                    datos.append(['PARTICULAR', total1vez, totalsubsec])

                    total1vez = atenciones.filter(tipopaciente=5, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=5, primeravez=False).count()
                    datos.append(['PARTICULAR/EPUNEMI', total1vez, totalsubsec])

                    total1vez = atenciones.filter(tipopaciente=6, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=6, primeravez=False).count()
                    datos.append(['TRABAJADOR', total1vez, totalsubsec])

                    total1vez = atenciones.filter(tipopaciente=7, primeravez=True).count()
                    totalsubsec = atenciones.filter(tipopaciente=7, primeravez=False).count()
                    datos.append(['NIVELACION', total1vez, totalsubsec])

                    totalgeneral1vez = atenciones.filter(primeravez=True).count()
                    totalgeneralsubsec = atenciones.filter(primeravez=False).count()
                    totalgeneral = atenciones.count()

                    titulografica = "ATENCIONES PRIMERA VEZ"
                    valores = [
                        [datos[0][1], datos[1][1], datos[2][1], datos[3][1], datos[4][1], datos[5][1], datos[6][1]]]
                    categorias = [datos[0][0], datos[1][0], datos[2][0], datos[3][0], datos[4][0], datos[5][0],
                                  datos[6][0]]
                    mostrarsimboloporcentaje = False
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[2], PALETA_COLORES[2], PALETA_COLORES[2],
                                         PALETA_COLORES[2], PALETA_COLORES[2], PALETA_COLORES[2]]
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    data['imagen1'] = path_to_save + filename + ".png"

                    titulografica = "ATENCIONES SUBSECUENTES"
                    valores = [[datos[0][2], datos[1][2], datos[2][2], datos[3][2], datos[4][2], datos[5][2], datos[6][2]]]
                    categorias = [datos[0][0], datos[1][0], datos[2][0], datos[3][0], datos[4][0], datos[5][0], datos[6][0]]
                    mostrarsimboloporcentaje = False
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresindividual = [PALETA_COLORES[5], PALETA_COLORES[5], PALETA_COLORES[5], PALETA_COLORES[5],
                                         PALETA_COLORES[5], PALETA_COLORES[5], PALETA_COLORES[5]]
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    data['imagen2'] = path_to_save + filename + ".png"

                    titulografica = "ATENCIONES POR TIPO DE CITA"
                    porc1vez = round((totalgeneral1vez * 100) / totalgeneral, 2)
                    porcsubs = round((totalgeneralsubsec * 100) / totalgeneral, 2)
                    valores = [[porc1vez, porcsubs]]
                    categorias = ['PRIMERA VEZ', 'SUBSECUENTE']
                    mostrarsimboloporcentaje = True
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[5]]
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda,
                                           barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    data['imagen3'] = path_to_save + filename + ".png"

                    data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                    titulos = persona.titulo3y4nivel()
                    data['titulo1'] = titulos['tit1']
                    data['titulo2'] = titulos['tit2']
                    data['medico'] = persona
                    data['desde'] = request.POST['desde']
                    data['hasta'] = request.POST['hasta']
                    data['totalgeneral'] = totalgeneral
                    data['totalgeneral1vez'] = totalgeneral1vez
                    data['totalgeneralsubsec'] = totalgeneralsubsec
                    data['fecha'] = datetime.now().date()
                    data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''
                    data['datos'] = datos

                    return conviert_html_to_pdf(
                        'box_medical/resumentipocita_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                else:
                    datos = []
                    facultades = []
                    carreras = []

                    atenciones = atenciones.filter(tipopaciente=3)

                    for f in atenciones.values_list('matricula__inscripcion__coordinacion_id', flat=True).order_by(
                            'matricula__inscripcion__coordinacion').distinct():
                        fac = Coordinacion.objects.get(pk=f)
                        idfacultad = fac.id
                        nfacultad = fac.nombre + ' (' + fac.alias + ')'
                        abreviaturafac = fac.alias
                        total1vez = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                      primeravez=True).count()
                        totalsubsec = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                        primeravez=False).count()

                        facultades.append([idfacultad, nfacultad, total1vez, totalsubsec, abreviaturafac, '', ''])

                        for c in atenciones.values_list('matricula__inscripcion__carrera_id', flat=True).filter(
                                matricula__inscripcion__coordinacion=fac).order_by(
                            'matricula__inscripcion__carrera').distinct():
                            carr = Carrera.objects.get(pk=c)
                            idcarrera = carr.id
                            ncarrera = carr.nombre
                            acarrera = (carr.alias)[:20]
                            total1vezcarr = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                              matricula__inscripcion__carrera=carr,
                                                              primeravez=True).count()
                            totalsubseccarr = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                                matricula__inscripcion__carrera=carr,
                                                                primeravez=False).count()
                            carreras.append([idfacultad, nfacultad, idcarrera, ncarrera, total1vezcarr, totalsubseccarr, acarrera if len(acarrera) > 0 else '-'])

                        titulografica = "ATENCIONES POR CARRERAS Y TIPO DE CITA DE LA FACULTAD"

                        valores = []
                        items = []
                        items2 = []
                        categorias = []
                        coloresindividual = []

                        for dato in carreras:
                            if dato[0] == idfacultad:
                                items.append(dato[4])
                                items2.append(dato[5])
                                categorias.append(dato[6])
                                coloresindividual.append(PALETA_COLORES[3])

                        valores.append(items)
                        valores.append(items2)

                        mostrarsimboloporcentaje = False
                        tieneleyenda = True
                        barrasagrupadas = True
                        coloresagrupado = [PALETA_COLORES[2], PALETA_COLORES[5]]
                        leyenda = []
                        leyenda.append([coloresagrupado[0], '1ERA VEZ'])
                        leyenda.append([coloresagrupado[1], 'SUBSECUENTE'])

                        imagen = grafica_barra(titulografica, 200, valores, categorias, mostrarsimboloporcentaje,
                                               tieneleyenda,
                                               leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                        filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                        imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                        rutaimg = path_to_save + filename + ".png"
                        facultades[len(facultades) - 1][5] = rutaimg

                        titulografica = "ATENCIONES POR TIPO DE CITA DE LA FACULTAD"
                        totalgeneral1vezfac = facultades[len(facultades) - 1][2]
                        totalgeneralsubsecfac = facultades[len(facultades) - 1][3]
                        totalgeneralfac = totalgeneral1vezfac + totalgeneralsubsecfac

                        porc1vez = round((totalgeneral1vezfac * 100) / totalgeneralfac, 2)
                        porcsubs = round((totalgeneralsubsecfac * 100) / totalgeneralfac, 2)
                        valores = [[porc1vez, porcsubs]]
                        categorias = ['PRIMERA VEZ', 'SUBSECUENTE']
                        mostrarsimboloporcentaje = True
                        tieneleyenda = False
                        barrasagrupadas = False
                        coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[5]]
                        coloresagrupado = []
                        leyenda = []

                        imagen = grafica_barra(titulografica, 250, valores, categorias, mostrarsimboloporcentaje,
                                               tieneleyenda,
                                               leyenda,
                                               barrasagrupadas, coloresindividual, coloresagrupado)

                        filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                        imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                        rutaimg = path_to_save + filename + ".png"
                        facultades[len(facultades) - 1][6] = rutaimg

                    totalgeneral1vez = atenciones.filter(primeravez=True).count()
                    totalgeneralsubsec = atenciones.filter(primeravez=False).count()
                    totalgeneral = atenciones.count()

                    titulografica = "TOTALES ATENCIONES PACIENTES PRIMERA VEZ"

                    valores = []
                    items = []
                    categorias = []
                    coloresindividual = []

                    for dato in facultades:
                        items.append(dato[2])
                        categorias.append(dato[4])
                        coloresindividual.append(PALETA_COLORES[2])

                    valores.append(items)

                    mostrarsimboloporcentaje = False
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 250, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    data['imagenfac1vez'] = path_to_save + filename + ".png"

                    titulografica = "TOTALES ATENCIONES PACIENTES SUBSECUENTES"

                    valores = []
                    items = []
                    categorias = []
                    coloresindividual = []

                    for dato in facultades:
                        items.append(dato[3])
                        categorias.append(dato[4])
                        coloresindividual.append(PALETA_COLORES[5])

                    valores.append(items)

                    mostrarsimboloporcentaje = False
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 250, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    data['imagenfacsubsec'] = path_to_save + filename + ".png"

                    titulografica = "TOTAL ATENCIONES POR TIPO DE CITA"
                    porc1vez = round((totalgeneral1vez * 100) / totalgeneral, 2)
                    porcsubs = round((totalgeneralsubsec * 100) / totalgeneral, 2)
                    valores = [[porc1vez, porcsubs]]
                    categorias = ['PRIMERA VEZ', 'SUBSECUENTE']
                    mostrarsimboloporcentaje = True
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[5]]
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 270, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda,
                                           barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    data['imagenfac1vezsubporc'] = path_to_save + filename + ".png"

                    data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                    titulos = persona.titulo3y4nivel()
                    data['titulo1'] = titulos['tit1']
                    data['titulo2'] = titulos['tit2']

                    data['medico'] = persona
                    data['desde'] = request.POST['desde']
                    data['hasta'] = request.POST['hasta']
                    data['totalgeneral'] = totalgeneral
                    data['fecha'] = datetime.now().date()
                    data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''
                    data['datos'] = datos
                    data['facultades'] = facultades
                    data['carreras'] = carreras

                    return conviert_html_to_pdf(
                        'box_medical/resumentipocitafaccar_pdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )

            except Exception as ex:
                pass

        elif action == 'resumenfacultadcarrera':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                facultad = int(request.POST['facultad'])
                carrera = int(request.POST['carrera'])

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen de atenciones del Área Odontológica por Facultad y Carrera'
                atenciones = PersonaConsultaOdontologica.objects.filter(tipopaciente=3, matricula__isnull=False,
                                                                  fecha__range=(desde, hasta), status=True)

                if facultad != 0 and carrera != 0:
                    fac = Coordinacion.objects.get(pk=facultad)
                    carr = Carrera.objects.get(pk=carrera)
                    atenciones = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                   matricula__inscripcion__carrera=carr).order_by(
                        'matricula__inscripcion__coordinacion', 'matricula__inscripcion__carrera',
                        'matricula__nivelmalla_id')
                elif facultad != 0:
                    fac = Coordinacion.objects.get(pk=facultad)
                    atenciones = atenciones.filter(matricula__inscripcion__coordinacion=fac).order_by(
                        'matricula__inscripcion__coordinacion', 'matricula__inscripcion__carrera',
                        'matricula__nivelmalla_id')

                # if esdirectordbu is False:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                nusuario = str(persona.usuario)
                area = "odon"
                filename = "ge_" + area + "_" + nusuario + "_"

                path_to_save = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar')) + '/'

                for filenameremove in glob.glob(path_to_save + "/" + filename + "*"):
                    os.remove(filenameremove)

                datos = []
                facultades = []
                carreras = []

                for f in atenciones.values_list('matricula__inscripcion__coordinacion_id', flat=True).order_by(
                        'matricula__inscripcion__coordinacion').distinct():
                    fac = Coordinacion.objects.get(pk=f)
                    idfacultad = fac.id
                    nfacultad = fac.nombre + ' (' + fac.alias + ')'
                    abreviaturafac = fac.alias
                    totalfacfem = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                    persona__sexo_id=1).count()
                    totalfacmasc = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                     persona__sexo_id=2).count()

                    facultades.append([idfacultad, nfacultad, totalfacfem, totalfacmasc, abreviaturafac, ''])

                    for c in atenciones.values_list('matricula__inscripcion__carrera_id', flat=True).filter(
                            matricula__inscripcion__coordinacion=fac).order_by(
                        'matricula__inscripcion__carrera').distinct():
                        carr = Carrera.objects.get(pk=c)
                        idcarrera = carr.id
                        ncarrera = carr.nombre
                        acarrera = carr.alias if len(carr.alias) > 0 else '-'
                        totalcarrfem = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                         matricula__inscripcion__carrera=carr,
                                                         persona__sexo_id=1).count()
                        totalcarrmasc = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                          matricula__inscripcion__carrera=carr,
                                                          persona__sexo_id=2).count()
                        carreras.append([idfacultad, nfacultad, idcarrera, ncarrera, totalcarrfem, totalcarrmasc, acarrera])

                        for n in atenciones.values_list('matricula__nivelmalla_id', flat=True).filter(
                                matricula__inscripcion__coordinacion=fac,
                                matricula__inscripcion__carrera=carr).order_by('matricula__nivelmalla_id').distinct():
                            nmalla = NivelMalla.objects.get(pk=n)
                            idnivel = nmalla.id
                            nnivel = nmalla.nombre

                            totalfem = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                         matricula__inscripcion__carrera=carr,
                                                         matricula__nivelmalla=nmalla, persona__sexo_id=1).count()
                            totalmasc = atenciones.filter(matricula__inscripcion__coordinacion=fac,
                                                          matricula__inscripcion__carrera=carr,
                                                          matricula__nivelmalla=nmalla, persona__sexo_id=2).count()

                            datos.append(
                                [idfacultad, nfacultad, idcarrera, ncarrera, idnivel, nnivel, totalfem, totalmasc])

                    titulografica = "ATENCIONES POR CARRERAS DE LA " + nfacultad

                    valores = []
                    items = []
                    categorias = []
                    coloresindividual = []

                    for dato in carreras:
                        if dato[0] == idfacultad:
                            items.append(dato[4] + dato[5])
                            categorias.append(dato[6])
                            coloresindividual.append(PALETA_COLORES[3])

                    valores.append(items)

                    mostrarsimboloporcentaje = False
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 10, valores, categorias, mostrarsimboloporcentaje,
                                           tieneleyenda,
                                           leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                    filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                    imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                    rutaimg = path_to_save + filename + ".png"
                    facultades[len(facultades) - 1][5] = rutaimg

                totalgeneral = atenciones.count()

                titulografica = "ATENCIONES POR FACULTADES"

                valores = []
                items = []
                categorias = []
                coloresindividual = []

                for dato in facultades:
                    items.append(dato[2] + dato[3])
                    categorias.append(dato[4])
                    coloresindividual.append(PALETA_COLORES[3])

                valores.append(items)

                mostrarsimboloporcentaje = False
                tieneleyenda = False
                barrasagrupadas = False
                coloresagrupado = []
                leyenda = []

                imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
                                       leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                data['imagenfac'] = path_to_save + filename + ".png"

                data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                titulos = persona.titulo3y4nivel()
                data['titulo1'] = titulos['tit1']
                data['titulo2'] = titulos['tit2']

                data['medico'] = persona
                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['totalgeneral'] = totalgeneral
                data['fecha'] = datetime.now().date()
                data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''
                data['datos'] = datos
                data['facultades'] = facultades
                data['carreras'] = carreras

                return conviert_html_to_pdf(
                    'box_medical/resumenfacultadcarrera_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        elif action == 'resumentipoacciones':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen por Acciones realizadas del Área Odontológica'
                atenciones = PersonaConsultaOdontologica.objects.filter(fecha__range=(desde, hasta), status=True)

                # if not esdirectordbu:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                tiposacciones = AccionConsulta.objects.filter(area=2, status=True).order_by('descripcion')
                listaacciones = []
                datos = []

                for a in atenciones:
                    for acc in a.accion.all():
                        listaacciones.append(acc.descripcion)

                totalgeneral = 0
                for a in tiposacciones:
                    descripcion = a.descripcion
                    total = listaacciones.count(descripcion)
                    datos.append([descripcion, total])
                    totalgeneral += total


                nusuario = str(persona.usuario)
                area = "odon"
                filename = "ge_" + area + "_" + nusuario + "_"

                path_to_save = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar')) + '/'

                for filenameremove in glob.glob(path_to_save + "/" + filename + "*"):
                    os.remove(filenameremove)

                titulografica = "RESUMEN ACCIONES REALIZADAS"

                valores = []
                items = []
                categorias = []
                coloresindividual = []

                for dato in datos:
                    items.append(dato[1])
                    categorias.append(dato[0])
                    coloresindividual.append(PALETA_COLORES[3])

                valores.append(items)

                mostrarsimboloporcentaje = False
                tieneleyenda = False
                barrasagrupadas = False
                coloresagrupado = []
                leyenda = []

                imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
                                       leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                data['imgagenresumen'] = path_to_save + filename + ".png"

                data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                titulos = persona.titulo3y4nivel()
                data['titulo1'] = titulos['tit1']
                data['titulo2'] = titulos['tit2']

                data['medico'] = persona
                data['desde'] = request.POST['desde']
                data['hasta'] = request.POST['hasta']
                data['totalgeneral'] = totalgeneral
                data['fecha'] = datetime.now().date()
                data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''
                data['datos'] = datos

                return conviert_html_to_pdf(
                    'box_medical/resumentipoaccion_pdf.html',
                    {
                        'pagesize': 'A4',
                        'data': data,
                    }
                )

            except Exception as ex:
                pass

        elif action == 'consultaodontologica':
            try:
                form = PersonaConsultaOdontologicaForm(request.POST)
                persona = Persona.objects.get(pk=request.POST['id'])
                idmatricula = request.POST['idmatricula']
                if form.is_valid():
                    enfermedades = json.loads(request.POST['lista_items1'])
                    # if not enfermedades:
                    #     return JsonResponse({"result": "bad", "mensaje": u"El campo Código CIE-10 debe tener al menos 1 elemento seleccionado."})

                    fecha = form.cleaned_data['fechaatencion']
                    hora = datetime.now().time()

                    atenciones = persona.personaconsultaodontologica_set.filter(status=True, fecha__year=fecha.year).count()

                    consulta = PersonaConsultaOdontologica(persona=persona,
                                                           #fecha=datetime.now(),
                                                           fecha=datetime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute, hora.second),
                                                           tipoatencion=int(form.cleaned_data['tipoatencion']),
                                                           motivo=form.cleaned_data['motivo'].strip().upper(),
                                                           diagnostico=form.cleaned_data['diagnostico'].strip().upper(),
                                                           plantratamiento=form.cleaned_data['plantratamiento'].strip().upper(),
                                                           #trabajosrealizados=form.cleaned_data['trabajosrealizados'].strip().upper(),
                                                           indicaciones=form.cleaned_data['indicaciones'].strip().upper(),
                                                           medico=request.session['persona'],
                                                           profilaxis=form.cleaned_data['profilaxis'],
                                                           causaprofilaxis=form.cleaned_data['causaprofilaxis'] if form.cleaned_data['profilaxis'] else None,
                                                           tipopaciente= form.cleaned_data['tipopaciente'],
                                                           matricula_id=idmatricula,
                                                           primeravez=True if atenciones == 0 else False)
                    consulta.save(request)
                    consulta.accion.clear()
                    for acc in form.cleaned_data['accion']:
                        consulta.accion.add(acc)
                    consulta.save(request)

                    for e in enfermedades:
                        idcatalogo = int(e['id'])
                        catalogo = CatalogoEnfermedad.objects.get(pk=idcatalogo)
                        consulta.enfermedad.add(catalogo)

                    if form.cleaned_data['cita']:
                        fecha = form.cleaned_data['fecha']
                        hora = form.cleaned_data['hora']
                        fechacita = datetime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute, hora.second)
                        if fechacita < datetime.now():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha de próxima cita incorrecta."})
                        proximacita = ProximaCita(persona=consulta.persona,
                                                  fecha=fechacita,
                                                  medico=consulta.medico,
                                                  indicaciones=form.cleaned_data['indicaciones'],
                                                  tipoconsulta=2)
                        proximacita.save(request)
                    if 'idc' in request.POST:
                        cita = ProximaCita.objects.get(pk=request.POST['idc'])
                        cita.asistio = True
                        cita.save(request)
                    log(u'Adiciono consulta odontologica: %s' % consulta, request, "add")
                    return JsonResponse({"result": "ok", "id": consulta.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'antecedente':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica

                persona = pexamenfisico.personafichamedica.personaextension.persona

                f = AntecedenteOdontologicoForm(request.POST)
                if f.is_valid():
                    if AntecedenteOdontologico.objects.values('id').filter(personafichamedica=personafichamedica).exists():
                        antecedente = AntecedenteOdontologico.objects.get(personafichamedica=personafichamedica)
                        antecedente.bajotratamiento = f.cleaned_data['bajotratamiento']
                        antecedente.esalergico = f.cleaned_data['esalergico']
                        antecedente.propensohemorragia = f.cleaned_data['propensohemorragia']
                        antecedente.complicacionanestesiaboca = f.cleaned_data['complicacionanestesiaboca']
                        antecedente.toperatoria = f.cleaned_data['toperatoria']
                        antecedente.tperiodoncia = f.cleaned_data['tperiodoncia']
                        antecedente.totro = f.cleaned_data['totro']
                        antecedente.periodontal = f.cleaned_data['periodontal']
                        antecedente.materiaalba = f.cleaned_data['materiaalba']
                        antecedente.placabacteriana = f.cleaned_data['placabacteriana']
                        antecedente.calculossupra = f.cleaned_data['calculossupra']
                    else:
                        fecha = persona.obtener_fecha_ficha_odontologica()
                        antecedente = AntecedenteOdontologico(personafichamedica=personafichamedica,
                                                              fecha=fecha,
                                                              bajotratamiento=f.cleaned_data['bajotratamiento'],
                                                              esalergico=f.cleaned_data['esalergico'],
                                                              propensohemorragia=f.cleaned_data['propensohemorragia'],
                                                              complicacionanestesiaboca=f.cleaned_data['complicacionanestesiaboca'],
                                                              toperatoria=f.cleaned_data['toperatoria'],
                                                              tperiodoncia=f.cleaned_data['tperiodoncia'],
                                                              totro=f.cleaned_data['totro'],
                                                              periodontal=f.cleaned_data['periodontal'],
                                                              materiaalba=f.cleaned_data['materiaalba'],
                                                              placabacteriana=f.cleaned_data['placabacteriana'],
                                                              calculossupra=f.cleaned_data['calculossupra']
                                                            )
                        antecedente.save(request)

                    antecedente.alergias.set(f.cleaned_data['alergias'])
                    antecedente.save(request)
                    log(u'Adiciono antecedentes odontológico: %s' % pexamenfisico.personafichamedica.personaextension.persona, request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'actualizarfechaficha':
            try:
                idficha = int(request.POST['idficha'])
                f = FechaFichaMedicaForm(request.POST)
                if f.is_valid():
                    ficha = AntecedenteOdontologico.objects.get(pk=idficha)
                    ficha.fecha = f.cleaned_data['fechaficha']
                    ficha.save(request)
                    log(u'Modifico fecha de ficha odontológica: %s' % ficha, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editconsultaodontologicaprevia':
            try:
                consulta = PersonaConsultaOdontologica.objects.get(pk=request.POST['id'])
                form = PersonaConsultaOdontologicaForm(request.POST)
                if form.is_valid():
                    enfermedades = json.loads(request.POST['lista_items1'])
                    # if not enfermedades:
                    #     return JsonResponse({"result": "bad", "mensaje": u"El campo Código CIE-10 debe tener al menos 1 elemento seleccionado."})

                    consulta.fecha = form.cleaned_data['fechaatencion']
                    consulta.tipoatencion = int(form.cleaned_data['tipoatencion'])
                    consulta.motivo = form.cleaned_data['motivo'].strip().upper()
                    consulta.diagnostico = form.cleaned_data['diagnostico'].strip().upper()
                    consulta.plantratamiento = form.cleaned_data['plantratamiento'].strip().upper()
                    #consulta.trabajosrealizados = form.cleaned_data['trabajosrealizados'].strip().upper()
                    consulta.indicaciones = form.cleaned_data['indicaciones'].strip().upper()
                    consulta.profilaxis = form.cleaned_data['profilaxis']
                    consulta.causaprofilaxis = form.cleaned_data['causaprofilaxis'] if form.cleaned_data['profilaxis'] else None
                    consulta.accion.set(form.cleaned_data['accion'])
                    consulta.save(request)

                    consulta.enfermedad.clear()

                    for e in enfermedades:
                        idcatalogo = int(e['id'])
                        catalogo = CatalogoEnfermedad.objects.get(pk=idcatalogo)
                        consulta.enfermedad.add(catalogo)

                    log(u'Modifico consulta previa odontologica: %s' % consulta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Consultas odontológicas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'consultaodontologica':
                try:
                    persona = Persona.objects.get(pk=request.GET['id'])
                    data['title'] = u'Consulta odontológica - Paciente: ' + str(persona) + ' - ' + persona.identificacion()
                    data['paciente'] = persona
                    form = PersonaConsultaOdontologicaForm(initial={'fechaatencion': datetime.now().date(),
                                                                    'fecha': datetime.now().date(),
                                                                    'hora': "12:00",
                                                                    })

                    tpac = persona.tipo_paciente()
                    form.tipos_paciente(tpac['tipoper'], tpac['regimen'])

                    if tpac['tipoper'] == 'ALU':
                        matri = persona.datos_ultima_matricula()
                        data['idmatricula'] = matri['idmatricula']

                    data['form'] = form
                    data['form2'] = AccionConsultaForm()
                    data['odontograma'] = persona.odontograma()
                    data['cita'] = request.GET['idc'] if 'idc' in request.GET else None
                    return render(request, "box_odontologica/consultaodontologica.html", data)
                except Exception as ex:
                    pass

            elif action == 'ficha':
                try:
                    data['title'] = u'Ficha odontológica'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['pex'] = pex = persona.datos_examen_fisico()

                    antecedentes = fechaficha = None
                    data['tienefichaodontologica'] = False
                    if AntecedenteOdontologico.objects.filter(personafichamedica=pex.personafichamedica).exists():
                        antecedentes = AntecedenteOdontologico.objects.get(personafichamedica=pex.personafichamedica)
                        data['tienefichaodontologica'] = True
                        fechaficha = antecedentes.fecha

                    data['fechaficha'] = fechaficha
                    data['odontograma'] = persona.odontograma()
                    data['antecedentes'] = antecedentes
                    data['form2'] = FechaFichaMedicaForm(initial={'fechaficha': fechaficha})
                    return render(request, "box_odontologica/ficha.html", data)
                except Exception as ex:
                    pass

            elif action == 'antecedente':
                try:
                    data['title'] = u'Antecedentes odontológicos'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if AntecedenteOdontologico.objects.filter(personafichamedica=personafichamedica).exists():
                        antecedente = AntecedenteOdontologico.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(antecedente)
                        data['form'] = AntecedenteOdontologicoForm(initial=initial)
                    else:
                        data['form'] = AntecedenteOdontologicoForm()

                    data['form2'] = Alergia2Form()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_odontologica/antecedente.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadodetalladoareaodontologica':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)
                    tipopaciente = int(request.GET['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    persona = request.session['persona']
                    esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                    titulo = easyxf('font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf('font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf('font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('ListadoGeneral')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_atenciones_odontologicas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 12, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                    ws.write_merge(2, 2, 0, 12, 'LISTADO DETALLADO DE ATENCIONES DEL ÁREA ODONTOLÓGICA', titulo2)
                    ws.write_merge(3, 3, 0, 12, 'DESDE:   ' + str(convertir_fecha(request.GET['desde'])) + '     HASTA:   ' + str(convertir_fecha(request.GET['hasta'])), titulo2)
                    ws.write_merge(4, 4, 0, 12, str(persona) if not esdirectordbu else '', titulo2)

                    row_num = 6
                    columns = [
                        (u"FECHA", 3000),
                        (u"TIPO PACIENTE", 4000),
                        (u"CITA", 4000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"APELLIDOS", 7000),
                        (u"NOMBRES", 7000),
                        (u"GÉNERO", 4000),
                        (u"EDAD", 3000),
                        (u"TELÉFONO", 3000),
                        (u"E-MAIL INSTITUCIONAL", 3000),
                        (u"E-MAIL PERSONAL", 3000),
                        (u"DIRECCIÓN", 10000),
                        (u"FACULTAD", 10000),
                        (u"CARRERA", 10000),
                        (u"NIVEL", 5000),
                        (u"DIAGNOSTICO", 20000),
                        (u"CÓDIGO CIE-10", 20000),
                        (u"ACCIONES REALIZADAS", 20000),
                        (u"RESPONSABLE", 8000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 6

                    atenciones = PersonaConsultaOdontologica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True).order_by('-fecha')

                    # if not esdirectordbu:
                    #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                    for a in atenciones:
                        row_num += 1
                        facultad = carrera = nivel = ""
                        ws.write(row_num, 0, a.fecha, fuentefecha)
                        #fechaatencion = a.fecha.date()
                        p = Persona.objects.get(pk=a.persona_id)
                        ws.write(row_num, 1, TIPO_PACIENTE[a.tipopaciente-1][1], fuentenormal)
                        # totreg = p.personaconsultaodontologica_set.filter(fecha__lte=a.fecha, status=True).count()
                        # cita = 'PRIMERA VEZ' if totreg <= 1 else 'SUBSEQUENTE'

                        cita = 'PRIMERA VEZ' if a.primeravez else 'SUBSECUENTE'

                        ws.write(row_num, 2, cita, fuentenormal)
                        ws.write(row_num, 3, p.identificacion(), fuentenormal)
                        ws.write(row_num, 4, p.apellido1 + ' ' + p.apellido2, fuentenormal)
                        ws.write(row_num, 5, p.nombres, fuentenormal)
                        ws.write(row_num, 6, str(p.sexo), fuentenormal)
                        ws.write(row_num, 7, calcula_edad(p.nacimiento), fuentenumeroentero)
                        ws.write(row_num, 8, p.telefono, fuentenormal)
                        ws.write(row_num, 9, p.emailinst, fuentenormal)
                        ws.write(row_num, 10, p.email, fuentenormal)
                        ws.write(row_num, 11, p.direccion_corta(), fuentenormal)

                        if a.tipopaciente == 3:
                            m = Matricula.objects.get(pk=a.matricula_id)

                            if m:
                                facultad = str(m.nivel.coordinacion())
                                carrera = str(m.inscripcion.carrera)
                                nivel = m.nivelmalla.nombre

                        ws.write(row_num, 12, facultad, fuentenormal)
                        ws.write(row_num, 13, carrera, fuentenormal)
                        ws.write(row_num, 14, nivel, fuentenormal)
                        ws.write(row_num, 15, a.diagnostico.upper(), fuentenormal)

                        cie10 = acciones = ""
                        for e in a.enfermedad.all():
                            cie10 = cie10 + ", " + e.clave + " - " + e.descripcion if cie10 != "" else e.clave + " - " + e.descripcion
                        ws.write(row_num, 16, cie10, fuentenormal)

                        if a.trabajosrealizados:
                            acciones = a.trabajosrealizados.upper()
                        else:
                            for ac in a.accion.all():
                                acciones = acciones + ", " + ac.descripcion if acciones != "" else ac.descripcion

                        ws.write(row_num, 17, acciones, fuentenormal)

                        responsable = Persona.objects.get(usuario=a.usuario_creacion)
                        ws.write(row_num, 18, responsable.apellido1+ ' ' + responsable.apellido2 + ' ' +responsable.nombres, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'fichapdf':
                try:
                    # r = cargo_titulo1_titulo2(persona) HAN BORRADO LA FUNCION Y NO SE ENCUENTRA HISTORIAL
                    # data['cargo'] = r['cargo']
                    # data['titulo1'] = r['titulo1']
                    # data['titulo2'] = r['titulo2']
                    data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                    titulos = persona.titulo3y4nivel()
                    data['titulo1'] = titulos['tit1']
                    data['titulo2'] = titulos['tit2']

                    data['medico'] = persona
                    data['fecha'] = datetime.now().date()

                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    ficha = PersonaFichaMedica.objects.get(personaextension__persona=persona)
                    pex = PersonaExamenFisico.objects.get(personafichamedica=ficha)
                    data['antecedentes'] = antecedentes = AntecedenteOdontologico.objects.get(personafichamedica=ficha)
                    data['edad'] = calcula_edad_fn_fc(persona.nacimiento, antecedentes.fecha)
                    persona.odontograma()
                    data['grupo1adulto'] = persona.odontogramagrupo1adulto()
                    data['grupo2adulto'] = persona.odontogramagrupo2adulto()
                    data['grupo1infantil'] = persona.odontogramagrupo1infantil()
                    data['grupo2infantil'] = persona.odontogramagrupo2infantil()
                    data['consultas'] = consultas = PersonaConsultaOdontologica.objects.filter(persona=persona, status=True).order_by('-id')

                    tpac = persona.tipo_paciente()
                    data['esalumno'] = True if tpac['tipoper'] == 'ALU' else False
                    data['esadministrativo'] = True if tpac['tipoper'] == 'ADT' and tpac['regimen'] == 1 else False
                    data['estrabajador'] = True if tpac['tipoper'] == 'ADT' and tpac['regimen'] == 2 else False
                    data['esdocente'] = True if tpac['tipoper'] == 'ADT' and tpac['regimen'] not in [1, 2] else False

                    if not consultas:
                        if tpac['tipoper'] == 'ALU':
                            matri = persona.datos_ultima_matricula()
                            data['facultad'] = matri['facultad']
                            data['carrera'] = matri['carrera']
                            data['nivel'] = matri['nivel']
                            data['seccion'] = matri['seccion']
                    else:
                        if consultas.filter(tipopaciente=3).exists():
                            primeraconsulta = consultas.filter(tipopaciente=3).order_by('fecha')[0]
                            m = Matricula.objects.get(pk=primeraconsulta.matricula_id)
                            data['facultad'] = str(m.nivel.coordinacion())
                            data['carrera'] = str(m.inscripcion.carrera)
                            data['nivel'] = m.nivelmalla.nombre
                            data['seccion'] = m.inscripcion.sesion.nombre


                    data['personaexamenfisico'] = pex

                    return conviert_html_to_pdf(
                        'box_odontologica/fichapdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'consultaodontologicaprevias':
                try:
                    data['title'] = u'Consultas odontológicas previas'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    if 'idc' in request.GET:
                        data['consultas'] = PersonaConsultaOdontologica.objects.filter(persona=persona, medico=data['persona'], id=request.GET['idc'])
                    else:
                        data['consultas'] = PersonaConsultaOdontologica.objects.filter(persona=persona)

                    data['odontograma'] = persona.odontograma()
                    return render(request, "box_odontologica/consultaodontologicaprevias.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconsultaodontologicaprevia':
                try:
                    data['consulta'] = consulta = PersonaConsultaOdontologica.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar consulta odontológica - Paciente: ' + str(consulta.persona) + ' - ' + consulta.persona.identificacion()
                    tipos = (consulta.tipopaciente, TIPO_PACIENTE[consulta.tipopaciente - 1][1])

                    enfermedad = consulta.enfermedad.values('id', 'descripcion').all()
                    data['enfermedad'] = enfermedad

                    initial = model_to_dict(consulta)
                    form = PersonaConsultaOdontologicaForm(initial=initial)

                    form.editar(tipos, consulta.fecha)
                    data['form'] = form
                    data['form2'] = AccionConsultaForm()
                    data['paciente'] = consulta.persona
                    return render(request, "box_odontologica/editconsultaodontologicaprevia.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()
            search = None
            ids = None

            consultas = PersonaConsultaOdontologica.objects.values_list('id').filter(status=True)
            totalgeneral = consultas.count()
            totalgeneralusuario = consultas.filter(usuario_creacion_id=persona.usuario.id).count()
            totalhoy = consultas.filter(fecha__date=datetime.now().date()).count()
            totalusuariohoy = consultas.filter(fecha__date=datetime.now().date(), usuario_creacion_id=persona.usuario.id).count()

            personal = Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False)
                                              | Q(perfilusuario__inscripcion__isnull=False)
                                              | Q(perfilusuario__profesor__isnull=False)
                                              | (Q(perfilusuario__externo__isnull=False) & Q(tipopersona=1))
                                              )

            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    personal = personal.filter(Q(nombres__icontains=search) |
                                               Q(apellido1__icontains=search) |
                                               Q(apellido2__icontains=search) |
                                               Q(cedula__icontains=search) |
                                               Q(pasaporte__icontains=search) |
                                               Q(inscripcion__identificador__icontains=search) |
                                               Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                               Q(inscripcion__carrera__nombre__icontains=search)).distinct()
                else:
                    personal = personal.filter(Q(apellido1__icontains=ss[0]) &
                                               Q(apellido2__icontains=ss[1])).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                personal = personal.filter(id=ids).distinct()
            paging = MiPaginador(personal, 25)
            p = 1
            try:
                if 'page' in request.GET:
                    p = int(request.GET['page'])
                page = paging.page(p)
            except Exception as ex:
                p = 1
                page = paging.page(p)
            data['paging'] = paging
            data['rangospaging'] = paging.rangos_paginado(p)
            data['page'] = page
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['personal'] = page.object_list
            data['fecha'] = datetime.now().strftime('%d-%m-%Y')
            data['area'] = "Área odontológica"
            data['tipopacientes'] = TIPO_PACIENTE
            data['totalgeneral'] = totalgeneral
            data['totalgeneralusuario'] = totalgeneralusuario
            data['totalhoy'] = totalhoy
            data['totalusuariohoy'] = totalusuariohoy
            data['medico'] = persona.usuario
            codigos_facultad = PersonaConsultaOdontologica.objects.values_list('matricula__inscripcion__coordinacion_id', flat=True).filter(status=True, matricula__isnull=False, tipopaciente=3).order_by('matricula__inscripcion__coordinacion_id').distinct()
            codigos_carrera = PersonaConsultaOdontologica.objects.values_list('matricula__inscripcion__carrera_id', flat=True).filter(status=True, matricula__isnull=False, tipopaciente=3).order_by('matricula__inscripcion__carrera_id').distinct()
            carreras = ','.join(str(c) for c in codigos_carrera)
            data['facultades'] = Coordinacion.objects.filter(status=True, excluir=False, pk__in=codigos_facultad).order_by('id')
            data['codigos_carrera'] = carreras
            data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''

            return render(request, "box_odontologica/view.html", data)