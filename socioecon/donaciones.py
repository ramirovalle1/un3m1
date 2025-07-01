from sga.templatetags.sga_extras import encrypt
from socioecon.models import *
from socioecon.forms import *
from django.db import transaction
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from sga.funciones import log, generar_nombre, convertir_fecha_invertida, convertir_fecha, MiPaginador
from django.db.models import Sum, Q, F, FloatField
import datetime

@transaction.atomic()
def view(request):
    data = {}
    data['currenttime'] = currenttime = datetime.datetime.now()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = data['action'] = request.POST['action']
            if action == 'addcontribuidor':
                try:
                    with transaction.atomic():
                        mensaje, person = '', ''
                        f = ContribuidorDonacionForm(request.POST)
                        if f.is_valid():
                            tipopersona = int(f.cleaned_data['tipodonante'])
                            if tipopersona == 1:
                                cedula = f.cleaned_data['cedula']
                                if not cedula or len(cedula) <= 10:
                                    if len(request.POST['cedula']) == 13:
                                        if request.POST['tipoidentificacion'] == '3' and not request.POST['cedula'][-3:] == '001':
                                            return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de RUC de persona natural valido."})
                                        if request.POST['tipoidentificacion'] == '2' and not request.POST['cedula'][2:].upper() == 'VS':
                                            return JsonResponse({"result": "bad", "mensaje": u"Para ingresar pasaporte digite VS al inicio de la numeración."})
                                else:
                                    return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})

                                if not Persona.objects.filter(Q(cedula=cedula) | Q(ruc=cedula)).exists():
                                    person = Persona(cedula=cedula if len(cedula) == 10 else '',
                                                     ruc=cedula if len(cedula) == 13 else '',
                                                     tipopersona=1,
                                                     pasaporte=f.cleaned_data['pasaporte'] if f.cleaned_data['pasaporte'] else '',
                                                     nombres=(u"%s %s" % (f.cleaned_data['nombre1'], f.cleaned_data['nombre2'])).upper(),
                                                     apellido1=f.cleaned_data['apellido1'].upper(),
                                                     apellido2=f.cleaned_data['apellido2'].upper(),
                                                     nacimiento=currenttime.date(),
                                                     email=f.cleaned_data['email'],
                                                     sexo=f.cleaned_data['sexo'] if f.cleaned_data['sexo'] else '')
                            elif tipopersona == 2:
                                if not f.cleaned_data['ruc']:
                                    return JsonResponse({"result": "bad", "mensaje": u"Debe especificar un numero de identificación."})

                                if not Persona.objects.filter(ruc=f.cleaned_data['ruc']).exists():
                                    person = Persona(ruc=f.cleaned_data['ruc'], email=f.cleaned_data['email'], tipopersona=2, nombres=f.cleaned_data['razonsocial'].upper())
                            if person:
                                person.save(request)
                            else:
                                if tipopersona == 1:
                                    person = Persona.objects.get(cedula=f.cleaned_data['cedula'])
                                elif tipopersona == 2:
                                    person = Persona.objects.get(ruc=f.cleaned_data['ruc'])

                            if not ContribuidorDonacion.objects.filter(persona=person):
                                contribuidor = ContribuidorDonacion(persona=person, es_anonimo=f.cleaned_data['esanonimo'])
                                contribuidor.save(request)

                            request.session['persona'] = person
                            request.session['externo'] = True
                            return JsonResponse({"result": 'ok'}, safe=False)
                        else:
                            return JsonResponse({'error': True, 'form': [{k: v[0]} for k, v in f.errors.items()],
                                                 'message': "Error en el formulario"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": True, "mensaje": "Intentelo más tarde."}, safe=False)

            if action == 'adddonacion':
                try:
                    with transaction.atomic():
                        if request.session['persona']:
                            if ContribuidorDonacion.objects.filter(persona=request.session['persona']).exists():
                                contribuidor = ContribuidorDonacion.objects.get(persona=request.session['persona'])
                                donacion = DetalleContribuidorDonacion(contribuidordonacion_id=contribuidor.pk,
                                                                       detalleproductopublicacion_id=int(encrypt(request.POST['iddp'])),
                                                                       cantidad=int(request.POST['cantidad']) if request.POST['cantidad'] else 0)
                                donacion.save(request)

                        return JsonResponse({"result": 'ok'}, safe=False)
                except Exception as ex:
                    transaction.set_rollback(True)
                    pass

            return HttpResponseRedirect(request.path)
    else:
        if 'action' in request.GET:
            action = data['action'] = request.GET['action']
            if action == 'get_persona':
                try:
                    if request.GET['c'] or request.GET['ruc']:
                        if int(request.GET['tipo']) == 1:
                            if Persona.objects.filter(cedula=request.GET['c']):
                                per = Persona.objects.get(cedula=request.GET['c'])
                                return JsonResponse({"result": True, 'data': {"pasaporte": per.pasaporte,
                                                                              "nombre1": per.nombres.split(' ')[0],
                                                                              "nombre2": per.nombres.split(' ')[1],
                                                                              "apellido1": per.apellido1,
                                                                              "apellido2": per.apellido2,
                                                                              "email": per.email,
                                                                              "sexo": per.sexo_id}})
                        else:
                            if int(request.GET['tipo']) == 2:
                                if Persona.objects.filter(ruc=request.GET['ruc']):
                                    per = Persona.objects.get(cedula=request.GET['ruc'])
                                    return JsonResponse({"result": True, 'data': {"nombres": per.nombres}})

                    return JsonResponse({"result": False})
                except Exception as ex:
                    return JsonResponse({"result": False})

            return HttpResponseRedirect(request.path)
        else:
            try:
                if 'persona' in request.session:
                    data['perfildonante'] = ContribuidorDonacion.objects.filter(persona=request.session['persona']).exists()

                form = ContribuidorDonacionForm()
                data['form'] = form
                data['publicacionesexternas'] = PublicacionDonacion.objects.filter(estado=2, fechafinentrega__gte=currenttime.date(), status=True).annotate(PUBLICADO_HACE=(currenttime - F('fecha_creacion')), DIAS_FIN_RECEPCION=(F('fechafinrecepcion') - F('fechainiciorecepcion'))).order_by('estadoprioridad')
                data['title'] = "Donaciones"
                return render(request, "adm_publicaciondonacion/adddonacion.html", data)
            except Exception as ex:
                pass