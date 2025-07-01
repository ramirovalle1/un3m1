# -*- coding: latin-1 -*-
import sys
from django.contrib.auth.decorators import login_required
from django.db.models.functions import Coalesce
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db import transaction
from decorators import secure_module, last_access
from matricula.funciones import puede_matricularse_seguncronograma_coordinacion_prematricula
from sagest.models import Rubro
from settings import TIPO_PERIODO_REGULAR,DEBUG
from sga.commonviews import adduserdata, prematricular
from sga.forms import ActualizarDatosForm
from sga.funciones import log
from sga.models import Periodo, Sesion, Materia, PreMatricula, HistoricoRecordAcademico, UbicacionPersona
from django.template.loader import get_template
from django.db.models import Count, Sum
from sga.templatetags.sga_extras import encrypt_alu


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['coordinacion'] = coordinacion = request.session['coordinacion']
    perfilprincipal = request.session['perfilprincipal']
    # periodo = request.session['periodo']
    periodo = Periodo.objects.filter(id=126).first()
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al módulo.")
    data['inscripcion'] = inscripcion = perfilprincipal.inscripcion
    if periodo.nivel_set.first().matricula_set.filter(inscripcion=inscripcion, status=True).values('id').exists():
        return HttpResponseRedirect(u"/?info=Usted ya se encuentra matriculado en el periodo " + str(periodo))
    if not coordinacion in [1, 2, 3, 4, 5]:
        return HttpResponseRedirect(u"/?info=Solo los estudiantes de pre grado pueden ingresar al modulo.")
    if inscripcion.graduado() or inscripcion.egresado() or inscripcion.estainactivo():
        return HttpResponseRedirect(u"/?info=Solo podrán planificar sus asignaturas los estudiantes activos.")
    carrera = inscripcion.carrera
    inscripcionmalla = inscripcion.malla_inscripcion()
    if not inscripcionmalla:
        return HttpResponseRedirect(u"/?info=Debe tener malla asociada para poder planificar sus asignaturas.")
    data['malla'] = inscripcionmalla.malla

    # if inscripcion.tiene_ultima_matriculas(3):
    #     return HttpResponseRedirect("/?info=Atencion: Estimado/a estudiante, su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria de la facultad para mas informacion.")

    # PERDIDA DE CARRERA POR 4TA MATRICULA
    if inscripcion.tiene_perdida_carrera(periodo.periodomatricula_set.first().num_matriculas):
        return HttpResponseRedirect(u"/?info=Atención: No puede acceder al módulo por pérdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
    if not inscripcion.tiene_malla():
        return HttpResponseRedirect(u"/?info=No tiene malla asignada.")
    if not Periodo.objects.filter(tipo__id=TIPO_PERIODO_REGULAR, prematriculacionactiva=True).values('id').exists():
        return HttpResponseRedirect("/?info=No existen periodos futuros para planificación de matriculación.")
    # PERIODO ACTIVO PARA MATRICULACION
    if not periodo.prematriculacionactiva:
        return HttpResponseRedirect(u"/?info=El periodo no se encuentra activo para planificación de matriculación.")
    if not DEBUG:
        if not puede_matricularse_seguncronograma_coordinacion_prematricula(inscripcion, periodo):
            return HttpResponseRedirect(u"/?info=Aun no esta habilitado para la planificación de matrícula")

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'prematricular':
                from runback.arreglos.calculoprematricula import agregacion_aux
                valormatriculapago = agregacion_aux(request)
                return prematricular(request, valormatriculapago)
            elif action == 'actualizadatos':
                try:
                    form = ActualizarDatosForm(request.POST)
                    perfil = persona.mi_perfil()
                    if 'latitud' not in request.POST or request.POST['latitud'] == '' and 'longitud' not in request.POST or request.POST['longitud'] == '':
                        return JsonResponse({"result": "bad",  "mensaje": 'Debe ingresar su ubicación en el mapa'})
                    if form.is_valid():
                        perfil.raza = form.cleaned_data['raza']
                        perfil.nacionalidadindigena = form.cleaned_data['nacionalidadindigena']
                        persona.pais = form.cleaned_data['pais']
                        if form.cleaned_data['pais'].pk == 1:
                            persona.provincia = form.cleaned_data['provincia']
                            persona.canton = form.cleaned_data['canton']
                            persona.parroquia = form.cleaned_data['parroquia']
                        persona.direccion = form.cleaned_data['direccion']
                        persona.direccion2 = form.cleaned_data['direccion2']
                        persona.sector = form.cleaned_data['sector']
                        persona.num_direccion = form.cleaned_data['num_direccion']
                        persona.referencia = form.cleaned_data['referencia']
                        persona.telefono = form.cleaned_data['telefono']
                        persona.telefono_conv = form.cleaned_data['telefono_conv'] if form.cleaned_data['telefono_conv'] else None
                        persona.tipocelular = form.cleaned_data['tipocelular']
                        perfil.tienediscapacidad = form.cleaned_data['tienediscapacidad']
                        perfil.tipodiscapacidad = form.cleaned_data['tipodiscapacidad']
                        perfil.porcientodiscapacidad = form.cleaned_data['porcientodiscapacidad']
                        perfil.carnetdiscapacidad = form.cleaned_data['carnetdiscapacidad']
                        perfil.institucionvalida = form.cleaned_data['institucionvalida']
                        persona.eszurdo = form.cleaned_data['zurdo']
                        persona.save(request)
                        perfil.save(request)
                        ubicacion = UbicacionPersona(persona=persona, latitud=float(request.POST['latitud']), longitud=float(request.POST['longitud']))
                        ubicacion.save(request)
                        log('Actualizo informacion personal {} - {}'.format(persona.pk, persona), request, "edit")
                        return JsonResponse({"result": "ok"})
                except Exception as e:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
            elif action == 'delprematricula':
                id = int(encrypt_alu(request.POST['id']))
                if PreMatricula.objects.filter(id=id).values('id').exists():
                    obj = PreMatricula.objects.get(id=id)
                    obj.delete()
                    log(u'Eliminó planificacion de matricula: %s' % obj, request, "del")
                    return JsonResponse({"result": "ok"})
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if inscripcion.prematricula_set.filter(periodo=periodo).values('id').exists():
            data['tienedeuda'] = deuda = Rubro.objects.filter(status=True, matricula__isnull=False, persona=persona, cancelado=False).aggregate(total=Coalesce(Sum('saldo'), 0)).get('total')
            data['title'] = u'Detalle de mi planificacion de matricula'
            data['miprematricula'] = miprematricula = inscripcion.prematricula_set.filter(periodo=periodo, status=True).first()
            data['total'] = miprematricula.valorpagoaprox + deuda
            return render(request, "alu_prematricula/view_miprematricula.html", data)
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'prematricula':
                data['periodoprematricula'] = periodo
                data['title'] = u'Planificación de matrícula'
                aprobadas = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__isnull=False).values_list('asignatura_id', flat=True)
                asignaturas_malla_pendientes = inscripcionmalla.malla.asignaturamalla_set.values_list('asignatura_id', flat=True).filter(status=True).exclude(asignatura_id__in=aprobadas)
                xyz = [1, 2, 3]
                if inscripcion.itinerario and inscripcion.itinerario > 0:
                    xyz.remove(inscripcion.itinerario)
                    asignaturas_malla_pendientes = asignaturas_malla_pendientes.exclude(itinerario__in=xyz)
                materias = Materia.objects.filter(status=True, nivel__periodo=periodo, asignatura_id__in=asignaturas_malla_pendientes, asignaturamalla__malla__carrera=carrera)
                data['modalidades'] = modalidades = materias.values_list('nivel__modalidad__nombre', flat=True).distinct()
                jornadas = materias.values_list('nivel__sesion', flat=True).filter(cupo__gt=0).distinct() if len(materias) == materias.values_list('id', flat=True).filter(cupo__gt=0).count() else []
                data['jornadas_lista'] = jornadas = Sesion.objects.filter(status=True, id__in=jornadas)
                data['terminos'] = periodo.periodomatricula_set.first().terminos
                try:
                    data['materiasmalla'] = mtfilter = {}
                    if 'jornada' in request.GET and len(jornadas) > 0:
                        jornada_seleccionada = int(encrypt_alu(request.GET['jornada']))
                        if jornada_seleccionada > 0:
                            data['jornada_select'] = jornada_seleccionada
                            lista = []
                            for materia in materias.filter(nivel__sesion_id=int(jornada_seleccionada)).distinct('asignatura_id'):
                                lista.append(materia.id)
                                # countcoupo = len(PreMatriculaAsignatura.objects.filter(asignatura=materia.asignatura, prematricula__inscripcion__carrera=inscripcion.carrera, sesion=materia.nivel.sesion).values('asignatura_id'))
                                # cupom = Materia.objects.filter(status=True, nivel__periodo=periodo, asignaturamalla__malla__carrera=carrera, nivel__sesion_id=int(jornada_seleccionada), asignatura=materia.asignatura).aggregate(cupot=Coalesce(Sum('cupo'), 0)).get('cupot')
                                # if cupom > countcoupo:
                                # else:
                                #     data['sincupo'] = True
                                #     return render(request, "alu_prematricula/view_prematricula2.html", data)
                            materias_1 = Materia.objects.filter(id__in=lista).order_by('asignaturamalla__nivelmalla_id')
                            # data['materiasmalla'] = mtfilter = materias.filter(nivel__sesion_id=int(jornada_seleccionada)).order_by('asignaturamalla__nivelmalla_id').distinct('asignatura_id','asignaturamalla__nivelmalla_id')
                            data['materiasmalla'] = mtfilter = materias_1
                            data['materiasterceramatricula'] = len(HistoricoRecordAcademico.objects.values('asignatura_id').filter(asignatura_id__in=mtfilter.values_list('asignatura_id'), inscripcion=inscripcion, aprobada=False).exclude(materiaregular__nivel__periodo__cuentavecesmatricula=False).annotate(total=Count('asignatura_id')).filter(total__gte=2))
                    return render(request, "alu_prematricula/view_prematricula2.html", data)
                except Exception as e:
                    print(e)
                    pass
            if action == 'verdeuda':
                try:
                    json_content = None
                    # if Rubro.objects.values('id').filter(status=True, persona=persona, matricula__isnull=False, cancelado=False).exists():
                    rubros = Rubro.objects.filter(status=True, persona=persona, matricula__isnull=False)
                    data['title'] = u'Detalle de rubros'
                    data['rubros'] = rubros
                    template = get_template("alu_prematricula/consultadeuda.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as e:
                    print(e)
                    print('Error on line {}'.format(sys.exc_info()[-1].tb_lineno))
                    return JsonResponse({"result": "bad"})
        else:
            try:
                if UbicacionPersona.objects.filter(status=True, persona=persona, fecha_creacion__gte='2022-04-01'):
                    return HttpResponseRedirect(u"/alu_prematricula?action=prematricula")
                data['periodoprematricula'] = periodo
                data['title'] = u'Actualiza tus datos personales'
                perfil = persona.mi_perfil()
                data['form'] = form = ActualizarDatosForm(initial={'raza': perfil.raza,
                                                            'nacionalidadindigena': perfil.nacionalidadindigena,
                                                            'pais': persona.pais,
                                                            'provincia': persona.provincia,
                                                            'canton': persona.canton,
                                                            'parroquia': persona.parroquia,
                                                            'direccion': persona.direccion,
                                                            'direccion2': persona.direccion2,
                                                            'sector': persona.sector,
                                                            'num_direccion': persona.num_direccion,
                                                            'referencia': persona.referencia,
                                                            'telefono': persona.telefono,
                                                            'telefono_conv': persona.telefono_conv,
                                                            'tipocelular': persona.tipocelular,
                                                            'tienediscapacidad': perfil.tienediscapacidad,
                                                            'tipodiscapacidad': perfil.tipodiscapacidad,
                                                            'porcientodiscapacidad': perfil.porcientodiscapacidad,
                                                            'carnetdiscapacidad': perfil.carnetdiscapacidad,
                                                            'institucionvalida': perfil.institucionvalida,
                                                            'eszurdo': persona.eszurdo
                                                            })
                data['form'] = form
                return render(request, "alu_prematricula/formencuesta.html", data)
            except Exception as ex:
                print('Error on line {} - {}'.format(sys.exc_info()[-1].tb_lineno, ex))
                return HttpResponseRedirect("/?info=Error al mostrar el formulario.")

