# -*- coding: UTF-8 -*-
import json
import os
from math import ceil

import PyPDF2
from datetime import time
from decimal import Decimal

import requests
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.shortcuts import render
import time as pausaparaemail
from xlwt import easyxf, XFStyle, Workbook
import random
from decorators import secure_module
from investigacion.forms import RegistroPropuestaProyectoInvestigacionForm, ContenidoProyectoInvestigacionForm, \
    PresupuestoProyectoInvestigacionForm, CronogramaActividadProyectoInvestigacionForm, ExternoForm, \
    FinalizaEdicionForm, InformeProyectoForm
from investigacion.funciones import coordinador_investigacion, director_posgrado
from investigacion.models import ProyectoInvestigacion, TipoRecursoPresupuesto, ProyectoInvestigacionInstitucion, \
    ProyectoInvestigacionIntegrante, ProyectoInvestigacionRecorrido, ProyectoInvestigacionItemPresupuesto, \
    TIPO_INTEGRANTE, ProyectoInvestigacionObjetivo, TipoResultadoCompromiso, ProyectoInvestigacionResultado, \
    ConvocatoriaProyecto, ConvocatoriaMontoFinanciamiento, ProyectoInvestigacionCronogramaActividad, \
    ProyectoInvestigacionCronogramaResponsable, ProyectoInvestigacionPasajeIntegrante, \
    ProyectoInvestigacionViaticoIntegrante, ProyectoInvestigacionActividadEvidencia, \
    ProyectoInvestigacionCronogramaEntregable, ProyectoInvestigacionHistorialArchivo, \
    ProyectoInvestigacionHistorialActividadEvidencia, ProyectoInvestigacionInforme, \
    ProyectoInvestigacionHistorialInforme, ProyectoInvestigacionInformeActividad, ProyectoInvestigacionInformeAnexo, ESTADO_EVALUACION_INTERNA_EXTERNA, EvaluacionProyecto, EvaluacionProyectoDetalle
from sagest.commonviews import obtener_estado_solicitud
from sagest.models import datetime, Banco, DistributivoPersona, UnidadMedida, ExperienciaLaboral, Producto
from settings import SITE_STORAGE, ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID
from sga.commonviews import adduserdata
from sga.funciones import MiPaginador, log, variable_valor, \
    convertir_fecha, remover_caracteres_tildes_unicode, cuenta_email_disponible, generar_nombre, email_valido, \
    validar_archivo, null_to_decimal, cuenta_email_disponible_para_envio, fechaletra_corta
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsaveqrcertificado, convert_html_to_pdf, conviert_html_to_pdf
from sga.models import CUENTAS_CORREOS, ActividadConvalidacionPPV, Profesor, Administrativo, Inscripcion, \
    TituloInstitucion, Externo, miinstitucion, Titulo, InstitucionEducacionSuperior, Pais, NivelTitulacion, \
    AreaConocimientoTitulacion, Persona, Titulacion, ArticuloPersonaExterna, PonenciaPersonaExterna, \
    LibroPersonaExterna, ProyectoInvestigacionPersonaExterna, Coordinacion, MESES_CHOICES, RedPersona, ModuloGrupo, Modulo
from django.template import Context
from django.template.loader import get_template

import time as ET

from sga.tasks import send_html_mail, conectar_cuenta
from sga.templatetags.sga_extras import encrypt

from django.core.cache import cache


@login_required(redirect_field_name='ret', login_url='/loginsga')
@transaction.atomic()
@secure_module
def view(request):
    data = {}
    adduserdata(request, data)
    data['persona'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    es_estudiante = perfilprincipal.es_estudiante()
    es_profesor = perfilprincipal.es_profesor()
    es_administrativo = perfilprincipal.es_administrativo()

    # es_evaluador_externo = persona.es_evaluador_externo_proyectos_investigacion()

    if not es_profesor and not es_administrativo:
        return HttpResponseRedirect("/?info=El Módulo está disponible para administrativos y docentes.")

    if request.method == 'POST':
        action = request.POST['action']

        if action == 'subirinforme':
            try:
                if not 'idinforme' in request.POST:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos"})

                informeproyecto = ProyectoInvestigacionInforme.objects.get(pk=int(encrypt(request.POST['idinforme'])))

                archivo = request.FILES['archivoinforme']
                descripcionarchivo = 'Archivo del informe firmado'
                tipoinforme = "avance" if informeproyecto.tipo == 1 else "final"

                # Validar el archivo
                resp = validar_archivo(descripcionarchivo, archivo, ['PDF'], '4MB')
                if resp['estado'] != "OK":
                    return JsonResponse({"result": "bad", "mensaje": resp["mensaje"]})

                archivo._name = generar_nombre("informeproyecto" + tipoinforme, archivo._name)

                # Guardo el archivo del informe
                informeproyecto.archivo = archivo
                informeproyecto.estado = 4
                informeproyecto.save(request)

                log(u'Agregó archivo del informe firmado: %s' % (informeproyecto), request, "add")
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                msg = ex.__str__()
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. [%s]" % msg})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'propuestas':
                try:
                    search = None
                    ids = None

                    convocatoria = ConvocatoriaProyecto.objects.get(pk=int(encrypt(request.GET['idc'])))

                    if 'id' in request.GET:
                        ids = request.GET['id']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, pk=int(encrypt(request.GET['id'])))
                    elif 's' in request.GET:
                        search = request.GET['s']
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True,  proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacionevaluador__tipo=2, proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacionevaluador__status=True, titulo__icontains=search)
                    else:
                        proyectos = ProyectoInvestigacion.objects.filter(convocatoria=convocatoria, status=True, proyectoinvestigacionevaluador__persona=persona, proyectoinvestigacionevaluador__tipo=2, proyectoinvestigacionevaluador__tipoproyecto=1, proyectoinvestigacionevaluador__status=True).order_by('-id')

                    paging = MiPaginador(proyectos, 25)
                    p = 1
                    try:
                        paginasesion = 1
                        if 'paginador' in request.session:
                            paginasesion = int(request.session['paginador'])
                        if 'page' in request.GET:
                            p = int(request.GET['page'])
                        else:
                            p = paginasesion
                        try:
                            page = paging.page(p)
                        except:
                            p = 1
                        page = paging.page(p)
                    except:
                        page = paging.page(p)
                    request.session['paginador'] = p
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['search'] = search if search else ""
                    data['ids'] = ids if ids else ""
                    data['proyectos'] = page.object_list
                    data['evaluacionvigente'] = convocatoria.evaluacion_externa_abierta()
                    data['title'] = u'Propuestas de Proyectos de Investigación'
                    data['tituloconvocatoria'] = convocatoria.descripcion if convocatoria else ''
                    data['idconvocatoria'] = convocatoria.id

                    return render(request, "eva_proyectoinvestigacion/propuestas.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Gestión de Investigación'
                GESTION_INVESTIGACION_ID = 371
                if es_estudiante:
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=[ALUMNOS_GROUP_ID]).distinct()
                    modulosEnCache = cache.get(f"modulos__{ALUMNOS_GROUP_ID}")
                    if modulosEnCache:
                        modulos = modulosEnCache
                    else:
                        modulos = Modulo.objects.filter(Q(modulogrupo__in=misgrupos), activo=True).order_by('nombre')
                        cache.set(f"modulos__{ALUMNOS_GROUP_ID}", modulos, 60 * 60 * 12)
                    modulos = modulos.values("id", "url", "icono", "nombre", "descripcion").order_by('nombre')
                    frolvacio = Q(roles__isnull=True) | Q(roles='')
                    inscripcion_principal = perfilprincipal.inscripcion
                    coordinacion_principal = inscripcion_principal.coordinacion_id

                    if coordinacion_principal == 9:
                        # Mostrar modulos  para la coordinación de Admisión
                        data['mismodulos'] = modulos.filter(frolvacio | Q(roles__icontains=1)).distinct()
                    elif coordinacion_principal == 7:
                        # Mostrar modulos  para la coordinación de Postgrado
                        data['mismodulos'] = modulos.filter(frolvacio | Q(roles__icontains=3)).distinct()
                    else:
                        # Mostrar modulos  para la coordinación de Pregado
                        data['mismodulos'] = modulos.filter(frolvacio | Q(roles__icontains=2)).distinct()

                elif es_profesor:
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=[PROFESORES_GROUP_ID]).distinct()
                    data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos) | Q(id=MODULO_EVALUACION_PARESDIRECTIVOS_ID), activo=True).distinct().order_by('nombre')
                    grupos = persona.usuario.groups.filter(id__in=[PROFESORES_GROUP_ID])

                elif perfilprincipal.es_instructor():
                    print("None")
                    # misgrupos = ModuloGrupo.objects.filter(grupos__id__in=[INSTRUCTOR_GROUP_ID]).distinct()
                    # data['mismodulos'] = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(Q(modulogrupo__in=misgrupos), activo=True).distinct().order_by('nombre')
                    # grupos = persona.usuario.groups.filter(id__in=[variable_valor('INSTRUCTOR_GRUPO_ID')])
                else:
                    misgrupos = ModuloGrupo.objects.filter(grupos__in=persona.usuario.groups.all()).exclude(grupos__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID]).distinct()

                    misgrupos = misgrupos.filter(grupos__id=GESTION_INVESTIGACION_ID).distinct()

                    modulos = Modulo.objects.values("id", "url", "icono", "nombre", "descripcion").filter(modulogrupo__in=misgrupos, activo=True).distinct().order_by('nombre')
                    # if data['tiposistema'] == 'sga':
                    #     modulos = modulos.filter(sga=True).distinct().order_by('nombre')
                    # elif data['tiposistema'] == 'sagest':
                    #     modulos = modulos.filter(sagest=True).distinct().order_by('nombre')
                    # elif data['tiposistema'] == 'posgrado':
                    #     modulos = modulos.filter(posgrado=True).distinct().order_by('nombre')
                    # elif data['tiposistema'] == 'seleccionposgrado':
                    #     modulos = modulos.filter(postulacionposgrado=True).distinct().order_by('nombre')
                    # elif data['tiposistema'] == 'postulate':
                    #     modulos = modulos.filter(postulate=True).distinct().order_by('nombre')
                    #     data['mismodulos'] = modulos
                    #     grupos = persona.usuario.groups.exclude(id__in=[ALUMNOS_GROUP_ID, PROFESORES_GROUP_ID])

                data['modulos2'] = modulos
                return render(request, "inv_investigacion/panel.html", data)
            except Exception as ex:
                pass


