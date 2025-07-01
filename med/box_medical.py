# -*- coding: latin-1 -*-
import json
import os
import random
from datetime import datetime, time, date
from decimal import Decimal
from itertools import count

import xlwt
import glob

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Count
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from django.template import Context
from django.template.loader import get_template
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.legends import Legend
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.textlabels import Label
from reportlab.graphics.shapes import Drawing, String
from reportlab.lib import colors
from reportlab.lib.colors import PCMYKColor
from reportlab.lib.formatters import DecimalFormatter
from reportlab.lib.validators import Auto
from xlwt import easyxf, XFStyle, Workbook

from decorators import secure_module, last_access
from med.forms import PersonaExtensionForm, PersonaExamenFisicoForm, \
    PersonaConsultaMedicaForm, PatologicoFamiliarForm, PatologicoPersonalForm, PatologicoQuirurgicosForm, \
    AntecedenteTraumatologicosForm, AntecedenteGinecoobstetricoForm, HabitoForm, InspeccionSomaticaForm, \
    InspeccionTopograficaForm, RutagramaForm, VacunaForm, EnfermedadForm, AlergiaForm, MedicinaForm, CirugiaForm, \
    LugarAnatomicoForm, DrogaForm, MetodoAnticonceptivoForm, LesionesForm, FechaFichaMedicaForm, AccionConsultaForm, \
    RevisarRexmedForm, ConsultaMedicaForm
from med.models import PersonaExamenFisico, PersonaConsultaMedica, \
    IndicadorSobrepeso, ProximaCita, PatologicoFamiliar, PatologicoPersonal, PatologicoQuirurgicos, \
    AntecedenteTraumatologicos, AntecedenteGinecoobstetrico, Habito, InspeccionSomatica, InspeccionTopografica, \
    Rutagrama, PersonaExtension, PersonaFichaMedica, TIPO_PACIENTE, PersonaConsultaOdontologica, \
    PersonaConsultaPsicologica, Vacuna, Enfermedad, Alergia, Medicina, CatalogoEnfermedad, Cirugia, LugarAnatomico, \
    Droga, MetodoAnticonceptivo, Lesiones, AccionConsulta, InventarioMedico, InventarioMedicoLote, InventarioMedicoMovimiento
from sagest.models import Jornada, DistributivoPersona, VacunaCovid, Producto
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import MiPaginador, log, convertir_fecha, calcula_edad, grafica_barra, variable_valor
from sga.models import Persona, Matricula, Inscripcion, Coordinacion, Carrera, NivelMalla, PALETA_COLORES, \
    miinstitucion, PersonaDatosFamiliares, Periodo
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo_actual = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'datos':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=request.POST['id'])
                f = PersonaExtensionForm(request.POST)
                if f.is_valid():
                    pexamenfisico.personafichamedica.personaextension.persona.direccion = f.cleaned_data['direccion']
                    pexamenfisico.personafichamedica.personaextension.persona.direccion2 = f.cleaned_data['direccion2']
                    pexamenfisico.personafichamedica.personaextension.horanacimiento = f.cleaned_data['horanacimiento']
                    pexamenfisico.personafichamedica.personaextension.edadaparenta = f.cleaned_data['edadaparenta']
                    pexamenfisico.personafichamedica.personaextension.estadocivil = f.cleaned_data['estadocivil']
                    pexamenfisico.personafichamedica.personaextension.tienelicencia = f.cleaned_data['tienelicencia']
                    pexamenfisico.personafichamedica.personaextension.tipolicencia = f.cleaned_data['tipolicencia']
                    pexamenfisico.personafichamedica.personaextension.telefonos = f.cleaned_data['telefonos']
                    pexamenfisico.personafichamedica.personaextension.tieneconyuge = f.cleaned_data['tieneconyuge']
                    pexamenfisico.personafichamedica.personaextension.hijos = f.cleaned_data['hijos']
                    pexamenfisico.personafichamedica.personaextension.contactoemergencia = f.cleaned_data[
                        'contactoemergencia']
                    pexamenfisico.personafichamedica.personaextension.telefonoemergencia = f.cleaned_data[
                        'telefonoemergencia']
                    pexamenfisico.personafichamedica.gestacion = f.cleaned_data['gestacion']

                    pexamenfisico.personafichamedica.save(request)
                    pexamenfisico.personafichamedica.personaextension.save(request)
                    pexamenfisico.personafichamedica.personaextension.persona.save(request)
                    log(u'Adiciono datos medicos: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregaraccionconsulta':
            try:
                f = AccionConsultaForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionaccion'].strip().upper()
                    area = request.POST['area']
                    if AccionConsulta.objects.filter(descripcion=descripcion, area=area, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la acción ya existe."})
                    else:
                        accionconsulta = AccionConsulta(descripcion=descripcion,
                                                        area=area)
                        accionconsulta.save(request)
                        log(u'Agrego acción de consulta médica: %s' % (accionconsulta), request, "add")
                        return JsonResponse({"result": "ok", "id": accionconsulta.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarlesion':
            try:
                f = LesionesForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionlesion'].strip().upper()
                    tipo = request.POST['tipolesion']
                    if Lesiones.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la lesión ya existe."})
                    else:
                        lesion = Lesiones(descripcion=descripcion,
                                          tipo=tipo)
                        lesion.save(request)
                        log(u'Agrego lesión: %s' % (lesion), request, "add")
                        return JsonResponse({"result": "ok", "id": lesion.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarmetodo':
            try:
                f = MetodoAnticonceptivoForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionmetodo'].strip().upper()
                    if MetodoAnticonceptivo.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse(
                            {"result": "bad", "mensaje": u"La descripción del método anticonceptivo ya existe."})
                    else:
                        metodo = MetodoAnticonceptivo(descripcion=descripcion)
                        metodo.save(request)
                        log(u'Agrego método anticonceptivo: %s' % (metodo), request, "add")
                        return JsonResponse({"result": "ok", "id": metodo.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregardroga':
            try:
                f = DrogaForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripciondroga'].strip().upper()
                    tipo = f.cleaned_data['tipodroga']
                    if Droga.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la droga ya existe."})
                    else:
                        droga = Droga(descripcion=descripcion,
                                      tipo=tipo)
                        droga.save(request)
                        log(u'Agrego droga: %s' % (droga), request, "add")
                        return JsonResponse({"result": "ok", "id": droga.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarlugaranatomico':
            try:
                f = LugarAnatomicoForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionlugaranatomico'].strip().upper()
                    if LugarAnatomico.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la cirugía ya existe."})
                    else:
                        lugar = LugarAnatomico(descripcion=descripcion)
                        lugar.save(request)
                        log(u'Agrego lugar anatómico: %s' % (lugar), request, "add")
                        return JsonResponse({"result": "ok", "id": lugar.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarcirugia':
            try:
                f = CirugiaForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcioncirugia'].strip().upper()
                    if Cirugia.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la cirugía ya existe."})
                    else:
                        cirugia = Cirugia(descripcion=descripcion)
                        cirugia.save(request)
                        log(u'Agrego cirugía: %s' % (cirugia), request, "add")
                        return JsonResponse({"result": "ok", "id": cirugia.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarvacuna':
            try:
                f = VacunaForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionvacuna'].strip().upper()
                    if Vacuna.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la vacuna ya existe."})
                    else:
                        vacuna = Vacuna(descripcion=descripcion)
                        vacuna.save(request)
                        log(u'Agrego vacuna: %s' % (vacuna), request, "add")
                        return JsonResponse({"result": "ok", "id": vacuna.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarenfermedad':
            try:
                f = EnfermedadForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionenfermedad'].strip().upper()
                    if Enfermedad.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la enfermedad ya existe."})
                    else:
                        enfermedad = Enfermedad(descripcion=descripcion,
                                                tipo_id=int(request.POST['tipoenfermedad']))
                        enfermedad.save(request)
                        log(u'Agrego enfermedad: %s' % (enfermedad), request, "add")
                        return JsonResponse({"result": "ok", "id": enfermedad.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregaralergia':
            try:
                f = AlergiaForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionalergia'].strip().upper()
                    if Alergia.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la alergia ya existe."})
                    else:
                        alergia = Alergia(descripcion=descripcion,
                                          tipo=request.POST['tipoalergia'])
                        alergia.save(request)
                        log(u'Agrego alergia: %s' % (alergia), request, "add")
                        return JsonResponse({"result": "ok", "id": alergia.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'agregarmedicina':
            try:
                f = MedicinaForm(request.POST)
                if f.is_valid():
                    descripcion = f.cleaned_data['descripcionmedicina'].strip().upper()
                    if Medicina.objects.filter(descripcion=descripcion, status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"La descripción de la medicina ya existe."})
                    else:
                        medicina = Medicina(descripcion=descripcion)
                        medicina.save(request)
                        log(u'Agrego medicina: %s' % (medicina), request, "add")
                        return JsonResponse({"result": "ok", "id": medicina.id})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el formulario."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'datospaciente':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                data['persona'] = persona
                data['examenfisico'] = persona.datos_examen_fisico()
                data['datosextension'] = persona.datos_extension()
                data['vacunascovid'] = VacunaCovid.objects.filter(persona=persona, status=True).order_by('-id')
                tpac = persona.tipo_paciente()
                data['tipopaciente'] = tpac['tipoper']
                data['regimen'] = tpac['regimen']

                if tpac['tipoper'] == "ALU":
                    mat = persona.datos_ultima_matricula()
                    data['periodo'] = mat['periodo']
                    data['facultad'] = mat['facultad']
                    data['carrera'] = mat['carrera']
                    data['nivel'] = mat['nivel']
                    data['seccion'] = mat['seccion']

                template = get_template("box_medical/datospaciente.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'verificar_atenciones':
            try:
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

                    atenciones = PersonaConsultaMedica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True)

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
                    return JsonResponse(
                        {"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
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

                    atenciones = PersonaConsultaMedica.objects.filter(fecha__range=(desde, hasta), status=True)

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

        elif action == 'resumengeneralareamedica':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área Médica'
                atenciones = PersonaConsultaMedica.objects.filter(fecha__range=(desde, hasta), status=True)

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
                area = "med"
                filename = "ge_" + area + "_" + nusuario + "_"

                path_to_save = os.path.join(os.path.join(SITE_STORAGE, 'media', 'bienestar')) + '/'

                for filenameremove in glob.glob(path_to_save+"/"+filename+"*"):
                    os.remove(filenameremove)

                titulografica = "ATENCIONES POR TIPO DE PACIENTE"
                totaladmin = totaladminf + totaladminm
                totaldocen = totaldocenf + totaldocenm
                totalestu = totalestuf + totalestum
                totalpart = totalpartf + totalpartm
                totalepun = totalepunf + totalepunm
                totaltrab = totaltrabf + totaltrabm
                totalniv = totalnivf + totalnivm

                padmin = round((totaladmin*100) / totalgeneral, 2)
                pdocen = round((totaldocen*100) / totalgeneral, 2)
                pestu = round((totalestu*100) / totalgeneral, 2)
                ppart = round((totalpart*100) / totalgeneral, 2)
                pepun = round((totalepun*100) / totalgeneral, 2)
                ptrab = round((totaltrab*100) / totalgeneral, 2)
                pniv = round((totalniv*100) / totalgeneral, 2)

                #valores = [[totaladmin, totaldocen, totalestu, totalpart, totalepun, totaltrab, totalniv]]
                valores = [[padmin, pdocen, pestu, ppart, pepun, ptrab, pniv]]
                categorias = ['ADMINISTRATIVOS', 'DOCENTES', 'ESTUDIANTES',
                                 'PARTICULARES', 'PARTICULARES/EPUNEMI', 'TRABAJADORES', 'NIVELACION']
                mostrarsimboloporcentaje = True
                tieneleyenda = False
                barrasagrupadas = False
                coloresindividual = [PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3], PALETA_COLORES[3]]
                coloresagrupado = []
                leyenda = []

                imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda, leyenda, barrasagrupadas, coloresindividual, coloresagrupado)

                filename = "ge_" + area + "_" + nusuario + "_" + random.randint(1, 10000).__str__()
                imagen.save(formats=['png'], outDir=path_to_save, fnRoot=filename)
                data['imagen1'] = path_to_save + filename + ".png"


                titulografica = "ATENCIONES POR TIPO DE GÉNERO"
                porcfem = round((totalfemenino * 100) / totalgeneral,2)
                porcmasc = round((totalmasculino * 100) / totalgeneral,2)
                valores = [[porcfem, porcmasc]]
                categorias = ['FEMENINO', 'MASCULINO']
                mostrarsimboloporcentaje = True
                tieneleyenda = False
                barrasagrupadas = False
                coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[5]]
                coloresagrupado = []
                leyenda = []

                imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda, leyenda,
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

        elif action == 'resumengeneralareamedicatipocita':
            try:
                data = {}

                desde = datetime.combine(convertir_fecha(request.POST['desde']), time.min)
                hasta = datetime.combine(convertir_fecha(request.POST['hasta']), time.max)
                tipopaciente = int(request.POST['tipopaciente'])
                facultad = int(request.POST['facultad'])
                carrera = int(request.POST['carrera'])


                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área Médica por Tipo de Cita'
                atenciones = PersonaConsultaMedica.objects.filter(fecha__range=(desde, hasta), status=True)

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
                area = "med"
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
                    valores = [[datos[0][1], datos[1][1], datos[2][1], datos[3][1], datos[4][1], datos[5][1], datos[6][1]]]
                    categorias = [datos[0][0], datos[1][0], datos[2][0], datos[3][0], datos[4][0], datos[5][0], datos[6][0]]
                    mostrarsimboloporcentaje = False
                    tieneleyenda = False
                    barrasagrupadas = False
                    coloresindividual = [PALETA_COLORES[2], PALETA_COLORES[2], PALETA_COLORES[2], PALETA_COLORES[2],
                                         PALETA_COLORES[2], PALETA_COLORES[2], PALETA_COLORES[2]]
                    coloresagrupado = []
                    leyenda = []

                    imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
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

                    imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
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

                    imagen = grafica_barra(titulografica, 300, valores, categorias, mostrarsimboloporcentaje, tieneleyenda,
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
                            carreras.append(
                                [idfacultad, nfacultad, idcarrera, ncarrera, total1vezcarr, totalsubseccarr, acarrera if len(acarrera) > 0 else '-'])

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

                data['tituloreporte'] = 'Reporte Resumen de atenciones del Área Médica por Facultad y Carrera'
                atenciones = PersonaConsultaMedica.objects.filter(tipopaciente=3, matricula__isnull=False,
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
                area = "med"
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
                    facultades[len(facultades)-1][5] = rutaimg


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

                data['tituloreporte'] = 'Reporte Resumen por Acciones realizadas del Área Médica'
                atenciones = PersonaConsultaMedica.objects.filter(fecha__range=(desde, hasta), status=True)

                # if not esdirectordbu:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                tiposacciones = AccionConsulta.objects.filter(area=1, status=True).order_by('descripcion')
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
                area = "med"
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
                data['esdirectordbu'] = esdirectordbu if esdirectordbu else 0
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

        elif action == 'patologicop':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = PatologicoPersonalForm(request.POST)
                if f.is_valid():
                    if PatologicoPersonal.objects.values('id').filter(personafichamedica=personafichamedica).exists():
                        patologicopersonal = PatologicoPersonal.objects.get(personafichamedica=personafichamedica)
                        patologicopersonal.nacio = f.cleaned_data['nacio']
                        patologicopersonal.partonormal = f.cleaned_data['partonormal']
                        patologicopersonal.partocesarea = f.cleaned_data['partocesarea']
                        patologicopersonal.partocomplicacion = f.cleaned_data['partocomplicacion']
                        patologicopersonal.lactanciamaterna = f.cleaned_data['lactanciamaterna']
                        patologicopersonal.lactanciaartificial = f.cleaned_data['lactanciaartificial']
                        patologicopersonal.ablactacion = f.cleaned_data['ablactacion']
                        patologicopersonal.vacuna = f.cleaned_data['vacuna']
                        patologicopersonal.letes = f.cleaned_data['letes']
                        patologicopersonal.transfusion = f.cleaned_data['transfusion']
                        patologicopersonal.gruposangre = f.cleaned_data['gruposangre']
                        patologicopersonal.factorrh = f.cleaned_data['factorrh']
                        patologicopersonal.alergiamedicina = f.cleaned_data['alergiamedicina']
                        patologicopersonal.alergiaambiente = f.cleaned_data['alergiaambiente']
                        patologicopersonal.alergiaalimento = f.cleaned_data['alergiaalimento']
                        patologicopersonal.tomamedicina = f.cleaned_data['tomamedicina']
                        patologicopersonal.enfermedad = f.cleaned_data['enfermedad']
                        patologicopersonal.enfermedadvenerea = f.cleaned_data['enfermedadvenerea']
                    else:
                        patologicopersonal = PatologicoPersonal(personafichamedica=personafichamedica,
                                                                nacio=f.cleaned_data['nacio'],
                                                                partonormal=f.cleaned_data['partonormal'],
                                                                partocesarea=f.cleaned_data['partocesarea'],
                                                                partocomplicacion=f.cleaned_data['partocomplicacion'],
                                                                lactanciamaterna=f.cleaned_data['lactanciamaterna'],
                                                                lactanciaartificial=f.cleaned_data[
                                                                    'lactanciaartificial'],
                                                                ablactacion=f.cleaned_data['ablactacion'],
                                                                vacuna=f.cleaned_data['vacuna'],
                                                                letes=f.cleaned_data['letes'],
                                                                transfusion=f.cleaned_data['transfusion'],
                                                                gruposangre=f.cleaned_data['gruposangre'],
                                                                factorrh=f.cleaned_data['factorrh'],
                                                                alergiamedicina=f.cleaned_data['alergiamedicina'],
                                                                alergiaambiente=f.cleaned_data['alergiaambiente'],
                                                                alergiaalimento=f.cleaned_data['alergiaalimento'],
                                                                tomamedicina=f.cleaned_data['tomamedicina'],
                                                                enfermedad=f.cleaned_data['enfermedad'],
                                                                enfermedadvenerea=f.cleaned_data['enfermedadvenerea'])
                        patologicopersonal.save(request)

                    patologicopersonal.vacunas.set(f.cleaned_data['vacunas'])
                    patologicopersonal.medicinas.set(f.cleaned_data['medicinas'])
                    patologicopersonal.enfermedadinfancia.set(f.cleaned_data['enfermedadinfancia'])
                    patologicopersonal.enfermedadvisual.set(f.cleaned_data['enfermedadvisual'])
                    patologicopersonal.alergiamedicinas.set(f.cleaned_data['alergiamedicinas'])
                    patologicopersonal.alergiaambientes.set(f.cleaned_data['alergiaambientes'])
                    patologicopersonal.alergiaalimentos.set(f.cleaned_data['alergiaalimentos'])
                    patologicopersonal.enfermedades.set(f.cleaned_data['enfermedades'])
                    patologicopersonal.enfermedadtrabajo.set(f.cleaned_data['enfermedadtrabajo'])
                    patologicopersonal.enfermedadvenereas.set(f.cleaned_data['enfermedadvenereas'])
                    patologicopersonal.save(request)
                    log(
                        u'Adiciono antecedentes patologico personal: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'patologicoq':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = PatologicoQuirurgicosForm(request.POST)
                if f.is_valid():
                    if PatologicoQuirurgicos.objects.values('id').filter(
                            personafichamedica=personafichamedica).exists():
                        patologicoquirurgico = PatologicoQuirurgicos.objects.get(personafichamedica=personafichamedica)
                        patologicoquirurgico.cirugia = f.cleaned_data['cirugia']
                        patologicoquirurgico.fechacirugia = f.cleaned_data['fechacirugia']
                        patologicoquirurgico.complicacion = f.cleaned_data['complicacion']
                        patologicoquirurgico.establecimiento = f.cleaned_data['establecimiento']
                    else:
                        patologicoquirurgico = PatologicoQuirurgicos(personafichamedica=personafichamedica,
                                                                     cirugia=f.cleaned_data['cirugia'],
                                                                     fechacirugia=f.cleaned_data['fechacirugia'],
                                                                     complicacion=f.cleaned_data['complicacion'],
                                                                     establecimiento=f.cleaned_data['establecimiento'])
                        patologicoquirurgico.save(request)
                    patologicoquirurgico.cirugias.set(f.cleaned_data['cirugias'])
                    patologicoquirurgico.save(request)
                    log(
                        u'Adiciono antecedentes patologico quirurgico: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'traumatologico':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = AntecedenteTraumatologicosForm(request.POST)
                if f.is_valid():
                    if AntecedenteTraumatologicos.objects.values('id').filter(
                            personafichamedica=personafichamedica).exists():
                        traumatologico = AntecedenteTraumatologicos.objects.get(personafichamedica=personafichamedica)
                        traumatologico.fractura = f.cleaned_data['fractura']
                        traumatologico.accidentelaboral = f.cleaned_data['accidentelaboral']
                    else:
                        traumatologico = AntecedenteTraumatologicos(personafichamedica=personafichamedica,
                                                                    fractura=f.cleaned_data['fractura'],
                                                                    accidentelaboral=f.cleaned_data['accidentelaboral'])
                        traumatologico.save(request)
                    traumatologico.lugaranatomico.set(f.cleaned_data['lugaranatomico'])
                    traumatologico.save(request)
                    log(
                        u'Adiciono antecedentes traumatologico: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'ginecologico':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = AntecedenteGinecoobstetricoForm(request.POST)
                if f.is_valid():
                    if AntecedenteGinecoobstetrico.objects.values('id').filter(
                            personafichamedica=personafichamedica).exists():
                        ginecologico = AntecedenteGinecoobstetrico.objects.get(personafichamedica=personafichamedica)
                        ginecologico.flujomenstrual = f.cleaned_data['flujomenstrual']
                        ginecologico.menarquia = f.cleaned_data['menarquia']
                        ginecologico.catamenial = f.cleaned_data['catamenial']
                        ginecologico.embrazos = f.cleaned_data['embrazos']
                        ginecologico.partos = f.cleaned_data['partos']
                        ginecologico.partonormal = f.cleaned_data['partonormal']
                        ginecologico.partoprematuro = f.cleaned_data['partoprematuro']
                        ginecologico.cesareas = f.cleaned_data['cesareas']
                        ginecologico.hijosvivos = f.cleaned_data['hijosvivos']
                        ginecologico.abortos = f.cleaned_data['abortos']
                        ginecologico.abortonatural = f.cleaned_data['abortonatural']
                        ginecologico.abortoprovocado = f.cleaned_data['abortoprovocado']
                        ginecologico.puerperiocomplicacion = f.cleaned_data['puerperiocomplicacion']
                        ginecologico.anticonceptivo = f.cleaned_data['anticonceptivo']
                        ginecologico.legrado = f.cleaned_data['legrado']
                    else:
                        ginecologico = AntecedenteGinecoobstetrico(personafichamedica=personafichamedica,
                                                                   flujomenstrual=f.cleaned_data['flujomenstrual'],
                                                                   menarquia=f.cleaned_data['menarquia'],
                                                                   catamenial=f.cleaned_data['catamenial'],
                                                                   embrazos=f.cleaned_data['embrazos'],
                                                                   partos=f.cleaned_data['partos'],
                                                                   partonormal=f.cleaned_data['partonormal'],
                                                                   partoprematuro=f.cleaned_data['partoprematuro'],
                                                                   cesareas=f.cleaned_data['cesareas'],
                                                                   hijosvivos=f.cleaned_data['hijosvivos'],
                                                                   abortos=f.cleaned_data['abortos'],
                                                                   abortonatural=f.cleaned_data['abortonatural'],
                                                                   abortoprovocado=f.cleaned_data['abortoprovocado'],
                                                                   puerperiocomplicacion=f.cleaned_data[
                                                                       'puerperiocomplicacion'],
                                                                   anticonceptivo=f.cleaned_data['anticonceptivo'],
                                                                   legrado=f.cleaned_data['legrado'])
                        ginecologico.save(request)
                    ginecologico.metodoanticonceptivo.set(f.cleaned_data['metodoanticonceptivo'])
                    ginecologico.save(request)
                    log(
                        u'Adiciono antecedentes Ginecoobstetrico: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'habitos':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = HabitoForm(request.POST)
                if f.is_valid():
                    if Habito.objects.values('id').filter(personafichamedica=personafichamedica).exists():
                        habito = Habito.objects.get(personafichamedica=personafichamedica)
                        habito.cafecantidad = f.cleaned_data['cafecantidad']
                        habito.cafecalidad = f.cleaned_data['cafecalidad']
                        habito.cafefrecuencia = f.cleaned_data['cafefrecuencia']
                        habito.teismocantidad = f.cleaned_data['teismocantidad']
                        habito.tecalidad = f.cleaned_data['tecalidad']
                        habito.tefrecuencia = f.cleaned_data['tefrecuencia']
                        habito.consumetabaco = f.cleaned_data['consumetabaco']
                        habito.tabaquismo = f.cleaned_data['tabaquismo']
                        habito.consumealcohol = f.cleaned_data['consumealcohol']
                        habito.alcoholismo = f.cleaned_data['alcoholismo']
                        habito.consumedroga = f.cleaned_data['consumedroga']
                        habito.alimentocantidad = f.cleaned_data['alimentocantidad']
                        habito.alimentocalidad = f.cleaned_data['alimentocalidad']
                        habito.remuneracion = f.cleaned_data['remuneracion']
                        habito.cargafamiliar = f.cleaned_data['cargafamiliar']
                        habito.manutencion = f.cleaned_data['manutencion']
                        habito.vivienda = f.cleaned_data['vivienda']
                        habito.zona = f.cleaned_data['zona']
                        habito.tipoconstruccion = f.cleaned_data['tipoconstruccion']
                        habito.ventilacion = f.cleaned_data['ventilacion']
                        habito.numeropersonas = f.cleaned_data['numeropersonas']
                        habito.animalesdomesticos = f.cleaned_data['animalesdomesticos']
                        habito.animalclase = f.cleaned_data['animalclase']
                        habito.animalcantidad = f.cleaned_data['animalcantidad']
                        habito.servicioshigienicos = f.cleaned_data['servicioshigienicos']
                        habito.aguapotable = f.cleaned_data['aguapotable']
                        habito.luz = f.cleaned_data['luz']
                        habito.transporte = f.cleaned_data['transporte']
                    else:
                        habito = Habito(personafichamedica=personafichamedica,
                                        cafecantidad=f.cleaned_data['cafecantidad'],
                                        cafecalidad=f.cleaned_data['cafecalidad'],
                                        cafefrecuencia=f.cleaned_data['cafefrecuencia'],
                                        teismocantidad=f.cleaned_data['teismocantidad'],
                                        tecalidad=f.cleaned_data['tecalidad'],
                                        tefrecuencia=f.cleaned_data['tefrecuencia'],
                                        consumetabaco=f.cleaned_data['consumetabaco'],
                                        tabaquismo=f.cleaned_data['tabaquismo'],
                                        consumealcohol=f.cleaned_data['consumealcohol'],
                                        alcoholismo=f.cleaned_data['alcoholismo'],
                                        consumedroga=f.cleaned_data['consumedroga'],
                                        alimentocantidad=f.cleaned_data['alimentocantidad'],
                                        alimentocalidad=f.cleaned_data['alimentocalidad'],
                                        remuneracion=f.cleaned_data['remuneracion'],
                                        cargafamiliar=f.cleaned_data['cargafamiliar'],
                                        manutencion=f.cleaned_data['manutencion'],
                                        vivienda=f.cleaned_data['vivienda'],
                                        zona=f.cleaned_data['zona'],
                                        tipoconstruccion=f.cleaned_data['tipoconstruccion'],
                                        ventilacion=f.cleaned_data['ventilacion'],
                                        numeropersonas=f.cleaned_data['numeropersonas'],
                                        animalesdomesticos=f.cleaned_data['animalesdomesticos'],
                                        animalclase=f.cleaned_data['animalclase'],
                                        animalcantidad=f.cleaned_data['animalcantidad'],
                                        servicioshigienicos=f.cleaned_data['servicioshigienicos'],
                                        aguapotable=f.cleaned_data['aguapotable'],
                                        luz=f.cleaned_data['luz'],
                                        transporte=f.cleaned_data['transporte'])
                        habito.save(request)
                    habito.droga.set(f.cleaned_data['droga'])
                    habito.save(request)
                    log(u'Adiciono habitos: %s' % pexamenfisico.personafichamedica.personaextension.persona, request,
                        "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'habitos':
        #     try:
        #         pexamenfisico = PersonaExamenFisico.objects.get(pk=request.POST['id'])
        #         f = PersonaHabitoForm(request.POST)
        #         if f.is_valid():
        #             pexamenfisico.personafichamedica.cigarro = f.cleaned_data['cigarro']
        #             pexamenfisico.personafichamedica.numerocigarros = f.cleaned_data['numerocigarros']
        #             pexamenfisico.personafichamedica.tomaalcohol = f.cleaned_data['tomaalcohol']
        #             pexamenfisico.personafichamedica.tipoalcohol = f.cleaned_data['tipoalcohol']
        #             pexamenfisico.personafichamedica.copasalcohol = f.cleaned_data['copasalcohol']
        #             pexamenfisico.personafichamedica.tomaantidepresivos = f.cleaned_data['tomaantidepresivos']
        #             pexamenfisico.personafichamedica.antidepresivos = f.cleaned_data['antidepresivos']
        #             pexamenfisico.personafichamedica.tomaotros = f.cleaned_data['tomaotros']
        #             pexamenfisico.personafichamedica.otros = f.cleaned_data['otros']
        #             pexamenfisico.personafichamedica.horassueno = f.cleaned_data['horassueno']
        #             pexamenfisico.personafichamedica.calidadsuenno = f.cleaned_data['calidadsuenno']
        #             pexamenfisico.personafichamedica.save()
        #             log(u'Adiciono habitos personales: %s' % pexamenfisico.personafichamedica.personaextension.persona, request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        # elif action == 'ginecologico':
        #     try:
        #         pexamenfisico = PersonaExamenFisico.objects.get(pk=request.POST['id'])
        #         f = PersonaGinecologicoForm(request.POST)
        #         if f.is_valid():
        #             pexamenfisico.personafichamedica.gestacion = f.cleaned_data['gestacion']
        #             pexamenfisico.personafichamedica.partos = f.cleaned_data['partos']
        #             pexamenfisico.personafichamedica.abortos = f.cleaned_data['abortos']
        #             pexamenfisico.personafichamedica.cesareas = f.cleaned_data['cesareas']
        #             pexamenfisico.personafichamedica.hijos2 = f.cleaned_data['hijos2']
        #             pexamenfisico.personafichamedica.save()
        #             log(u'Adiciono datos medicos ginecologicos: %s' % pexamenfisico.personafichamedica.personaextension.persona, request, "add")
        #             return JsonResponse({"result": "ok"})
        #         else:
        #              raise NameError('Error')
        #     except Exception as ex:
        #         transaction.set_rollback(True)
        #         return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'patologicof_add':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = PatologicoFamiliarForm(request.POST)
                if f.is_valid():
                    patologicofamiliarx = PatologicoFamiliar(personafichamedica=personafichamedica,
                                                             parentesco=f.cleaned_data['parentesco'],
                                                             paterno=f.cleaned_data['paterno'])
                    patologicofamiliarx.save(request)
                    patologicofamiliarx.enfermedades.set(f.cleaned_data['enfermedades'])
                    patologicofamiliarx.save(request)
                    log(
                        u'Adiciono datos medicos patologicos familiares: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'patologicof_edit':
            try:
                patologicof = PatologicoFamiliar.objects.get(pk=int(request.POST['id']))
                f = PatologicoFamiliarForm(request.POST)
                if f.is_valid():
                    patologicof.parentesco = f.cleaned_data['parentesco']
                    patologicof.paterno = f.cleaned_data['paterno']
                    patologicof.enfermedades = f.cleaned_data['enfermedades']
                    patologicof.save(request)
                    log(
                        u'Modifico datos medicos patologicos familiares: %s' % patologicof.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'patologicof_delete':
            try:
                patologicof = PatologicoFamiliar.objects.get(pk=request.POST['id'])
                log(u'Elimino Patologico Familiar: %s' % patologicof, request, "del")
                patologicof.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": "Error al eliminar los datos."})

        elif action == 'editarinspeccionsomatica':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                f = InspeccionSomaticaForm(request.POST)
                if f.is_valid():
                    if InspeccionSomatica.objects.values('id').filter(personaexamenfisico=pexamenfisico).exists():
                        somatica = InspeccionSomatica.objects.get(personaexamenfisico=pexamenfisico)
                        somatica.postura = f.cleaned_data['postura']
                        somatica.gradoactividad = f.cleaned_data['gradoactividad']
                        somatica.estadomental = f.cleaned_data['estadomental']
                        somatica.orientaciontiempo = f.cleaned_data['orientaciontiempo']
                        somatica.colaborainterrogantorio = f.cleaned_data['colaborainterrogantorio']
                        somatica.estadocaracter = f.cleaned_data['estadocaracter']
                        somatica.facies = f.cleaned_data['facies']
                        somatica.biotipo = f.cleaned_data['biotipo']
                        somatica.tallaclase = f.cleaned_data['tallaclase']
                        somatica.imc = Decimal(request.POST['indicemasacorporal']).quantize(Decimal('.01'))
                        somatica.nutricional = f.cleaned_data['nutricional']
                        somatica.color = f.cleaned_data['color']
                        somatica.humedad = f.cleaned_data['humedad']
                        somatica.pilificacion = f.cleaned_data['pilificacion']
                        somatica.pelo = f.cleaned_data['pelo']
                        somatica.unas = f.cleaned_data['unas']
                        somatica.marcha = f.cleaned_data['marcha']
                        somatica.movimiento = f.cleaned_data['movimiento']
                    else:
                        somatica = InspeccionSomatica(personaexamenfisico=pexamenfisico,
                                                      postura=f.cleaned_data['postura'],
                                                      gradoactividad=f.cleaned_data['gradoactividad'],
                                                      estadomental=f.cleaned_data['estadomental'],
                                                      orientaciontiempo=f.cleaned_data['orientaciontiempo'],
                                                      colaborainterrogantorio=f.cleaned_data['colaborainterrogantorio'],
                                                      estadocaracter=f.cleaned_data['estadocaracter'],
                                                      facies=f.cleaned_data['facies'],
                                                      biotipo=f.cleaned_data['biotipo'],
                                                      tallaclase=f.cleaned_data['tallaclase'],
                                                      imc=Decimal(request.POST['indicemasacorporal']).quantize(
                                                          Decimal('.01')),
                                                      nutricional=f.cleaned_data['nutricional'],
                                                      color=f.cleaned_data['color'],
                                                      humedad=f.cleaned_data['humedad'],
                                                      pilificacion=f.cleaned_data['pilificacion'],
                                                      pelo=f.cleaned_data['pelo'],
                                                      unas=f.cleaned_data['unas'],
                                                      marcha=f.cleaned_data['marcha'],
                                                      movimiento=f.cleaned_data['movimiento'])
                        somatica.save(request)
                    pexamenfisico.talla = f.cleaned_data['talla']
                    pexamenfisico.peso = f.cleaned_data['peso']
                    pexamenfisico.save(request)
                    somatica.lesioneprimaria.set(f.cleaned_data['lesioneprimaria'])
                    somatica.lesionesecundaria.set(f.cleaned_data['lesionesecundaria'])
                    somatica.save(request)
                    log(
                        u'Adiciono Inspeccion Somatica: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'editarinspecciontopografica':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                f = InspeccionTopograficaForm(request.POST)
                if f.is_valid():
                    if InspeccionTopografica.objects.values('id').filter(personaexamenfisico=pexamenfisico).exists():
                        topografica = InspeccionTopografica.objects.get(personaexamenfisico=pexamenfisico)
                        topografica.craneo = f.cleaned_data['craneo']
                        topografica.craneotamanio = f.cleaned_data['craneotamanio']
                        topografica.cabelloforma = f.cleaned_data['cabelloforma']
                        topografica.cabellocolor = f.cleaned_data['cabellocolor']
                        topografica.cabelloaspecto = f.cleaned_data['cabelloaspecto']
                        topografica.cabellodistribucion = f.cleaned_data['cabellodistribucion']
                        topografica.cabellocantidad = f.cleaned_data['cabellocantidad']
                        topografica.cabelloconsistencia = f.cleaned_data['cabelloconsistencia']
                        topografica.cabelloimplantacion = f.cleaned_data['cabelloimplantacion']
                        topografica.caraterciosuperior = f.cleaned_data['caraterciosuperior']
                        topografica.caraterciomedio = f.cleaned_data['caraterciomedio']
                        topografica.caratercioinferior = f.cleaned_data['caratercioinferior']
                        topografica.cuellocaraanterior = f.cleaned_data['cuellocaraanterior']
                        topografica.cuellocaralateralderecha = f.cleaned_data['cuellocaralateralderecha']
                        topografica.cuellocaralateralizquierda = f.cleaned_data['cuellocaralateralizquierda']
                        topografica.cuellocaraposterior = f.cleaned_data['cuellocaraposterior']
                        topografica.toraxcaraanterior = f.cleaned_data['toraxcaraanterior']
                        topografica.toraxcaralateralderecha = f.cleaned_data['toraxcaralateralderecha']
                        topografica.toraxcaralateralizquierda = f.cleaned_data['toraxcaralateralizquierda']
                        topografica.toraxcaraposterior = f.cleaned_data['toraxcaraposterior']
                        topografica.abdomenanterior = f.cleaned_data['abdomenanterior']
                        topografica.abdomenanteriorformas = f.cleaned_data['abdomenanteriorformas']
                        topografica.abdomenanteriorvolumen = f.cleaned_data['abdomenanteriorvolumen']
                        topografica.abdomenanteriorcicatrizumbilical = f.cleaned_data[
                            'abdomenanteriorcicatrizumbilical']
                        topografica.abdomenanteriorcirculacionlateral = f.cleaned_data[
                            'abdomenanteriorcirculacionlateral']
                        topografica.abdomenanteriorcicatrices = f.cleaned_data['abdomenanteriorcicatrices']
                        topografica.abdomenanteriornebus = f.cleaned_data['abdomenanteriornebus']
                        topografica.abdomenlateralizquierdo = f.cleaned_data['abdomenlateralizquierdo']
                        topografica.abdomenlateralderecho = f.cleaned_data['abdomenlateralderecho']
                        topografica.abdomenposterior = f.cleaned_data['abdomenposterior']
                        topografica.inguinogenitalvello = f.cleaned_data['inguinogenitalvello']
                        topografica.inguinogenitalhernias = f.cleaned_data['inguinogenitalhernias']
                        topografica.inguinogenitalpene = f.cleaned_data['inguinogenitalpene']
                        topografica.superioreshombro = f.cleaned_data['superioreshombro']
                        topografica.superioresbrazo = f.cleaned_data['superioresbrazo']
                        topografica.superioresantebrazo = f.cleaned_data['superioresantebrazo']
                        topografica.superioresmano = f.cleaned_data['superioresmano']
                        topografica.inferiormuslo = f.cleaned_data['inferiormuslo']
                        topografica.inferiorpierna = f.cleaned_data['inferiorpierna']
                        topografica.inferiorpie = f.cleaned_data['inferiorpie']
                        topografica.save(request)
                    else:
                        topografica = InspeccionTopografica(personaexamenfisico=pexamenfisico,
                                                            craneo=f.cleaned_data['craneo'],
                                                            craneotamanio=f.cleaned_data['craneotamanio'],
                                                            cabelloforma=f.cleaned_data['cabelloforma'],
                                                            cabellocolor=f.cleaned_data['cabellocolor'],
                                                            cabelloaspecto=f.cleaned_data['cabelloaspecto'],
                                                            cabellodistribucion=f.cleaned_data['cabellodistribucion'],
                                                            cabellocantidad=f.cleaned_data['cabellocantidad'],
                                                            cabelloconsistencia=f.cleaned_data['cabelloconsistencia'],
                                                            cabelloimplantacion=f.cleaned_data['cabelloimplantacion'],
                                                            caraterciosuperior=f.cleaned_data['caraterciosuperior'],
                                                            caraterciomedio=f.cleaned_data['caraterciomedio'],
                                                            caratercioinferior=f.cleaned_data['caratercioinferior'],
                                                            cuellocaraanterior=f.cleaned_data['cuellocaraanterior'],
                                                            cuellocaralateralderecha=f.cleaned_data[
                                                                'cuellocaralateralderecha'],
                                                            cuellocaralateralizquierda=f.cleaned_data[
                                                                'cuellocaralateralizquierda'],
                                                            cuellocaraposterior=f.cleaned_data['cuellocaraposterior'],
                                                            toraxcaraanterior=f.cleaned_data['toraxcaraanterior'],
                                                            toraxcaralateralderecha=f.cleaned_data[
                                                                'toraxcaralateralderecha'],
                                                            toraxcaralateralizquierda=f.cleaned_data[
                                                                'toraxcaralateralizquierda'],
                                                            toraxcaraposterior=f.cleaned_data['toraxcaraposterior'],
                                                            abdomenanterior=f.cleaned_data['abdomenanterior'],
                                                            abdomenanteriorformas=f.cleaned_data[
                                                                'abdomenanteriorformas'],
                                                            abdomenanteriorvolumen=f.cleaned_data[
                                                                'abdomenanteriorvolumen'],
                                                            abdomenanteriorcicatrizumbilical=f.cleaned_data[
                                                                'abdomenanteriorcicatrizumbilical'],
                                                            abdomenanteriorcirculacionlateral=f.cleaned_data[
                                                                'abdomenanteriorcirculacionlateral'],
                                                            abdomenanteriorcicatrices=f.cleaned_data[
                                                                'abdomenanteriorcicatrices'],
                                                            abdomenanteriornebus=f.cleaned_data['abdomenanteriornebus'],
                                                            abdomenlateralizquierdo=f.cleaned_data[
                                                                'abdomenlateralizquierdo'],
                                                            abdomenlateralderecho=f.cleaned_data[
                                                                'abdomenlateralderecho'],
                                                            abdomenposterior=f.cleaned_data['abdomenposterior'],
                                                            inguinogenitalvello=f.cleaned_data['inguinogenitalvello'],
                                                            inguinogenitalhernias=f.cleaned_data[
                                                                'inguinogenitalhernias'],
                                                            inguinogenitalpene=f.cleaned_data['inguinogenitalpene'],
                                                            superioreshombro=f.cleaned_data['superioreshombro'],
                                                            superioresbrazo=f.cleaned_data['superioresbrazo'],
                                                            superioresantebrazo=f.cleaned_data['superioresantebrazo'],
                                                            superioresmano=f.cleaned_data['superioresmano'],
                                                            inferiormuslo=f.cleaned_data['inferiormuslo'],
                                                            inferiorpierna=f.cleaned_data['inferiorpierna'],
                                                            inferiorpie=f.cleaned_data['inferiorpie'])
                        topografica.save(request)
                    log(
                        u'Adiciono Inspeccion Topografica: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarrutagrama':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                persona = pexamenfisico.personafichamedica.personaextension.persona
                f = RutagramaForm(request.POST)
                if f.is_valid():
                    if Rutagrama.objects.values('id').filter(
                            personafichamedica=pexamenfisico.personafichamedica).exists():
                        rutagrama = Rutagrama.objects.get(personafichamedica=pexamenfisico.personafichamedica)
                        rutagrama.tipovehiculo = f.cleaned_data['tipovehiculo']
                        rutagrama.destinotrabajo = f.cleaned_data['destinotrabajo']
                        rutagrama.tiempo = f.cleaned_data['tiempo']
                        rutagrama.horasalida = f.cleaned_data['horasalida']
                        rutagrama.tiempoviaja = f.cleaned_data['tiempoviaja']
                        rutagrama.escala = f.cleaned_data['escala']
                        rutagrama.tipoescala = f.cleaned_data['tipoescala']
                        rutagrama.escala1 = f.cleaned_data['escala1']
                        rutagrama.escala2 = f.cleaned_data['escala2']
                        rutagrama.rutaalterna1 = f.cleaned_data['rutaalterna1']
                        rutagrama.rutaalterna2 = f.cleaned_data['rutaalterna2']
                        rutagrama.actividadsalir = f.cleaned_data['actividadsalir']
                        rutagrama.ubicacion = f.cleaned_data['ubicacion']
                        rutagrama.tiempoaproximado = f.cleaned_data['tiempoaproximado']
                        rutagrama.frecuencia = f.cleaned_data['frecuencia']
                        rutagrama.actividad1 = f.cleaned_data['actividad1']
                        rutagrama.actividad2 = f.cleaned_data['actividad2']
                        rutagrama.actividadcalle = f.cleaned_data['actividadcalle']
                    else:
                        rutagrama = Rutagrama(personafichamedica=pexamenfisico.personafichamedica,
                                              tipovehiculo=f.cleaned_data['tipovehiculo'],
                                              destinotrabajo=f.cleaned_data['destinotrabajo'],
                                              tiempo=f.cleaned_data['tiempo'],
                                              horasalida=f.cleaned_data['horasalida'],
                                              tiempoviaja=f.cleaned_data['tiempoviaja'],
                                              escala=f.cleaned_data['escala'],
                                              tipoescala=f.cleaned_data['tipoescala'],
                                              escala1=f.cleaned_data['escala1'],
                                              escala2=f.cleaned_data['escala2'],
                                              rutaalterna1=f.cleaned_data['rutaalterna1'],
                                              rutaalterna2=f.cleaned_data['rutaalterna2'],
                                              actividadsalir=f.cleaned_data['actividadsalir'],
                                              ubicacion=f.cleaned_data['ubicacion'],
                                              tiempoaproximado=f.cleaned_data['tiempoaproximado'],
                                              frecuencia=f.cleaned_data['frecuencia'],
                                              actividad1=f.cleaned_data['actividad1'],
                                              actividad2=f.cleaned_data['actividad2'],
                                              actividadcalle=f.cleaned_data['actividadcalle'])
                        rutagrama.save(request)
                    rutagrama.tipoactividad.set(f.cleaned_data['tipoactividad'])
                    rutagrama.save(request)
                    persona.direccion = f.cleaned_data['direccion']
                    persona.direccion2 = f.cleaned_data['direccion2']
                    persona.save(request)
                    log(
                        u'Adiciono Rutagrama: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "add")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editarvaloracion':
            try:
                paciente = Persona.objects.get(pk=request.POST['id'])
                pexamenfisico = paciente.datos_examen_fisico()
                f = PersonaExamenFisicoForm(request.POST)
                if f.is_valid():
                    pexamenfisico.peso = f.cleaned_data['peso']
                    pexamenfisico.talla = f.cleaned_data['talla']
                    pexamenfisico.pa = f.cleaned_data['pa']
                    pexamenfisico.pulso = f.cleaned_data['pulso']
                    pexamenfisico.rcar = f.cleaned_data['rcar']
                    pexamenfisico.rresp = f.cleaned_data['rresp']
                    pexamenfisico.temp = f.cleaned_data['temp']
                    pexamenfisico.observaciones = f.cleaned_data['observaciones']
                    pexamenfisico.save(request)
                    log(u'Modifico examen fisico: %s' % pexamenfisico.personafichamedica.personaextension.persona,
                        request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        elif action == 'consultamedica':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                idmatricula = request.POST['idmatricula']

                f = PersonaConsultaMedicaForm(request.POST)
                if f.is_valid():
                    enfermedades = json.loads(request.POST['lista_items1'])
                    # if not enfermedades:
                    #     return JsonResponse({"result": "bad",
                    #                          "mensaje": u"El campo Código CIE-10 debe tener al menos 1 elemento seleccionado."})

                    fecha = f.cleaned_data['fechaatencion']
                    hora = datetime.now().time()

                    atenciones = persona.personaconsultamedica_set.filter(status=True, fecha__year=fecha.year).count()

                    consulta = PersonaConsultaMedica(persona=persona,
                                                     # fecha=datetime.now(),
                                                     fecha=datetime(fecha.year, fecha.month, fecha.day, hora.hour,
                                                                    hora.minute, hora.second),
                                                     tipoatencion=f.cleaned_data['tipoatencion'],
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
                        if ProximaCita.objects.values('id').filter(persona=consulta.persona, fecha__gte=datetime.now(),
                                                                   medico=consulta.medico).exists():
                            transaction.set_rollback(True)
                            return JsonResponse(
                                {"result": "bad", "mensaje": u"Ya existe una cita programada para este paciente."})
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
                    log(u'Adiciono consulta medica: %s' % consulta, request, "add")
                    return JsonResponse({"result": "ok", "id": consulta.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addconsultamedica':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto al paciente
                paciente = Persona.objects.get(pk=int(encrypt(request.POST['id'])))

                # Obtengo los valores del formulario
                fechaatencion = datetime.strptime(request.POST['fechaatencion'], '%Y-%m-%d').date()
                horaatencion = datetime.now().time()
                fechahora = datetime.combine(fechaatencion, horaatencion)
                tipopaciente = request.POST['tipopaciente']
                tipoatencion = request.POST['tipoatencion']
                motivo = request.POST['motivo'].strip().upper()
                diagnostico = request.POST['diagnostico'].strip().upper()
                enfermedades = request.POST.getlist('enfermedad')
                tratamiento = request.POST['tratamiento'].strip().upper()
                acciones = request.POST.getlist('accion')
                matricula = None
                productos = json.loads(request.POST['lista_items1'])

                if 'idmatricula' in request.POST:
                    matricula = Matricula.objects.get(pk=int(encrypt(request.POST['idmatricula'])))

                if 'proximacita' in request.POST:
                    fechacita = datetime.strptime(request.POST['fechacita'], '%Y-%m-%d').date()
                    horacita = datetime.strptime(request.POST['horacita'], '%H:%M').time()
                    indicaciones = request.POST['indicaciones'].strip().upper()
                    fechahoracita = datetime.combine(fechacita, horacita)

                    # Validar fecha de cita vs fecha de atención
                    if fechacita < fechaatencion:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de pxóxima cita debe ser mayor a la fecha de atención", "showSwal": "True", "swalType": "warning"})

                    # Validar que no tenga próxima cita registrada
                    if ProximaCita.objects.values('id').filter(persona=paciente, fecha__gte=datetime.now(), medico=persona).exists():
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El paciente ya tiene registrada una próxima cita", "showSwal": "True", "swalType": "warning"})

                # Verifico si tuvo atenciones previas
                atenciones = paciente.personaconsultamedica_set.filter(status=True, fecha__year=fechaatencion.year).count()

                # Guardo la atención médica
                atencionmedica = PersonaConsultaMedica(
                    persona=paciente,
                    fecha=fechahora,
                    tipoatencion=tipoatencion,
                    motivo=motivo,
                    medicacion='',
                    diagnostico=diagnostico,
                    tratamiento=tratamiento,
                    medico=request.session['persona'],
                    tipopaciente=tipopaciente,
                    matricula=matricula,
                    primeravez=True if atenciones == 0 else False
                )
                atencionmedica.save(request)

                # Guardo las enfermedades
                for idenfermedad in enfermedades:
                    catalogoenfermedad = CatalogoEnfermedad.objects.get(pk=idenfermedad)
                    atencionmedica.enfermedad.add(catalogoenfermedad)

                # Guardo las acciones realizadas
                for idaccion in acciones:
                    accionconsulta = AccionConsulta.objects.get(pk=idaccion)
                    atencionmedica.accion.add(accionconsulta)

                # Guardo la próxima cita en caso de requerir
                if 'proximacita' in request.POST:
                    proximacita = ProximaCita(
                        consultamedica=atencionmedica,
                        persona=paciente,
                        fecha=fechahoracita,
                        medico=persona,
                        indicaciones=indicaciones,
                        tipoconsulta=1
                    )
                    proximacita.save(request)

                # En caso de que la atención actual corresponda a una cita registrada
                if 'idcita' in request.POST:
                    citaactual = ProximaCita.objects.get(pk=int(encrypt(request.POST['idcita'])))
                    citaactual.asistio = True
                    citaactual.save(request)

                # Guardo los productos entregados
                if productos:
                    guardar_insumos_entregados(atencionmedica, fechahora, persona, paciente, productos, request)

                log(u'%s adicionó consulta médica: %s' % (persona, atencionmedica), request, "add")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro guardado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'editconsultamedica':
            try:
                if not 'id' in request.POST:
                    return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al procesar la solicitud", "showSwal": "True", "swalType": "error"})

                # Consulto la atención médica
                atencionmedica = PersonaConsultaMedica.objects.get(pk=int(encrypt(request.POST['id'])))
                proximacita = atencionmedica.proxima_cita()
                paciente = atencionmedica.persona

                # Obtengo los valores del formulario
                fechaatencion = datetime.strptime(request.POST['fechaatencion'], '%Y-%m-%d').date()
                horaatencion = datetime.now().time()
                fechahora = datetime.combine(fechaatencion, horaatencion)
                tipopaciente = request.POST['tipopaciente']
                tipoatencion = request.POST['tipoatencion']
                motivo = request.POST['motivo'].strip().upper()
                diagnostico = request.POST['diagnostico'].strip().upper()
                enfermedades = request.POST.getlist('enfermedad')
                tratamiento = request.POST['tratamiento'].strip().upper()
                acciones = request.POST.getlist('accion')
                productos = json.loads(request.POST['lista_items1'])

                if 'proximacita' in request.POST:
                    fechacita = datetime.strptime(request.POST['fechacita'], '%Y-%m-%d').date()
                    horacita = datetime.strptime(request.POST['horacita'], '%H:%M').time()
                    indicaciones = request.POST['indicaciones'].strip().upper()
                    fechahoracita = datetime.combine(fechacita, horacita)

                    # Validar fecha de cita vs fecha de atención
                    if fechacita < fechaatencion:
                        return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"La fecha de pxóxima cita debe ser mayor a la fecha de atención", "showSwal": "True", "swalType": "warning"})

                    # Validar que no tenga próxima cita registrada
                    if not proximacita:
                        if ProximaCita.objects.values('id').filter(persona=paciente, fecha__gte=datetime.now(), medico=persona).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El paciente ya tiene registrada una próxima cita", "showSwal": "True", "swalType": "warning"})
                    else:
                        if ProximaCita.objects.values('id').filter(persona=paciente, fecha__gte=datetime.now(), medico=persona).exclude(pk=proximacita.id).exists():
                            return JsonResponse({"result": "bad", "titulo": "Atención!!!", "mensaje": u"El paciente ya tiene registrada una próxima cita", "showSwal": "True", "swalType": "warning"})

                # Actualizo la consulta médica
                atencionmedica.fecha = fechahora
                atencionmedica.tipoatencion = tipoatencion
                atencionmedica.motivo = motivo
                atencionmedica.diagnostico = diagnostico
                atencionmedica.tratamiento = tratamiento
                atencionmedica.save(request)

                atencionmedica.enfermedad.clear()
                # Guardo las enfermedades
                for idenfermedad in enfermedades:
                    catalogoenfermedad = CatalogoEnfermedad.objects.get(pk=idenfermedad)
                    atencionmedica.enfermedad.add(catalogoenfermedad)

                atencionmedica.accion.clear()
                # Guardo las acciones realizadas
                for idaccion in acciones:
                    accionconsulta = AccionConsulta.objects.get(pk=idaccion)
                    atencionmedica.accion.add(accionconsulta)

                # Guardo o actualizo la próxima cita en caso de requerir
                if 'proximacita' in request.POST:
                    if not proximacita:
                        proximacita = ProximaCita(
                            consultamedica=atencionmedica,
                            persona=paciente,
                            fecha=fechahoracita,
                            medico=persona,
                            indicaciones=indicaciones,
                            tipoconsulta=1
                        )
                        proximacita.save(request)
                    else:
                        proximacita.fecha = fechahoracita
                        proximacita.indicaciones = indicaciones
                        proximacita.save(request)
                else:
                    # Si existe registro de próxima cita lo elimino
                    if proximacita:
                        proximacita.status = False
                        proximacita.save(request)

                # Si existen detalles de productos entregados
                if productos:
                    # Si inicialmente no existieron detalles de medicación entregada
                    if not atencionmedica.insumos_utilizados():
                        # Guardo los productos entregados
                        guardar_insumos_entregados(atencionmedica, fechahora, persona, paciente, productos, request)
                    else:
                        # Consultar los movimientos de inventario de la consulta médica
                        movimientosinventario = atencionmedica.insumos_utilizados()

                        # Recorro los movimientos
                        for movimiento in movimientosinventario:
                            # Ontengo y actualizo stock del lote
                            inventariolote = movimiento.inventariomedicolote
                            inventariolote.stock = inventariolote.stock + movimiento.cantidad
                            inventariolote.save(request)

                            # Obtengo inventario general
                            inventariomedico = inventariolote.inventariomedico
                            inventariomedico.stock = inventariomedico.stock + movimiento.cantidad
                            inventariomedico.save(request)

                            # Elimino el movimiento
                            movimiento.detalle = movimiento.detalle + '. MOVIMIENTO ANULADO POR ACTUALIZACIONES'
                            movimiento.status = False
                            movimiento.save(request)

                        # Guardo los productos entregados
                        guardar_insumos_entregados(atencionmedica, fechahora, persona, paciente, productos, request)
                else:
                    # Consultar los movimientos de inventario de la consulta médica
                    movimientosinventario = atencionmedica.insumos_utilizados()

                    # Recorro los movimientos
                    for movimiento in movimientosinventario:
                        # Ontengo y actualizo stock del lote
                        inventariolote = movimiento.inventariomedicolote
                        inventariolote.stock = inventariolote.stock + movimiento.cantidad
                        inventariolote.save(request)

                        # Obtengo inventario general
                        inventariomedico = inventariolote.inventariomedico
                        inventariomedico.stock = inventariomedico.stock + movimiento.cantidad
                        inventariomedico.save(request)

                        # Elimino el movimiento
                        movimiento.detalle = movimiento.detalle + '. MOVIMIENTO ANULADO POR ACTUALIZACIONES'
                        movimiento.status = False
                        movimiento.save(request)

                log(u'%s editó consulta médica: %s' % (persona, atencionmedica), request, "edit")
                return JsonResponse({"result": "ok", "titulo": "Proceso exitoso!!!", "mensaje": u"Registro actualizado con éxito", "showSwal": True})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "titulo": "Error", "mensaje": u"Error al guardar los datos. [%s]" % msg, "showSwal": "True", "swalType": "error"})

        elif action == 'actualizarfechaficha':
            try:
                idficha = int(request.POST['idficha'])
                f = FechaFichaMedicaForm(request.POST)
                if f.is_valid():
                    ficha = PersonaFichaMedica.objects.get(pk=idficha)
                    ficha.fecha = f.cleaned_data['fechaficha']
                    ficha.save(request)
                    log(u'Modifico fecha de ficha médica: %s' % ficha, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'validardocumento':
            try:
                idficha = int(request.POST['idficha'])
                f = RevisarRexmedForm(request.POST)
                if f.is_valid():
                    ficha = PersonaFichaMedica.objects.get(pk=idficha)
                    ficha.estadorevisionexlab = f.cleaned_data['estado']
                    ficha.observacionexlab = f.cleaned_data['observacion']
                    ficha.save(request)
                    log(u'Revisión de resultados de exámenes de laboratorio: %s' % ficha, request, "edit")

                    # Envío de e-mail al estudiante
                    tituloemail = "Validación de Resultado de exámenes de laboratorio"

                    send_html_mail(tituloemail,
                                   "emails/notificacion_rexlab.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'fase': 'VAL',
                                    'estadorevision': 'VALIDÓ' if f.cleaned_data['estado'] == 2 else 'RECHAZÓ',
                                    'observaciones': f.cleaned_data['observacion'],
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'medico': persona,
                                    'estudiante': ficha.personaextension.persona,
                                    'autoridad2': '',
                                    't': miinstitucion()
                                    },
                                   ficha.personaextension.persona.lista_emails_envio(),
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editconsultamedicaprevia':
            try:
                consulta = PersonaConsultaMedica.objects.get(pk=request.POST['id'])
                f = PersonaConsultaMedicaForm(request.POST)
                if f.is_valid():
                    enfermedades = json.loads(request.POST['lista_items1'])
                    # if not enfermedades:
                    #     return JsonResponse({"result": "bad",
                    #                          "mensaje": u"El campo Código CIE-10 debe tener al menos 1 elemento seleccionado."})

                    consulta.fecha = f.cleaned_data['fechaatencion']
                    consulta.tipoatencion = f.cleaned_data['tipoatencion']
                    consulta.motivo = f.cleaned_data['motivo'].strip().upper()
                    consulta.medicacion = f.cleaned_data['medicacion'].strip().upper()
                    consulta.diagnostico = f.cleaned_data['diagnostico'].strip().upper()
                    consulta.tratamiento = f.cleaned_data['tratamiento'].strip().upper()
                    consulta.accion = f.cleaned_data['accion']
                    consulta.save(request)

                    consulta.enfermedad.clear()

                    for e in enfermedades:
                        idcatalogo = int(e['id'])
                        catalogo = CatalogoEnfermedad.objects.get(pk=idcatalogo)
                        consulta.enfermedad.add(catalogo)

                    log(u'Modifico consulta medica previa: %s' % consulta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # data = {}
        # adduserdata(request, data)
        data['title'] = u'Fichas médicas'
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'ficha':
                try:
                    data['title'] = u'Ficha medica'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['hijo'] = PersonaDatosFamiliares.objects.db_manager("sga_select").filter(parentesco_id__in=[11,14], persona= persona)
                    data['pex'] = pex = persona.datos_examen_fisico()
                    fechaficha = pex.personafichamedica.fecha
                    data['fechaficha'] = fechaficha
                    data['corregirfecha'] = False if fechaficha else True
                    data['patologicofamiliar'] = pex.personafichamedica.patologicofamiliar_set.all()
                    data['patologicopersonal'] = PatologicoPersonal.objects.get(
                        personafichamedica=pex.personafichamedica) if PatologicoPersonal.objects.values('id').filter(
                        personafichamedica=pex.personafichamedica).exists() else ''
                    data['patologicoquirurgico'] = PatologicoQuirurgicos.objects.get(
                        personafichamedica=pex.personafichamedica) if PatologicoQuirurgicos.objects.values('id').filter(
                        personafichamedica=pex.personafichamedica).exists() else ''
                    data['antecedentetraumatologico'] = AntecedenteTraumatologicos.objects.get(
                        personafichamedica=pex.personafichamedica) if AntecedenteTraumatologicos.objects.filter(
                        personafichamedica=pex.personafichamedica).exists() else ''
                    data['antecedenteginecoobstetrico'] = AntecedenteGinecoobstetrico.objects.get(
                        personafichamedica=pex.personafichamedica) if AntecedenteGinecoobstetrico.objects.filter(
                        personafichamedica=pex.personafichamedica).exists() else ''
                    data['habito'] = Habito.objects.get(
                        personafichamedica=pex.personafichamedica) if Habito.objects.filter(
                        personafichamedica=pex.personafichamedica).exists() else ''
                    data['form2'] = FechaFichaMedicaForm(initial={'fechaficha': fechaficha})
                    formrex = RevisarRexmedForm()
                    formrex.cargarestado()
                    data['form3'] = formrex
                    # data['reporte_0'] = obtener_reporte('med_fichamedica')
                    return render(request, "box_medical/ficha.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadodetalladoareamedica':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)
                    tipopaciente = int(request.GET['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                       estadopuesto_id=1, status=True).exists()

                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('ListadoGeneral')
                    response = HttpResponse(content_type="application/ms-excel")
                    response[
                        'Content-Disposition'] = 'attachment; filename=listado_atenciones_medicas_' + random.randint(1,
                                                                                                                     10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 12, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 12, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                    ws.write_merge(2, 2, 0, 12, 'LISTADO DETALLADO DE ATENCIONES DEL ÁREA MÉDICA', titulo2)
                    ws.write_merge(3, 3, 0, 12,
                                   'DESDE:   ' + str(convertir_fecha(request.GET['desde'])) + '     HASTA:   ' + str(
                                       convertir_fecha(request.GET['hasta'])), titulo2)
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
                        (u"MEDICACIÓN ENTREGADA", 20000),
                        (u"ACCIONES REALIZADAS", 20000),
                        (u"RESPONSABLE", 8000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 6

                    atenciones = PersonaConsultaMedica.objects.filter(tipopaciente__in=tipos,
                                                                      fecha__range=(desde, hasta),
                                                                      status=True).order_by('-fecha')

                    # if not esdirectordbu:
                    #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                    for a in atenciones:
                        row_num += 1
                        facultad = carrera = nivel = ""
                        ws.write(row_num, 0, a.fecha, fuentefecha)
                        p = Persona.objects.get(pk=a.persona_id)
                        ws.write(row_num, 1, TIPO_PACIENTE[a.tipopaciente - 1][1], fuentenormal)

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
                            cie10 = cie10 + ", "+ e.clave + " - " +e.descripcion if cie10 != "" else e.clave + " - " +e.descripcion
                        ws.write(row_num, 16, cie10, fuentenormal)

                        insumos = ", ".join([insumo.inventariomedicolote.inventariomedico.nombre + ' x ' + str(int(insumo.cantidad)) for insumo in a.insumos_utilizados()])
                        ws.write(row_num, 17, insumos, fuentenormal)

                        acciones = ''

                        for ac in a.accion.all():
                            acciones = acciones + ", " + ac.descripcion if acciones != "" else ac.descripcion

                        ws.write(row_num, 18, acciones, fuentenormal)

                        responsable = Persona.objects.get(usuario=a.usuario_creacion)
                        ws.write(row_num, 19, responsable.apellido1 + ' ' + responsable.apellido2 + ' ' + responsable.nombres, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadodetalladoareamedicamedicacion':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.combine(convertir_fecha(request.GET['desde']), time.min)
                    hasta = datetime.combine(convertir_fecha(request.GET['hasta']), time.max)
                    tipopaciente = int(request.GET['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                       estadopuesto_id=1, status=True).exists()

                    titulo = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                    titulo2 = easyxf(
                        'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                    fuentecabecera = easyxf(
                        'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                    fuentenormal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                    fuentemoneda = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str=' "$" #,##0.00')
                    fuentefecha = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                        num_format_str='yyyy-mm-dd')
                    fuentenumerodecimal = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                        num_format_str='#,##0.00')
                    fuentenumeroentero = easyxf(
                        'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                    font_style = XFStyle()
                    font_style.font.bold = True
                    font_style2 = XFStyle()
                    font_style2.font.bold = False
                    wb = Workbook(encoding='utf-8')
                    ws = wb.add_sheet('ListadoGeneral')
                    response = HttpResponse(content_type="application/ms-excel")
                    response['Content-Disposition'] = 'attachment; filename=listado_atenciones_medicas_medicacion_' + random.randint(1, 10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 8, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 8, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                    ws.write_merge(2, 2, 0, 8, 'LISTADO DETALLADO DE ATENCIONES DEL ÁREA MÉDICA - MEDICACIÓN ENTREGADA', titulo2)
                    ws.write_merge(3, 3, 0, 8, 'DESDE:   ' + str(convertir_fecha(request.GET['desde'])) + '     HASTA:   ' + str(convertir_fecha(request.GET['hasta'])), titulo2)
                    ws.write_merge(4, 4, 0, 8, str(persona) if not esdirectordbu else '', titulo2)

                    row_num = 6
                    columns = [
                        (u"FECHA", 3000),
                        (u"TIPO PACIENTE", 4000),
                        (u"IDENTIFICACIÓN", 5000),
                        (u"APELLIDOS", 7000),
                        (u"NOMBRES", 7000),
                        (u"EDAD", 3000),
                        (u"CÓDIGO CIE-10", 20000),
                        (u"MEDICACIÓN ENTREGADA", 20000),
                        (u"RESPONSABLE", 8000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 6

                    atenciones = PersonaConsultaMedica.objects.filter(tipopaciente__in=tipos,
                                                                      fecha__range=(desde, hasta),
                                                                      status=True).order_by('-fecha')

                    # if not esdirectordbu:
                    #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                    for a in atenciones:
                        row_num += 1
                        facultad = carrera = nivel = ""
                        ws.write(row_num, 0, a.fecha, fuentefecha)
                        p = Persona.objects.get(pk=a.persona_id)
                        ws.write(row_num, 1, TIPO_PACIENTE[a.tipopaciente - 1][1], fuentenormal)
                        ws.write(row_num, 2, p.identificacion(), fuentenormal)
                        ws.write(row_num, 3, p.apellido1 + ' ' + p.apellido2, fuentenormal)
                        ws.write(row_num, 4, p.nombres, fuentenormal)
                        ws.write(row_num, 5, calcula_edad(p.nacimiento), fuentenumeroentero)

                        cie10 = ""
                        for e in a.enfermedad.all():
                            cie10 = cie10 + ", "+ e.clave + " - " +e.descripcion if cie10 != "" else e.clave + " - " +e.descripcion
                        ws.write(row_num, 6, cie10, fuentenormal)

                        insumos = ", ".join([insumo.inventariomedicolote.inventariomedico.nombre + ' x ' + str(int(insumo.cantidad)) for insumo in a.insumos_utilizados()])
                        ws.write(row_num, 7, insumos, fuentenormal)

                        responsable = Persona.objects.get(usuario=a.usuario_creacion)
                        ws.write(row_num, 8, responsable.apellido1 + ' ' + responsable.apellido2 + ' ' + responsable.nombres, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'datos':
                try:
                    data['title'] = u'Datos adicionales del paciente'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    datos = pex.personafichamedica.personaextension
                    data['form'] = PersonaExtensionForm(initial={'direccion': datos.persona.direccion,
                                                                 'direccion2': datos.persona.direccion2,
                                                                 'horanacimiento': datos.horanacimiento,
                                                                 'edadaparenta': datos.edadaparenta,
                                                                 'estadocivil': datos.estadocivil,
                                                                 'tienelicencia': datos.tienelicencia,
                                                                 'tipolicencia': datos.tipolicencia,
                                                                 'telefonos': datos.telefonos,
                                                                 'tieneconyuge': datos.tieneconyuge,
                                                                 'hijos': datos.hijos,
                                                                 'contactoemergencia': datos.contactoemergencia,
                                                                 'telefonoemergencia': datos.telefonoemergencia,
                                                                 'gestacion': pex.personafichamedica.gestacion})
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/datos.html", data)
                except Exception as ex:
                    pass

            elif action == 'patologicop':
                try:
                    data['title'] = u'Antecedentes patológicos'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if PatologicoPersonal.objects.filter(personafichamedica=personafichamedica).exists():
                        patologicop = PatologicoPersonal.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(patologicop)
                        data['form'] = PatologicoPersonalForm(initial=initial)
                    else:
                        data['form'] = PatologicoPersonalForm()

                    data['form2'] = VacunaForm()
                    data['form3'] = EnfermedadForm()
                    data['form4'] = AlergiaForm()
                    data['form5'] = MedicinaForm()

                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/patologicop.html", data)
                except Exception as ex:
                    pass

            elif action == 'patologicoq':
                try:
                    data['title'] = u'Antecedentes Quirurgicos'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if PatologicoQuirurgicos.objects.filter(personafichamedica=personafichamedica).exists():
                        patologicoq = PatologicoQuirurgicos.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(patologicoq)
                        data['form'] = PatologicoQuirurgicosForm(initial=initial)
                    else:
                        data['form'] = PatologicoQuirurgicosForm()

                    data['form2'] = CirugiaForm()

                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/patologicoq.html", data)
                except Exception as ex:
                    pass

            elif action == 'ginecologico':
                try:
                    data['title'] = u'Antecedentes ginecobstétricos'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if AntecedenteGinecoobstetrico.objects.filter(personafichamedica=personafichamedica).exists():
                        ginecologico = AntecedenteGinecoobstetrico.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(ginecologico)
                        data['form'] = AntecedenteGinecoobstetricoForm(initial=initial)
                    else:
                        data['form'] = AntecedenteGinecoobstetricoForm()

                    data['form2'] = MetodoAnticonceptivoForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/ginecoobstetrico.html", data)
                except Exception as ex:
                    pass

            elif action == 'traumatologico':
                try:
                    data['title'] = u'Antecedentes Traumatologico'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if AntecedenteTraumatologicos.objects.filter(personafichamedica=personafichamedica).exists():
                        traumatologico = AntecedenteTraumatologicos.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(traumatologico)
                        data['form'] = AntecedenteTraumatologicosForm(initial=initial)
                    else:
                        data['form'] = AntecedenteTraumatologicosForm()

                    data['form2'] = LugarAnatomicoForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/traumatologico.html", data)
                except Exception as ex:
                    pass

            elif action == 'reportevacunadosestudiantes':
                __author__ = 'Unemi'
                facultad_id = int(request.GET['facultad'])
                carrera_id = int(request.GET['carrera'])
                periodo_id = int(request.GET['periodo'])
                periodo_get = Periodo.objects.get(pk=periodo_id)
                matriculas_periodo = Matricula.objects.select_related().filter(status=True, nivel__periodo=periodo_get, inscripcion__activo=True)
                if facultad_id != 0:
                    matriculas_periodo = matriculas_periodo.filter(inscripcion__coordinacion__id=facultad_id)
                else:
                    facultades = Coordinacion.objects.filter(status=True, excluir=False).order_by('id')
                    matriculas_periodo = matriculas_periodo.filter(inscripcion__coordinacion__in=facultades.values_list('id',flat=True))
                if carrera_id != 0:
                    matriculas_periodo = matriculas_periodo.filter(inscripcion__carrera_id=carrera_id)
                listapersonas = matriculas_periodo.values_list('inscripcion__persona_id',flat=True)
                queryvacuna = VacunaCovid.objects.select_related().filter(status=True, persona__in=listapersonas, recibiovacuna=True)

                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('ListadoGeneral')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=listado_vacunados_estudiantes_' + random.randint(1, 10000).__str__() + '.xls'
                ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                ws.write_merge(2, 2, 0, 11, 'LISTADO DETALLADO DE ESTUDIANATES VACUNADOS', titulo2)
                ws.write_merge(3, 3, 0, 11, periodo_get.nombre, titulo2)
                row_num = 6
                columns = [
                    (u"Facultad", 10000),
                    (u"Carrera", 10000),
                    (u"Nivel", 5000),
                    (u"Identificación", 5000),
                    (u"Apellidos", 7000),
                    (u"Nombres", 7000),
                    (u"Género", 4000),
                    (u"Edad", 3000),
                    (u"Telefono", 7000),
                    (u"Email", 7000),
                    (u"Tipo Vacuna", 10000),
                    (u"¿Dosis Completa?", 10000),
                    (u"Num Dosis", 10000),
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 6
                for a in queryvacuna:
                    row_num += 1
                    facultad, carrera, nivel = "", "", ""
                    personaid = a.persona
                    mat = matriculas_periodo.filter(inscripcion__persona=personaid).first()
                    if mat:
                        facultad = str(mat.nivel.coordinacion())
                        carrera = str(mat.inscripcion.carrera)
                        nivel = mat.nivelmalla.nombre
                    ws.write(row_num, 0, facultad, fuentenormal)
                    ws.write(row_num, 1, carrera, fuentenormal)
                    ws.write(row_num, 2, nivel, fuentenormal)
                    ws.write(row_num, 3, personaid.identificacion(), fuentenormal)
                    ws.write(row_num, 4, personaid.apellido1 + ' ' + personaid.apellido2, fuentenormal)
                    ws.write(row_num, 5, personaid.nombres, fuentenormal)
                    ws.write(row_num, 6, str(personaid.sexo), fuentenormal)
                    ws.write(row_num, 7, calcula_edad(personaid.nacimiento), fuentenumeroentero)
                    ws.write(row_num, 8, personaid.telefono, fuentenormal)
                    ws.write(row_num, 9, personaid.emailinst, fuentenormal)
                    ws.write(row_num, 10, a.tipovacuna.nombre, fuentenormal)
                    dosis_completa = 'SI' if a.recibiodosiscompleta else 'NO'
                    ws.write(row_num, 11, dosis_completa, fuentenormal)
                    ws.write(row_num, 12, a.total_dosis(), fuentenormal)
                wb.save(response)
                return response

            elif action == 'novacunados':
                __author__ = 'Unemi'

                queryvacuna = VacunaCovid.objects.filter(status=True, recibiovacuna=False).order_by('persona__apellido1')

                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('ListadoGeneral')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=listado_NO_vacunados_' + random.randint(1, 10000).__str__() + '.xls'
                ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                ws.write_merge(2, 2, 0, 11, 'LISTADO DETALLADO DE COMUNIDAD NO VACUNADOS', titulo2)
                row_num = 4
                columns = [
                    (u"Identificación", 5000),
                    (u"Apellidos", 7000),
                    (u"Nombres", 7000),
                    (u"Género", 4000),
                    (u"Edad", 3000),
                    (u"Telefono", 7000),
                    (u"Email", 7000),
                    (u"¿Es Estudiante?", 10000),
                    (u"¿Es Docente?", 10000),
                    (u"¿Es Administrativo?", 10000),
                    (u"¿Desea Vacunarse?", 8000),
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 4
                for a in queryvacuna:
                    row_num += 1
                    facultad, carrera, nivel = "", "", ""
                    p = Persona.objects.get(pk=a.persona_id)
                    ws.write(row_num, 0, p.identificacion(), fuentenormal)
                    ws.write(row_num, 1, p.apellido1 + ' ' + p.apellido2, fuentenormal)
                    ws.write(row_num, 2, p.nombres, fuentenormal)
                    ws.write(row_num, 3, str(p.sexo), fuentenormal)
                    ws.write(row_num, 4, calcula_edad(p.nacimiento), fuentenumeroentero)
                    ws.write(row_num, 5, p.telefono, fuentenormal)
                    ws.write(row_num, 6, p.emailinst, fuentenormal)
                    es_estudiante = 'SI' if p.es_estudiante() else 'NO'
                    es_docente = 'SI' if p.es_profesor() else 'NO'
                    es_administrativo = 'SI' if p.es_administrativo() else 'NO'
                    deseavacunarse = 'SI' if a.deseavacunarse else 'NO'
                    ws.write(row_num, 7, es_estudiante, fuentenormal)
                    ws.write(row_num, 8, es_docente, fuentenormal)
                    ws.write(row_num, 9, es_administrativo, fuentenormal)
                    ws.write(row_num, 10, deseavacunarse, fuentenormal)
                wb.save(response)
                return response

            elif action == 'docentesvacunados':
                __author__ = 'Unemi'
                queryvacuna = VacunaCovid.objects.filter(status=True, recibiovacuna=True, persona__perfilusuario__profesor__isnull=False).order_by('persona__apellido1')

                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('ListadoGeneral')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=listado_DOCENTES_vacunados_' + random.randint(1, 10000).__str__() + '.xls'
                ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                ws.write_merge(2, 2, 0, 11, 'LISTADO DETALLADO DE DOCENTES VACUNADOS', titulo2)
                row_num = 4
                columns = [
                    (u"Identificación", 5000),
                    (u"Apellidos", 7000),
                    (u"Nombres", 7000),
                    (u"Género", 4000),
                    (u"Edad", 3000),
                    (u"Telefono", 7000),
                    (u"Email", 7000),
                    (u"Tipo Vacuna", 10000),
                    (u"¿Dosis Completa?", 10000),
                    (u"Num Dosis", 10000),
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 4
                for a in queryvacuna:
                    row_num += 1
                    facultad, carrera, nivel = "", "", ""
                    p = Persona.objects.get(pk=a.persona_id)
                    ws.write(row_num, 0, p.identificacion(), fuentenormal)
                    ws.write(row_num, 1, p.apellido1 + ' ' + p.apellido2, fuentenormal)
                    ws.write(row_num, 2, p.nombres, fuentenormal)
                    ws.write(row_num, 3, str(p.sexo), fuentenormal)
                    ws.write(row_num, 4, calcula_edad(p.nacimiento), fuentenumeroentero)
                    ws.write(row_num, 5, p.telefono, fuentenormal)
                    ws.write(row_num, 6, p.emailinst, fuentenormal)
                    ws.write(row_num, 7, a.tipovacuna.nombre, fuentenormal)
                    dosis_completa = 'SI' if a.recibiodosiscompleta else 'NO'
                    ws.write(row_num, 8, dosis_completa, fuentenormal)
                    ws.write(row_num, 9, a.total_dosis(), fuentenormal)
                wb.save(response)
                return response

            elif action == 'administrativosvacunados':
                __author__ = 'Unemi'
                queryvacuna = VacunaCovid.objects.filter(status=True, recibiovacuna=True, persona__perfilusuario__administrativo__isnull=False).order_by('persona__apellido1')

                titulo = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 350; alignment: horiz centre')
                titulo2 = easyxf(
                    'font: name Times New Roman, color-index black, bold on , height 250; alignment: horiz centre')
                fuentecabecera = easyxf(
                    'font: name Verdana, color-index black, bold on, height 150; pattern: pattern solid, fore_colour gray25; alignment: vert distributed, horiz centre; borders: left thin, right thin, top thin, bottom thin')
                fuentenormal = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin')
                fuentemoneda = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str=' "$" #,##0.00')
                fuentefecha = easyxf(
                    'font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz center',
                    num_format_str='yyyy-mm-dd')
                fuentenumerodecimal = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right',
                    num_format_str='#,##0.00')
                fuentenumeroentero = easyxf('font: name Verdana, color-index black, height 150; borders: left thin, right thin, top thin, bottom thin; alignment: horiz right')

                font_style = XFStyle()
                font_style.font.bold = True
                font_style2 = XFStyle()
                font_style2.font.bold = False
                wb = Workbook(encoding='utf-8')
                ws = wb.add_sheet('ListadoGeneral')
                response = HttpResponse(content_type="application/ms-excel")
                response['Content-Disposition'] = 'attachment; filename=listado_ADMINISTRATIVOS_vacunados_' + random.randint(1, 10000).__str__() + '.xls'
                ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                ws.write_merge(2, 2, 0, 11, 'LISTADO DETALLADO DE DOCENTES VACUNADOS', titulo2)
                row_num = 4
                columns = [
                    (u"Identificación", 5000),
                    (u"Apellidos", 7000),
                    (u"Nombres", 7000),
                    (u"Género", 4000),
                    (u"Edad", 3000),
                    (u"Telefono", 7000),
                    (u"Email", 7000),
                    (u"Tipo Vacuna", 10000),
                    (u"¿Dosis Completa?", 10000),
                    (u"Num Dosis", 10000),
                ]
                for col_num in range(len(columns)):
                    ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                    ws.col(col_num).width = columns[col_num][1]
                row_num = 4
                for a in queryvacuna:
                    row_num += 1
                    facultad, carrera, nivel = "", "", ""
                    p = Persona.objects.get(pk=a.persona_id)
                    ws.write(row_num, 0, p.identificacion(), fuentenormal)
                    ws.write(row_num, 1, p.apellido1 + ' ' + p.apellido2, fuentenormal)
                    ws.write(row_num, 2, p.nombres, fuentenormal)
                    ws.write(row_num, 3, str(p.sexo), fuentenormal)
                    ws.write(row_num, 4, calcula_edad(p.nacimiento), fuentenumeroentero)
                    ws.write(row_num, 5, p.telefono, fuentenormal)
                    ws.write(row_num, 6, p.emailinst, fuentenormal)
                    ws.write(row_num, 7, a.tipovacuna.nombre, fuentenormal)
                    dosis_completa = 'SI' if a.recibiodosiscompleta else 'NO'
                    ws.write(row_num, 8, dosis_completa, fuentenormal)
                    ws.write(row_num, 9, a.total_dosis(), fuentenormal)
                wb.save(response)
                return response


            # elif action == 'ginecologico':
            #     try:
            #         data['title'] = u'Antecedentes ginecologicos'
            #         pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
            #         datos = pex.personafichamedica
            #         data['form'] = PersonaGinecologicoForm(initial={'gestacion': datos.gestacion,
            #                                                         'partos': datos.partos,
            #                                                         'abortos': datos.abortos,
            #                                                         'cesareas': datos.cesareas,
            #                                                         'hijos2': datos.hijos2})
            #         data['pex'] = pex
            #         data['paciente'] = pex.personafichamedica.personaextension.persona
            #         return render(request, "box_medical/ginecologico.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'habitos':
                try:
                    data['title'] = u'Hábitos personales'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if Habito.objects.filter(personafichamedica=personafichamedica).exists():
                        habito = Habito.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(habito)
                        data['form'] = HabitoForm(initial=initial)
                    else:
                        data['form'] = HabitoForm()

                    data['form2'] = DrogaForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/habitos.html", data)
                except Exception as ex:
                    pass
            # elif action == 'habitos':
            #     try:
            #         data['title'] = u'Habitos'
            #         data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
            #         datos = pex.personafichamedica
            #         data['form'] = PersonaHabitoForm(initial={'cigarro': datos.cigarro,
            #                                                   'numerocigarros': datos.numerocigarros,
            #                                                   'tomaalcohol': datos.tomaalcohol,
            #                                                   'tipoalcohol': datos.tipoalcohol,
            #                                                   'copasalcohol': datos.copasalcohol,
            #                                                   'tomaantidepresivos': datos.tomaantidepresivos,
            #                                                   'antidepresivos': datos.antidepresivos,
            #                                                   'tomaotros': datos.tomaotros,
            #                                                   'otros': datos.otros,
            #                                                   'horassueno': datos.horassueno,
            #                                                   'calidadsuenno': datos.calidadsuenno})
            #         data['paciente'] = pex.personafichamedica.personaextension.persona
            #         return render(request, "box_medical/habitos.html", data)
            #     except Exception as ex:
            #         pass

            # elif action == 'patologicof':
            #     try:
            #         data['title'] = u'Antecedentes patologicos de familiares'
            #         pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
            #         datos = pex.personafichamedica.personaextension
            #         data['form'] = PersonaPatologicoFamiliarForm(initial={'enfermedadpadre': datos.enfermedadpadre,
            #                                                               'enfermedadmadre': datos.enfermedadmadre,
            #                                                               'enfermedadabuelos': datos.enfermedadabuelos,
            #                                                               'enfermedadhermanos': datos.enfermedadhermanos,
            #                                                               'enfermedadotros': datos.enfermedadotros})
            #
            #         data['pex'] = pex
            #         data['paciente'] = pex.personafichamedica.personaextension.persona
            #         return render(request, "box_medical/patologicof.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'patologicof':
                try:
                    data['title'] = u'Antecedentes patológicos de familiares'
                    pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    data['pex'] = pex
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    data['patologicofamiliar'] = pex.personafichamedica.patologicofamiliar_set.all()
                    return render(request, "box_medical/patologicof_view.html", data)
                except Exception as ex:
                    pass

            elif action == 'patologicof_add':
                try:
                    data['title'] = u'Antecedentes patológicos familiares'
                    data['form'] = PatologicoFamiliarForm()
                    data['form2'] = EnfermedadForm()
                    pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    data['pex'] = pex
                    return render(request, 'box_medical/patologicof_add.html', data)
                except Exception as ex:
                    pass

            elif action == 'patologicof_edit':
                try:
                    data['title'] = u'Modificar Antecedentes patológicos'
                    data['patologicof'] = patologicof = PatologicoFamiliar.objects.get(pk=request.GET['id'])
                    personafichamedica = patologicof.personafichamedica
                    data['pex'] = PersonaExamenFisico.objects.filter(personafichamedica=personafichamedica)[0]
                    initial = model_to_dict(patologicof)
                    data['form'] = PatologicoFamiliarForm(initial=initial)
                    data['form2'] = EnfermedadForm()
                    return render(request, 'box_medical/patologico_edit.html', data)
                except Exception as ex:
                    pass

            elif action == 'patologicof_delete':
                try:
                    data['title'] = u'Eliminar Antecedentes patologico'
                    data['patologicof'] = patologicof = PatologicoFamiliar.objects.get(pk=request.GET['id'])
                    personafichamedica = patologicof.personafichamedica
                    data['pex'] = PersonaExamenFisico.objects.filter(personafichamedica=personafichamedica)[0]
                    return render(request, 'box_medical/patologico_delete.html', data)
                except Exception as ex:
                    pass

            elif action == 'valoracionpersona':
                try:
                    data['title'] = u'Valoracion medica'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['pex'] = pex = persona.datos_examen_fisico()
                    data['inspeccionsomatica'] = InspeccionSomatica.objects.get(
                        personaexamenfisico=pex) if InspeccionSomatica.objects.filter(
                        personaexamenfisico=pex).exists() else ''
                    data['inspecciontopografica'] = InspeccionTopografica.objects.get(
                        personaexamenfisico=pex) if InspeccionTopografica.objects.filter(
                        personaexamenfisico=pex).exists() else ''
                    return render(request, "box_medical/valoracionpersonal.html", data)
                except Exception as ex:
                    pass

            elif action == 'rutagrama':
                try:
                    data['title'] = u'Rutagrama'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['pex'] = pex = persona.datos_examen_fisico()
                    data['rutagrama'] = Rutagrama.objects.get(
                        personafichamedica=pex.personafichamedica) if Rutagrama.objects.filter(
                        personafichamedica=pex.personafichamedica).exists() else ''
                    return render(request, "box_medical/rutagramaview.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarrutagrama':
                try:
                    data['title'] = u'Rutagrama Unemi'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    persona = personafichamedica.personaextension.persona
                    if Rutagrama.objects.filter(personafichamedica=personafichamedica).exists():
                        rutagrama = Rutagrama.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(rutagrama)
                        initial.update({'direccion': persona.direccion, 'direccion2': persona.direccion2})
                        data['form'] = RutagramaForm(initial=initial)
                    else:
                        data['form'] = RutagramaForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/rutagrama.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarinspeccionsomatica':
                try:
                    data['title'] = u'Editar Inspección Somática General'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    if InspeccionSomatica.objects.filter(personaexamenfisico=pex).exists():
                        somatica = InspeccionSomatica.objects.get(personaexamenfisico=pex)
                        initial = model_to_dict(somatica)
                        initial.update({'talla': pex.talla, 'peso': pex.peso})
                        form = InspeccionSomaticaForm(initial=initial)
                        form.editar()
                        data['form'] = form
                    else:
                        form = InspeccionSomaticaForm()
                        form.editar()
                        data['form'] = form

                    data['form2'] = LesionesForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/inspeccionsomatica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarinspecciontopografica':
                try:
                    data['title'] = u'Editar Inspección Topografica'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    if InspeccionTopografica.objects.filter(personaexamenfisico=pex).exists():
                        topografica = InspeccionTopografica.objects.get(personaexamenfisico=pex)
                        initial = model_to_dict(topografica)
                        data['form'] = InspeccionTopograficaForm(initial=initial)
                    else:
                        data['form'] = InspeccionTopograficaForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/inspecciontopografica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editarvaloracion':
                try:
                    data['title'] = u'Editar Valoración'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['pex'] = pex = persona.datos_examen_fisico()
                    form = PersonaExamenFisicoForm(initial={'peso': pex.peso if pex.peso else 0,
                                                            'talla': pex.talla if pex.talla else 0,
                                                            'indicecorporal': pex.indicecorporal,
                                                            'pa': pex.pa,
                                                            'pulso': pex.pulso,
                                                            'rcar': pex.rcar,
                                                            'rresp': pex.rresp if pex.rresp else 0,
                                                            'temp': pex.temp if pex.temp else 0,
                                                            'observaciones': pex.observaciones})
                    form.editar()
                    data['form'] = form
                    data['indicadores'] = IndicadorSobrepeso.objects.all()
                    return render(request, "box_medical/editar.html", data)
                except Exception as ex:
                    pass

            # elif action == 'editar':
            #     try:
            #         data['title'] = u'Editar valoracion medica'
            #         data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
            #         data['pex'] = pex = persona.datos_examen_fisico()
            #         form = PersonaExamenFisicoForm(initial={'inspeccion': pex.inspeccion,
            #                                                 'usalentes': pex.usalentes,
            #                                                 'motivo': pex.motivo,
            #                                                 'peso': pex.peso if pex.peso else 0,
            #                                                 'talla': pex.talla if pex.talla else 0,
            #                                                 'indicecorporal': pex.indicecorporal,
            #                                                 'pa': pex.pa,
            #                                                 'pulso': pex.pulso,
            #                                                 'rcar': pex.rcar,
            #                                                 'rresp': pex.rresp if pex.rresp else 0,
            #                                                 'temp': pex.temp if pex.temp else 0,
            #                                                 'observaciones': pex.observaciones})
            #         form.editar()
            #         data['form'] = form
            #         data['indicadores'] = IndicadorSobrepeso.objects.all()
            #         return render(request, "box_medical/editar.html", data)
            #     except Exception as ex:
            #         pass

            elif action == 'consultamedica':
                try:
                    persona = Persona.objects.get(pk=request.GET['id'])
                    data['title'] = u'Consultas médicas - Paciente: ' + str(persona) + ' - ' + persona.identificacion()
                    data['paciente'] = persona

                    form = PersonaConsultaMedicaForm(initial={'fechaatencion': datetime.now().date(),
                                                              'fecha': datetime.now().date(),
                                                              'hora': "12:00"})
                    tpac = persona.tipo_paciente()
                    form.tipos_paciente(tpac['tipoper'], tpac['regimen'])

                    if tpac['tipoper'] == 'ALU':
                        matri = persona.datos_ultima_matricula()
                        data['idmatricula'] = matri['idmatricula']

                    data['form'] = form
                    data['form2'] = AccionConsultaForm()
                    data['cita'] = request.GET['idc'] if 'idc' in request.GET else None
                    return render(request, "box_medical/consultamedica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addconsultamedica':
                try:
                    paciente = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Agregar Consulta Médica - Paciente: ' + str(paciente) + ' - ' + paciente.identificacion()
                    data['paciente'] = paciente
                    form = ConsultaMedicaForm()

                    tpac = paciente.tipo_paciente()
                    form.tipos_paciente(tpac['tipoper'], tpac['regimen'])

                    if tpac['tipoper'] == 'ALU':
                        matri = paciente.datos_ultima_matricula()
                        data['idmatricula'] = matri['idmatricula']

                    data['fecha'] = datetime.now().date()
                    data['hora'] = datetime.now().time().strftime("%H:%M")
                    data['idcita'] = request.GET['idcita'] if 'idcita' in request.GET else None
                    data['form'] = form
                    return render(request, "box_medical/addconsultamedica.html", data)
                except Exception as ex:
                    pass

            elif action == 'addmedicacionentregar':
                try:
                    data['title'] = u'Agregar Medicación a Entregar'
                    template = get_template("box_medical/addmedicacionentregar.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content, 'title': data['title']})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'buscarenfermedad':
                try:
                    q = request.GET['q'].upper().strip()

                    catalogo = CatalogoEnfermedad.objects.filter(descripcion__icontains=q, status=True).distinct()[:20]
                    data = {"result": "ok", "results": [{"id": c.id, "name": c.flexbox_repr()} for c in catalogo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'buscarproducto':
                try:
                    q = request.GET['q'].upper().strip()
                    productos = InventarioMedico.objects.filter(status=True, nombre__icontains=q)
                    data = {"result": "ok", "results": [{"id": c.producto.id, "name": c.flexbox_repr(), "stock": c.stock} for c in productos]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'consultamedicaprevias':
                try:
                    data['title'] = u'Consultas médicas previas'
                    data['paciente'] = persona = Persona.objects.get(pk=int(encrypt(request.GET['id'])))
                    if 'idc' in request.GET:
                        data['consultas'] = PersonaConsultaMedica.objects.filter(persona=persona,
                                                                                 medico=data['persona'],
                                                                                 id=request.GET['idc'],
                                                                                 status=True)
                    else:
                        data['consultas'] = PersonaConsultaMedica.objects.filter(persona=persona, status=True)
                    return render(request, "box_medical/consultamedicaprevias.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconsultamedica':
                try:
                    data['consulta'] = consulta = PersonaConsultaMedica.objects.get(pk=int(encrypt(request.GET['id'])))
                    data['title'] = u'Editar consulta médica - Paciente: ' + str(consulta.persona) + ' - ' + consulta.persona.identificacion()
                    tipos = (consulta.tipopaciente, TIPO_PACIENTE[consulta.tipopaciente - 1][1])
                    data['enfermedad'] = consulta.enfermedad.values('id', 'descripcion').all()
                    data['insumos'] = consulta.insumos_utilizados()

                    cita = consulta.proxima_cita()
                    if cita:
                        cita = consulta.proxima_cita()
                        proximacita = True
                        fechacita = cita.fecha.date()
                        horacita = cita.fecha.time().strftime("%H:%M")
                        indicaciones = cita.indicaciones
                    else:
                        proximacita = False
                        fechacita = datetime.now().date()
                        horacita = datetime.now().time().strftime("%H:%M")
                        indicaciones = ''

                    form = ConsultaMedicaForm(initial={
                        'fechaatencion': consulta.fecha,
                        'tipoatencion': consulta.tipoatencion,
                        'motivo': consulta.motivo,
                        'diagnostico': consulta.diagnostico,
                        'tratamiento': consulta.tratamiento,
                        'proximacita': proximacita,
                        'fechacita': fechacita,
                        'horacita': horacita,
                        'indicaciones': indicaciones,
                        'accion': consulta.accion.all()
                    })

                    form.editar(tipos)

                    data['fecha'] = datetime.now().date()
                    data['hora'] = datetime.now().time().strftime("%H:%M")
                    data['proximacita'] = cita
                    data['form'] = form

                    # data['form2'] = AccionConsultaForm()
                    data['paciente'] = consulta.persona
                    return render(request, "box_medical/editconsultamedica.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconsultamedicaprevia':
                try:
                    data['consulta'] = consulta = PersonaConsultaMedica.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar consulta médica - Paciente: ' + str(
                        consulta.persona) + ' - ' + consulta.persona.identificacion()
                    tipos = (consulta.tipopaciente, TIPO_PACIENTE[consulta.tipopaciente - 1][1])
                    enfermedad = consulta.enfermedad.values('id', 'descripcion').all()
                    data['enfermedad'] = enfermedad

                    initial = model_to_dict(consulta)
                    form = PersonaConsultaMedicaForm(initial=initial)
                    form.editar(tipos, consulta.fecha)
                    data['form'] = form
                    data['form2'] = AccionConsultaForm()
                    data['paciente'] = consulta.persona
                    return render(request, "box_medical/editconsultamedicaprevia.html", data)
                except Exception as ex:
                    pass

            elif action == 'rutagramapdf':
                try:
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    jornada = persona.jornada_actual()
                    if Jornada.objects.filter(nombre=jornada).exists():
                        data['jornada'] = Jornada.objects.get(nombre=jornada)
                    if Rutagrama.objects.filter(personafichamedica__personaextension__persona=persona).exists():
                        data['rutagrama'] = Rutagrama.objects.get(personafichamedica__personaextension__persona=persona)
                    data['personaextension'] = PersonaExtension.objects.get(persona=persona)
                    # return render(request, "box_medical/rutagramapdf.html", data)
                    return conviert_html_to_pdf(
                        'box_medical/rutagramapdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'fichapdf':
                try:
                    data['cargo'] = persona.mi_cargo_actual().denominacionpuesto
                    titulos = persona.titulo3y4nivel()
                    data['titulo1'] = titulos['tit1']
                    data['titulo2'] = titulos['tit2']
                    # r = cargo_titulo1_titulo2(persona) HAN BORRADO LA FUNCION Y NO SE ENCUENTRA HISTORIAL
                    # data['cargo'] = r['cargo']
                    # data['titulo1'] = r['titulo1']
                    # data['titulo2'] = r['titulo2']
                    data['medico'] = persona
                    data['fecha'] = datetime.now().date()

                    personal = None
                    pato = None
                    traumatologicos = None
                    ginecoobstetrico = None
                    somatica = None
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    ficha = PersonaFichaMedica.objects.get(personaextension__persona=persona)
                    pex = PersonaExamenFisico.objects.get(personafichamedica=ficha)
                    data['patologicofamiliar'] = ficha.patologicofamiliar_set.all()
                    if PatologicoPersonal.objects.filter(personafichamedica=ficha).exists():
                        personal = PatologicoPersonal.objects.get(personafichamedica=ficha)
                    if PatologicoQuirurgicos.objects.filter(personafichamedica=ficha).exists():
                        pato = PatologicoQuirurgicos.objects.get(personafichamedica=ficha)
                    if AntecedenteTraumatologicos.objects.filter(personafichamedica=ficha).exists():
                        traumatologicos = AntecedenteTraumatologicos.objects.get(personafichamedica=ficha)
                    if AntecedenteGinecoobstetrico.objects.filter(personafichamedica=ficha).exists():
                        ginecoobstetrico = AntecedenteGinecoobstetrico.objects.get(personafichamedica=ficha)
                    if Habito.objects.filter(personafichamedica=ficha).exists():
                        data['habito'] = Habito.objects.get(personafichamedica=ficha)
                    if InspeccionSomatica.objects.filter(personaexamenfisico=pex).exists():
                        somatica = InspeccionSomatica.objects.get(personaexamenfisico=pex)
                    if InspeccionTopografica.objects.filter(personaexamenfisico=pex).exists():
                        data['inspecciontopografica'] = InspeccionTopografica.objects.get(personaexamenfisico=pex)
                    data['fechaficha'] = ficha.fecha
                    data['antecedentetraumatologicos'] = traumatologicos
                    data['patologicopersonal'] = personal
                    data['antecedenteginecoobstetrico'] = ginecoobstetrico
                    data['patologicoquirurgicos'] = pato
                    data['personaexamenfisico'] = pex
                    data['inspeccionsomatica'] = somatica
                    data['personaextension'] = PersonaExtension.objects.get(persona=persona)
                    data['consultas'] = PersonaConsultaMedica.objects.filter(persona=persona, status=True).order_by(
                        '-id')
                    return conviert_html_to_pdf(
                        'box_medical/fichapdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['periodo_actual'] = periodo_actual
            esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                               estadopuesto_id=1, status=True).exists()
            search = None
            ids = None

            consultas = PersonaConsultaMedica.objects.values_list('id').filter(status=True)
            totalgeneral = consultas.count()
            totalgeneralusuario = consultas.filter(usuario_creacion_id=persona.usuario.id).count()
            totalhoy = consultas.filter(fecha__date=datetime.now().date()).count()
            totalusuariohoy = consultas.filter(fecha__date=datetime.now().date(),
                                               usuario_creacion_id=persona.usuario.id).count()

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
                personal = personal.filter(id=int(encrypt(ids))).distinct()
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
            data['area'] = "Área médica"
            data['tipopacientes'] = TIPO_PACIENTE
            data['totalgeneral'] = totalgeneral
            data['totalgeneralusuario'] = totalgeneralusuario
            data['totalhoy'] = totalhoy
            data['totalusuariohoy'] = totalusuariohoy
            data['medico'] = persona.usuario
            codigos_facultad = PersonaConsultaMedica.objects.values_list('matricula__inscripcion__coordinacion_id',
                                                                         flat=True).filter(status=True,
                                                                                           matricula__isnull=False,
                                                                                           tipopaciente=3).order_by(
                'matricula__inscripcion__coordinacion_id').distinct()
            codigos_carrera = PersonaConsultaMedica.objects.values_list('matricula__inscripcion__carrera_id',
                                                                        flat=True).filter(status=True,
                                                                                          matricula__isnull=False,
                                                                                          tipopaciente=3).order_by(
                'matricula__inscripcion__carrera_id').distinct()
            carreras = ','.join(str(c) for c in codigos_carrera)
            data['facultades'] = Coordinacion.objects.filter(status=True, excluir=False,
                                                             pk__in=codigos_facultad).order_by('id')
            data['codigos_carrera'] = carreras
            data['esdirectordbu'] = esdirectordbu if esdirectordbu else ''
            data['periodos_lista'] = periodos = Periodo.objects.filter(status=True).order_by('-pk')

            return render(request, "box_medical/view.html", data)


def add_legend(draw_obj, chart, data):
    legend = Legend()
    legend.alignment = 'right'
    legend.x = 10
    legend.y = 70
    legend.fontSize = 20
    legend.colorNamePairs = Auto(obj=chart)
    draw_obj.add(legend)


def pie_chart_with_legend():
    data = list(range(15, 105, 15))
    drawing = Drawing(width=800, height=500)
    my_title = String(170, 40, 'My Pie Chart', fontSize=14)
    pie = Pie()
    pie.sideLabels = True
    pie.x = 150
    pie.y = 65
    pie.width = 250
    pie.height = 250
    pie.data = data
    pie.labels = [letter for letter in 'abcdefg']
    pie.slices.strokeWidth = 0.5
    drawing.add(my_title)
    drawing.add(pie)
    add_legend(drawing, pie, data)
    return drawing


def guardar_insumos_entregados(atencionmedica, fechahora, medico, paciente, productos, request):
    # Guardo los productos entregados
    for item in productos:
        idproducto = int(item["idproducto"])
        cantidad = float(item["cantidad"])

        # Consulto el producto
        producto = Producto.objects.get(pk=idproducto)

        # Consulto el inventario medico
        inventariomedico = InventarioMedico.objects.get(producto=producto, status=True)

        # Restar el stock de inventario medico
        inventariomedico.stock = inventariomedico.stock - cantidad
        inventariomedico.save(request)

        # Restar del lote de inventario consultando desde el más antiguo
        while cantidad > 0:
            # Consulto el lote de inventario más antiguo con saldo disponible
            inventariomedicolote = InventarioMedicoLote.objects.filter(inventariomedico=inventariomedico, status=True, stock__gt=0).order_by('id')[0]
            stockdisponible = inventariomedicolote.stock

            if cantidad <= stockdisponible:
                cantidadrestar = cantidad
            else:
                cantidadrestar = stockdisponible

            # Resto del lote
            inventariomedicolote.stock = inventariomedicolote.stock - cantidadrestar
            inventariomedicolote.save(request)

            # Guardo el movimiento del lote
            movimientoinventario = InventarioMedicoMovimiento(
                inventariomedicolote=inventariomedicolote,
                numerodocumento=str(atencionmedica.id),
                tipo=2,
                fecha=fechahora,
                cantidad=cantidadrestar,
                saldoant=stockdisponible,
                ingreso=0,
                salida=cantidadrestar,
                saldo=stockdisponible - cantidadrestar,
                entrega=medico,
                recibe=paciente,
                detalle='CONSULTA MÉDICA # ' + str(atencionmedica.id),
                consultamedica=atencionmedica
            )
            movimientoinventario.save(request)

            # Determinar si debo seguir consultando otro lote para restar cantidades
            cantidad = 0 if cantidad <= stockdisponible else cantidad - stockdisponible
