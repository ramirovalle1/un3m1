# -*- coding: latin-1 -*-
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from datetime import datetime

from decorators import last_access, secure_module
from sga.models import Provincia, Test, PersonaTest, ResultadoTest, Matricula, Inscripcion



from sga.templatetags.sga_extras import encrypt
# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'addregistro':
                try:
                    nombres = request.POST['nombres']
                    sumavalores = int(request.POST['sumavalores'])
                    antecedentesmedicos = request.POST['antecedentesid']
                    edad = request.POST['edadid']
                    sexo = request.POST['genero']
                    provinciaid = request.POST['provinciaid']
                    cantonid = request.POST['cantonid']
                    numerofamilia = request.POST['numerofamilia']
                    personatest = PersonaTest(nombres=nombres,
                                              antecedentesmedicos=antecedentesmedicos,
                                              sexo_id=sexo,
                                              edad=edad,
                                              provincia_id=provinciaid,
                                              canton_id=cantonid,
                                              totalvive=numerofamilia)
                    personatest.save(request)
                    lista = request.POST['lista'].split(',')
                    for elemento in lista:
                        cadena = elemento.split('_')
                        resultadotest = ResultadoTest(personatest=personatest,
                                                      test_id=cadena[0],
                                                      valor=cadena[1])
                        resultadotest.save(request)
                    if sumavalores <=2:
                        resultadotest = 'containercero'
                    if sumavalores >=3 and sumavalores <=5:
                        resultadotest = 'containeruno'
                    if sumavalores >=6 and sumavalores <=11:
                        resultadotest = 'containerdos'
                    if sumavalores >=12:
                        resultadotest = 'containertres'

                    return JsonResponse({'result': 'ok', "mensaje": u"Correcto.", "resultadotest": resultadotest})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'certificadoasistencia':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    data['codi'] = Matricula.objects.get(pk=int(encrypt(request.GET['codi'])))
                    return render(request, "certificadovalido/certificadoasistenciavalido.html", data)
                except Exception as ex:
                    pass

            if action == 'certificadoasistenciaxperiodo':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    data['codi'] = Matricula.objects.get(pk=int(encrypt(request.GET['codi'])))
                    return render(request, "certificadovalido/certificadoasistenciaxperiodovalido.html", data)
                except Exception as ex:
                    pass

            if action == 'certificadomodalidadestudio':
                try:
                    data['title'] = u'Registrar certificado'
                    hoy = datetime.now().date()
                    data['codi'] = Inscripcion.objects.get(pk=int(encrypt(request.GET['codi'])))
                    return render(request, "certificadovalido/certificadomodalidadestudio.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Registrar certificado'
                hoy = datetime.now().date()
                data['codi'] = Matricula.objects.get(pk=int(encrypt(request.GET['codi'])))
                return render(request, "certificadovalido/certificadovalido.html", data)
            except Exception as ex:
                pass