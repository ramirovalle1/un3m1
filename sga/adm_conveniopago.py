# -*- coding: latin-1 -*-
import json
from decimal import Decimal
from django.contrib.auth.decorators import login_required
from django.db import transaction, connection
from django.db.models import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template import Context
from django.template.loader import get_template
from datetime import *

from decorators import secure_module, last_access
from sagest.models import Rubro
from sga.commonviews import adduserdata
from sga.forms import ConvenioPagoForm
from sga.funciones import MiPaginador, proximafecha, convertir_fecha, log
from sga.models import ConvenioPago, DetalleConvenioPago, null_to_decimal, ConvenioPagoInscripcion

@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    if request.method == 'POST':
        action = request.POST['action']
        
        if action == 'add':
            try:
                f = ConvenioPagoForm(request.POST)
                if f.is_valid():
                    if ConvenioPago.objects.filter(periodo=f.cleaned_data['periodo'], carrera=f.cleaned_data['carrera']).exists():
                        return JsonResponse({"result": "bad", "mensaje": u"Ya existe un convenio para era carrera en ese periodo."})
                    convenio = ConvenioPago(inicio=f.cleaned_data['inicio'],
                                            fin=f.cleaned_data['fin'],
                                            inicioproceso=f.cleaned_data['inicioproceso'],
                                            finproceso=f.cleaned_data['finproceso'],
                                            periodo=f.cleaned_data['periodo'],
                                            carrera=f.cleaned_data['carrera'],
                                            rubro=f.cleaned_data['rubro'],
                                            mesesplazo=f.cleaned_data['plazo'],
                                            valormaestria=f.cleaned_data['valormaestria'],
                                            valorinscripcion=f.cleaned_data['valorinscripcion'],
                                            matricula=f.cleaned_data['valormatricula'])
                    convenio.save(request)
                    cursor = connection.cursor()
                    cursor.execute("INSERT INTO sga_detalleconveniopago (usuario_creacion_id, fecha_creacion, conveniopago_id, inscripcion_id, meses) "
                                   "SELECT %s, now(), %s, sga_inscripcion.id, %s from sga_inscripcion, sga_matricula, sga_nivel WHERE sga_matricula.inscripcion_id = sga_inscripcion.id AND sga_matricula.nivel_id = sga_nivel.id AND sga_nivel.periodo_id=%s;", [request.user.id, convenio.id, convenio.mesesplazo, convenio.periodo.id])
                    log(u"Adiciono un convenio de pago para esta carrera en ese periodo : %s - %s [%s]" % (convenio, convenio.rubro, convenio.id), request, "add")
                    return JsonResponse({"result": "ok", "id": convenio.id})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'inscipcionconvenio':
            try:
                data = {}
                data['convenio'] = convenio = ConvenioPago.objects.get(pk=int(request.POST['id']))
                detalle = convenio.detalleconveniopago_set.all()
                pagina = 1
                paging = MiPaginador(detalle, 100)
                p = 1
                try:
                    if 'page' in request.POST:
                        p = int(request.POST['page'])
                    page = paging.page(p)
                except:
                    page = paging.page(1)
                data['paging'] = paging
                data['rangospaging'] = paging.rangos_paginado(p)
                data['page'] = page
                data['detalles'] = page.object_list
                data['usuario'] = request.user
                template = get_template("adm_conveniopago/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'data': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

        if action == 'detalle_convenio':
            try:
                data['detalle'] = detalle = DetalleConvenioPago.objects.get(pk=int(request.POST['id']))
                data['detalles'] = detalle.conveniopagoinscripcion_set.all()
                template = get_template("alu_conveniopago/detalle.html")
                json_content = template.render(data)
                return JsonResponse({"result": "ok", 'html': json_content})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        if action == 'cambia_mes':
            try:
                detalle = DetalleConvenioPago.objects.get(pk=int(request.POST['id']))
                if int(request.POST['valor']) > detalle.conveniopago.mesesplazo:
                    return JsonResponse({"result": "bad", "mensaje": u"El valor excede el plazo máximo"})
                detalle.meses = int(request.POST['valor'])
                detalle.save(request)
                log(u"cambio de mes en detalle convenio de pago: %s - %s [%s]" % (detalle, detalle.meses, detalle.id), request, "edit")
                return JsonResponse({"result": "ok", "reload": 'False', 'valor': detalle.meses})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'cambia_porciento':
            try:
                detalle = DetalleConvenioPago.objects.get(pk=int(request.POST['id']))
                detalle.porcientodescuento = int(request.POST['valor'])
                detalle.save(request)
                log(u"cambio de porciento descuento en detalle convenio de pago: %s - %s [%s]" % (detalle, detalle.porcientodescuento, detalle.id),request, "edit")
                return JsonResponse({"result": "ok", "reload": 'False', 'valor': detalle.porcientodescuento})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        if action == 'edit':
            try:
                convenio = ConvenioPago.objects.get(pk=request.POST['id'])
                f = ConvenioPagoForm(request.POST)
                if f.is_valid():
                    convenio.inicio = f.cleaned_data['inicio']
                    convenio.fin = f.cleaned_data['fin']
                    convenio.inicioproceso = f.cleaned_data['inicioproceso']
                    convenio.finproceso = f.cleaned_data['finproceso']
                    convenio.mesesplazo = f.cleaned_data['plazo']
                    convenio.valormaestria = f.cleaned_data['valormaestria']
                    convenio.valorinscripcion = f.cleaned_data['valorinscripcion']
                    convenio.matricula = f.cleaned_data['valormatricula']
                    convenio.save(request)
                    log(u"Edito convenio de pago: %s -[%s]" % (convenio, convenio.id), request, "add")
                    fechacobro = convenio.inicioproceso
                    fechacobrofinal = proximafecha(fechacobro, 3, convenio.inicioproceso.day)
                    for detalle in convenio.detalleconveniopago_set.filter(aprobado=False):
                        detalle.conveniopagoinscripcion_set.all().delete()
                        valorcuota = null_to_decimal(detalle.valor_total_diferido() / detalle.meses, 2)
                        for cuota in range(detalle.meses):
                            if cuota == 0:
                                fechacobrofinal = proximafecha(fechacobro, 3, convenio.inicioproceso.day)
                            else:
                                fechacobrofinal = proximafecha(fechacobrofinal, 3, convenio.inicioproceso.day)
                            cpi = ConvenioPagoInscripcion(detalleconveniopago=detalle,
                                                          fecha=fechacobrofinal,
                                                          valorcuota=valorcuota)
                            cpi.save(request)
                        detalle.verifica_diferencia(request)
                    return JsonResponse({"result": "ok"})
                else:
                     raise NameError('Error')
            except Exception as ex:
                transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'adicionar':
            try:
                detalle = DetalleConvenioPago.objects.get(pk=int(request.POST['id']))
                fechamaxima = detalle.conveniopagoinscripcion_set.all().order_by('-fecha')[0].fecha
                fechacobrofinal = proximafecha(fechamaxima, 3, detalle.conveniopago.inicioproceso.day)
                cpi = ConvenioPagoInscripcion(detalleconveniopago=detalle,
                                              fecha=fechacobrofinal,
                                              valorcuota=0)
                cpi.save(request)
                log(u"Adiciona convenio de pago incripcion: %s -[%s]" % (cpi, cpi.id), request, "add")
                detalle.meses += 1
                detalle.save(request)
                valorcuota = null_to_decimal(detalle.valor_total_diferido() / detalle.meses, 2)
                detalle.conveniopagoinscripcion_set.update(valorcuota=valorcuota)
                detalle.verifica_diferencia(request)
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'eliminardetalle':
            try:
                detalle = ConvenioPagoInscripcion.objects.get(pk=int(request.POST['id']))
                convenio = detalle.detalleconveniopago
                log(u"Elimina convenio de pago incripcion: %s -[%s]" % (detalle, detalle.id), request, "del")
                detalle.delete()
                convenio.meses = convenio.conveniopagoinscripcion_set.count()
                convenio.save(request)
                valorcuota = null_to_decimal(convenio.valor_total_diferido() / convenio.meses, 2)
                convenio.conveniopagoinscripcion_set.update(valorcuota=valorcuota)
                convenio.verifica_diferencia(request)
                return JsonResponse({"result": "ok"})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'confirmar_convenio':
            try:
                convenio = DetalleConvenioPago.objects.get(id=int(request.POST['id']))
                valorconvenio = convenio.valor_total_diferido()
                datos = json.loads(request.POST['datos'])
                valor = 0
                for d in datos:
                    valor += null_to_decimal(d['valor'], 2)
                if valor != valorconvenio:
                    return JsonResponse({"result": "bad","mensaje": u"El valor total de las cuotas no es igual al valor del convenio"})
                cuota = 1
                rubro = Rubro(tipo=convenio.conveniopago.rubro,
                              persona=convenio.inscripcion.persona,
                              matricula=convenio.inscripcion.matricula(),
                              nombre=U'MATRÍCULA  ' + str(convenio.conveniopago.rubro),
                              cuota=cuota,
                              fecha=datetime.now().date(),
                              fechavence=convenio.conveniopago.inicioproceso,
                              valor=convenio.conveniopago.matricula,
                              iva_id=1,
                              valortotal=convenio.conveniopago.matricula,
                              saldo=convenio.conveniopago.matricula)
                rubro.save(request)
                for d in datos:
                    cpi = ConvenioPagoInscripcion.objects.get(id=int(d['id']))
                    cpi.fecha = convertir_fecha(d['fecha'])
                    cpi.valorcuota = Decimal(d['valor'])
                    cpi.save(request)
                    rubro = Rubro(tipo=convenio.conveniopago.rubro,
                                  persona=convenio.inscripcion.persona,
                                  matricula=convenio.inscripcion.matricula(),
                                  nombre=u'CUOTA  ' + str(convenio.conveniopago.rubro),
                                  cuota=cuota,
                                  fecha=datetime.now().date(),
                                  fechavence=cpi.fecha,
                                  valor=cpi.valorcuota,
                                  iva_id=1,
                                  valortotal=cpi.valorcuota,
                                  saldo=cpi.valorcuota)
                    rubro.save(request)
                    cpi.rubro=rubro
                convenio.aprobado = True
                convenio.save(request)
                log(u"Confima convenio de pago: %s - Rubro: %s - [%s]" % (convenio, rubro, convenio.id), request, "add")
                return JsonResponse({"result": "ok", "reload": 'False'})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Nuevo Convenio'
                    form = ConvenioPagoForm()
                    data['form'] = form
                    return render(request, "adm_conveniopago/add.html", data)
                except Exception as ex:
                    pass

            if action == 'edit':
                try:
                    data['title'] = u'Editar Convenio'
                    data['convenio'] = convenio = ConvenioPago.objects.get(pk=request.GET['id'])
                    data['detalles'] = convenio.detalleconveniopago_set.all().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    form = ConvenioPagoForm(initial={'periodo': convenio.periodo,
                                                     'carrera': convenio.carrera,
                                                     'rubro': convenio.rubro,
                                                     'inicio': convenio.inicio,
                                                     'inicioproceso': convenio.inicioproceso,
                                                     'finproceso': convenio.finproceso,
                                                     'fin': convenio.fin,
                                                     'plazo': convenio.mesesplazo,
                                                     'valormaestria': convenio.valormaestria,
                                                     'valorinscripcion': convenio.valorinscripcion,
                                                     'valormatricula': convenio.matricula})
                    form.editar()
                    data['form'] = form
                    return render(request, "adm_conveniopago/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'inscritos':
                try:
                    data['title'] = u'Inscripciones'
                    data['convenio'] = convenio = ConvenioPago.objects.get(pk=request.GET['id'])
                    data['detalles'] = convenio.detalleconveniopago_set.filter(aprobado=True).order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    return render(request, "adm_conveniopago/inscritos.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobar':
                try:
                    data['title'] = u'Aprobar Convenios'
                    data['convenio'] = convenio = ConvenioPago.objects.get(pk=request.GET['id'])
                    data['detalles'] = convenio.detalleconveniopago_set.all().order_by('inscripcion__persona__apellido1', 'inscripcion__persona__apellido2', 'inscripcion__persona__nombres')
                    return render(request, "adm_conveniopago/aprobar.html", data)
                except Exception as ex:
                    pass

            if action == 'aprobarins':
                try:
                    data['title'] = u'Editar Convenio'
                    data['convenio'] = convenio = DetalleConvenioPago.objects.get(pk=request.GET['id'])
                    data['detalles'] = convenio.conveniopagoinscripcion_set.all().order_by('fecha')
                    return render(request, "adm_conveniopago/aprobarins.html", data)
                except Exception as ex:
                    pass

            if action == 'addlinea':
                try:
                    data['title'] = u'Confirmar adicionar un mes'
                    data['convenio'] = DetalleConvenioPago.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_conveniopago/adicionar.html", data)
                except:
                    pass

            if action == 'eliminardetalle':
                try:
                    data['title'] = u'Confirmar eliminar mes'
                    data['convenio'] = convenio = ConvenioPagoInscripcion.objects.get(pk=int(request.GET['id']))
                    return render(request, "adm_conveniopago/eliminardetalle.html", data)
                except:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Convenios de Pago'
            search = None
            ids = None
            if 's' in request.GET:
                search = request.GET['s']
                convenios = ConvenioPago.objects.filter(Q(inicio__icontains=search)).distinct()
            elif 'id' in request.GET:
                ids = request.GET['id']
                convenios = ConvenioPago.objects.filter(id=ids)
            else:
                convenios = ConvenioPago.objects.all()
            paging = MiPaginador(convenios, 25)
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
            data['convenios'] = page.object_list
            return render(request, "adm_conveniopago/view.html", data)