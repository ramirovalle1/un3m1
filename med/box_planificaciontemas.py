# -*- coding: latin-1 -*-
import os
import random
from datetime import datetime, time, date
import json
import xlwt
from django.contrib.auth.decorators import login_required
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
    ConsumoFichaNutricionForm, ControlBarNutricionForm, PlanificacionTemaForm, CursoTemasPlanificacionForm
from med.models import PersonaExamenFisico, PersonaConsultaMedica, \
    IndicadorSobrepeso, ProximaCita, PatologicoFamiliar, PatologicoPersonal, PatologicoQuirurgicos, \
    AntecedenteTraumatologicos, AntecedenteGinecoobstetrico, Habito, InspeccionSomatica, InspeccionTopografica, \
    Rutagrama, PersonaExtension, PersonaFichaMedica, TIPO_PACIENTE, PersonaConsultaOdontologica, \
    PersonaConsultaPsicologica, Vacuna, Enfermedad, Alergia, Medicina, CatalogoEnfermedad, SintomasAlimentario, \
    FrecuenciaConsumo, FRECUENCIACONSUMO, Antropometria, PersonaConsultaNutricion, ConsultaNutricionAntropometria, \
    PersonaFichaNutricion, ComidaFichaNutricion, Comidas, PruebaLaboratorioFichaNutricion, SintomasFichaNutricion, \
    ConsumoFichaNutricion, EnfermedadPersonaConsultaNutricion, BarUniversitario, GrupoAlimento, PreguntasBar, \
    ControlBarUniversitario, TIPO_CONSERVACION, ConservacionControlBarUniversitario, RespuestaControlBarUniversitario, \
    TemasPlanificacion, CursoTemasPlanificacion, ParticipantesCursoTemasPlanificacion
from sagest.models import Jornada, DistributivoPersona
from settings import SITE_STORAGE
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, convertir_fecha, calcula_edad
from sga.models import Persona, Matricula, Inscripcion, Nivel, Carrera, Paralelo, NivelMalla, MateriaAsignada
from sga.funcionesxhtml2pdf import conviert_html_to_pdf


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

        if action == 'addplanificaciontema':
            try:
                f = PlanificacionTemaForm(request.POST)
                if f.is_valid():
                    tema = TemasPlanificacion(tema=f.cleaned_data['tema'],
                                              objetivo=f.cleaned_data['objetivo'])
                    tema.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'editplanificaciontema':
            try:
                tema = TemasPlanificacion.objects.get(pk=request.POST['id'])
                f = PlanificacionTemaForm(request.POST)
                if f.is_valid():
                    tema.tema = f.cleaned_data['tema']
                    tema.objetivo = f.cleaned_data['objetivo']
                    tema.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'delplanificaciontema':
            try:
                tema = TemasPlanificacion.objects.get(pk=request.POST['id'])
                tema.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        elif action == 'delparticipantes':
            try:
                curso = CursoTemasPlanificacion.objects.get(pk=request.POST['id'])
                curso.delete()
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar los datos."})

        if action == 'niveles':
            try:
                niveles = Nivel.objects.filter(nivellibrecoordinacion__coordinacion_id=request.POST['id'], periodo_id=90, modalidad_id__in=[1,2])
                lista = []
                for niv in niveles:
                    lista.append([niv.id, niv.sesion.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'carrerasnivel':
            try:
                niveles = Nivel.objects.get(pk=request.POST['id'])
                listadocarreras = Carrera.objects.filter(id__in=niveles.coordinacion().carrera.filter(modalidad__in=[1,2] ,status=True), modalidad__in=[1,2])
                lista = []
                for car in listadocarreras:
                    mencion = ''
                    if car.mencion:
                        mencion = 'MENCION '+ car.mencion
                    lista.append([car.id, car.nombre + ' ' + mencion])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'paralelosnivel':
            try:
                niveles = Nivel.objects.get(pk=request.POST['codnivel'])
                listadoparalelos = Paralelo.objects.filter(nombre__in=niveles.materia_set.values_list('paralelo', flat=True).filter(status=True, asignaturamalla__malla__carrera_id=request.POST['id']).distinct(), status=True)
                lista = []
                for par in listadoparalelos:
                    lista.append([par.id, par.nombre])
                return JsonResponse({'result': 'ok', 'lista': lista})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'ver_alumnos':
            try:
                data = {}
                paralelo = Paralelo.objects.get(pk=request.POST['id'])
                data['nivel'] = nivel = Nivel.objects.get(pk=request.POST['idnivel'])
                nivelmalla = NivelMalla.objects.get(pk=request.POST['idnivelmalla'])
                data['matriculas'] = Matricula.objects.filter(pk__in=MateriaAsignada.objects.values_list('matricula_id').filter(materia__nivel=nivel, materia__asignaturamalla__nivelmalla=nivelmalla, materia__asignaturamalla__malla__carrera_id=request.POST['idcarrera'], materia__paralelo__icontains=paralelo.nombre).distinct()).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2')
                template = get_template("box_planificaciontemas/ver_alumnos.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        elif action == 'addplanificacioncurso':
            try:
                tema = TemasPlanificacion.objects.get(pk=request.POST['id'], status=True)
                f = CursoTemasPlanificacionForm(request.POST)
                if f.is_valid():
                    lista_items1 = json.loads(request.POST['lista_items1'])
                    curso = CursoTemasPlanificacion(tema=tema,
                                                    coordinacion=f.cleaned_data['coordinacion'],
                                                    carrera=f.cleaned_data['carrera'],
                                                    nivelmalla=f.cleaned_data['semestre'],
                                                    paralelo=f.cleaned_data['paralelo'],
                                                    fecha=f.cleaned_data['fecha'],
                                                    nivel=f.cleaned_data['nivel'])
                    curso.save(request)
                    if lista_items1:
                        for lista in lista_items1:
                            conservacion = ParticipantesCursoTemasPlanificacion(curso=curso,
                                                                                matricula_id=lista['codmatri'])
                            conservacion.save(request)
                    return JsonResponse({"result": "ok"})
                else:
                    raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        elif action == 'changetieneasistencia':
            try:
                participante = ParticipantesCursoTemasPlanificacion.objects.get(pk=request.POST['idparti'])
                if participante.asistencia:
                    participante.asistencia = False
                else:
                    participante.asistencia = True
                participante.save(request)
                return JsonResponse({'result': 'ok', 'valor': participante.asistencia})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addplanificaciontema':
                try:
                    data['title'] = u'Planificación de temas'
                    form = PlanificacionTemaForm()
                    data['form'] = form
                    return render(request, "box_planificaciontemas/addplanificaciontema.html", data)
                except Exception as ex:
                    pass

            if action == 'addplanificacioncurso':
                try:
                    data['title'] = u'Planificación de curso'
                    data['tema'] = TemasPlanificacion.objects.get(pk=request.GET['idtema'], status=True)
                    form = CursoTemasPlanificacionForm()
                    form.adicionar()
                    data['form'] = form
                    return render(request, "box_planificaciontemas/addplanificacioncurso.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoplanificacion':
                try:
                    data['title'] = u'Lista de planificaciones'
                    data['tema'] = tema = TemasPlanificacion.objects.get(pk=request.GET['idtema'], status=True)
                    data['listacursos'] = tema.cursotemasplanificacion_set.filter(status=True).order_by('-fecha')
                    return render(request, "box_planificaciontemas/listadoplanificacion.html", data)
                except Exception as ex:
                    pass

            elif action == 'listadoparticipantes':
                try:
                    data['title'] = u'Lista de participantes'
                    data['cursotema'] = cursotema = CursoTemasPlanificacion.objects.get(pk=request.GET['idcurso'], status=True)
                    data['listadoparticipantes'] = cursotema.participantescursotemasplanificacion_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return render(request, "box_planificaciontemas/listadoparticipantes.html", data)
                except Exception as ex:
                    pass

            elif action == 'imprimirpdf':
                try:
                    data['curso'] = curso = CursoTemasPlanificacion.objects.get(pk=request.GET['idcurso'])
                    data['listaparticipantes'] = curso.participantescursotemasplanificacion_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1', 'matricula__inscripcion__persona__apellido2')
                    return conviert_html_to_pdf(
                        'box_planificaciontemas/imprimirpdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass

            elif action == 'editplanificaciontema':
                try:
                    data['title'] = u'Editar planificación tema'
                    data['tema'] = tema = TemasPlanificacion.objects.get(pk=request.GET['id'])
                    data['form'] = PlanificacionTemaForm(initial={'tema': tema.tema,
                                                                  'objetivo': tema.objetivo})
                    return render(request, "box_planificaciontemas/editplanificaciontema.html", data)
                except Exception as ex:
                    pass

            elif action == 'delplanificaciontema':
                try:
                    data['title'] = u'Eliminar planificación tema'
                    data['tema'] = TemasPlanificacion.objects.get(pk=request.GET['idtema'])
                    return render(request, "box_planificaciontemas/delplanificaciontema.html", data)
                except Exception as ex:
                    pass

            elif action == 'delparticipantes':
                try:
                    data['title'] = u'Eliminar curso'
                    data['curso'] = CursoTemasPlanificacion.objects.get(pk=request.GET['idcurso'])
                    return render(request, "box_planificaciontemas/delparticipantes.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Planificación tema'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                ss = search.split(' ')
                while '' in ss:
                    ss.remove('')
                if len(ss) == 1:
                    personal = TemasPlanificacion.objects.filter(Q(tema__icontains=search) |
                                                                 Q(objetivo__icontains=search),status=True).distinct()
                else:
                    personal = TemasPlanificacion.objects.filter(Q(tema__icontains=search) |
                                                                 Q(objetivo__icontains=search),status=True).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                personal = TemasPlanificacion.objects.filter(id=ids)
            else:
                personal = TemasPlanificacion.objects.filter(status=True)
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
            data['temasplanificacion'] = page.object_list
            data['fecha'] = datetime.now().strftime('%d-%m-%Y')
            data['tipopacientes'] = TIPO_PACIENTE
            data['medico'] = persona.usuario
            return render(request, "box_planificaciontemas/view.html", data)