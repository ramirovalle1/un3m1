import json
import sys
from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Q, Value, Sum
from django.db.models.aggregates import Min
from django.db.models.functions import Coalesce, ExtractYear
from django.forms import model_to_dict
from django.shortcuts import render, redirect

from django.core.cache import cache
from decorators import secure_module, last_access
from posgrado.forms import PreguntaSeguimientoGraduadoForm, PeriodoEncuestaForm, GrupoEncuestaForm, \
    DatosDataGraduadoForm, PersonaNuevaDatosDataGraduadoForm
from posgrado.models import SagPosgradoPregunta, SagPosgradoPeriodo, SagPosgradoEncuesta, SagPosgradoEncuestaCarrera, \
    PersonaDataPosgradoPrograma, PersonaDataPosgrado
from sga.commonviews import adduserdata
from django.http import JsonResponse,HttpResponseRedirect
from django.template.loader import get_template
from sga.funciones import log, MiPaginador
from collections import defaultdict

from sga.models import Graduado, Carrera, Inscripcion, TemaTitulacionPosgradoMatricula, AsignaturaMalla
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    hoy = datetime.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year
    data['personasesion'] = persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'add_pregunta':
                try:
                    form = PreguntaSeguimientoGraduadoForm(request.POST)
                    if form.is_valid():
                        eSagPosgradoPregunta = SagPosgradoPregunta(
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                        )
                        eSagPosgradoPregunta.save(request)

                        log(u'Agregó nueva pregunta  %s' % eSagPosgradoPregunta, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'edit_pregunta':
                try:
                    form = PreguntaSeguimientoGraduadoForm(request.POST)
                    id = int(request.POST['id'])
                    eSagPosgradoPregunta = SagPosgradoPregunta.objects.get(pk=id)
                    if form.is_valid():
                        eSagPosgradoPregunta.nombre = form.cleaned_data['nombre']
                        eSagPosgradoPregunta.descripcion = form.cleaned_data['descripcion']
                        eSagPosgradoPregunta.save(request)
                        log(u'Edito pregunta %s' % eSagPosgradoPregunta, request,  "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "message": f"Error: {ex.__str__()}"})

            elif action == 'eliminar_pregunta':
                try:
                    eSagPosgradoPregunta = SagPosgradoPregunta.objects.get(pk=int(request.POST['id']))
                    eSagPosgradoPregunta.status = False
                    eSagPosgradoPregunta.save(request)
                    log(f"Eliminó pregunta:{eSagPosgradoPregunta}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_periodoencuesta':
                try:
                    form = PeriodoEncuestaForm(request.POST)
                    if form.is_valid():
                        eSagPosgradoPeriodo = SagPosgradoPeriodo(
                            anio=form.cleaned_data['anio'],
                            tipoperiodo=form.cleaned_data['tipo'],
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                            fechainicio=form.cleaned_data['fechaInicio'],
                            fechafin=form.cleaned_data['fechaFin'],
                            estado=form.cleaned_data['estado'],
                        )
                        eSagPosgradoPeriodo.save(request)

                        log(u'Agregó nuevo periodo de encuedta  %s' % eSagPosgradoPeriodo, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'edit_periodo_encuesta':
                try:
                    id = int(request.POST['id'])
                    eSagPosgradoPeriodo = SagPosgradoPeriodo.objects.get(pk=id)
                    form = PeriodoEncuestaForm(request.POST)
                    if form.is_valid():
                        eSagPosgradoPeriodo.anio=form.cleaned_data['anio']
                        eSagPosgradoPeriodo.tipoperiodo=form.cleaned_data['tipo']
                        eSagPosgradoPeriodo.nombre=form.cleaned_data['nombre']
                        eSagPosgradoPeriodo.descripcion=form.cleaned_data['descripcion']
                        eSagPosgradoPeriodo.fechainicio=form.cleaned_data['fechainicio']
                        eSagPosgradoPeriodo.fechafin=form.cleaned_data['fechafin']
                        eSagPosgradoPeriodo.estado=form.cleaned_data['estado']
                        eSagPosgradoPeriodo.save(request)

                        log(u'Edito periodo  encuesta  %s' % eSagPosgradoPeriodo, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                    return JsonResponse(res_js)

            elif action == 'eliminar_periodo_encuesta':
                try:
                    eSagPosgradoPeriodo = SagPosgradoPeriodo.objects.get(pk=int(request.POST['id']))
                    eSagPosgradoPeriodo.status = False
                    eSagPosgradoPeriodo.save(request)
                    log(f"Eliminó periodo encuesta:{eSagPosgradoPeriodo}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'add_grupoencuesta':
                try:
                    form = GrupoEncuestaForm(request.POST)
                    eSagPosgradoPeriodo = SagPosgradoPeriodo.objects.get(pk=int(encrypt(request.POST['id'])))
                    if form.is_valid():
                        eSagPosgradoEncuesta = SagPosgradoEncuesta(
                            sagposgradoperiodo=eSagPosgradoPeriodo,
                            nombre=form.cleaned_data['nombre'],
                            descripcion=form.cleaned_data['descripcion'],
                            orden=form.cleaned_data['orden'],
                        )
                        eSagPosgradoEncuesta.save(request)

                        log(u'Agregó nuevo grupo de encuesta %s' % eSagPosgradoEncuesta, request, "add")
                    else:
                        return JsonResponse({"result": False, "message": f"Error al validar los datos.", "form": [{key: value[0]} for key, value in form.errors.items()]})
                    res_js = {'result': True}
                except Exception as ex:
                    transaction.set_rollback(True)
                    err = 'Error on line {}'.format(sys.exc_info()[-1].tb_lineno)
                    msg_err = f"Ocurrio un error: {ex.__str__()}. {err}"
                    res_js = {'result': False, 'message': msg_err}
                return JsonResponse(res_js)

            elif action == 'eliminar_grupoencuesta':
                try:
                    eSagPosgradoEncuesta = SagPosgradoEncuesta.objects.get(pk=int(request.POST['id']))
                    eSagPosgradoEncuesta.status = False
                    eSagPosgradoEncuesta.save(request)
                    log(f"Eliminó grupo encuesta:{eSagPosgradoEncuesta}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})

            elif action == 'asignar_quitar_carrera_encuesta':
                try:
                    eSagPosgradoEncuesta = SagPosgradoEncuesta.objects.get(pk=int(request.POST['eSagPosgradoEncuestaPk']))
                    pk_carrera = request.POST['pk_carrera']
                    if request.POST['activar'] == 'true':
                        eSagPosgradoEncuestaCarrera = SagPosgradoEncuestaCarrera(
                            sagposgradoencuesta = eSagPosgradoEncuesta,
                            carrera_id = pk_carrera
                        )
                        eSagPosgradoEncuestaCarrera.save(request)
                        log(f"agrego carrera a  encuesta:{eSagPosgradoEncuesta}", request, 'add')
                    else:
                        eSagPosgradoEncuestaCarrera = SagPosgradoEncuestaCarrera.objects.filter(status=True, sagposgradoencuesta=eSagPosgradoEncuesta,carrera_id =pk_carrera )
                        eSagPosgradoEncuestaCarrera.update(status=False)
                        log(f"Eliminó carrera de la encuesta:{eSagPosgradoEncuesta}", request, 'del')
                    return JsonResponse({"result": True, "error": False})
                except Exception as ex:
                    transaction.rollback()
                    return JsonResponse({"result": "bad", "mensaje": f"Error: {ex.__str__()}"})


    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action == 'configuraciones':
                try:
                    data['title'] = f'Configuraciones Seguimiento a Graduados Posgrado'
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 0
                    return render(request, "seguimientograduado/configuraciones/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/seguimientograduadoposgrado")

            elif action == 'configuraciones_pregunta':
                try:
                    data['title'] = f"Preguntas"
                    data['menu_principal'] = 1
                    data['menu_configuracion'] = 1
                    filtro = Q(status=True)
                    url_vars = f'&action=configuraciones_pregunta'
                    eSagPosgradoPreguntas = SagPosgradoPregunta.objects.filter(filtro)
                    paging = MiPaginador(eSagPosgradoPreguntas, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["eSagPosgradoPreguntas"] = page.object_list
                    return render(request, "seguimientograduado/configuraciones/preguntas/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/seguimientograduado")

            elif action == 'add_pregunta':
                try:
                    form = PreguntaSeguimientoGraduadoForm()
                    data['form'] = form
                    template = get_template('seguimientograduado/modalForm.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_pregunta':
                try:

                    data['id'] = id = int(request.GET['id'])
                    eSagPosgradoPregunta = SagPosgradoPregunta.objects.get(pk=id)
                    form = PreguntaSeguimientoGraduadoForm(initial=model_to_dict(eSagPosgradoPregunta))
                    data['form'] = form
                    template = get_template('seguimientograduado/modalForm.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'datagraduadosposgrado':
                try:
                    data['title'] = f'Recopilación de Graduados de Posgrado'
                    data['menu_principal'] = 2
                    url_vars = f'&action=datagraduadosposgrado'
                    search = None
                    ePersonaDataPosgrados = PersonaDataPosgrado.objects.filter(status=True)
                    paging = MiPaginador(ePersonaDataPosgrados, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["ePersonaDataPosgrados"] = page.object_list
                    return render(request, "seguimientograduado/graduados/view.html", data)
                except Exception as ex:
                    messages.error(request, f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}')
                    return HttpResponseRedirect(f"/seguimientograduadoposgrado")

            elif action == 'periodo_encuestas':
                try:
                    data['title'] = f'Seguimiento a graduados - Encuestas'
                    data['menu_principal'] = 3

                    filtro = Q(status=True)
                    url_vars = f'&action=encuestas'
                    eSagPosgradoPeriodos= SagPosgradoPeriodo.objects.filter(filtro)
                    paging = MiPaginador(eSagPosgradoPeriodos, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["eSagPosgradoPeriodos"] = page.object_list
                    return render(request, "seguimientograduado/encuestas/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/seguimientograduadoposgrado")

            elif action == 'add_periodoencuesta':
                try:
                    form = PeriodoEncuestaForm(initial={'anio': anio_actual})
                    data['form'] = form
                    template = get_template('seguimientograduado/modalForm.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'edit_periodo_encuesta':
                try:

                    data['id'] = id = int(request.GET['id'])
                    eSagPosgradoPregunta = SagPosgradoPregunta.objects.get(pk=id)
                    form = PreguntaSeguimientoGraduadoForm(initial=model_to_dict(eSagPosgradoPregunta))
                    data['form'] = form
                    template = get_template('seguimientograduado/modalForm.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action =='grupoencuestas':
                try:
                    data['title'] = f'Personalización de encuesta'
                    data['menu_principal'] = 3
                    url_vars = f'&action=grupoencuestas'
                    id = int(request.GET['id'])
                    eSagPosgradoPeriodo= SagPosgradoPeriodo.objects.get(pk=id)
                    filtro = Q(status=True, sagposgradoperiodo_id=eSagPosgradoPeriodo.pk)
                    eSagPosgradoEncuestas = SagPosgradoEncuesta.objects.filter(filtro)

                    paging = MiPaginador(eSagPosgradoEncuestas, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["eSagPosgradoEncuestas"] = page.object_list
                    data["eSagPosgradoPeriodo"] =eSagPosgradoPeriodo
                    return render(request, "seguimientograduado/encuestas/grupoencuesta/view.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/seguimientograduadoposgrado?action=periodo_encuestas")

            elif action =='grupoencuestas_carreras':
                try:
                    data['title'] = f'Programas aplicados a la encuesta'
                    data['menu_principal'] = 3
                    url_vars = f'&action=grupoencuestas_carreras'
                    id = int(request.GET['id'])
                    eSagPosgradoEncuesta= SagPosgradoEncuesta.objects.get(pk=id)
                    filtro = Q(status=True, sagposgradoencuesta_id=eSagPosgradoEncuesta.pk)
                    eSagPosgradoEncuestaCarreras = SagPosgradoEncuestaCarrera.objects.filter(filtro)
                    data["eCarreras"] = Carrera.objects.filter(status=True, coordinacion__id=7).exclude( pk__in=eSagPosgradoEncuestaCarreras.values_list('carrera_id',flat=True))
                    paging = MiPaginador(eSagPosgradoEncuestaCarreras, 25)
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
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data["url_vars"] = url_vars
                    data["eSagPosgradoEncuestaCarreras"] = page.object_list
                    data["eSagPosgradoEncuesta"] =eSagPosgradoEncuesta

                    return render(request, "seguimientograduado/encuestas/grupoencuesta/carrerasview.html", data)
                except Exception as ex:
                    return HttpResponseRedirect(f"/seguimientograduadoposgrado?action=periodo_encuestas")


            elif action == 'add_grupoencuesta':
                try:
                    form = GrupoEncuestaForm()
                    data['id'] = int(request.GET['id'])
                    data['form'] = form
                    template = get_template('seguimientograduado/modalForm.html')
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

        else:
            try:
                data['title'] = f'Seguimiento a graduados'
                data['menu_principal'] = 0
                return render(request, "seguimientograduado/view.html", data)
            except Exception as ex:
                pass


@transaction.atomic()
def view_actualizadato(request):
    from sga.models import Persona
    from posgrado.models import PersonaDataPosgrado
    data = {}
    hoy = datetime.now().date()
    mes_actual = hoy.month
    anio_actual = hoy.year

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'segmento':
                try:
                    datospersona = None
                    tipoiden = int(request.POST['tipoiden'])
                    documento = request.POST['cedula'].strip()
                    fechanacimiento = request.POST['fechanacimiento'].strip()
                    if Persona.objects.filter(cedula=documento, status=True,nacimiento=fechanacimiento).exists():
                        datospersona = Persona.objects.filter(cedula=documento, status=True,nacimiento=fechanacimiento).first()
                    if Persona.objects.filter(pasaporte=documento, status=True,nacimiento=fechanacimiento).exists():
                        datospersona = Persona.objects.filter(pasaporte=documento, status=True,nacimiento=fechanacimiento).first()
                    if Persona.objects.filter(ruc=documento, status=True,nacimiento=fechanacimiento).exists():
                        datospersona = Persona.objects.filter(ruc=documento,nacimiento=fechanacimiento, status=True).first()
                    if not datospersona:
                        eCarreras = Carrera.objects.filter(status=True,coordinacion__id=7)
                        if not PersonaDataPosgrado.objects.filter(status=True,cedula = documento).exists() or  Persona.objects.filter(cedula=documento, status=True).exists() or Persona.objects.filter(pasaporte=documento, status=True).exists() or Persona.objects.filter(ruc=documento,status=True).exists():
                            form = PersonaNuevaDatosDataGraduadoForm()
                            data['form'] = form
                            data['eCarreras'] = eCarreras
                            # no existe registro de esta persona de graduado
                            template = get_template( "seguimientograduado/actualizadatograduado/registrarnuevapersona.html")
                        else:
                            ePersonaDataPosgrado = PersonaDataPosgrado.objects.filter(status=True, cedula=documento).first()
                            data['ePersonaDataPosgrado'] = ePersonaDataPosgrado
                            form = PersonaNuevaDatosDataGraduadoForm(initial={
                                'pais': ePersonaDataPosgrado.pais,
                                'provincia': ePersonaDataPosgrado.provincia,
                                'canton': ePersonaDataPosgrado.canton,
                                'parroquia': ePersonaDataPosgrado.parroquia,
                                'ciudadela': ePersonaDataPosgrado.ciudadela,
                                'sector': ePersonaDataPosgrado.sector,
                                'zona': ePersonaDataPosgrado.zona,
                                'direccion': ePersonaDataPosgrado.direccion,
                                'direccion2': ePersonaDataPosgrado.direccion2,
                                'num_direccion': ePersonaDataPosgrado.num_direccion,
                                'referencia': ePersonaDataPosgrado.referencia,
                                'telefono': ePersonaDataPosgrado.telefono,
                                'telefono_conv': ePersonaDataPosgrado.telefono_conv,
                                'email': ePersonaDataPosgrado.email,
                            })
                            data['form'] = form
                            programas_posgrados = ePersonaDataPosgrado.get_programas_posgrados().values('carrera', 'fechagraduado')
                            # Usamos map para convertir las fechas a strings
                            programas_list = list(map(lambda programa: {
                                'carrera': programa['carrera'],
                                'fechagraduado': programa['fechagraduado'].strftime('%Y-%m-%d') if programa['fechagraduado'] else None
                            }, programas_posgrados))

                            # Serializamos la lista a JSON
                            data['programa_json'] =json.dumps(programas_list)
                            template = get_template("seguimientograduado/actualizadatograduado/editarrnuevapersona.html")



                    else:
                        # solo estudiantes de posgrado ingresan al formulario
                        if Inscripcion.objects.filter(status=True,persona = datospersona,coordinacion_id=7).exists():
                            data['datospersona'] = datospersona

                            if Graduado.objects.filter(status=True,inscripcion__persona = datospersona,inscripcion__coordinacion_id=7).exists():
                                #si esta graduado y en el sistema
                                data['eInscripciones'] = eInscripciones = Inscripcion.objects.filter(status=True,pk__in=Graduado.objects.filter(status=True,inscripcion__persona = datospersona,inscripcion__coordinacion_id=7).values_list('inscripcion',flat=True),coordinacion_id=7)
                                eGraduados = Graduado.objects.filter(status=True,inscripcion__in = eInscripciones,inscripcion__coordinacion_id=7)
                                def consultar_fecha_graduado(eGraduado):
                                    fechagraduado = PersonaDataPosgradoPrograma.objects.filter(status=True,inscripcion =eGraduado.inscripcion,carrera = eGraduado.inscripcion.carrera).first().fechagraduado if PersonaDataPosgradoPrograma.objects.filter(status=True,inscripcion =eGraduado.inscripcion,carrera = eGraduado.inscripcion.carrera).exists() else None
                                    return {
                                        'id':eGraduado.id,
                                        'fechagraduado':eGraduado.fechagraduado if eGraduado.fechagraduado else fechagraduado,
                                        'consta_en_graduado': True if eGraduado.fechagraduado else False,
                                        'inscripcion':eGraduado.inscripcion,
                                    }

                                estructura_graduado = list(filter(None, map(lambda eGraduado: consultar_fecha_graduado(eGraduado) , eGraduados)))
                                data['eGraduados'] =estructura_graduado
                                data['form'] = form =DatosDataGraduadoForm(initial={
                                    'pais':datospersona.pais,
                                    'provincia':datospersona.provincia,
                                    'canton':datospersona.canton,
                                    'parroquia':datospersona.parroquia,
                                    'ciudadela':datospersona.ciudadela,
                                    'sector':datospersona.sector,
                                    'zona':datospersona.zona,
                                    'direccion':datospersona.direccion,
                                    'direccion2':datospersona.direccion2,
                                    'num_direccion':datospersona.num_direccion,
                                    'referencia':datospersona.referencia,
                                    'telefono':datospersona.telefono,
                                    'telefono_conv':datospersona.telefono_conv,
                                    'email':datospersona.email,
                                })
                                template = get_template("seguimientograduado/actualizadatograduado/actualizardatosgraduado.html")
                            else:
                                #validar que halla completado su malla verifiar si esta entitulacion
                                eInscripciones = Inscripcion.objects.filter(status=True,persona=datospersona, coordinacion_id=7)
                                def consultar_informacion_inscripcion(eInscripcion):
                                    puedo_actualizar_datos_local = False
                                    cantidad_record = eInscripcion.recordacademico_set.filter(status=True).count()
                                    anio_minimo = eInscripcion.recordacademico_set.filter(status=True).annotate(anio=ExtractYear('fecha')).aggregate(Min('anio'))['anio__min']
                                    cantidad_malla = AsignaturaMalla.objects.filter(status=True,malla=eInscripcion.malla_inscripcion().malla,creditos__gt=0).count()
                                    tiene_malla_completa =  cantidad_record >= cantidad_malla if not cantidad_malla == 0 else False
                                    esta_en_titulacion =  TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula__inscripcion=eInscripcion).exists()
                                    if anio_minimo <= 2022:
                                        puedo_actualizar_datos_local  =True
                                    return {
                                        'id':eInscripcion.id,
                                        'carrera':eInscripcion.carrera,
                                        'tiene_malla_completa':tiene_malla_completa,
                                        'esta_en_titulacion':esta_en_titulacion,
                                        'puedo_actualizar_datos': puedo_actualizar_datos_local
                                    }

                                estructura_inscripcion = list(filter(None, map(lambda eInscripcion: consultar_informacion_inscripcion(eInscripcion) , eInscripciones)))
                                data['eInscripciones'] = estructura_inscripcion
                                data['puedo_actualizar_datos'] =  any(item['puedo_actualizar_datos'] for item in estructura_inscripcion)

                                data['form'] = form = DatosDataGraduadoForm(initial={
                                    'pais': datospersona.pais,
                                    'provincia': datospersona.provincia,
                                    'canton': datospersona.canton,
                                    'parroquia': datospersona.parroquia,
                                    'ciudadela': datospersona.ciudadela,
                                    'sector': datospersona.sector,
                                    'zona': datospersona.zona,
                                    'direccion': datospersona.direccion,
                                    'direccion2': datospersona.direccion2,
                                    'num_direccion': datospersona.num_direccion,
                                    'referencia': datospersona.referencia,
                                    'telefono': datospersona.telefono,
                                    'telefono_conv': datospersona.telefono_conv,
                                    'email': datospersona.email,
                                })
                                template = get_template("seguimientograduado/actualizadatograduado/registrargraduado.html")

                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Solo estudiantes de posgrado, pueden actualizar sus datos personales."})


                    json_content = template.render((data))
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            elif action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip()
                    datospersona = None
                    if Persona.objects.filter(cedula=cedula,status=True).exists():
                        datospersona = Persona.objects.get(cedula=cedula,status=True)
                    if Persona.objects.filter(pasaporte=cedula,status=True).exists():
                        datospersona = Persona.objects.get(pasaporte=cedula,status=True)
                    if datospersona:
                        return JsonResponse({"result": "ok", "mensaje": "Ya existe una persona registrada con esta cédula"})


                except Exception as ex:
                    err_ = f'{ex}({sys.exc_info()[-1].tb_lineno})'
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": err_})

            elif action == 'guardar_datos_graduado_en_el_sistema_data':
                try:
                    with transaction.atomic():
                        ePersona = Persona.objects.get(pk=int(request.POST['persona']))

                        ePersona.pais_id = int(request.POST['pais'])
                        if 'provincia' in request.POST:
                            ePersona.provincia_id = int(request.POST['provincia'])
                        if 'canton' in request.POST:
                            ePersona.canton_id = int(request.POST['canton'])
                        if 'parroquia' in request.POST:
                            ePersona.parroquia_id = int(request.POST['parroquia'])

                        ePersona.ciudadela = request.POST['ciudadela']

                        ePersona.sector = request.POST['sector']
                        if 'zona' in request.POST:
                            ePersona.zona = int(request.POST['zona'])
                        ePersona.ciudad_id = int(request.POST['canton'])
                        ePersona.direccion = request.POST['direccion']
                        ePersona.direccion2 = request.POST['direccion2']
                        ePersona.num_direccion = request.POST['num_direccion']
                        ePersona.referencia = request.POST['referencia']
                        ePersona.telefono = request.POST['telefono']
                        ePersona.telefono_conv = request.POST['telefono_conv']
                        ePersona.email = request.POST['email']
                        ePersona.save()
                        #verificar
                        ePersonaDataPosgrado =PersonaDataPosgrado.objects.filter(status=True,cedula = ePersona.cedula)
                        if not ePersonaDataPosgrado.exists():
                            eDataPersonaMatriz = PersonaDataPosgrado(
                                persona= ePersona,
                                nombres= ePersona.nombres,
                                apellido1= ePersona.apellido1,
                                apellido2= ePersona.apellido2,
                                cedula= ePersona.cedula,
                                pasaporte= ePersona.pasaporte,
                                nacimiento= ePersona.nacimiento,
                                sexo= ePersona.sexo,
                                nacionalidad= ePersona.nacionalidad,
                                paisnacionalidad= ePersona.paisnacionalidad,
                                pais= ePersona.pais,
                                provincia= ePersona.provincia,
                                canton= ePersona.canton,
                                parroquia= ePersona.parroquia,
                                ciudadela= ePersona.ciudadela,
                                sector= ePersona.sector,
                                zona= ePersona.zona,
                                ciudad= ePersona.ciudad,
                                direccion= ePersona.direccion,
                                direccion2= ePersona.direccion2,
                                num_direccion= ePersona.num_direccion,
                                referencia= ePersona.referencia,
                                telefono= ePersona.telefono,
                                telefono_conv= ePersona.telefono_conv,
                                emailinst= ePersona.emailinst,
                                email= ePersona.email,
                                graduado =True,
                                registradosistema =True,
                            )
                            eDataPersonaMatriz.save()
                        else:
                            eDataPersonaMatriz = ePersonaDataPosgrado.first()
                            eDataPersonaMatriz.nombres= ePersona.nombres
                            eDataPersonaMatriz.apellido1= ePersona.apellido1
                            eDataPersonaMatriz.apellido2= ePersona.apellido2
                            eDataPersonaMatriz.cedula= ePersona.cedula
                            eDataPersonaMatriz.pasaporte= ePersona.pasaporte
                            eDataPersonaMatriz.nacimiento= ePersona.nacimiento
                            eDataPersonaMatriz.sexo= ePersona.sexo
                            eDataPersonaMatriz.nacionalidad= ePersona.nacionalidad
                            eDataPersonaMatriz.paisnacionalidad= ePersona.paisnacionalidad
                            eDataPersonaMatriz.pais= ePersona.pais
                            eDataPersonaMatriz.provincia= ePersona.provincia
                            eDataPersonaMatriz.canton= ePersona.canton
                            eDataPersonaMatriz.parroquia= ePersona.parroquia
                            eDataPersonaMatriz.ciudadela= ePersona.ciudadela
                            eDataPersonaMatriz.sector= ePersona.sector
                            eDataPersonaMatriz.zona= ePersona.zona
                            eDataPersonaMatriz.ciudad= ePersona.ciudad
                            eDataPersonaMatriz.direccion= ePersona.direccion
                            eDataPersonaMatriz.direccion2= ePersona.direccion2
                            eDataPersonaMatriz.num_direccion= ePersona.num_direccion
                            eDataPersonaMatriz.referencia= ePersona.referencia
                            eDataPersonaMatriz.telefono= ePersona.telefono
                            eDataPersonaMatriz.telefono_conv= ePersona.telefono_conv
                            eDataPersonaMatriz.emailinst= ePersona.emailinst
                            eDataPersonaMatriz.email= ePersona.email
                            eDataPersonaMatriz.save(request)

                        inscripcion_ids = request.POST.getlist('inscripcion_ids')
                        fechas_graduacions = request.POST.getlist('fechagraduacions')
                        carrera_ids = request.POST.getlist('carrera_ids')

                        for inscripcion_id,carrera_id, fecha_graduacion in zip(inscripcion_ids,carrera_ids, fechas_graduacions):
                            if not PersonaDataPosgradoPrograma.objects.filter(status=True,persona =eDataPersonaMatriz,carrera_id =carrera_id).exists():
                                ePersonaDataPosgradoPrograma = PersonaDataPosgradoPrograma(
                                    persona =eDataPersonaMatriz,
                                    inscripcion_id =inscripcion_id,
                                    carrera_id =carrera_id,
                                    fechagraduado =fecha_graduacion
                                )
                                ePersonaDataPosgradoPrograma.save()
                            else:
                                ePersonaDataPosgradoPrograma = PersonaDataPosgradoPrograma.objects.filter(status=True,persona =eDataPersonaMatriz,carrera_id =carrera_id).first()
                                ePersonaDataPosgradoPrograma.fechagraduado = fecha_graduacion
                                ePersonaDataPosgradoPrograma.save(request)
                        return JsonResponse({"result": "ok", "mensaje": "Usted realizo la actualización de datos correctamente"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje":f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'})

            elif action == 'guardar_egresado_titulado_senecyt_en_el_sistema_data':
                try:
                    with transaction.atomic():
                        ePersona = Persona.objects.get(pk=int(request.POST['persona']))

                        ePersona.pais_id = int(request.POST['pais'])
                        if 'provincia' in request.POST:
                            ePersona.provincia_id = int(request.POST['provincia'])
                        if 'canton' in request.POST:
                            ePersona.canton_id = int(request.POST['canton'])
                        if 'parroquia' in request.POST:
                            ePersona.parroquia_id = int(request.POST['parroquia'])

                        ePersona.ciudadela = request.POST['ciudadela']

                        ePersona.sector = request.POST['sector']
                        if 'zona' in request.POST:
                            ePersona.zona = int(request.POST['zona'])
                        ePersona.ciudad_id = int(request.POST['canton'])
                        ePersona.direccion = request.POST['direccion']
                        ePersona.direccion2 = request.POST['direccion2']
                        ePersona.num_direccion = request.POST['num_direccion']
                        ePersona.referencia = request.POST['referencia']
                        ePersona.telefono = request.POST['telefono']
                        ePersona.telefono_conv = request.POST['telefono_conv']
                        ePersona.email = request.POST['email']
                        ePersona.save()
                        #verificar
                        ePersonaDataPosgrado =PersonaDataPosgrado.objects.filter(status=True,cedula = ePersona.cedula)
                        if not ePersonaDataPosgrado.exists():
                            eDataPersonaMatriz = PersonaDataPosgrado(
                                persona= ePersona,
                                nombres= ePersona.nombres,
                                apellido1= ePersona.apellido1,
                                apellido2= ePersona.apellido2,
                                cedula= ePersona.cedula,
                                pasaporte= ePersona.pasaporte,
                                nacimiento= ePersona.nacimiento,
                                sexo= ePersona.sexo,
                                nacionalidad= ePersona.nacionalidad,
                                paisnacionalidad= ePersona.paisnacionalidad,
                                pais= ePersona.pais,
                                provincia= ePersona.provincia,
                                canton= ePersona.canton,
                                parroquia= ePersona.parroquia,
                                ciudadela= ePersona.ciudadela,
                                sector= ePersona.sector,
                                zona= ePersona.zona,
                                ciudad= ePersona.ciudad,
                                direccion= ePersona.direccion,
                                direccion2= ePersona.direccion2,
                                num_direccion= ePersona.num_direccion,
                                referencia= ePersona.referencia,
                                telefono= ePersona.telefono,
                                telefono_conv= ePersona.telefono_conv,
                                emailinst= ePersona.emailinst,
                                email= ePersona.email,
                                graduado =False,
                                registradosistema =True,
                            )
                            eDataPersonaMatriz.save()
                        else:
                            eDataPersonaMatriz = ePersonaDataPosgrado.first()
                            eDataPersonaMatriz.nombres= ePersona.nombres
                            eDataPersonaMatriz.apellido1= ePersona.apellido1
                            eDataPersonaMatriz.apellido2= ePersona.apellido2
                            eDataPersonaMatriz.cedula= ePersona.cedula
                            eDataPersonaMatriz.pasaporte= ePersona.pasaporte
                            eDataPersonaMatriz.nacimiento= ePersona.nacimiento
                            eDataPersonaMatriz.sexo= ePersona.sexo
                            eDataPersonaMatriz.nacionalidad= ePersona.nacionalidad
                            eDataPersonaMatriz.paisnacionalidad= ePersona.paisnacionalidad
                            eDataPersonaMatriz.pais= ePersona.pais
                            eDataPersonaMatriz.provincia= ePersona.provincia
                            eDataPersonaMatriz.canton= ePersona.canton
                            eDataPersonaMatriz.parroquia= ePersona.parroquia
                            eDataPersonaMatriz.ciudadela= ePersona.ciudadela
                            eDataPersonaMatriz.sector= ePersona.sector
                            eDataPersonaMatriz.zona= ePersona.zona
                            eDataPersonaMatriz.ciudad= ePersona.ciudad
                            eDataPersonaMatriz.direccion= ePersona.direccion
                            eDataPersonaMatriz.direccion2= ePersona.direccion2
                            eDataPersonaMatriz.num_direccion= ePersona.num_direccion
                            eDataPersonaMatriz.referencia= ePersona.referencia
                            eDataPersonaMatriz.telefono= ePersona.telefono
                            eDataPersonaMatriz.telefono_conv= ePersona.telefono_conv
                            eDataPersonaMatriz.emailinst= ePersona.emailinst
                            eDataPersonaMatriz.email= ePersona.email
                            eDataPersonaMatriz.save(request)

                        inscripcion_ids = request.POST.getlist('inscripcion_ids')
                        fechas_graduacions = request.POST.getlist('fechagraduacions')
                        carrera_ids = request.POST.getlist('carrera_ids')

                        for inscripcion_id,carrera_id, fecha_graduacion in zip(inscripcion_ids,carrera_ids, fechas_graduacions):
                            if not PersonaDataPosgradoPrograma.objects.filter(status=True,persona =eDataPersonaMatriz,carrera_id =carrera_id).exists():
                                ePersonaDataPosgradoPrograma = PersonaDataPosgradoPrograma(
                                    persona =eDataPersonaMatriz,
                                    inscripcion_id =inscripcion_id,
                                    carrera_id =carrera_id,
                                    fechagraduado =fecha_graduacion
                                )
                                ePersonaDataPosgradoPrograma.save()
                            else:
                                ePersonaDataPosgradoPrograma = PersonaDataPosgradoPrograma.objects.filter(status=True,persona =eDataPersonaMatriz,carrera_id =carrera_id).first()
                                ePersonaDataPosgradoPrograma.fechagraduado = fecha_graduacion
                                ePersonaDataPosgradoPrograma.save(request)
                        return JsonResponse({"result": "ok", "mensaje": "Usted realizo la actualización de datos correctamente"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje":f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'})


            elif action == 'guardar_nueva_persona_graduado':
                try:
                    with transaction.atomic():
                        cedularegistro = request.POST['cedularegistro'].strip()
                        sexo = int(request.POST['sexo'].strip())
                        nombres = request.POST['nombres'].strip()
                        apellido1 = request.POST['apellido1'].strip()
                        apellido2 = request.POST['apellido2'].strip()
                        nacimiento = request.POST['nacimiento']
                        pais = int(request.POST['pais']) or 0 if  'pais' in request.POST else 0
                        provincia = int(request.POST['provincia']  or '0') if  'provincia' in request.POST else 0
                        canton = int(request.POST['canton']  or '0') if 'canton' in request.POST else 0
                        parroquia = int(request.POST['parroquia']  or '0') if 'parroquia' in request.POST else 0

                        direccion = request.POST['direccion'].strip()
                        direccion2 = request.POST['direccion2'].strip()
                        ciudadela = request.POST['ciudadela'].strip()
                        num_direccion = request.POST['num_direccion'].strip()
                        referencia = request.POST['referencia'].strip()
                        telefono_conv = request.POST['telefono_conv'].strip()
                        telefono = request.POST['telefono'].strip()
                        sector = request.POST['sector'].strip()
                        zona = int(request.POST['zona'].strip())
                        email = request.POST['email'].strip()

                        if not PersonaDataPosgrado.objects.filter(status=True,cedula = cedularegistro).exists() and not PersonaDataPosgrado.objects.filter(status=True,pasaporte = cedularegistro).exists():
                            ePersonaDataPosgrado = PersonaDataPosgrado(
                                nombres = nombres,
                                apellido1= apellido1,
                                apellido2 = apellido2,
                                nacimiento = nacimiento,
                                sexo_id = sexo,
                                ciudadela = ciudadela,
                                sector = sector,
                                zona = zona,
                                direccion = direccion,
                                direccion2 = direccion2,
                                num_direccion = num_direccion,
                                referencia = referencia,
                                telefono = telefono,
                                telefono_conv = telefono_conv,
                                email = email,
                                sinregistrosistema=True
                            )
                            ePersonaDataPosgrado.save(request)
                            if not pais == 0:
                             ePersonaDataPosgrado.pais_id = pais

                            if not provincia == 0:
                                ePersonaDataPosgrado.provincia_id = provincia
                            if not canton == 0:
                                ePersonaDataPosgrado.canton_id = canton
                            if not parroquia == 0:
                                ePersonaDataPosgrado.parroquia_id = parroquia

                            ePersonaDataPosgrado.save(request)
                            if int(request.POST['iden']) == 1:
                                ePersonaDataPosgrado.cedula = cedularegistro
                            else:
                                ePersonaDataPosgrado.pasaporte = cedularegistro


                            ePersonaDataPosgrado.save(request)
                            carreras = json.loads(request.POST.get('carreras', '[]'))  # Deserializar el JSON
                            if len(carreras) == 0:
                                return JsonResponse( {'result': 'error', 'mensaje': 'Debe agregar al menos una carrera.'})

                            for carrera in carreras:
                                ePersonaDataPosgradoPrograma = PersonaDataPosgradoPrograma(
                                    persona=ePersonaDataPosgrado,
                                    carrera_id = carrera.get('carreraId') ,
                                    fechagraduado = carrera.get('fechaGraduacion')


                                )
                                ePersonaDataPosgradoPrograma.save(request)








                        return JsonResponse({"result": "ok", "mensaje": "Usted realizo la actualización de datos correctamente"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje":f'Ocurrió un error: {str(ex)}, linea {sys.exc_info()[-1].tb_lineno}'})

    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']


        else:
            try:
                data['title'] = f'Actualiza datos graduado de posgrado - UNEMI'

                return render(request, "seguimientograduado/actualizadatograduado/view.html", data)
            except Exception as ex:
                pass
