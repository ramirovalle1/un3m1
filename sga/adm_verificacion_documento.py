# -*- coding: UTF-8 -*-
import random
from datetime import datetime

import xlwt
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.aggregates import Avg
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from xlwt import *

from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante
from settings import HOMITIRCAPACIDADHORARIO, CALCULO_POR_CREDITO, NOTA_ESTADO_EN_CURSO, MATRICULACION_LIBRE
from sga.commonviews import adduserdata, conflicto_materias_seleccionadas
from sga.forms import SolicitudForm, ConfiguracionTerceraMatriculaForm
from sga.funciones import MiPaginador, log, generar_nombre, fechatope, variable_valor
from sga.models import SolicitudMatricula, SolicitudDetalle, AsignaturaMalla, Asignatura, Matricula, Materia, \
    AgregacionEliminacionMaterias, MateriaAsignada, \
    Coordinacion, TipoSolicitud, ConfiguracionTerceraMatricula, Inscripcion, ProfesorMateria, GruposProfesorMateria, \
    AlumnosPracticaMateria, PeriodoActulizacionHojaVida, PersonaEnfermedad, Persona
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_administrativo():
        return HttpResponseRedirect(f"/?info=Solo se permite perfiles administrativos")
    persona = request.session['persona']
    periodo = request.session['periodo']
    hoy = datetime.now().date()
    miscarreras = persona.mis_carreras()

    if request.method == 'POST':
        action = request.POST['action']

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Servicios de Verificación de Documentos'

                inscripciones = Inscripcion.objects

                #CONTADORES DE ARTISTAS
                artistas = inscripciones.filter(matricula__status=True,
                                                matricula__nivel__periodo=periodo,
                                                persona__artistapersona__isnull=False,
                                                persona__artistapersona__status=True,
                                                persona__artistapersona__vigente=1
                                                )
                negadosbecadosartistas = artistas.filter(persona__artistapersona__estadoarchivo__in=[3, 6])
                verificadosartistas = artistas.filter(persona__artistapersona__verificado=True)

                data['contarartitasnegadas'] = negadosbecadosartistas.count()
                data['contarartistasverificados'] = verificadosartistas.count()
                data['contarartistassolicitudes'] = artistas.exclude(
                    pk__in=negadosbecadosartistas | verificadosartistas).count()

                #CONTADORES DE BECADOS EXTERNOS
                becados = inscripciones.filter(matricula__status=True,
                                               matricula__nivel__periodo=periodo,
                                               persona__becapersona__isnull=False,
                                               persona__becapersona__status=True,
                                               )
                negadosbecados = becados.filter(persona__becapersona__estadoarchivo__in=[3, 6])
                verificadosbecados = becados.filter(persona__becapersona__verificado=True)
                data['contarbecadosnegadas'] = negadosbecados.count()
                data['contarbecadosverificados'] = verificadosbecados.count()
                data['contarbecadossolicitudes'] = becados.exclude(pk__in=negadosbecados | verificadosbecados).count()

                #CONTADORES DE DEPORTISTAS
                deportistas = inscripciones.filter(matricula__status=True,
                                                   matricula__nivel__periodo=periodo,
                                                   persona__deportistapersona__isnull=False,
                                                   persona__deportistapersona__status=True,
                                                   persona__deportistapersona__vigente=1)
                negadosdeportistas = deportistas.filter(
                    persona__deportistapersona__estadoarchivoevento__in=[3, 6],
                    persona__deportistapersona__estadoarchivoentrena__in=[3, 6]
                )
                verificadosdeportistas = deportistas.filter(persona__deportistapersona__verificado=True)
                data['contardeportistasnegadas'] = negadosdeportistas.count()
                data['contardeportistasverificados'] = verificadosdeportistas.count()
                data['contardeportistassolicitudes'] = deportistas.exclude(
                    pk__in=negadosdeportistas | verificadosdeportistas).count()

                #CONTADORES DE DISCAPACITADOS
                discapacitados = inscripciones.filter(matricula__status=True,
                                                      matricula__nivel__periodo=periodo,
                                                      persona__perfilinscripcion__tienediscapacidad=True)
                negadosdiscapacitados = discapacitados.filter(
                    persona__perfilinscripcion__estadoarchivodiscapacidad__in=[3, 6]
                )
                verificadosdiscapacitados = discapacitados.filter(persona__perfilinscripcion__verificadiscapacidad=True)
                data['contardiscapacitadosnegadas'] = negadosdiscapacitados.count()
                data['contardiscapacitadosverificados'] = verificadosdiscapacitados.count()
                data['contardiscapacitadossolicitudes'] = discapacitados.exclude(
                    pk__in=negadosdiscapacitados | verificadosdiscapacitados).count()

                #CONTADORES DE ETNIAS
                etnias = inscripciones.filter(matricula__status=True,
                                              matricula__nivel__periodo=periodo,
                                              persona__perfilinscripcion__raza__id__in=[1, 2, 4, 5])
                negadosetnias = etnias.filter(
                    persona__perfilinscripcion__estadoarchivoraza__in=[3, 6]
                )
                verificadosetnias = etnias.filter(persona__perfilinscripcion__verificaraza=True)
                data['contaretniasnegadas'] = negadosetnias.count()
                data['contaretniasverificados'] = verificadosetnias.count()
                data['contaretniassolicitudes'] = etnias.exclude(
                    pk__in=negadosetnias | verificadosetnias).count()

                #CONTADORES DE MIGRANTES
                migrantes = inscripciones.filter(matricula__status=True,
                                                 matricula__nivel__periodo=periodo,
                                                 persona__migrantepersona__isnull=False,
                                                 persona__migrantepersona__status=True)
                negadosmigrantes = migrantes.filter(
                    persona__migrantepersona__estadoarchivo__in=[3, 6]
                )
                verificadosmigrantes = etnias.filter(persona__migrantepersona__verificado=True)
                data['contarmigrantesnegadas'] = negadosmigrantes.count()
                data['contarmigrantesverificados'] = verificadosmigrantes.count()
                data['contarmigrantessolicitudes'] = migrantes.exclude(
                    pk__in=negadosmigrantes | verificadosmigrantes).count()

                # HOJAS DE VIDA
                periodos = PeriodoActulizacionHojaVida.objects.filter(status=True)
                data['contarperiodospendientes'] = periodos.filter(estado=0).count()
                data['contarperiodosaperturados'] = periodos.filter(estado=1).count()
                data['contarperiodoscerrados'] = periodos.filter(estado=2).count()

                # ENFERMEDADES
                ePersonaEnfermedades = PersonaEnfermedad.objects.filter(persona__id__in=inscripciones.values("persona__id").filter(matricula__status=True, matricula__nivel__periodo=periodo))
                # data['contarperiodospendientes'] = ePersonas = Persona.objects.filter(pk__in=ePersonaEnfermedades.values("persona__id"))
                data['contarenfermedadpendientes'] = ePersonaEnfermedades.filter(estadoarchivo__in=[1,4,5,6]).count()
                data['contarenfermedadaprobados'] = ePersonaEnfermedades.filter(estadoarchivo__in=[2]).count()
                data['contarenfermedadrechazados'] = ePersonaEnfermedades.filter(estadoarchivo__in=[3]).count()
                return render(request, "adm_verificacion_documento/view.html", data)
            except Exception as ex:
                return HttpResponseRedirect(f'/?info={ex.__str__()}')

