# -*- coding: latin-1 -*-
import glob
import json
import os
import random
from datetime import datetime, time, timedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template.context import Context
from xlwt import easyxf, XFStyle, Workbook

from decorators import secure_module, last_access
from med.forms import PersonaConsultaPsicologicaForm, DatosPsicologicoForm, AccionConsultaForm, PreguntaTestForm, \
    EscalaPreguntaTestForm
from med.funciones import actioncalculotestpsicologico
from med.models import PersonaConsultaPsicologica, ProximaCita, TIPO_PACIENTE, CatalogoEnfermedad, DatosPsicologico, \
    AccionConsulta, TestPsicologico, TestPsicologicoPreguntas, PsicologicoPreguntasBanco, \
    PsicologicoPreguntasBancoEscala, PersonaTestPsicologica, RespuestaTestPsicologica, TestPsicologicoCalculoDiagnostico
from sagest.models import DistributivoPersona
from settings import UTILIZA_GRUPOS_ALUMNOS, SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, calcula_edad, grafica_barra
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.models import Persona, Matricula, Coordinacion, Carrera, NivelMalla, PALETA_COLORES, TipoRespuesta, Sexo, \
    Respuesta


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
        if action == 'consultapsicologica':
            try:
                f = PersonaConsultaPsicologicaForm(request.POST)
                persona = Persona.objects.get(pk=request.POST['id'])
                idmatricula = request.POST['idmatricula']
                if f.is_valid():
                    enfermedades = json.loads(request.POST['lista_items1'])
                    # if not enfermedades:
                    #     return JsonResponse({"result": "bad", "mensaje": u"El campo Código CIE-10 debe tener al menos 1 elemento seleccionado."})

                    fecha = f.cleaned_data['fechaatencion']
                    hora = datetime.now().time()

                    atenciones = persona.personaconsultapsicologica_set.filter(status=True, fecha__year=fecha.year).count()

                    consulta = PersonaConsultaPsicologica(persona=persona,
                                                          #fecha=datetime.now(),
                                                          fecha=datetime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute, hora.second),
                                                          tipoatencion=f.cleaned_data['tipoatencion'],
                                                          tipoterapia=f.cleaned_data['tipoterapia'],
                                                          motivo=f.cleaned_data['motivo'].strip().upper(),
                                                          medicacion=f.cleaned_data['medicacion'].strip().upper(),
                                                          diagnostico=f.cleaned_data['diagnostico'].strip().upper(),
                                                          tratamiento=f.cleaned_data['tratamiento'].strip().upper(),
                                                          medico=request.session['persona'],
                                                          tipopaciente=f.cleaned_data['tipopaciente'],
                                                          matricula_id=idmatricula,
                                                          primeravez=True if atenciones == 0 else False)
                    consulta.save(request)
                    consulta.accion.set(f.cleaned_data['accion'])
                    consulta.save(request)

                    for e in enfermedades:
                        idcatalogo = int(e['id'])
                        catalogo = CatalogoEnfermedad.objects.get(pk=idcatalogo)
                        consulta.enfermedad.add(catalogo)

                    if f.cleaned_data['cita']:
                        fecha = f.cleaned_data['fecha']
                        hora = f.cleaned_data['hora']
                        fechacita = datetime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute, hora.second)
                        if fechacita < datetime.now():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha de próxima cita incorrecta."})
                        if ProximaCita.objects.filter(persona=consulta.persona, fecha__gte=datetime.now(), medico=consulta.medico).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe una cita programada para este paciente."})
                        proximacita = ProximaCita(persona=consulta.persona,
                                                  fecha=fechacita,
                                                  medico=consulta.medico,
                                                  indicaciones=f.cleaned_data['indicaciones'],
                                                  tipoconsulta=1)
                        proximacita.save(request)
                    if 'idc' in request.POST:
                        cita = ProximaCita.objects.get(pk=request.POST['idc'])
                        cita.asistio = True
                        cita.save(request)
                    log(u'Adiciono consulta psicologica: %s' % consulta, request, "add")
                    return JsonResponse({"result": "ok", "id": consulta.id})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificar_atenciones':
            try:
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    tipopaciente = int(request.POST['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    atenciones = PersonaConsultaPsicologica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True)

                    if atenciones:
                        # if esdirectordbu is False:
                        #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                        if atenciones:
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})



                    # if esdirectordbu:
                    #     if PersonaConsultaPsicologica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    # else:
                    #     if PersonaConsultaPsicologica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True, usuario_creacion_id=persona.usuario.id).exists():
                    #         return JsonResponse({"result": "ok"})
                    #     else:
                    #         return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'verificar_atencionesfc':
            try:
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                if datetime.strptime(request.POST['desde'], '%d-%m-%Y') <= datetime.strptime(request.POST['hasta'], '%d-%m-%Y'):
                    desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                    facultad = int(request.POST['facultad'])
                    carrera = int(request.POST['carrera'])
                    tipopaciente = int(request.POST['tipopaciente'])

                    atenciones = PersonaConsultaPsicologica.objects.filter(fecha__range=(desde, hasta), status=True)

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

                    # if esdirectordbu:
                    #     if facultad == 0 and carrera == 0:
                    #         if PersonaConsultaPsicologica.objects.filter(tipopaciente=3, fecha__range=(desde, hasta), status=True).exists():
                    #             return JsonResponse({"result": "ok"})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    #     elif carrera == 0:
                    #         fac = Coordinacion.objects.get(pk=facultad)
                    #         if PersonaConsultaPsicologica.objects.filter(tipopaciente=3, fecha__range=(desde, hasta), status=True, matricula__isnull=False, matricula__inscripcion__coordinacion=fac).exists():
                    #             return JsonResponse({"result": "ok"})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    #     else:
                    #         fac = Coordinacion.objects.get(pk=facultad)
                    #         carr = Carrera.objects.get(pk=carrera)
                    #         if PersonaConsultaPsicologica.objects.filter(tipopaciente=3, fecha__range=(desde, hasta), status=True, matricula__isnull=False, matricula__inscripcion__coordinacion=fac, matricula__inscripcion__carrera=carr).exists():
                    #             return JsonResponse({"result": "ok"})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    # else:
                    #     if facultad == 0 and carrera == 0:
                    #         if PersonaConsultaPsicologica.objects.filter(tipopaciente=3, fecha__range=(desde, hasta), status=True, usuario_creacion_id=persona.usuario.id).exists():
                    #             return JsonResponse({"result": "ok"})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    #     elif carrera == 0:
                    #         fac = Coordinacion.objects.get(pk=facultad)
                    #         if PersonaConsultaPsicologica.objects.filter(tipopaciente=3, fecha__range=(desde, hasta), status=True, matricula__isnull=False, matricula__inscripcion__coordinacion=fac, usuario_creacion_id=persona.usuario.id).exists():
                    #             return JsonResponse({"result": "ok"})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                    #     else:
                    #         fac = Coordinacion.objects.get(pk=facultad)
                    #         carr = Carrera.objects.get(pk=carrera)
                    #         if PersonaConsultaPsicologica.objects.filter(tipopaciente=3, fecha__range=(desde, hasta), status=True, matricula__isnull=False, matricula__inscripcion__coordinacion=fac, matricula__inscripcion__carrera=carr, usuario_creacion_id=persona.usuario.id).exists():
                    #             return JsonResponse({"result": "ok"})
                    #         else:
                    #             return JsonResponse({"result": "bad", "mensaje": "No existen registros para generar el reporte"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'resumengeneralareapsicologica':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área Psicológica'
                atenciones = PersonaConsultaPsicologica.objects.filter(fecha__range=(desde, hasta), status=True)

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
                area = "psico"
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

        elif action == 'resumengeneralareapsicologicatipocita':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                tipopaciente = int(request.POST['tipopaciente'])
                facultad = int(request.POST['facultad'])
                carrera = int(request.POST['carrera'])

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área Psicológica por Tipo de Cita'
                atenciones = PersonaConsultaPsicologica.objects.filter(fecha__range=(desde, hasta), status=True)

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
                area = "psico"
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
                    valores = [
                        [datos[0][2], datos[1][2], datos[2][2], datos[3][2], datos[4][2], datos[5][2], datos[6][2]]]
                    categorias = [datos[0][0], datos[1][0], datos[2][0], datos[3][0], datos[4][0], datos[5][0],
                                  datos[6][0]]
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
                            carreras.append([idfacultad, nfacultad, idcarrera, ncarrera, total1vezcarr, totalsubseccarr,
                                             acarrera if len(acarrera) > 0 else '-'])

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

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen de atenciones del Área Psicológica por Facultad y Carrera'
                atenciones = PersonaConsultaPsicologica.objects.filter(tipopaciente=3, matricula__isnull=False, fecha__range=(desde, hasta), status=True)

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
                area = "psico"
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
                        carreras.append(
                            [idfacultad, nfacultad, idcarrera, ncarrera, totalcarrfem, totalcarrmasc, acarrera])

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

                data['tituloreporte'] = 'Reporte Resumen por Acciones realizadas del Área Psicológica'
                atenciones = PersonaConsultaPsicologica.objects.filter(fecha__range=(desde, hasta), status=True)

                # if not esdirectordbu:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                tiposacciones = AccionConsulta.objects.filter(area=3, status=True).order_by('descripcion')
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
                area = "psico"
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

        elif action == 'editconsultapsicologicaprevia':
            try:
                consulta = PersonaConsultaPsicologica.objects.get(pk=request.POST['id'])
                f = PersonaConsultaPsicologicaForm(request.POST)
                if f.is_valid():
                    enfermedades = json.loads(request.POST['lista_items1'])
                    # if not enfermedades:
                    #     return JsonResponse({"result": "bad", "mensaje": u"El campo Código CIE-10 debe tener al menos 1 elemento seleccionado."})

                    #consulta.pacientegrupo = f.cleaned_data['grupo']
                    consulta.tipoatencion = f.cleaned_data['tipoatencion']
                    consulta.tipoterapia = f.cleaned_data['tipoterapia']
                    consulta.motivo = f.cleaned_data['motivo'].strip().upper()
                    consulta.medicacion = f.cleaned_data['medicacion'].strip().upper()
                    consulta.diagnostico = f.cleaned_data['diagnostico'].strip().upper()
                    consulta.tratamiento = f.cleaned_data['tratamiento'].strip().upper()
                    consulta.accion.set(f.cleaned_data['accion'])
                    consulta.save(request)

                    consulta.enfermedad.clear()

                    for e in enfermedades:
                        idcatalogo = int(e['id'])
                        catalogo = CatalogoEnfermedad.objects.get(pk=idcatalogo)
                        consulta.enfermedad.add(catalogo)

                    log(u'Modifico consulta previa psicologica: %s' % consulta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfichapsicologica':
            try:
                consulta = DatosPsicologico.objects.get(pk=request.POST['id'])
                f = DatosPsicologicoForm(request.POST)
                if f.is_valid():
                    consulta.relemointpadre = f.cleaned_data['relemointpadre']
                    consulta.relemointmadre = f.cleaned_data['relemointmadre']
                    consulta.relemointotros = f.cleaned_data['relemointotros']

                    consulta.antecedentes = f.cleaned_data['antecedentes']
                    consulta.alergia = f.cleaned_data['alergia']
                    consulta.nauseas = f.cleaned_data['nauseas']
                    consulta.vomito = f.cleaned_data['vomito']
                    consulta.anorexia = f.cleaned_data['anorexia']
                    consulta.bulimia = f.cleaned_data['bulimia']
                    consulta.enuresis = f.cleaned_data['enuresis']
                    consulta.encopresis = f.cleaned_data['encopresis']
                    consulta.onicofagia = f.cleaned_data['onicofagia']
                    consulta.ticsnervioso = f.cleaned_data['ticsnervioso']
                    consulta.trastornoneurologico = f.cleaned_data['trastornoneurologico']
                    consulta.edadtrastorno = f.cleaned_data['edadtrastorno']
                    consulta.tratamientotrastorno = f.cleaned_data['tratamientotrastorno']
                    consulta.secuelastrastorno = f.cleaned_data['secuelastrastorno']
                    consulta.actitudenfermedada = f.cleaned_data['actitudenfermedada']
                    consulta.actitudmuerte = f.cleaned_data['actitudmuerte']
                    consulta.actitudpadre = f.cleaned_data['actitudpadre']

                    consulta.masturbacionarea = f.cleaned_data['masturbacionarea']
                    consulta.curiosidadsexualinfancia = f.cleaned_data['curiosidadsexualinfancia']
                    consulta.edadcuriosidad = f.cleaned_data['edadcuriosidad']
                    consulta.relaciones = f.cleaned_data['relaciones']
                    consulta.edaddesarrollosexual = f.cleaned_data['edaddesarrollosexual']
                    consulta.actitudpadredesarrollosexual = f.cleaned_data['actitudpadredesarrollosexual']

                    consulta.amigospreferidos = f.cleaned_data['amigospreferidos']
                    consulta.numeroamigos = f.cleaned_data['numeroamigos']
                    consulta.comportamientoanteadulto = f.cleaned_data['comportamientoanteadulto']
                    consulta.relacompaneros = f.cleaned_data['relacompaneros']
                    consulta.relamaestros = f.cleaned_data['relamaestros']

                    consulta.dificultadcaminar = f.cleaned_data['dificultadcaminar']
                    consulta.lenguaje = f.cleaned_data['lenguaje']
                    consulta.balbuceo = f.cleaned_data['balbuceo']
                    consulta.silabas = f.cleaned_data['silabas']
                    consulta.primerapalabra = f.cleaned_data['primerapalabra']
                    consulta.frases = f.cleaned_data['frases']
                    consulta.dificultades = f.cleaned_data['dificultades']
                    consulta.idiomas.set(f.cleaned_data['idiomas'])
                    consulta.estadoactual = f.cleaned_data['estadoactual']

                    consulta.separacionmatrimonial = f.cleaned_data['separacionmatrimonial']
                    consulta.cambioresidencia = f.cleaned_data['cambioresidencia']
                    consulta.enfermedades = f.cleaned_data['enfermedades']
                    consulta.defunciones = f.cleaned_data['defunciones']
                    consulta.viajesprolongados = f.cleaned_data['viajesprolongados']
                    consulta.problemaeconomicos = f.cleaned_data['problemaeconomicos']

                    consulta.edadprimerarelacion = f.cleaned_data['edadprimerarelacion']
                    consulta.matrimoniounion = f.cleaned_data['matrimoniounion']
                    consulta.compromisosociales = f.cleaned_data['compromisosociales']
                    consulta.cargotrabajo = f.cleaned_data['cargotrabajo']
                    consulta.masturbacionadolecencia = f.cleaned_data['masturbacionadolecencia']
                    consulta.alcoholadolecencia = f.cleaned_data['alcoholadolecencia']
                    if consulta.alcoholadolecencia:
                        consulta.edadalcohol = f.cleaned_data['edadalcohol']
                        consulta.motivoalcohol = f.cleaned_data['motivoalcohol']
                    else:
                        consulta.edadalcohol = 0
                        consulta.motivoalcohol = ''
                    consulta.drogasadolecencia = f.cleaned_data['drogasadolecencia']
                    if consulta.drogasadolecencia:
                        consulta.edaddrogas = f.cleaned_data['edaddrogas']
                        consulta.motivodrogas = f.cleaned_data['motivodrogas']
                    else:
                        consulta.edaddrogas = 0
                        consulta.motivodrogas = ''

                    consulta.enamoramiento = f.cleaned_data['enamoramiento']
                    consulta.cantidadrelaciones = f.cleaned_data['cantidadrelaciones']
                    consulta.ultimarelacion = f.cleaned_data['ultimarelacion']
                    consulta.matrimoniounionadulto = f.cleaned_data['matrimoniounionadulto']
                    consulta.edadultimarelacion = f.cleaned_data['edadultimarelacion']
                    consulta.compromisosocialesadulto = f.cleaned_data['compromisosocialesadulto']
                    consulta.masturbacionadulto = f.cleaned_data['masturbacionadulto']
                    consulta.cargotrabajoadulto = f.cleaned_data['cargotrabajoadulto']
                    consulta.alcoholadolecenciaadulto = f.cleaned_data['alcoholadolecenciaadulto']
                    if consulta.alcoholadolecenciaadulto:
                        consulta.edadalcoholadulto = f.cleaned_data['edadalcoholadulto']
                        consulta.motivoalcoholadulto = f.cleaned_data['motivoalcoholadulto']
                    else:
                        consulta.edadalcoholadulto = 0
                        consulta.motivoalcoholadulto = ''
                    consulta.drogasadolecenciaadulto = f.cleaned_data['drogasadolecenciaadulto']
                    if consulta.drogasadolecenciaadulto:
                        consulta.edaddrogasadulto = f.cleaned_data['edaddrogasadulto']
                        consulta.motivodrogasadulto = f.cleaned_data['motivodrogasadulto']
                    else:
                        consulta.edaddrogasadulto = 0
                        consulta.motivodrogasadulto = ''

                    consulta.save(request)

                    # for e in enfermedades:
                    #     idcatalogo = int(e['id'])
                    #     catalogo = CatalogoEnfermedad.objects.get(pk=idcatalogo)
                    #     consulta.enfermedad.add(catalogo)

                    log(u'Modifico consulta previa psicologica: %s' % consulta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'load_datatable_tests':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                aaData = []
                tCount = 0
                tests = TestPsicologico.objects.filter()
                isView = 1
                if not persona.usuario.is_staff:
                    tests = tests.filter(status=True)
                    isView = 0

                if txt_filter:
                    tests = tests.filter(Q(nombre__icontains=txt_filter))

                tests = tests.order_by('nombre')

                tCount = tests.count()
                if offset == 0:
                    testsRows = tests[offset:limit]
                elif offset == limit:
                    testsRows = tests[offset:tCount]
                else:
                    testsRows = tests[offset:offset + limit]
                aaData = []

                for dataRow in testsRows:

                    aaData.append([dataRow.id,
                                   dataRow.nombre,
                                   dataRow.version,
                                   {'id': dataRow.id, 'can_delete_edit': dataRow.can_delete()}])
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex, "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'load_datatable_tests_paciente':
            try:
                idp = request.POST['idp'] if 'idp' in request.POST and request.POST['idp'] else 0
                filter_date_begin = request.POST['filter_date_begin'] if request.POST['filter_date_begin'] else ''
                filter_date_end = request.POST['filter_date_end'] if request.POST['filter_date_end'] else ''
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                aaData = []
                tCount = 0
                paciente = Persona.objects.get(pk=idp)
                tests = PersonaTestPsicologica.objects.filter(persona=paciente)
                filter_date_begin = convertir_fecha(filter_date_begin)
                filter_date_end = convertir_fecha(filter_date_end)
                tests = tests.filter(fecha__range=(filter_date_begin, filter_date_end))
                isView = 1
                if not persona.usuario.is_staff:
                    tests = tests.filter(status=True)
                    isView = 0

                if txt_filter:
                    tests = tests.filter(Q(test__nombre__icontains=txt_filter))

                tests = tests.order_by('test__nombre')

                tCount = tests.count()
                if offset == 0:
                    testsRows = tests[offset:limit]
                elif offset == limit:
                    testsRows = tests[offset:tCount]
                else:
                    testsRows = tests[offset:offset + limit]
                aaData = []

                for dataRow in testsRows:
                    aaData.append([{'nombre': dataRow.test.nombre,
                                    'version': dataRow.test.version,
                                    'fecha': dataRow.fecha.strftime("%d/%m/%Y"),
                                    'medico': dataRow.medico.__str__(),
                                    },
                                    {'diagnostico': dataRow.diagnostico if dataRow.diagnostico else 'Sin diagnóstico',
                                     'diagnosticoverbose': dataRow.diagnosticoverbose if dataRow.diagnosticoverbose else 'Sin diagnóstico'},
                                    dataRow.id
                                   ])
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount, 'paciente': paciente.__str__()})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex, "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0, 'paciente': None})

        elif action == 'load_questions':
            try:
                q = request.POST['q'] if 'q' in request.POST and request.POST['q'] else ''
                preguntas = PsicologicoPreguntasBanco.objects.filter(status=True)
                if q:
                    preguntas = preguntas.filter(Q(descripcion__icontains=q))[:25]
                else:
                    preguntas = preguntas[:25]
                aData = []
                for pregunta in preguntas:
                    aData.append({'id': pregunta.id, 'text': pregunta.descripcion, 'leyenda': pregunta.leyenda})
                return JsonResponse({"result": "ok", "mensaje": u"", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error no se pudo cargar los datos.", "aData": []})

        elif action == 'load_test':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else 0
                if not TestPsicologico.objects.filter(pk=id).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro el test."})

                test = TestPsicologico.objects.get(pk=id)
                detalles = TestPsicologicoPreguntas.objects.filter(test=test, status=True).order_by('orden')

                aDataDetalles = []
                for detalle in detalles:
                    aDataDetalles.append({
                                            'pregunta':
                                                        {
                                                            'id': detalle.pregunta.id,
                                                            'text': detalle.pregunta.descripcion,
                                                            'leyenda': detalle.pregunta.leyenda
                                                        },
                                            'tiporespuesta':
                                                            {
                                                                'id': detalle.tiporespuesta.id,
                                                                'text': detalle.tiporespuesta.nombre,
                                                            },
                                            'escala':
                                                        {
                                                            'id': detalle.escala.id if detalle.escala else 0,
                                                            'text': detalle.escala.descripcion if detalle.escala else '',
                                                        }
                                    })
                aData = {
                    'id': test.id,
                    'nombre': test.nombre,
                    'subnombre': test.subnombre,
                    'version': test.version,
                    'instruccion': test.instruccion,
                    'preguntas': aDataDetalles
                }
                return JsonResponse({"result": "ok", "mensaje": u"", "aData": aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error no se pudo cargar datos.", "aData": []})

        elif action == 'save_test_psicologico':
            try:
                id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else 0
                nombre = request.POST['nombre'] if 'nombre' in request.POST and request.POST['nombre'] else ''
                subnombre = request.POST['subnombre'] if 'subnombre' in request.POST and request.POST['subnombre'] else ''
                version = int(request.POST['version']) if 'version' in request.POST and request.POST['version'] else 0
                instruccion = request.POST['instruccion'] if 'instruccion' in request.POST and request.POST['instruccion'] else ''
                detalles = json.loads(request.POST['preguntas'])
                formError = []
                isError = False
                if not nombre:
                    formError.append({'name':'nombre', 'error': u"Ingrese un nombre al test"})
                    isError = True
                if version <= 0:
                    formError.append({'name':'version', 'error':  u"Ingrese solo numeros entero mayor a cero"})
                    isError = True

                if isError:
                    return JsonResponse({"result": "bad", "mensaje": u"Existe errores por superar", "errores": formError})
                orden = 0
                if id:
                    if not TestPsicologico.objects.filter(pk=id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El test a editar no se encontro", "errores": []})
                    if TestPsicologico.objects.filter(nombre=nombre, version=version).exclude(pk=id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El test a editar ya existe", "errores": []})
                    test = TestPsicologico.objects.get(pk=id)
                    test.nombre = nombre
                    test.subnombre = subnombre
                    test.version = version
                    test.instruccion = instruccion
                    test.save(request)
                    log(u"Modifico test psicológico: %s" % test, request, 'edit')

                    arrIds = []
                    for detalle in detalles:
                        pregunta = None
                        test_detalle_id = 0
                        if PsicologicoPreguntasBanco.objects.filter(pk=detalle['id_pregunta']).exists():
                            pregunta = PsicologicoPreguntasBanco.objects.get(pk=detalle['id_pregunta'])
                        if TestPsicologicoPreguntas.objects.filter(pregunta=pregunta, test=test).exists():
                            test_detalle = TestPsicologicoPreguntas.objects.filter(pregunta=pregunta, test=test)[0]
                            arrIds.append(test_detalle.id)

                    if TestPsicologicoPreguntas.objects.filter(test=test).exists():
                        TestPsicologicoPreguntas.objects.filter(test=test).exclude(pk__in=arrIds).delete()

                    for detalle in detalles:
                        orden += 1
                        pregunta = None
                        tiporespuesta = None
                        escala = None
                        if PsicologicoPreguntasBanco.objects.filter(pk=detalle['id_pregunta']).exists():
                            pregunta = PsicologicoPreguntasBanco.objects.get(pk=detalle['id_pregunta'])

                        if TipoRespuesta.objects.filter(pk=detalle['id_tiprespuesta']).exists():
                            tiporespuesta = TipoRespuesta.objects.get(pk=detalle['id_tiprespuesta'])

                        if PsicologicoPreguntasBancoEscala.objects.filter(pk=detalle['id_escala']).exists():
                            escala = PsicologicoPreguntasBancoEscala.objects.get(pk=detalle['id_escala'])

                        if TestPsicologicoPreguntas.objects.filter(test=test, pregunta=pregunta).exists():
                            detalle_test = TestPsicologicoPreguntas.objects.filter(test=test, pregunta=pregunta)[0]
                            detalle_test.tiporespuesta = tiporespuesta
                            detalle_test.escala = escala
                            detalle_test.orden = orden
                        else:
                            detalle_test = TestPsicologicoPreguntas(test=test, pregunta=pregunta,tiporespuesta=tiporespuesta, escala=escala, orden=orden)
                        detalle_test.save(request)

                else:
                    if TestPsicologico.objects.filter(nombre=nombre, version=version).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"El test ya existe", "errores": []})
                    test = TestPsicologico(nombre=nombre, subnombre=subnombre, version=version, instruccion=instruccion)
                    test.save(request)
                    log(u"Adiciono test psicológico: %s" % test, request, 'add')

                    for detalle in detalles:
                        orden += 1
                        pregunta = None
                        tiporespuesta = None
                        escala = None
                        if PsicologicoPreguntasBanco.objects.filter(pk=detalle['id_pregunta']).exists():
                            pregunta = PsicologicoPreguntasBanco.objects.get(pk=detalle['id_pregunta'])

                        if TipoRespuesta.objects.filter(pk=detalle['id_tiprespuesta']).exists():
                            tiporespuesta = TipoRespuesta.objects.get(pk=detalle['id_tiprespuesta'])

                        if PsicologicoPreguntasBancoEscala.objects.filter(pk=detalle['id_escala']).exists():
                            escala = PsicologicoPreguntasBancoEscala.objects.get(pk=detalle['id_escala'])

                        detalle_test = TestPsicologicoPreguntas(test=test, pregunta=pregunta, tiporespuesta=tiporespuesta, escala=escala, orden=orden)
                        detalle_test.save(request)


                preguntas = TestPsicologicoPreguntas.objects.filter(test=test)
                escalas = PsicologicoPreguntasBancoEscala.objects.filter(pk__in=preguntas.values_list('escala_id').distinct()).distinct()

                for escala in escalas:
                    orden = 0
                    for pre in preguntas.filter(escala=escala).order_by('orden'):
                        orden += 1
                        pre.orden = orden
                        pre.save(request)

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error no se pudo guardar los datos.", "errores": []})

        elif action == 'load_datatable_search_pacientes':
            try:
                txt_filter = request.POST['sSearch'] if request.POST['sSearch'] else ''
                limit = int(request.POST['iDisplayLength']) if request.POST['iDisplayLength'] else 25
                offset = int(request.POST['iDisplayStart']) if request.POST['iDisplayStart'] else 0
                aaData = []
                tCount = 0
                personas = Persona.objects.filter(Q(tipopersona=1) | Q(cedula__isnull=True) | Q(pasaporte__isnull=True))
                isView = 1
                if not persona.usuario.is_staff:
                    personas = personas.filter(status=True)
                    isView = 0

                if txt_filter:
                    ss = txt_filter.split(' ')
                    while '' in ss:
                        ss.remove('')
                    if len(ss) == 1:
                        personas = personas.filter(Q(nombres__icontains=txt_filter) |
                                                   Q(apellido1__icontains=txt_filter) |
                                                   Q(apellido2__icontains=txt_filter) |
                                                   Q(cedula__icontains=txt_filter) |
                                                   Q(pasaporte__icontains=txt_filter)).distinct()
                    else:
                        personas = personas.filter(Q(apellido1__icontains=ss[0]) &
                                                   Q(apellido2__icontains=ss[1])).distinct()

                personas = personas.order_by('apellido1', 'apellido2')

                tCount = personas.count()
                if offset == 0:
                    personasRows = personas[offset:limit]
                elif offset == limit:
                    personasRows = personas[offset:tCount]
                else:
                    personasRows = personas[offset:offset + limit]
                aaData = []

                for dataRow in personasRows:
                    documento = dataRow.cedula if dataRow.cedula else dataRow.pasaporte
                    aaData.append([{'id': dataRow.id, 'paciente': dataRow.__str__()},
                                   documento,
                                   dataRow.__str__(),
                                   dataRow.sexo.id if dataRow.sexo else 0,
                                   dataRow.nacimiento.strftime("%d/%m/%Y")])
                return JsonResponse({"result": "ok", "mensaje": u"Cargo los datos.", "data": aaData, "iTotalRecords": tCount, "iTotalDisplayRecords": tCount})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al cargar los datos: %s" % ex, "data": [], "iTotalRecords": 0, "iTotalDisplayRecords": 0})

        elif action == 'save_add_paciente':
            try:
                tipo_identificacion = int(request.POST['tipo_identificacion']) if 'tipo_identificacion' in request.POST and request.POST['tipo_identificacion'] else 0
                identificacion = request.POST['identificacion'] if 'identificacion' in request.POST and request.POST['identificacion'] else ''
                apellido_paterno = request.POST['apellido_paterno'] if 'apellido_paterno' in request.POST and request.POST['apellido_paterno'] else ''
                apellido_materno = request.POST['apellido_materno'] if 'apellido_materno' in request.POST and request.POST['apellido_materno'] else ''
                nombres = request.POST['nombres'] if 'nombres' in request.POST and request.POST['nombres'] else ''
                sexo = int(request.POST['sexo']) if 'sexo' in request.POST and request.POST['sexo'] else 0
                nacimiento = request.POST['nacimiento'] if 'nacimiento' in request.POST and request.POST['nacimiento'] else ''
                formError = []
                isError = False
                if not tipo_identificacion:
                    formError.append({'name':'tipo_identificacion', 'error': u"Seleccione un tipo de identificación"})
                    isError = True
                if not identificacion:
                    formError.append({'name': 'identificacion', 'error': u"Ingrese un número de identificación"})
                    isError = True
                if not apellido_paterno:
                    formError.append({'name':'apellido_paterno', 'error': u"Inhgrese el apellido paterno"})
                    isError = True
                if not nombres:
                    formError.append({'name':'nombres', 'error': u"Ingrese los nombres"})
                    isError = True
                if not sexo:
                    formError.append({'name':'sexo', 'error': u"Seleccione el sexo"})
                    isError = True
                if not nacimiento:
                    formError.append({'name':'nacimiento', 'error': u"Ingrese una fecha de nacimiento"})
                    isError = True

                if isError:
                    return JsonResponse({"result": "bad", "mensaje": u"Existe errores por superar", "errores": formError})
                if Persona.objects.filter(Q(cedula__icontains=identificacion) |  Q(pasaporte__icontains=identificacion)).exists():
                    return JsonResponse( {"result": "bad", "mensaje": u"Paciente ya existe", "errores": formError})

                cedula = ''
                pasaporte = ''
                if tipo_identificacion == 1:
                    cedula = identificacion
                else:
                    pasaporte = identificacion
                persona = Persona(cedula=cedula,
                                  pasaporte=pasaporte,
                                  nombres=nombres,
                                  apellido1=apellido_paterno,
                                  apellido2=apellido_materno,
                                  sexo_id=sexo,
                                  nacimiento=datetime.strptime(nacimiento, '%d-%m-%Y'))
                persona.save(request)
                log(u"Adiciono nueva persona: %s" % persona, request, 'add')

                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error no se pudo guardar los datos.", "errores": []})

        elif action == 'aplicar_test_paciente':
            try:
                id_paciente = int(request.POST['id_paciente']) if 'id_paciente' in request.POST and request.POST['id_paciente'] else 0
                if not Persona.objects.filter(pk=id_paciente).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro paciente para el test psicológico"})
                id_test = int(request.POST['id_test']) if 'id_test' in request.POST and request.POST['id_test'] else 0
                if not TestPsicologico.objects.filter(pk=id_test).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro el test psicológico"})
                data['paciente'] = paciente = Persona.objects.get(pk=id_paciente)
                data['test'] = test = TestPsicologico.objects.get(pk=id_test)
                data['preguntas'] = preguntas = TestPsicologicoPreguntas.objects.filter(test=test, status=True)
                data['escalas'] = escalas = PsicologicoPreguntasBancoEscala.objects.filter(pk__in=preguntas.values_list('escala_id').distinct()).distinct()
                template = get_template('box_psicologica/test_aplicar_paciente.html')
                json_contenido = template.render(data)

                aData = []
                for detalle in preguntas:
                    aData.append({'id': detalle.id,
                                  'regla': detalle.tiporespuesta.valor_valida_parent,
                                  'validar_children': 1 if detalle.tiporespuesta.children else 0,
                                  'pregunta': detalle.pregunta.id,
                                  'respuesta_id': None,
                                  'respuesta_valor': None,
                                  'respuesta_children_id': None,
                                  'respuesta_children_valor': None,
                                  })
                return JsonResponse({"result": "ok", "mensaje": u"Se cargo el test correctamente", "contenido": json_contenido, 'aData': aData})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error no se pudo cargar la información"})

        elif action == 'save_test_aplicado_paciente':
            try:
                id_paciente = int(request.POST['id_paciente']) if 'id_paciente' in request.POST and request.POST[
                    'id_paciente'] else 0
                if not Persona.objects.filter(pk=id_paciente).exists():
                    return JsonResponse(
                        {"result": "bad", "mensaje": u"Error no se encontro paciente para el test psicológico"})
                id_test = int(request.POST['id_test']) if 'id_test' in request.POST and request.POST['id_test'] else 0
                if not TestPsicologico.objects.filter(pk=id_test).exists():
                    return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro el test psicológico"})
                data['paciente'] = paciente = Persona.objects.get(pk=id_paciente)
                data['test'] = test = TestPsicologico.objects.get(pk=id_test)
                personatest = PersonaTestPsicologica(test=test,
                                                     persona=paciente,
                                                     fecha=datetime.now(),
                                                     medico=persona)
                personatest.save(request)

                respuestas = json.loads(request.POST['respuestas'])
                for res in respuestas:
                    if not PsicologicoPreguntasBanco.objects.filter(pk=int(res['pregunta'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro la pregunta"})
                    pregunta = PsicologicoPreguntasBanco.objects.get(pk=int(res['pregunta']))

                    if not Respuesta.objects.filter(pk=int(res['respuesta_id'])).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro la respuesta"})
                    respuesta = Respuesta.objects.get(pk=int(res['respuesta_id']))
                    respuesta_children = None
                    if res['validar_children'] == 1:
                        if respuesta.tiporespuesta.valor_valida_parent == float(res['respuesta_valor']):
                            if not res['respuesta_children_id']:
                                return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro la respuesta por verdadero"})
                            if not Respuesta.objects.filter(pk=int(res['respuesta_children_id'])).exists():
                                return JsonResponse({"result": "bad", "mensaje": u"Error no se encontro la respuesta"})
                            respuesta_children = Respuesta.objects.get(pk=int(res['respuesta_children_id']))

                    respuesta_test = RespuestaTestPsicologica(pregunta=pregunta,
                                                              respuesta=respuesta,
                                                              respuesta_valor=res['respuesta_valor'],
                                                              respuesta_children=respuesta_children,
                                                              respuesta_children_valor=res['respuesta_children_valor'])
                    respuesta_test.save(request)
                    personatest.respuestas.add(respuesta_test)

                if not TestPsicologicoCalculoDiagnostico.objects.filter(test=personatest.test).exists():
                    raise NameError('Error no existe calculo de diagnostico')

                action_run = TestPsicologicoCalculoDiagnostico.objects.filter(test=personatest.test)[0]
                diagnostico = actioncalculotestpsicologico(personatest, action_run.nombreaccion)
                if not diagnostico['result']:
                    raise NameError("Error no se puedo calcular el diagnostico")
                personatest.diagnostico = diagnostico['diagnostico']
                personatest.diagnosticoverbose = diagnostico['diagnosticoverbose']
                personatest.save(request)
                log(u"Adiciono test %s con la persona %s" % (test, persona), request, 'add')
                return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente el test"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error no se pudo guardar la información (%s)" % ex})

        elif action == 'add_pregunta_test':
            try:
                f = PreguntaTestForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['descripcion'] and PsicologicoPreguntasBanco.objects.filter(descripcion=f.cleaned_data['descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error, la pregunta ya existe."})
                    pregunta = PsicologicoPreguntasBanco(descripcion=f.cleaned_data['descripcion'], leyenda=f.cleaned_data['leyenda'])
                    pregunta.save(request)
                    log(u'Adiciono pregunta: %s' % pregunta, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
                else:
                     raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." })

        elif action == 'edit_pregunta_test':
            try:
                f = PreguntaTestForm(request.POST)
                if f.is_valid():
                    pregunta = PsicologicoPreguntasBanco.objects.get(pk=request.POST['id'])
                    if f.cleaned_data['descripcion'] and PsicologicoPreguntasBanco.objects.filter(descripcion=f.cleaned_data['descripcion']).exclude(pk=pregunta.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error, la pregunta ya existe."})
                    pregunta.descripcion = f.cleaned_data['descripcion']
                    pregunta.leyenda = f.cleaned_data['leyenda']
                    pregunta.save(request)
                    log(u'Modifico pregunta: %s' % pregunta, request, "edit")
                    return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
                else:
                     raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'delete_pregunta_test':
            try:
                pregunta = PsicologicoPreguntasBanco.objects.get(pk=request.POST['id'])
                pregunta.delete()
                log(u'Elimino pregunta: %s' % pregunta, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        elif action == 'add_escala_test':
            try:
                f = EscalaPreguntaTestForm(request.POST)
                if f.is_valid():
                    if f.cleaned_data['descripcion'] and PsicologicoPreguntasBancoEscala.objects.filter(descripcion=f.cleaned_data['descripcion']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error, la escala ya existe."})
                    escala = PsicologicoPreguntasBancoEscala(descripcion=f.cleaned_data['descripcion'], leyenda=f.cleaned_data['leyenda'])
                    escala.save(request)
                    log(u'Adiciono escala: %s' % escala, request, "add")
                    return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
                else:
                     raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos." })

        elif action == 'edit_escala_test':
            try:
                f = EscalaPreguntaTestForm(request.POST)
                if f.is_valid():
                    escala = PsicologicoPreguntasBancoEscala.objects.get(pk=request.POST['id'])
                    if f.cleaned_data['descripcion'] and PsicologicoPreguntasBancoEscala.objects.filter(descripcion=f.cleaned_data['descripcion']).exclude(pk=escala.id).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Error, la escala ya existe."})
                    escala.descripcion = f.cleaned_data['descripcion']
                    escala.leyenda = f.cleaned_data['leyenda']
                    escala.save(request)
                    log(u'Modifico escala: %s' % escala, request, "edit")
                    return JsonResponse({"result": "ok", "mensaje": u"Se guardo correctamente"})
                else:
                     raise NameError('Error en el formulario')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'delete_escala_test':
            try:
                escala = PsicologicoPreguntasBancoEscala.objects.get(pk=request.POST['id'])
                escala.delete()
                log(u'Elimino escala: %s' % escala, request, "del")
                return JsonResponse({"result": "ok", "mensaje": u"Se elimino correctamente"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})

    else:
        data = {}
        adduserdata(request, data)
        data['title'] = u'Consultas psicológicas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'consultapsicologica':
                try:
                    persona = Persona.objects.get(pk=request.GET['id'])
                    data['title'] = u'Consulta psicológica - Paciente: ' + str(persona) + ' - ' + persona.identificacion()
                    data['paciente'] = persona

                    form = PersonaConsultaPsicologicaForm(initial={'fechaatencion': datetime.now().date(),
                                                                   'fecha': datetime.now().date(),
                                                                   'hora': "12:00"
                                                                   })
                    tpac = persona.tipo_paciente()
                    form.tipos_paciente(tpac['tipoper'], tpac['regimen'])

                    if tpac['tipoper'] == 'ALU':
                        matri = persona.datos_ultima_matricula()
                        data['idmatricula'] = matri['idmatricula']

                    data['form'] = form
                    data['form2'] = AccionConsultaForm()
                    return render(request, "box_psicologica/consultapsicologica.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadodetalladoareapsicologica':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)
                    tipopaciente = int(request.GET['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

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
                    response['Content-Disposition'] = 'attachment; filename=listado_atenciones_psicologicas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO DETALLADO DE ATENCIONES DEL ÁREA PSICOLÓGICA', titulo2)
                    ws.write_merge(3, 3, 0, 11, 'DESDE:   ' + str(convertir_fecha(request.GET['desde'])) + '     HASTA:   ' + str(convertir_fecha(request.GET['hasta'])), titulo2)
                    ws.write_merge(4, 4, 0, 11, str(persona) if not esdirectordbu else '', titulo2)

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

                    atenciones = PersonaConsultaPsicologica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True).order_by('-fecha')

                    # if not esdirectordbu:
                    #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                    for a in atenciones:
                        row_num += 1
                        facultad = carrera = nivel = ""
                        ws.write(row_num, 0, a.fecha, fuentefecha)
                        #fechaatencion = a.fecha.date()
                        p = Persona.objects.get(pk=a.persona_id)
                        ws.write(row_num, 1, TIPO_PACIENTE[a.tipopaciente-1][1], fuentenormal)

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

                        cie10 = ""
                        for e in a.enfermedad.all():
                            cie10 = cie10 + ", " + e.clave + " - " + e.descripcion if cie10 != "" else e.clave + " - " + e.descripcion
                        ws.write(row_num, 16, cie10, fuentenormal)

                        acciones = ''
                        for ac in a.accion.all():
                            acciones = acciones + ", " + ac.descripcion if acciones != "" else ac.descripcion

                        ws.write(row_num, 17, acciones, fuentenormal)

                        responsable = Persona.objects.get(usuario=a.usuario_creacion)
                        ws.write(row_num, 18, responsable.apellido1+ ' ' + responsable.apellido2 + ' ' +responsable.nombres, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'consultapsicologicaprevias':
                try:
                    data['title'] = u'Consultas psicológicas previas'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['consultas'] = PersonaConsultaPsicologica.objects.filter(persona=persona)
                    return render(request, "box_psicologica/consultapsicologicaprevias.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconsultapsicologicaprevia':
                try:
                    data['consulta'] = consulta = PersonaConsultaPsicologica.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar consulta psicológica - Paciente: ' + str(consulta.persona) + ' - ' + consulta.persona.identificacion()
                    tipos = (consulta.tipopaciente, TIPO_PACIENTE[consulta.tipopaciente - 1][1])
                    enfermedad = consulta.enfermedad.values('id', 'descripcion').all()
                    data['enfermedad'] = enfermedad

                    # form = PersonaConsultaPsicologicaForm(initial={'grupo': consulta.pacientegrupo,
                    #                                                'tipoatencion': consulta.tipoatencion,
                    #                                                'tipoterapia': consulta.tipoterapia,
                    #                                                'motivo': consulta.motivo,
                    #                                                'diagnostico': consulta.diagnostico,
                    #                                                'tratamiento': consulta.tratamiento,
                    #                                                'medicacion': consulta.medicacion,
                    #                                                'tipopaciente': consulta.tipopaciente})

                    initial = model_to_dict(consulta)
                    form = PersonaConsultaPsicologicaForm(initial=initial)

                    form.editar(tipos)
                    data['form'] = form
                    data['form2'] = AccionConsultaForm()
                    data['paciente'] = consulta.persona
                    return render(request, "box_psicologica/editconsultapsicologicaprevia.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarfichapsicologica':
                try:
                    data['consulta'] = consulta = DatosPsicologico.objects.get(pk=request.GET['id'])
                    persona = consulta.personafichamedica.personaextension.persona
                    data['title'] = u'Editar ficha psicológica - Paciente: ' + str(persona) + ' - ' + persona.identificacion()
                    initial = model_to_dict(consulta)
                    form = DatosPsicologicoForm(initial=initial)
                    data['form'] = form
                    data['paciente'] = persona
                    return render(request, "box_psicologica/editarfichapsicologica.html", data)
                except Exception as ex:
                    pass

            elif action == 'ficha':
                try:
                    data['title'] = u'Ficha Psicológica'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['pex'] = pex = persona.datos_extension().personadatospsicologico()
                    #data['reporte_0'] = obtener_reporte('med_fichamedica')
                    return render(request, "box_psicologica/ficha.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionar_test':
                try:
                    data['title'] = u'Gestión de test psicológicos'
                    data['tiporespuestas'] = TipoRespuesta.objects.filter(status=True)
                    data['escalas'] = PsicologicoPreguntasBancoEscala.objects.filter(status=True)
                    return render(request, "box_psicologica/gestionartest.html", data)
                except Exception as ex:
                    pass

            elif action == 'pacientes_test_psicologicos':
                try:
                    data['title'] = u'Pacientes con test psicológicos'
                    search = None
                    ids = None
                    consultas = PersonaTestPsicologica.objects.filter(status=True)
                    esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()
                    pacientes = Persona.objects.filter(pk__in=PersonaTestPsicologica.objects.values_list('persona_id').filter(status=True).distinct()).distinct()
                    if 's' in request.GET:
                        search = request.GET['s']
                        ss = search.split(' ')
                        while '' in ss:
                            ss.remove('')
                        if len(ss) == 1:
                            pacientes = pacientes.filter(Q(nombres__icontains=search) |
                                                         Q(apellido1__icontains=search) |
                                                         Q(apellido2__icontains=search) |
                                                         Q(cedula__icontains=search) |
                                                         Q(pasaporte__icontains=search) |
                                                         Q(inscripcion__identificador__icontains=search) |
                                                         Q(inscripcion__inscripciongrupo__grupo__nombre__icontains=search) |
                                                         Q(inscripcion__carrera__nombre__icontains=search)).distinct()
                        else:
                            pacientes = pacientes.filter(Q(apellido1__icontains=ss[0]) & Q(apellido2__icontains=ss[1])).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        pacientes = pacientes.filter(id=ids).distinct()
                    paging = MiPaginador(pacientes, 25)
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
                    data['pacientes'] = page.object_list
                    data['sexos'] = Sexo.objects.filter(status=True)
                    data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''
                    data['medico'] = persona.usuario
                    data['totalgeneral'] = consultas.count()
                    data['totalgeneralusuario'] = consultas.filter(medico=persona).count()
                    data['totalhoy'] = consultas.filter(fecha__date=datetime.now().date()).count()
                    data['totalusuariohoy'] = consultas.filter(fecha__date=datetime.now().date(), medico=persona).count()
                    data['filter_date_begin'] = (datetime.now() - timedelta(days=90)).date()
                    data['filter_date_end'] = datetime.now().date() + timedelta(days=1)
                    return render(request, "box_psicologica/pacientes_test_psicologicos.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionar_preguntas_test':
                try:
                    data['title'] = u'Preguntas de test psicológicos'
                    search = None
                    ids = None
                    preguntas = PsicologicoPreguntasBanco.objects.filter().distinct()
                    if 's' in request.GET:
                        search = request.GET['s']
                        preguntas = preguntas.filter(Q(descripcion__icontains=search) | Q(leyenda__icontains=search)).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        preguntas = preguntas.filter(id=ids).distinct()
                    paging = MiPaginador(preguntas, 25)
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
                    data['preguntas'] = page.object_list
                    return render(request, "box_psicologica/view_preguntas_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_preguntas_test':
                try:
                    data['title'] = 'Adicionar pregunta'
                    form = PreguntaTestForm()
                    data['form'] = form
                    return render(request, "box_psicologica/add_pregunta_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit_preguntas_test':
                try:
                    data['title'] = 'Editar pregunta'
                    id = request.GET['id'] if 'id' in request.GET and request.GET['id'] else 0
                    if PsicologicoPreguntasBanco.objects.filter(pk=id).exists():
                        pregunta = PsicologicoPreguntasBanco.objects.get(pk=id)
                        form = PreguntaTestForm(initial={'descripcion': pregunta.descripcion, 'leyenda': pregunta.leyenda})
                        data['form'] = form
                        data['pregunta'] = pregunta
                        return render(request, "box_psicologica/edit_pregunta_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete_preguntas_test':
                try:
                    data['title'] = u'Eliminar pregunta'
                    data['pregunta'] = PsicologicoPreguntasBanco.objects.get(pk=request.GET['id'])
                    return render(request, "box_psicologica/eliminar_pregunta_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'gestionar_escalas_test':
                try:
                    data['title'] = u'Escalas de test psicológicos'
                    search = None
                    ids = None
                    escalas = PsicologicoPreguntasBancoEscala.objects.filter().distinct()
                    if 's' in request.GET:
                        search = request.GET['s']
                        escalas = escalas.filter(Q(descripcion__icontains=search) | Q(leyenda__icontains=search)).distinct()
                    elif 'id' in request.GET:
                        ids = request.GET['id']
                        escalas = escalas.filter(id=ids).distinct()
                    paging = MiPaginador(escalas, 25)
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
                    data['escalas'] = page.object_list
                    return render(request, "box_psicologica/view_escalas_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'add_escalas_test':
                try:
                    data['title'] = 'Adicionar escala'
                    form = EscalaPreguntaTestForm()
                    data['form'] = form
                    return render(request, "box_psicologica/add_escala_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit_escalas_test':
                try:
                    data['title'] = 'Editar escala'
                    id = request.GET['id'] if 'id' in request.GET and request.GET['id'] else 0
                    if PsicologicoPreguntasBancoEscala.objects.filter(pk=id).exists():
                        escala = PsicologicoPreguntasBancoEscala.objects.get(pk=id)
                        form = EscalaPreguntaTestForm(initial={'descripcion': escala.descripcion, 'leyenda': escala.leyenda})
                        data['form'] = form
                        data['escala'] = escala
                        return render(request, "box_psicologica/edit_escala_test.html", data)
                except Exception as ex:
                    pass

            elif action == 'delete_escalas_test':
                try:
                    data['title'] = u'Eliminar escala'
                    data['escala'] = PsicologicoPreguntasBancoEscala.objects.get(pk=request.GET['id'])
                    return render(request, "box_psicologica/eliminar_escala_test.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Consultas psicológicas'
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()
                search = None
                ids = None

                consultas = PersonaConsultaPsicologica.objects.values_list('id').filter(status=True)
                totalgeneral = consultas.count()
                totalgeneralusuario = consultas.filter(usuario_creacion_id=persona.usuario.id).count()
                totalhoy = consultas.filter(fecha__date=datetime.now().date()).count()
                totalusuariohoy = consultas.filter(fecha__date=datetime.now().date(), usuario_creacion_id=persona.usuario.id).count()

                personal = Persona.objects.filter(Q(perfilusuario__administrativo__isnull=False)
                                                  | Q(perfilusuario__inscripcion__isnull=False)
                                                  | Q(perfilusuario__profesor__isnull=False)
                                                  | (Q(perfilusuario__externo__isnull=False) & Q(tipopersona=1))
                                                  ).exclude(perfilusuario__empleador__isnull=False)

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
                data['utiliza_grupos_alumnos'] = UTILIZA_GRUPOS_ALUMNOS
                data['fecha'] = datetime.now().strftime('%d-%m-%Y')
                data['area'] = "Área psicológica"
                data['tipopacientes'] = TIPO_PACIENTE
                data['totalgeneral'] = totalgeneral
                data['totalgeneralusuario'] = totalgeneralusuario
                data['totalhoy'] = totalhoy
                data['totalusuariohoy'] = totalusuariohoy
                data['medico'] = persona.usuario
                codigos_facultad = PersonaConsultaPsicologica.objects.values_list('matricula__inscripcion__coordinacion_id', flat=True).filter(status=True, matricula__isnull=False, tipopaciente=3).order_by('matricula__inscripcion__coordinacion_id').distinct()
                codigos_carrera = PersonaConsultaPsicologica.objects.values_list('matricula__inscripcion__carrera_id', flat=True).filter(status=True, matricula__isnull=False, tipopaciente=3).order_by('matricula__inscripcion__carrera_id').distinct()
                carreras = ','.join(str(c) for c in codigos_carrera)
                data['facultades'] = Coordinacion.objects.filter(status=True, excluir=False, pk__in=codigos_facultad).order_by('id')
                data['codigos_carrera'] = carreras
                data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''

                return render(request, "box_psicologica/view.html", data)
            except Exception as ex:
                pass