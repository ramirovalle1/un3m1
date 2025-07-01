# -*- coding: latin-1 -*-
import glob
import os
import random
from datetime import datetime, time, date
import json

import pandas as pd
import xlwt
from django.contrib.auth.decorators import login_required
from django.core.checks import messages
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import easyxf, XFStyle, Workbook

from decorators import secure_module, last_access
from med.forms import PersonaExtensionForm, PersonaExamenFisicoForm, \
    PersonaConsultaMedicaForm, PatologicoFamiliarForm, PatologicoPersonalForm, PatologicoQuirurgicosForm, \
    AntecedenteTraumatologicosForm, AntecedenteGinecoobstetricoForm, HabitoForm, InspeccionSomaticaForm, \
    InspeccionTopograficaForm, RutagramaForm, VacunaForm, EnfermedadForm, AlergiaForm, MedicinaForm, \
    PersonaConsultaNutricionForm, PersonaFichaNutricionForm, ComidaFichaNutricionForm, PruebasFichaNutricionForm, \
    ConsumoFichaNutricionForm, ControlBarNutricionForm, CompletarConsultaNutricionForm, AntropometriaForm
from med.models import PersonaExamenFisico, PersonaConsultaMedica, \
    IndicadorSobrepeso, ProximaCita, PatologicoFamiliar, PatologicoPersonal, PatologicoQuirurgicos, \
    AntecedenteTraumatologicos, AntecedenteGinecoobstetrico, Habito, InspeccionSomatica, InspeccionTopografica, \
    Rutagrama, PersonaExtension, PersonaFichaMedica, TIPO_PACIENTE, PersonaConsultaOdontologica, \
    PersonaConsultaPsicologica, Vacuna, Enfermedad, Alergia, Medicina, CatalogoEnfermedad, SintomasAlimentario, \
    FrecuenciaConsumo, FRECUENCIACONSUMO, Antropometria, PersonaConsultaNutricion, ConsultaNutricionAntropometria, \
    PersonaFichaNutricion, ComidaFichaNutricion, Comidas, PruebaLaboratorioFichaNutricion, SintomasFichaNutricion, \
    ConsumoFichaNutricion, EnfermedadPersonaConsultaNutricion, BarUniversitario, GrupoAlimento, PreguntasBar, \
    ControlBarUniversitario, TIPO_CONSERVACION, ConservacionControlBarUniversitario, RespuestaControlBarUniversitario
from sagest.funciones import encrypt_id
from sagest.models import Jornada, DistributivoPersona
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, calcula_edad, grafica_barra
from sga.models import Persona, Matricula, Inscripcion, Coordinacion, Carrera, NivelMalla, PALETA_COLORES
from sga.funcionesxhtml2pdf import conviert_html_to_pdf
from utils.filtros_genericos import filtro_persona_principal, filtro_persona, filtro_persona_select


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    hoy = datetime.now()
    if request.method == 'POST':
        action = request.POST['action']

        if action == 'datosficha':
            try:
                fichanutricion = PersonaFichaNutricion.objects.get(pk=request.POST['id'])
                f = PersonaFichaNutricionForm(request.POST)
                if f.is_valid():
                    fichanutricion.fechaconsulta = f.cleaned_data['fechaconsulta']
                    fichanutricion.numeroficha = f.cleaned_data['numeroficha']
                    fichanutricion.patologia = f.cleaned_data['patologia']
                    fichanutricion.antecedentespatologicos = f.cleaned_data['antecedentespatologicos']
                    fichanutricion.consumoaldia = f.cleaned_data['consumoaldia']
                    fichanutricion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
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

        elif action == 'resumengeneralareanutricion':
            try:
                data = {}
                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área de Nutrición'
                atenciones = PersonaConsultaNutricion.objects.filter(fecha__range=(desde, hasta), status=True)

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
                area = "nutri"
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

        elif action == 'verificar_atenciones':
            try:
                persona = request.session['persona']
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()
                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')
                if desde <= hasta:
                    tipopaciente = int(request.POST['tipopaciente'])
                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    atenciones = PersonaConsultaNutricion.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True)

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

        elif action == 'patologicop':
            try:
                pexamenfisico = PersonaExamenFisico.objects.get(pk=int(request.POST['id']))
                personafichamedica = pexamenfisico.personafichamedica
                f = PatologicoPersonalForm(request.POST)
                if f.is_valid():
                    if PatologicoPersonal.objects.values('id').filter(personafichamedica=personafichamedica).exists():
                        patologicopersonal = PatologicoPersonal.objects.get(personafichamedica=personafichamedica)
                        patologicopersonal.nacio=f.cleaned_data['nacio']
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
                                                                lactanciaartificial=f.cleaned_data['lactanciaartificial'],
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

                    vacunash = f.cleaned_data['vacunas']
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
                    log(u'Adiciono antecedentes patologico personal: %s' % pexamenfisico.personafichamedica.personaextension.persona,
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
                    if PatologicoQuirurgicos.objects.values('id').filter(personafichamedica=personafichamedica).exists():
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
                    if AntecedenteTraumatologicos.objects.values('id').filter(personafichamedica=personafichamedica).exists():
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
                    if AntecedenteGinecoobstetrico.objects.values('id').filter(personafichamedica=personafichamedica).exists():
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
                                                                   puerperiocomplicacion=f.cleaned_data['puerperiocomplicacion'],
                                                                   anticonceptivo=f.cleaned_data['anticonceptivo'])
                        ginecologico.save(request)
                    ginecologico.metodoanticonceptivo.set(f.cleaned_data['metodoanticonceptivo'])
                    ginecologico.save(request)
                    log( u'Adiciono antecedentes Ginecoobstetrico: %s' % pexamenfisico.personafichamedica.personaextension.persona,
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
                        habito.tabaquismo = f.cleaned_data['tabaquismo']
                        habito.alcoholismo = f.cleaned_data['alcoholismo']
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
                                        tabaquismo=f.cleaned_data['tabaquismo'],
                                        alcoholismo=f.cleaned_data['alcoholismo'],
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
                    log(u'Adiciono habitos: %s' % pexamenfisico.personafichamedica.personaextension.persona,request, "add")
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
                    log(u'Adiciono datos medicos patologicos familiares: %s' % pexamenfisico.personafichamedica.personaextension.persona, request, "add")
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
                    patologicof.enfermedades.set(f.cleaned_data['enfermedades'])
                    patologicof.save(request)
                    log(
                        u'Modifico datos medicos patologicos familiares: %s' % patologicof.personafichamedica.personaextension.persona, request, "add")
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
                        somatica.imc = f.cleaned_data['imc']
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
                                                      imc=f.cleaned_data['imc'],
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
                        u'Adiciono Inspeccion Somatica: %s' % pexamenfisico.personafichamedica.personaextension.persona, request, "add")
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
                        topografica.abdomenanteriorcicatrizumbilical = f.cleaned_data['abdomenanteriorcicatrizumbilical']
                        topografica.abdomenanteriorcirculacionlateral = f.cleaned_data['abdomenanteriorcirculacionlateral']
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
                                                            cuellocaralateralderecha=f.cleaned_data['cuellocaralateralderecha'],
                                                            cuellocaralateralizquierda=f.cleaned_data['cuellocaralateralizquierda'],
                                                            cuellocaraposterior=f.cleaned_data['cuellocaraposterior'],
                                                            toraxcaraanterior=f.cleaned_data['toraxcaraanterior'],
                                                            toraxcaralateralderecha=f.cleaned_data['toraxcaralateralderecha'],
                                                            toraxcaralateralizquierda=f.cleaned_data['toraxcaralateralizquierda'],
                                                            toraxcaraposterior=f.cleaned_data['toraxcaraposterior'],
                                                            abdomenanterior=f.cleaned_data['abdomenanterior'],
                                                            abdomenanteriorformas=f.cleaned_data['abdomenanteriorformas'],
                                                            abdomenanteriorvolumen=f.cleaned_data['abdomenanteriorvolumen'],
                                                            abdomenanteriorcicatrizumbilical=f.cleaned_data['abdomenanteriorcicatrizumbilical'],
                                                            abdomenanteriorcirculacionlateral=f.cleaned_data['abdomenanteriorcirculacionlateral'],
                                                            abdomenanteriorcicatrices=f.cleaned_data['abdomenanteriorcicatrices'],
                                                            abdomenanteriornebus=f.cleaned_data['abdomenanteriornebus'],
                                                            abdomenlateralizquierdo=f.cleaned_data['abdomenlateralizquierdo'],
                                                            abdomenlateralderecho=f.cleaned_data['abdomenlateralderecho'],
                                                            abdomenposterior=f.cleaned_data['abdomenposterior'],
                                                            inguinogenitalvello=f.cleaned_data['inguinogenitalvello'],
                                                            inguinogenitalhernias=f.cleaned_data['inguinogenitalhernias'],
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
                    if Rutagrama.objects.values('id').filter(personafichamedica=pexamenfisico.personafichamedica).exists():
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
                    log(u'Modifico examen fisico: %s' % pexamenfisico.personafichamedica.personaextension.persona, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'consultanutricion':
            try:
                persona = Persona.objects.get(pk=request.POST['id'])
                idmatricula = request.POST['idmatricula']
                lista_items1 = json.loads(request.POST['lista_items1'])
                lista_items2 = json.loads(request.POST['lista_items2'])
                perimeravez = False
                if not persona.personaconsultanutricion_set.filter(status=True):
                    perimeravez = True
                f = PersonaConsultaNutricionForm(request.POST)
                if f.is_valid():
                    if PersonaConsultaNutricion.objects.filter(persona=persona, fecha=f.cleaned_data['fechaconsulta'], status=True).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Registro con la fecha de consulta ya se encuentra registrado."})
                    consulta = PersonaConsultaNutricion(persona=persona,
                                                        motivo=f.cleaned_data['motivo'].strip().upper(),
                                                        diagnostico=f.cleaned_data['diagnostico'].strip().upper(),
                                                        recomendacion=f.cleaned_data['recomendacion'].strip().upper(),
                                                        medico=request.session['persona'],
                                                        tipoatencion=f.cleaned_data['tipoatencion'],
                                                        tipopaciente=f.cleaned_data['tipopaciente'],
                                                        fecha=f.cleaned_data['fechaconsulta'],
                                                        actividadfisica=f.cleaned_data['actividadfisica'],
                                                        primeravez=perimeravez,
                                                        matricula_id=idmatricula)
                    consulta.save(request)
                    if lista_items1:
                        for lista in lista_items1:
                            antropometria = ConsultaNutricionAntropometria(consulta=consulta,
                                                                           antropometria_id=lista['idcod'],
                                                                           valor=lista['valorcaja'])
                            antropometria.save(request)
                    if lista_items2:
                        for e in lista_items2:
                            idcatalogo = int(e['id'])
                            catalogo = EnfermedadPersonaConsultaNutricion(consulta=consulta,
                                                                          enfermedad_id=idcatalogo)
                            catalogo.save(request)
                    if f.cleaned_data['cita']:
                        fecha = f.cleaned_data['fecha']
                        hora = f.cleaned_data['hora']
                        fechacita = datetime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute, hora.second)
                        if fechacita < datetime.now():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Fecha de próxima cita incorrecta."})
                        if ProximaCita.objects.values('id').filter(persona=consulta.persona, fecha__gte=datetime.now(), medico=consulta.medico).exists():
                            transaction.set_rollback(True)
                            return JsonResponse({"result": "bad", "mensaje": u"Ya existe una cita programada para este paciente."})
                        proximacita = ProximaCita(persona=consulta.persona,
                                                  fecha=fechacita,
                                                  medico=consulta.medico,
                                                  indicaciones=f.cleaned_data['indicaciones'],
                                                  tipoconsulta=4)
                        proximacita.save(request)
                    if 'idc' in request.POST:
                        cita = ProximaCita.objects.get(pk=request.POST['idc'])
                        cita.asistio = True
                        cita.save(request)
                    log(u'Adiciono consulta nutrición: %s' % consulta, request, "add")
                    return JsonResponse({"result": "ok", "id": consulta.id})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcontrolbares':
            try:
                bar = BarUniversitario.objects.get(pk=request.POST['id'])
                lista_items1 = json.loads(request.POST['lista_items1'])
                lista_items2 = json.loads(request.POST['lista_items2'])
                f = ControlBarNutricionForm(request.POST)
                if f.is_valid():
                    control = ControlBarUniversitario(baruniversitario=bar,
                                                      fecha=f.cleaned_data['fecha'],
                                                      observaciones=f.cleaned_data['observaciones'],
                                                      numeroficha=f.cleaned_data['numeroficha'])
                    control.save(request)
                    if lista_items1:
                        for lista in lista_items1:
                            conservacion = ConservacionControlBarUniversitario(control=control,
                                                                               conservacion_id=lista['idcodtipo'],
                                                                               tipoconservacion=lista['tipoconservacion'])
                            conservacion.save(request)

                    if lista_items2:
                        for lista2 in lista_items2:
                            respuesta = RespuestaControlBarUniversitario(control=control,
                                                                         pregunta_id=lista2['idcodpre'],
                                                                         valor=lista2['id_pregunta'])
                            respuesta.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editcontrolbares':
            try:
                control = ControlBarUniversitario.objects.get(pk=request.POST['id'])
                f = ControlBarNutricionForm(request.POST)
                if f.is_valid():
                    control.numeroficha = f.cleaned_data['numeroficha']
                    control.fecha = f.cleaned_data['fecha']
                    control.observaciones = f.cleaned_data['observaciones']
                    control.save(request)
                    lista_items1 = json.loads(request.POST['lista_items1'])
                    lista_items2 = json.loads(request.POST['lista_items2'])
                    if lista_items1:
                        for lista in lista_items1:
                            conservacion = ConservacionControlBarUniversitario.objects.get(pk=int(lista['idcodtipo']),status=True)
                            conservacion.tipoconservacion=lista['tipoconservacion']
                            conservacion.save(request)
                    if lista_items2:
                        for lista2 in lista_items2:
                            respuesta=RespuestaControlBarUniversitario.objects.get(pk=lista2['idcodpre'], status=True)
                            respuesta.valor=lista2['id_pregunta']
                            respuesta.save(request)
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
                    # consulta.pacientegrupo = f.cleaned_data['grupo']
                    consulta.tipoatencion = f.cleaned_data['tipoatencion']
                    consulta.motivo = f.cleaned_data['motivo'].strip().upper()
                    consulta.medicacion = f.cleaned_data['medicacion'].strip().upper()
                    consulta.diagnostico = f.cleaned_data['diagnostico'].strip().upper()
                    consulta.tratamiento = f.cleaned_data['tratamiento'].strip().upper()
                    consulta.save(request)
                    log(u'Modifico consulta medica previa: %s' % consulta, request, "edit")
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addcomidas':
            try:
                ficha = PersonaFichaNutricion.objects.get(pk=request.POST['id'])
                f = ComidaFichaNutricionForm(request.POST)
                if f.is_valid():
                    comidaficha = ComidaFichaNutricion(ficha=ficha,
                                                       comida=f.cleaned_data['comida'],
                                                       hora=f.cleaned_data['hora'],
                                                       lugar=f.cleaned_data['lugar'],
                                                       observacion=f.cleaned_data['observacion']
                                                       )
                    comidaficha.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addfrecuenciaconsumo':
            try:
                elemento = request.POST['id']
                individuales = elemento.split('_')
                ficha = PersonaFichaNutricion.objects.get(pk=individuales[0])
                f = ConsumoFichaNutricionForm(request.POST)
                if f.is_valid():
                    consumo = ConsumoFichaNutricion(ficha=ficha,
                                                    consumo_id=individuales[1],
                                                    frecuencia=f.cleaned_data['frecuencia'],
                                                    valor=f.cleaned_data['valor'])
                    consumo.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'editfrecuenciaconsumo':
            try:
                fichaconsumo = ConsumoFichaNutricion.objects.get(pk=request.POST['id'])
                f = ConsumoFichaNutricionForm(request.POST)
                if f.is_valid():
                    fichaconsumo.frecuencia=f.cleaned_data['frecuencia']
                    fichaconsumo.valor=f.cleaned_data['valor']
                    fichaconsumo.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'addpruebas':
            try:
                ficha = PersonaFichaNutricion.objects.get(pk=request.POST['id'])
                f = PruebasFichaNutricionForm(request.POST)
                if f.is_valid():
                    pruebaficha = PruebaLaboratorioFichaNutricion(ficha=ficha,
                                                                  observacion=f.cleaned_data['observacion'],
                                                                  valor=f.cleaned_data['valor'])
                    pruebaficha.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delcomidaficha':
            try:
                comidaficha = ComidaFichaNutricion.objects.get(pk=request.POST['id'])
                comidaficha.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delpruebaficha':
            try:
                pruebaficha = PruebaLaboratorioFichaNutricion.objects.get(pk=request.POST['id'])
                pruebaficha.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delconsultaprevia':
            try:
                consulta = PersonaConsultaNutricion.objects.get(pk=request.POST['id'])
                consulta.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delfrecuenciaconsumo':
            try:
                consumoficha = ConsumoFichaNutricion.objects.get(pk=request.POST['id'])
                consumoficha.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'changetienesintoma':
            try:
                ficha = PersonaFichaNutricion.objects.get(pk=request.POST['fichaid'])
                codsintoma = SintomasAlimentario.objects.get(pk=request.POST['sintomaid'])
                if ficha.sintomasfichanutricion_set.filter(sintoma=codsintoma, status=True):
                    sintomaficha = ficha.sintomasfichanutricion_set.get(sintoma=codsintoma, status=True)
                    if sintomaficha.activo:
                        sintomaficha.activo = False
                    else:
                        sintomaficha.activo = True
                    sintomaficha.save(request)
                else:
                    sintomaficha = SintomasFichaNutricion(ficha=ficha,
                                                          sintoma=codsintoma,
                                                          activo=True)
                    sintomaficha.save(request)
                return JsonResponse({'result': 'ok', 'valor': sintomaficha.activo})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'verificar_atencionesfc':
            try:
                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()
                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')
                if  desde <= hasta:
                    facultad = int(request.POST['facultad'])
                    carrera = int(request.POST['carrera'])
                    tipopaciente = int(request.POST['tipopaciente'])

                    atenciones = PersonaConsultaNutricion.objects.filter(fecha__range=(desde, hasta), status=True)

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
                    return JsonResponse({"result": "bad", "mensaje": "La fecha desde debe ser menor o igual a la fecha hasta"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al generar la consulta."})

        elif action == 'resumenfacultadcarrera':
            try:
                data = {}

                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')
                facultad = int(request.POST['facultad'])
                carrera = int(request.POST['carrera'])

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen de atenciones del Área de Nutrición por Facultad y Carrera'
                atenciones = PersonaConsultaNutricion.objects.filter(tipopaciente=3, matricula__isnull=False, fecha__range=(desde, hasta), status=True)

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
                area = "nutri"
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

        elif action == 'resumengeneralareanutriciontipocita':
            try:
                data = {}

                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')
                tipopaciente = int(request.POST['tipopaciente'])
                facultad = int(request.POST['facultad'])
                carrera = int(request.POST['carrera'])

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen General de atenciones del Área de Nutrición por Tipo de Cita'
                atenciones = PersonaConsultaNutricion.objects.filter(fecha__range=(desde, hasta), status=True)

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
                area = "nutri"
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

        elif action == 'resumentipoacciones':
            try:
                data = {}

                desde = datetime.strptime(request.POST['desde'], '%Y-%m-%d')
                hasta = datetime.strptime(request.POST['hasta'], '%Y-%m-%d')

                esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600,
                                                                   estadopuesto_id=1, status=True).exists()

                data['tituloreporte'] = 'Reporte Resumen por Acciones realizadas del Área de Nutrición'
                atenciones = PersonaConsultaNutricion.objects.filter(fecha__range=(desde, hasta), status=True)

                # if not esdirectordbu:
                #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                tiposacciones = Antropometria.objects.filter(status=True).order_by('nombre')

                listaacciones = []
                datos = []

                for a in atenciones:
                    for acc in a.consultaantropometria().all():
                        listaacciones.append(acc.antropometria.nombre)

                totalgeneral = 0
                for a in tiposacciones:
                    descripcion = a.nombre
                    total = listaacciones.count(descripcion)
                    datos.append([descripcion, total])
                    totalgeneral += total


                nusuario = str(persona.usuario)
                area = "nutri"
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

        elif action == 'importarfichas':
            try:
                if not 'archivo' in request.FILES:
                    raise NameError('Por favor seleccione un archivo antes de guardar')
                archivo = request.FILES['archivo']
                namefile = archivo.name
                ext = namefile[namefile.rfind("."):].lower()
                if not ext in ['.xls', '.xlsx']:
                    raise NameError('Formato no admitido, por favor suba un archivo con formato xls, xlsx')

                name_hoja = pd.ExcelFile(archivo).sheet_names[0]
                df = pd.read_excel(archivo, sheet_name=name_hoja)
                cont = 0
                formato = '%Y.%m.%d. %H:%M:%S'
                atropometrias = Antropometria.objects.filter(status=True)
                df.columns = df.columns.str.split('.').str[-1].str.strip().str.lower()
                for a in atropometrias:
                    if a.slug and not f'{a.slug.lower()}' in df.columns:
                        raise NameError(f'No existe la columna {a.slug.lower()}')

                for index, row in df.iterrows():
                    cedula = str(row['id'])
                    if cedula:
                        cedula = f'0{cedula}' if len(cedula) == 9 else cedula
                        fecha = datetime.strptime(str(row['test date / time']), formato) if str(row['test date / time']) else hoy
                        paciente = Persona.objects.filter(cedula=cedula, status=True).first()
                        p_nutricion = PersonaConsultaNutricion.objects.filter(persona=paciente, fecha=fecha, status=True).exists()
                        if paciente and not p_nutricion:
                            p_consulta = PersonaConsultaNutricion(persona=paciente,
                                                                  medico=persona,
                                                                  tipoatencion=3,
                                                                  fecha=fecha,
                                                                  importado=True)
                            p_consulta.save(request)
                            log(f'Adiciono persona consulta: {p_consulta}',request, 'add')
                            for a in atropometrias:
                                if a.slug and str(row[a.slug.lower()]):
                                    valor = str(row[a.slug.lower()])
                                    valor = valor if not valor == '-' else ''
                                    antropometria = ConsultaNutricionAntropometria(consulta=p_consulta,
                                                                                   antropometria=a,
                                                                                   valor=valor)
                                    antropometria.save(request)
                                    log(f'Adiciono consulta de nutricion: {antropometria}', request, 'add')
                return JsonResponse({'result': False, 'mensaje': 'Importado con éxito'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'completarconsulta':
            try:
                consulta = PersonaConsultaNutricion.objects.get(id=encrypt_id(request.POST['id']))
                idmatricula = request.POST.get('idmatricula', None)
                lista_items1 = json.loads(request.POST['lista_items1'])
                perimeravez = False
                if not consulta.persona.personaconsultanutricion_set.filter(status=True):
                    perimeravez = True
                f = CompletarConsultaNutricionForm(request.POST)
                if f.is_valid():
                    consulta.motivo = f.cleaned_data['motivo'].strip().upper()
                    consulta.diagnostico = f.cleaned_data['diagnostico'].strip().upper()
                    consulta.recomendacion = f.cleaned_data['recomendacion'].strip().upper()
                    consulta.tipoatencion = f.cleaned_data['tipoatencion']
                    consulta.tipopaciente = f.cleaned_data['tipopaciente']
                    consulta.actividadfisica = f.cleaned_data['actividadfisica']
                    consulta.medico = f.cleaned_data['medico']
                    consulta.primeravez = perimeravez
                    consulta.matricula_id = idmatricula
                    consulta.lleno = True
                    consulta.save(request)

                    for enfermedad in f.cleaned_data['enfermedad']:
                        catalogo = EnfermedadPersonaConsultaNutricion(consulta=consulta,
                                                                      enfermedad=enfermedad)
                        catalogo.save(request)

                    for lista in lista_items1:
                        if lista['id_consulta_ant']:
                            antropometria = ConsultaNutricionAntropometria.objects.get(id=lista['id_consulta_ant'])
                            antropometria.valor = lista['valor']
                        else:
                            antropometria = ConsultaNutricionAntropometria(consulta=consulta,
                                                                           antropometria_id=lista['id_antropometria'],
                                                                           valor=lista['valor'])
                        antropometria.save(request)


                    if f.cleaned_data['cita']:
                        fecha = f.cleaned_data['fechacita']
                        hora = f.cleaned_data['hora']
                        fechacita = datetime(fecha.year, fecha.month, fecha.day, hora.hour, hora.minute, hora.second)
                        if fechacita < datetime.now():
                            transaction.set_rollback(True)
                            raise NameError(u"Fecha de próxima cita incorrecta.")
                        if ProximaCita.objects.values('id').filter(persona=consulta.persona, fecha__gte=datetime.now(), medico=consulta.medico).exists():
                            transaction.set_rollback(True)
                            raise NameError(u"Ya existe una cita programada para este paciente.")
                        proximacita = ProximaCita(persona=consulta.persona,
                                                  fecha=fechacita,
                                                  medico=consulta.medico,
                                                  indicaciones=f.cleaned_data['indicaciones'],
                                                  tipoconsulta=4)
                        proximacita.save(request)
                    if 'idc' in request.POST:
                        cita = ProximaCita.objects.get(pk=request.POST['idc'])
                        cita.asistio = True
                        cita.save(request)
                    log(u'Adiciono consulta nutrición: %s' % consulta, request, "add")
                    return JsonResponse({"result": False, "mensaje": 'Guardado con exito'})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": True, "mensaje": f"Error: {ex}"})

        elif action == 'delconsultaimportada':
            try:
                consulta = PersonaConsultaNutricion.objects.get(pk=request.POST['id'])
                consulta.delete()
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        elif action == 'addantropometria':
            try:
                form = AntropometriaForm(request.POST)
                if not form.is_valid():
                    return JsonResponse({'result': True, "form": [{k: v[0]} for k, v in form.errors.items()],"mensaje": "Error en el formulario"})
                antropometria = Antropometria(nombre=form.cleaned_data['nombre'],
                                              slug=form.cleaned_data['slug'])
                antropometria.save(request)
                log(f'Adiciono nuevo antropometría {antropometria}', request, 'add')
                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'editantropometria':
            try:
                antropometria=Antropometria.objects.get(id=encrypt_id(request.POST['id']))
                form = AntropometriaForm(request.POST, instancia=antropometria)
                if not form.is_valid():
                    return JsonResponse({'result': True,"form": [{k: v[0]} for k, v in form.errors.items()],"mensaje": "Error en el formulario"})
                antropometria.nombre=form.cleaned_data['nombre']
                antropometria.slug=form.cleaned_data['slug']
                antropometria.save(request)
                log(f'Edito antropometría {antropometria}', request, 'edit')
                return JsonResponse({'result': False}, safe=False)
            except Exception as ex:
                return JsonResponse({'result': True, 'mensaje': f'Error: {ex}'})

        elif action == 'delantropometria':
            try:
                antropometria = Antropometria.objects.get(pk=encrypt_id(request.POST['id']))
                antropometria.status=False
                antropometria.save(request, update_fields=['status'])
                log(f'Elimino antropometría {antropometria}', request, 'del')
                res_json = {"error": False}
            except Exception as ex:
                res_json = {'error': True, "message": "Error: {}".format(ex)}
            return JsonResponse(res_json, safe=False)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        # data = {}
        # adduserdata(request, data)
        data['title'] = u'Fichas nutrición'
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'ficha':
                try:
                    data['title'] = u'Ficha nutrición'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    data['pex'] = pex = persona.datos_fichanutricion()
                    data['listadosintomas'] = SintomasAlimentario.objects.filter(status=True).order_by('id')
                    data['listadosintomasficha'] = pex.sintomasfichanutricion_set.values_list('sintoma_id', flat=True).filter(activo=True, status=True)
                    # data['frecuencia'] = FRECUENCIACONSUMO
                    data['listadoconsumos'] = FrecuenciaConsumo.objects.filter(status=True).order_by('id')
                    data['listadocomidas'] = pex.comidafichanutricion_set.filter(status=True).order_by('comida_id')
                    data['listapruebas'] = pex.pruebalaboratoriofichanutricion_set.filter(status=True).order_by('id')
                    return render(request, "box_nutricion/ficha.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcomidas':
                try:
                    data['title'] = u'Adicionar tiempo de comidas'
                    data['pex'] = ficha = PersonaFichaNutricion.objects.get(pk=request.GET['id'])
                    form = ComidaFichaNutricionForm()
                    form.fields['comida'].queryset = Comidas.objects.filter(status=True).exclude(pk__in=ficha.comidafichanutricion_set.values_list('comida_id'))
                    data['form'] = form
                    return render(request, "box_nutricion/addcomidas.html", data)
                except Exception as ex:
                    pass

            elif action == 'addcontrolbares':
                try:
                    data['title'] = u'Adicionar control bar'
                    data['bar'] = BarUniversitario.objects.get(pk=request.GET['idbar'])
                    data['grupoalimentos'] = GrupoAlimento.objects.filter(status=True)
                    data['listadopreguntas'] = PreguntasBar.objects.filter(activo=True, status=True)
                    data['tipoconservacion'] = TIPO_CONSERVACION
                    form = ControlBarNutricionForm()
                    data['form'] = form
                    return render(request, "box_nutricion/addcontrolbares.html", data)
                except Exception as ex:
                    pass

            elif action == 'editcontrolbares':
                try:
                    data['title'] = u'Control bar universitario'
                    data['control'] = control = ControlBarUniversitario.objects.get(pk=request.GET['id'])
                    data['grupoalimentos'] = control.conservacioncontrolbaruniversitario_set.filter(status=True).order_by('conservacion_id')
                    data['listadopreguntas'] = control.respuestacontrolbaruniversitario_set.filter(status=True).order_by('pregunta_id')
                    data['tipoconservacion'] = TIPO_CONSERVACION
                    data['form'] = ControlBarNutricionForm(initial={'numeroficha': control.numeroficha,
                                                                    'fecha': control.fecha,
                                                                    'observaciones': control.observaciones})
                    return render(request, "box_nutricion/editcontrolbares.html", data)
                except Exception as ex:
                    pass

            elif action == 'addfrecuenciaconsumo':
                try:
                    data['title'] = u'Adicionar frecuencia de consumo'
                    data['pex'] = PersonaFichaNutricion.objects.get(pk=request.GET['idficha'])
                    data['frecuenciaconsumo'] = FrecuenciaConsumo.objects.get(pk=request.GET['idcondumo'])
                    form = ConsumoFichaNutricionForm()
                    data['form'] = form
                    return render(request, "box_nutricion/addfrecuenciaconsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'editfrecuenciaconsumo':
                try:
                    data['title'] = u'Editar frecuencia de consumo'
                    data['consumoficha'] = consumoficha = ConsumoFichaNutricion.objects.get(pk=request.GET['idfichaconsumo'])
                    data['form'] = ConsumoFichaNutricionForm(initial={'frecuencia': consumoficha.frecuencia,
                                                                      'valor': consumoficha.valor})
                    return render(request, "box_nutricion/editfrecuenciaconsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addpruebas':
                try:
                    data['title'] = u'Adicionar pruebas de  laboratorio relevantes al caso'
                    data['pex'] = ficha = PersonaFichaNutricion.objects.get(pk=request.GET['id'])
                    form = PruebasFichaNutricionForm()
                    data['form'] = form
                    return render(request, "box_nutricion/addpruebas.html", data)
                except Exception as ex:
                    pass

            elif action == 'delcomidaficha':
                try:
                    data['title'] = u'Eliminar Comida'
                    data['fichacomida'] = ComidaFichaNutricion.objects.get(pk=request.GET['idfichacomida'])
                    return render(request, "box_nutricion/delcomidaficha.html", data)
                except Exception as ex:
                    pass

            elif action == 'delpruebaficha':
                try:
                    data['title'] = u'Eliminar Prueba'
                    data['fichaprueba'] = PruebaLaboratorioFichaNutricion.objects.get(pk=request.GET['idfichaprueba'])
                    return render(request, "box_nutricion/delpruebaficha.html", data)
                except Exception as ex:
                    pass

            elif action == 'delconsultaprevia':
                try:
                    data['title'] = u'Eliminar consulta'
                    data['consultaprevia'] = PersonaConsultaNutricion.objects.get(pk=request.GET['idconsultaprevia'])
                    return render(request, "box_nutricion/delconsultaprevia.html", data)
                except Exception as ex:
                    pass

            elif action == 'delfrecuenciaconsumo':
                try:
                    data['title'] = u'Eliminar consumo'
                    data['fichaconsumo'] = ConsumoFichaNutricion.objects.get(pk=request.GET['idfichaconsumo'])
                    return render(request, "box_nutricion/delfrecuenciaconsumo.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadogeneralareamedica':
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
                    response['Content-Disposition'] = 'attachment; filename=listado_atenciones_medicas_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO GENERAL DE ATENCIONES DEL ÁREA NUTRICIÓN', titulo2)
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
                        (u"RESPONSABLE", 8000)
                    ]
                    for col_num in range(len(columns)):
                        ws.write(row_num, col_num, columns[col_num][0], fuentecabecera)
                        ws.col(col_num).width = columns[col_num][1]

                    row_num = 6

                    atenciones = PersonaConsultaMedica.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True).order_by('-fecha')

                    # if not esdirectordbu:
                    #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                    for a in atenciones:
                        row_num += 1
                        facultad = carrera = nivel = ""
                        ws.write(row_num, 0, a.fecha, fuentefecha)
                        #fechaatencion = a.fecha.date()
                        p = Persona.objects.get(pk=a.persona_id)
                        ws.write(row_num, 1, TIPO_PACIENTE[a.tipopaciente-1][1], fuentenormal)

                        totreg = p.personaconsultamedica_set.filter(fecha__lte=a.fecha, status=True).count()
                        cita = 'PRIMERA VEZ' if totreg <= 1 else 'SUBSEQUENTE'

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
                        ws.write(row_num, 15, a.diagnostico, fuentenormal)
                        responsable = Persona.objects.get(usuario=a.usuario_creacion)
                        ws.write(row_num, 16, responsable.apellido1+ ' ' + responsable.apellido2 + ' ' +responsable.nombres, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'listadodetalladoareanutricion':
                try:
                    __author__ = 'Unemi'
                    desde = datetime.strptime(request.GET['desde'],'%Y-%m-%d')
                    hasta = datetime.strptime(request.GET['hasta'],'%Y-%m-%d')
                    tipopaciente = int(request.GET['tipopaciente'])

                    if tipopaciente == 0:
                        tipos = [1, 2, 3, 4, 5, 6, 7]
                    else:
                        tipos = [tipopaciente]

                    esdirectordbu = DistributivoPersona.objects.filter(persona=persona, denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()

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
                    response['Content-Disposition'] = 'attachment; filename=listado_atenciones_ nutricion_' + random.randint(1,10000).__str__() + '.xls'

                    ws.write_merge(0, 0, 0, 11, 'UNIVERSIDAD ESTATAL DE MILAGRO', titulo)
                    ws.write_merge(1, 1, 0, 11, 'DIRECCIÓN DE BIENESTAR UNIVERSITARIO', titulo2)
                    ws.write_merge(2, 2, 0, 11, 'LISTADO DETALLADO DE ATENCIONES DEL ÁREA NUTRICIÓN', titulo2)
                    ws.write_merge(3, 3, 0, 11, 'DESDE:   ' + str(desde) + '     HASTA:   ' + str(hasta), titulo2)
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

                    atenciones = PersonaConsultaNutricion.objects.filter(tipopaciente__in=tipos, fecha__range=(desde, hasta), status=True).order_by('-fecha')

                    # if not esdirectordbu:
                    #     atenciones = atenciones.filter(usuario_creacion_id=persona.usuario.id)

                    for a in atenciones:
                        row_num += 1
                        facultad = carrera = nivel = ""
                        ws.write(row_num, 0, a.fecha, fuentefecha)
                        p = Persona.objects.get(pk=a.persona_id)
                        ws.write(row_num, 1, TIPO_PACIENTE[a.tipopaciente-1][1], fuentenormal)

                        cita = 'PRIMERA VEZ' if a.primeravez else 'SUBSEQUENTE'

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

                        if a.tipopaciente == 3 and a.matricula:
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

                        enfermedad = EnfermedadPersonaConsultaNutricion.objects.filter(consulta=a, enfermedad__isnull=False)

                        if enfermedad:
                            for e in enfermedad:
                                cie10 = cie10 + ", " + e.enfermedad.clave + " - " + e.enfermedad.descripcion if cie10 != "" else e.enfermedad.clave + " - " + e.enfermedad.descripcion

                        ws.write(row_num, 16, cie10, fuentenormal)

                        acciones = ''
                        for ac in a.consultaantropometria().all():
                            acciones = acciones + ", " + ac.antropometria.nombre if acciones != "" else ac.antropometria.nombre

                        ws.write(row_num, 17, acciones, fuentenormal)
                        responsable = Persona.objects.get(usuario=a.usuario_creacion)
                        ws.write(row_num, 18, responsable.apellido1+ ' ' + responsable.apellido2 + ' ' +responsable.nombres, fuentenormal)

                    wb.save(response)
                    return response
                except Exception as ex:
                    pass

            elif action == 'datosficha':
                try:
                    data['title'] = u'Datos ficha'
                    data['pex'] = pex = PersonaFichaNutricion.objects.get(pk=request.GET['id'])
                    data['form'] = PersonaFichaNutricionForm(initial={'numeroficha': pex.numeroficha,
                                                                      'consumoaldia': pex.consumoaldia,
                                                                      'fechaconsulta': pex.fechaconsulta,
                                                                      'patologia': pex.patologia,
                                                                      'antecedentespatologicos': pex.antecedentespatologicos})
                    return render(request, "box_nutricion/datosficha.html", data)
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
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/patologicoq.html", data)
                except Exception as ex:
                    pass

            elif action == 'ginecologico':
                try:
                    data['title'] = u'Antecedentes Ginecoobstetrico'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if AntecedenteGinecoobstetrico.objects.filter(personafichamedica=personafichamedica).exists():
                        ginecologico = AntecedenteGinecoobstetrico.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(ginecologico)
                        data['form'] = AntecedenteGinecoobstetricoForm(initial=initial)
                    else:
                        data['form'] = AntecedenteGinecoobstetricoForm()
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
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/traumatologico.html", data)
                except Exception as ex:
                    pass

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
                    data['title'] = u'Habitos'
                    data['pex'] = pex = PersonaExamenFisico.objects.get(pk=request.GET['id'])
                    personafichamedica = pex.personafichamedica
                    if Habito.objects.filter(personafichamedica=personafichamedica).exists():
                        habito = Habito.objects.get(personafichamedica=personafichamedica)
                        initial = model_to_dict(habito)
                        data['form'] = HabitoForm(initial=initial)
                    else:
                        data['form'] = HabitoForm()
                    data['paciente'] = pex.personafichamedica.personaextension.persona
                    return render(request, "box_medical/habitos.html", data)
                except Exception as ex:
                    pass

            elif action == 'consultanutricion':
                try:
                    persona = Persona.objects.get(pk=request.GET['id'])
                    data['title'] = u'Consultas nutrición - Paciente: ' + str(persona) + ' - ' + persona.identificacion()
                    data['paciente'] = persona
                    form = PersonaConsultaNutricionForm(initial={'fechaconsulta': datetime.now().date(), 'fecha': datetime.now().date(), 'hora': "12:00"})
                    tpac = persona.tipo_paciente()
                    form.tipos_paciente(tpac['tipoper'], tpac['regimen'])
                    if tpac['tipoper'] == 'ALU':
                        matri = persona.datos_ultima_matricula()
                        data['idmatricula'] = matri['idmatricula']
                    data['listaantropometria'] = Antropometria.objects.filter(status=True)
                    data['form'] = form
                    data['cita'] = request.GET['idc'] if 'idc' in request.GET else None
                    return render(request, "box_nutricion/consultanutricion.html", data)
                except Exception as ex:
                    pass

            elif action == 'buscarenfermedad':
                try:
                    q = request.GET['q'].upper().strip()
                    catalogo = CatalogoEnfermedad.objects.filter(descripcion__icontains=q, status=True).distinct()[:20]
                    data = {"result": "ok", "results": [{"id": c.id, "name": c.flexbox_repr()} for c in catalogo]}
                    return JsonResponse(data)
                except Exception as ex:
                    pass

            elif action == 'consultamedicaprevias':
                try:
                    data['title'] = u'Consultas nutrición previas'
                    data['paciente'] = persona = Persona.objects.get(pk=request.GET['id'])
                    # data['listaantropometria'] = Antropometria.objects.filter(status=True)
                    if 'idc' in request.GET:
                        data['consultas'] = PersonaConsultaNutricion.objects.filter(persona=persona, medico=data['persona'], id=request.GET['idc'])
                    else:
                        data['consultas'] = PersonaConsultaNutricion.objects.filter(persona=persona)
                    return render(request, "box_nutricion/consultanutricionprevias.html", data)
                except Exception as ex:
                    pass

            elif action == 'editconsultamedicaprevia':
                try:
                    data['consulta'] = consulta = PersonaConsultaMedica.objects.get(pk=request.GET['id'])
                    data['title'] = u'Editar consulta nutrición - Paciente: ' + str(consulta.persona) + ' - ' + consulta.persona.identificacion()
                    tipos = (consulta.tipopaciente, TIPO_PACIENTE[consulta.tipopaciente-1][1])

                    form = PersonaConsultaMedicaForm(initial={'grupo': consulta.pacientegrupo,
                                                              #'tipoatencion': consulta.tipoatencion,
                                                              'motivo': consulta.motivo,
                                                              'diagnostico': consulta.diagnostico,
                                                              'tratamiento': consulta.tratamiento,
                                                              'medicacion': consulta.medicacion,
                                                              'tipopaciente': consulta.tipopaciente})
                    form.editar(tipos)
                    data['form'] = form
                    data['paciente'] = consulta.persona
                    return render(request, "box_medical/editconsultamedicaprevia.html", data)
                except Exception as ex:
                    pass

            elif action == 'fichapdf':
                try:
                    data['ficha'] = ficha = PersonaFichaNutricion.objects.get(pk=request.GET['id'])
                    cumple = ficha.persona.nacimiento
                    today = datetime.now()
                    rectifier = datetime(today.year, cumple.month, cumple.day) >= today
                    data['edad'] = format(today.year - cumple.year - rectifier)
                    data['listadosintomas'] = SintomasAlimentario.objects.filter(status=True).order_by('id')
                    data['listadosintomasficha'] = ficha.sintomasfichanutricion_set.values_list('sintoma_id', flat=True).filter(activo=True, status=True)
                    data['listadocomidas'] = ficha.comidafichanutricion_set.filter(status=True).order_by('comida_id')
                    data['listadoconsumos'] = FrecuenciaConsumo.objects.filter(status=True).order_by('id')
                    data['listapruebas'] = ficha.pruebalaboratoriofichanutricion_set.filter(status=True).order_by('id')
                    data['consultas'] = consulta = PersonaConsultaNutricion.objects.filter(persona=ficha.persona).order_by('-id')
                    if consulta:
                        data['primeraconsulta'] = consulta.filter(status=True).order_by('fecha')[0]
                    return conviert_html_to_pdf(
                        'box_nutricion/fichapdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'controlpdf':
                try:
                    data['bar'] = BarUniversitario.objects.get(pk=request.GET['id'])
                    data['grupoalimentos'] = GrupoAlimento.objects.filter(status=True).order_by('id')
                    data['listadopreguntas'] = PreguntasBar.objects.filter(status=True).order_by('id')
                    return conviert_html_to_pdf(
                        'box_nutricion/controlpdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'controlresueltopdf':
                try:
                    data['control'] = control = ControlBarUniversitario.objects.get(pk=request.GET['id'])
                    data['grupoalimentos'] = control.conservacioncontrolbaruniversitario_set.filter(status=True).order_by('conservacion_id')
                    data['listadopreguntas'] = control.respuestacontrolbaruniversitario_set.filter(status=True).order_by('pregunta_id')
                    return conviert_html_to_pdf(
                        'box_nutricion/controlresueltopdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'listadobares':
                try:
                    data['title'] = u'Lista de bares'
                    data['listadobares'] = BarUniversitario.objects.filter(status=True)
                    return render(request, "box_nutricion/listadobares.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadocontrolbares':
                try:
                    data['title'] = u'Lista de bares'
                    data['bar'] = bar = BarUniversitario.objects.get(pk=request.GET['idbar'], status=True)
                    data['listadocontrolbares'] = bar.controlbaruniversitario_set.filter(status=True).order_by('fecha')
                    return render(request, "box_nutricion/listadocontrolbares.html", data)
                except Exception as ex:
                    pass

            elif action == 'datospaciente':
                try:
                    persona = Persona.objects.get(pk=request.GET['id'])
                    data['persona'] = persona
                    data['examenfisico'] = persona.datos_examen_fisico()
                    data['datosextension'] = persona.datos_extension()
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

                    template = get_template("box_nutricion/datospaciente.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": True, 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": False, "mensaje": f"Error: {ex}"})
            
            elif action == 'importaciondatos':
                try:
                    data['title'] = 'Importaciones'
                    filtro, search, url_vars = Q(status=True, importado=True, lleno=False), \
                                               request.GET.get('s', ''), f'&action={action}'

                    if search:
                        data['s'] = search
                        filtro = filtro_persona(search, filtro)
                        url_vars+=f'&s={search}'

                    personal = PersonaConsultaNutricion.objects.filter(filtro)
                    paging = MiPaginador(personal, 20)
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
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    request.session['viewnutricion'] = action
                    return render(request, "importaciones_nutricion.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'completarconsulta':
                try:
                    data['personaconsulta'] = consulta = PersonaConsultaNutricion.objects.get(id=encrypt_id(request.GET['id']))
                    form = CompletarConsultaNutricionForm(initial=model_to_dict(consulta))
                    catalogos = consulta.consultaenfermedad().values_list('enfermedad_id', flat=True)
                    form.fields['enfermedad'].queryset = CatalogoEnfermedad.objects.filter(id__in=catalogos)
                    form.fields['medico'].queryset = Persona.objects.filter(id=consulta.medico.id)
                    tpac = consulta.persona.tipo_paciente()
                    form.tipos_paciente(tpac['tipoper'], tpac['regimen'])
                    if tpac['tipoper'] == 'ALU':
                        matri = persona.datos_ultima_matricula()
                        data['idmatricula'] = matri['idmatricula']
                    data['form'] = form
                    data['id'] = consulta.id
                    data['seccionado'] = True
                    data['switchery'] = True
                    data['listaantropometria'] = Antropometria.objects.filter(status=True)
                    template = get_template('modal/formcompletarconsulta.html')
                    return JsonResponse({'result': True, 'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje':f'Error: {ex}'})

            elif action == 'buscarenfer':
                try:
                    q = request.GET['q'].upper().strip()
                    catalogo = CatalogoEnfermedad.objects.filter(descripcion__icontains=q, status=True).distinct()[:20]
                    resp = [{"id": c.id, "text": c.flexbox_repr()} for c in catalogo]
                    return JsonResponse(resp, safe=False)
                except Exception as ex:
                    pass

            elif action == 'antropometria':
                try:
                    data['title']='Antropometria'
                    filtro, search, url_vars = Q(status=True), \
                                               request.GET.get('s', ''), f'&action={action}'

                    if search:
                        data['s'] = search
                        filtro = filtro & (Q(nombre__icontains = search) |
                                           Q(slug__icontains = search))
                        url_vars += f'&s={search}'

                    personal = Antropometria.objects.filter(filtro)
                    paging = MiPaginador(personal, 20)
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
                    data['url_vars'] = url_vars
                    data['listado'] = page.object_list
                    request.session['viewnutricion'] = action
                    return render(request, "antropometrias.html", data)
                except Exception as ex:
                    messages.error(request, f'Error: {ex}')

            elif action == 'addantropometria':
                try:
                    data['form'] = AntropometriaForm()
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje':f'Error: {ex}'})

            elif action == 'editantropometria':
                try:
                    antropometria=Antropometria.objects.get(id=encrypt_id(request.GET['id']))
                    form = AntropometriaForm(initial=model_to_dict(antropometria))
                    data['id'] = antropometria.id
                    data['form'] = form
                    template = get_template('ajaxformmodal.html')
                    return JsonResponse({'result': True, 'data':template.render(data)})
                except Exception as ex:
                    return JsonResponse({'result': False, 'mensaje':f'Error: {ex}'})

            elif action == 'buscarpersonas':
                try:
                    resp = filtro_persona_select(request)
                    return HttpResponse(json.dumps({'status': True, 'results': resp}))
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            search, ids, filtro, url_vars = request.GET.get('s', ''),\
                                            request.GET.get('id', ''), \
                                            (Q(perfilusuario__administrativo__isnull=False)
                                            | Q(perfilusuario__inscripcion__isnull=False)
                                            | Q(perfilusuario__profesor__isnull=False)
                                            | (Q(perfilusuario__externo__isnull=False) & Q(tipopersona=1))
                                            & Q(status=True)), \
                                            f''
            consultas = PersonaConsultaNutricion.objects.values_list('id').filter(status=True)

            if search:
                data['s'] = search = request.GET['s']
                filtro = filtro & filtro_persona_principal(search, filtro)
                url_vars += f'&s={search}'
            elif ids:
                ids = request.GET['id']
                url_vars += f'&id={ids}'
                filtro = filtro & Q(id=ids)
            personal = Persona.objects.filter(filtro).distinct()
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


            totalgeneral = consultas.count()
            totalgeneralusuario = consultas.filter(usuario_creacion_id=persona.usuario.id).count()
            totalhoy = consultas.filter(fecha__date=datetime.now().date()).count()
            totalusuariohoy = consultas.filter(fecha__date=datetime.now().date(), usuario_creacion_id=persona.usuario.id).count()
            data['fecha'] = datetime.now().strftime('%Y-%m-%d')
            data['area'] = "Área nutrición"
            data['tipopacientes'] = TIPO_PACIENTE
            data['totalgeneral'] = totalgeneral
            data['totalgeneralusuario'] = totalgeneralusuario
            data['totalhoy'] = totalhoy
            data['totalusuariohoy'] = totalusuariohoy
            data['medico'] = persona.usuario
            data['esdirectordbu'] = persona.distributivopersona_set.filter(denominacionpuesto_id=600, estadopuesto_id=1, status=True).exists()
            codigos_facultad = PersonaConsultaNutricion.objects.values_list('matricula__inscripcion__coordinacion_id', flat=True).filter(status=True,  matricula__isnull=False,  tipopaciente=3).order_by('matricula__inscripcion__coordinacion_id').distinct()
            codigos_carrera = PersonaConsultaNutricion.objects.values_list('matricula__inscripcion__carrera_id', flat=True).filter(status=True,  matricula__isnull=False, tipopaciente=3).order_by('matricula__inscripcion__carrera_id').distinct()
            carreras = ','.join(str(c) for c in codigos_carrera)
            data['facultades'] = Coordinacion.objects.filter(status=True, excluir=False, pk__in=codigos_facultad).order_by('id')
            data['codigos_carrera'] = carreras
            request.session['viewnutricion'] = 'fichas'
            return render(request, "box_nutricion/view.html", data)