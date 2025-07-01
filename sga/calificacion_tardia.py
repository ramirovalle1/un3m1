# -*- coding: latin-1 -*-
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from datetime import datetime
from decorators import secure_module, last_access
from settings import PAGO_ESTRICTO
from sga.commonviews import adduserdata, actualizar_nota, obtener_reporte
from sga.funciones import MiPaginador, log
from sga.models import Materia, MateriaAsignada, LeccionGrupo
from sga.tasks import send_html_mail
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'nota':
            try:
                result = actualizar_nota(request)
                return JsonResponse(result)
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'cerrarmateriaasignada':
            try:
                materiaasignada = MateriaAsignada.objects.get(pk=int(encrypt(request.POST['maid'])))
                materiaasignada.cerrado = (request.POST['cerrado'] == 'false')
                materiaasignada.fechacierre = datetime.now().date()
                materiaasignada.save(actualiza=True)
                materiaasignada.actualiza_estado()
                materiasabiertas = MateriaAsignada.objects.filter(materia=materiaasignada.materia,
                                                                  cerrado=False).count()
                return JsonResponse({"result": "ok", 'cerrado': materiaasignada.cerrado, 'importadeuda': PAGO_ESTRICTO,
                                     'tienedeuda': materiaasignada.matricula.inscripcion.persona.tiene_deuda(),
                                     'materiasabiertas': materiasabiertas, "estadoid": materiaasignada.estado.id,
                                     "estado": materiaasignada.estado.nombre,
                                     "valida": materiaasignada.valida_pararecord(), "maid": materiaasignada.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        if action == 'cerrarmateria':
            try:
                materia = Materia.objects.get(pk=int(encrypt(request.POST['mid'])))
                materia.cerrado = True
                materia.fechacierre = datetime.now().date()
                materia.save(request)
                for asig in materia.asignados_a_esta_materia():
                    asig.cerrado = True
                    asig.actualiza_estado()
                    asig.save(request)
                for asig in materia.asignados_a_esta_materia():
                    asig.cierre_materia_asignada()
                for lg in LeccionGrupo.objects.filter(lecciones__clase__materia=materia, abierta=True):
                    lg.abierta = False
                    lg.horasalida = lg.turno.termina
                    lg.save(request)
                # materia.materiaasignada_set.all()[0].cierre_materia_asignada_pre()
                log(u'Cerro la materia: %s' % materia, request, "add")
                # send_html_mail("Cierre de materia", "emails/cierremateria.html", {'profesor': profesor, 'materia': materia, 't': miinstitucion()}, profesor.persona.lista_emails_envio(), [], cuenta=CUENTAS_CORREOS[4][1])
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Calificación Materias'
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'calificaciontardia':
                try:
                    data['title'] = u'Calificación tardía'
                    data['materia'] = materia = Materia.objects.get(pk=int(encrypt(request.GET['idmateria'])))
                    if materia.tipomateria == 2:
                        data['validardeuda'] = False
                        data['incluyepago'] = False
                        data['incluyedatos'] = False
                        data['page'] = 1
                        if 'page' in request.GET:
                            data['page'] = request.GET['page']
                        if 'mallaid' in request.GET:
                            data['mallaid'] = mallaid = int(encrypt(request.GET['mallaid']))
                        if 'nivelmallaid' in request.GET:
                            data['nivelmallaid'] = nivelmallaid = int(encrypt(request.GET['nivelmallaid']))
                        return render(request, "calificacion_tardia/calificaciontardia.html", data)
                    else:
                        pass
                except Exception as ex:
                    pass

            if action == 'segmento':
                try:
                    data['materia'] = materia = Materia.objects.get(pk=request.GET['idma'])
                    materiaasignada = materia.materiaasignada_set.filter(status=True).order_by('matricula__inscripcion__persona__apellido1')
                    data['validardeuda'] = False
                    data['incluyepago'] = False
                    data['incluyedatos'] = False
                    data['auditor'] = False
                    data['cronograma'] = None
                    data['permitecambiarcodigo'] = False
                    data['campos'] = materia.modeloevaluativo.campos

                    paging = MiPaginador(materiaasignada, 30)
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
                    # data['search'] = search if search else ""
                    # data['ids'] = ids if ids else ""
                    data['materiaasignada'] = page.object_list

                    return render(request, "calificacion_tardia/segmento.html", data)
                except Exception as ex:
                    pass



            return HttpResponseRedirect(request.path)
        else:
            search = None
            ids = None
            if 'id' in request.GET:
                ids = request.GET['id']
                materias = Materia.objects.filter(id=ids, tipomateria=2)
            elif 's' in request.GET:
                search = request.GET['s']
                materias = Materia.objects.filter(asignatura__nombre__icontains=search, nivel__periodo=periodo, status=True, materiaasignada__isnull=False , asignaturamalla__malla__carrera__id=34, tipomateria=2).distinct().order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
            else:
                materias = Materia.objects.filter(nivel__periodo=periodo, status=True, materiaasignada__isnull=False , asignaturamalla__malla__carrera__id=34, tipomateria=2).distinct().order_by('asignaturamalla__nivelmalla', 'asignatura__nombre', 'inicio', 'identificacion', 'id')
            data['search'] = search if search else ""
            data['ids'] = ids if ids else ""
            data['materias'] = materias
            data['reporte_2'] = obtener_reporte('acta_notas_modulo')
            data['reporte_7'] = obtener_reporte('acta_notas_parcial_modulo')
            return render(request, "calificacion_tardia/view.html", data)