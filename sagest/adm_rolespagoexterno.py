# -*- coding: latin-1 -*-


from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db.models.query_utils import Q
from datetime import datetime

from sga.funciones import MiPaginador, variable_valor
from sga.funcionesxhtml2pdf import conviert_html_to_pdf

from django.template.loader import get_template

from decorators import last_access
from sagest.models import RolPago, DistributivoPersonaHistorial
from sga.commonviews import obtener_reporte

from sga.models import Persona, MESES_CHOICES


@last_access
@transaction.atomic()
def view(request):
    data = {}
    data['tipoentrada'] = 'SGA'
    data['url_'] = request.path
    data['currenttime'] = datetime.now()
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']


            if action == 'consultacedula':
                try:
                    cedula = request.POST['cedula'].strip().upper()
                    datospersona = None
                    idgenero = 0
                    if Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS'+cedula)) | Q(cedula=cedula[2:])).exists():
                        datospersona = Persona.objects.get(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS'+cedula)) | Q(cedula=cedula[2:]))
                    if datospersona:
                        if datospersona.sexo:
                            idgenero = datospersona.sexo_id
                        return JsonResponse({"result": "ok", "apellido1": datospersona.apellido1, "apellido2": datospersona.apellido2,
                                             "nombres": datospersona.nombres, "email": datospersona.email, "telefono": datospersona.telefono, "idgenero": idgenero,
                                             'nacionalidad':datospersona.nacionalidad})
                    else:
                        return JsonResponse({"result": "no"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})


            if action == 'detallerol':
                try:
                    data['detallerol'] = registro = RolPago.objects.get(pk=int(request.POST['id']), status=True)
                    data['detalleinformativo'] = registro.detallerolinformativo()
                    data['detalleingreso'] = registro.detallerolingreso()
                    data['detalleegreso'] = registro.detallerolegreso()
                    template = get_template("adm_rolespagoexterno/detallerol.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})


        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            data['action'] = action = request.GET['action']

            if action=='consultasolicitud':
                try:
                    cedula=request.GET['cedula'].upper()
                    tipo=int(request.GET['tipo'])
                    if tipo == 1:
                        if not Persona.objects.filter(cedula=cedula).exists():
                                return JsonResponse({"result": 'bad',
                                              "mensaje": "No se encontro registro en la aplicacion con esta identificacion"})
                    elif tipo == 2:
                        if not cedula[:2] == 'VS':
                            return JsonResponse({"result": 'bad',
                                                 "mensaje": "Para consultar por pasaporte no olvides colocar VS al principio"})
                        if not Persona.objects.filter(pasaporte=cedula).exists():
                            return JsonResponse({"result": 'bad',
                                                 "mensaje": "No se encontro registro en la aplicacion con esta identificacion"})

                    data['persona']=persona=Persona.objects.get(Q(cedula=cedula) | Q(pasaporte=cedula))
                    roles = RolPago.objects.filter(periodo__estado=5, periodo__status=True, persona=persona, status=True)
                    data['reporte_0'] = obtener_reporte('rol_pago')
                    # data['roles'] = roles

                    paging = MiPaginador(roles, 25)
                    p = 1
                    try:
                        if 'pagerol' in request.GET:
                            p = int(request.GET['pagerol'])
                        page = paging.page(p)
                    except Exception as ex:
                        page = paging.page(p)
                    data['paging'] = paging
                    data['rangospaging'] = paging.rangos_paginado(p)
                    data['page'] = page
                    data['roles'] = page.object_list

                    template = get_template("adm_rolespagoexterno/inforolexterno.html")
                    return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    mensaje = 'Intentelo mas tarde'
                    return JsonResponse({"result": 'bad', "mensaje": mensaje})

            if action == 'listaResultadosPaginacion':
                try:
                    cedula, tipo, anionac = request.GET.get('cedula',''), int(request.GET.get('tipo','')), int(request.GET.get('anionac',''))
                    anioselect, messelect = 0, 0
                    persona = Persona.objects.get(status=True, cedula=cedula)
                    if persona.nacimiento.year == anionac:
                        if 'anio' in request.GET:
                            anioselect = int(request.GET['anio'])
                        if 'mes' in request.GET:
                            messelect = int(request.GET['mes'])
                        if tipo == 1:
                            if not DistributivoPersonaHistorial.objects.filter(persona__cedula=cedula, status=True, regimenlaboral_id=3).exists():
                                    return JsonResponse({"result": 'bad',
                                                  "mensaje": "No se encontro registro de jubilado con esta identificación"})
                        elif tipo == 2:
                            if not cedula[:2] == 'VS':
                                return JsonResponse({"result": 'bad',
                                                     "mensaje": "Para consultar por pasaporte no olvides colocar VS al principio"})
                            if not DistributivoPersonaHistorial.objects.filter(persona__pasaporte=cedula, status=True, regimenlaboral_id=3).exists():
                                return JsonResponse({"result": 'bad',
                                                     "mensaje": "No se encontro registro de jubilado con esta identificación"})

                        data['persona']=persona=DistributivoPersonaHistorial.objects.filter(Q(persona__cedula=cedula) | Q(persona__pasaporte=cedula), status=True, regimenlaboral_id=3)[0]
                        roles = RolPago.objects.filter(periodo__estado=5, periodo__status=True, persona=persona.persona, status=True)
                        if anioselect > 0:
                            roles = roles.filter(periodo__anio=anioselect)
                        if messelect > 0:
                            roles = roles.filter(periodo__mes=messelect)
                        aniosrol = RolPago.objects.values_list('periodo__anio').distinct().order_by('-periodo__anio')
                        anios = []
                        for anio in aniosrol:
                            if anio not in anios:
                                anios.append(anio[0])
                        paging = MiPaginador(roles, 15)
                        p = 1
                        try:
                            if 'page' in request.GET:
                                p = int(request.GET['page'])
                            page = paging.page(p)
                        except:
                            page = paging.page(1)
                        data['paging'] = paging
                        data['rangospaging'] = paging.rangos_paginado(p)
                        data['page'] = page
                        data['roles'] = page.object_list
                        data['anios'] = anios
                        data['meses'] = MESES_CHOICES
                        data['anioselect'] = anioselect
                        data['messelect'] = messelect
                        template = get_template("adm_rolespagoexterno/paginacion.html")
                        json_content = template.render(data)
                        return JsonResponse({"result": "ok", 'data': json_content})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Datos incorrectos"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos"})

            if action == 'reportepdf':
                try:
                    data['rol'] = rol = RolPago.objects.get(pk=int(request.GET['id']), status=True)
                    data['detalleinformativo'] = rol.detallerolinformativo()
                    data['detalleingreso'] = rol.detallerolingreso()
                    data['detalleegreso'] = rol.detallerolegreso()
                    return conviert_html_to_pdf(
                        'adm_rolespagoexterno/reportepdf.html',
                        {
                            'pagesize': 'A4',
                            'data': data,
                        }
                    )
                except Exception as ex:
                    pass


            return HttpResponseRedirect(request.path)
        else:
            try:
                data['title'] = u'Roles de pago'
                data['institucion'] = u'UNIVERSIDAD ESTATAL DE MILAGRO'
                data['public_key'] = variable_valor('GOOGLE_RECAPTCHA_PUBLIC_KEY')
                return render(request, "adm_rolespagoexterno/view.html", data)
            except Exception as ex:
                pass