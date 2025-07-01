from datetime import datetime, timedelta

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import RegistrarIngresoCraiForm
from sga.funciones import log
from sga.models import Inscripcion, RegistrarIngresoCrai, ActividadesCrai, RegistrarActividadesCrai, Profesor, \
    TipoServicioCrai


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()

def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    data['periodo'] = periodo = request.session['periodo']
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addinscripcion':
            try:
                if 'id' in request.POST:
                    form = RegistrarIngresoCraiForm(request.POST)
                    if form.is_valid():
                        inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                        reg = RegistrarIngresoCrai(inscripcion=inscripcion,
                                                   profesor_id=form.cleaned_data['profesor'],
                                                   tiposerviciocrai=form.cleaned_data['tiposerviciocrai'],
                                                   actividad=form.cleaned_data['actividad'],
                                                   fecha=datetime.now().date(),
                                                   horainicio=datetime.now().time())
                        reg.save(request)
                        log(u'Adicionó una nueva visita de incripcion crai: %s' % reg.inscripcion.persona, request, "add")
                        return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addaux':
            try:
                inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                if not RegistrarIngresoCrai.objects.filter(inscripcion=inscripcion, tiposerviciocrai_id=1, actividad='BIBLIOTECA', fecha=datetime.now().date()).exists():
                    reg = RegistrarIngresoCrai(inscripcion=inscripcion,
                                               tiposerviciocrai_id=1,
                                               actividad='BIBLIOTECA',
                                               fecha=datetime.now().date(),
                                               horainicio=datetime.now().time())
                    reg.save(request)
                    log(u'Adicionó una nueva visita de incripcion crai - pantalla: %s' % reg.inscripcion.persona, request, "add")
                else:
                    regaux = RegistrarIngresoCrai.objects.filter(inscripcion=inscripcion, tiposerviciocrai_id=1, actividad='BIBLIOTECA', fecha=datetime.now().date())[0]
                    horaingreso = datetime(regaux.fecha.year, regaux.fecha.month, regaux.fecha.day, regaux.horainicio.hour, regaux.horainicio.minute, regaux.horainicio.second) + timedelta(hours=3, minutes=00, seconds=00)
                    horaconsulta = datetime.now()
                    if horaconsulta > horaingreso:
                        reg = RegistrarIngresoCrai(inscripcion=inscripcion,
                                                   tiposerviciocrai_id=1,
                                                   actividad='BIBLIOTECA',
                                                   fecha=datetime.now().date(),
                                                   horainicio=datetime.now().time())
                        reg.save(request)
                        log(u'Adicionó una nueva visita de incripcion crai - pantalla: %s' % reg.inscripcion.persona, request, "add")
                    else:
                        reg = regaux

                if RegistrarActividadesCrai.objects.filter(registraringresocrai=reg, actividadescrai_id=int(request.POST['ida'])).exists():
                    transaction.set_rollback(True)
                    # return JsonResponse({"result": "bad", "mensaje": "Actividad ya seleccionada."})
                    return JsonResponse({"result": "ok", "mensaje": "Se registro correctamente..."})
                reg1 = RegistrarActividadesCrai(registraringresocrai=reg, actividadescrai_id=int(request.POST['ida']))
                reg1.save(request)
                log(u'Adicionó una actividad al CRAI UNEMI: %s' % reg1, request, "add")
                return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})

            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al enviar los datos."})

        if action == 'existe_inscripcion_activa':
            try:
                return JsonResponse({"result": "ok", "existe": False})
                # if 'id' in request.POST:
                #     inscripcion = Inscripcion.objects.get(pk=int(request.POST['id']))
                #     if RegistrarIngresoCrai.objects.filter(status=True, inscripcion=inscripcion, fecha=datetime.now().date(), horafin__isnull=True).exists():
                #         return JsonResponse({"result": "ok", "existe": True, "mensaje": inscripcion.persona.nombre_completo_inverso()+', ya se encuentra registrado el dia de hoy...'})
                #     else:
                #         return JsonResponse({"result": "ok", "existe": False})
                # else:
                #     return JsonResponse({"result": "bad", "mensaje": u"Error al validar los datos."})
            except Exception as ex:
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        if action == 'addauxdocente':
            try:
                if 'id' in request.POST:
                    if 'idp' in request.POST:
                        reg = RegistrarIngresoCrai(inscripcion_id=int(request.POST['id']),
                                                   profesor_id=int(request.POST['idp']),
                                                   tiposerviciocrai_id=int(request.POST['idt']),
                                                   actividad='VISITA DOCENTE',
                                                   fecha=datetime.now().date(),
                                                   horainicio=datetime.now().time())
                        reg.save(request)
                        log(u'Adicionó una nueva visita de incripcion crai - pantalla: %s' % reg.inscripcion.persona, request, "add")
                        return JsonResponse({"result": "ok", "mensaje": u'Se registro correctamente...'})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'addinscripcion':
                try:
                    data['title'] = u'Registrar Ingreso CRAI - Seleccione al Docente de la visita'
                    # data['s'] = request.GET['s']
                    data['id'] = request.GET['id']
                    # data['idm'] = request.GET['idm']
                    profesores = Profesor.objects.filter(status=True, profesormateria__materia__materiaasignada__matricula__id=int(request.GET['idm']), profesormateria__materia__materiaasignada__status=True, profesormateria__status=True).distinct()
                    data['profesores'] = profesores
                    data['tiposerviciocrai'] = TipoServicioCrai.objects.filter(status=True).exclude(id=1)
                    data['colores'] = [u"#ff0000", u"#ff8000", u"#ffff00", u"#80ff00", u"#00ffff", u"#0080ff", u"#8000ff", u"#b87333", u"#bf00ff", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8"]
                    return render(request, "adm_crai_pantalla/addinscripcion.html", data)
                except Exception as ex:
                    pass

            if action == 'addaux':
                try:
                    data['title'] = u'Registrar Actividad CRAI Biblioteca'
                    data['inscripcion'] = Inscripcion.objects.get(pk=int(request.GET['idi']))
                    data['actividaid'] = int(request.GET['ida'])
                    data['ci'] = request.GET['ci']
                    return render(request, "adm_crai_pantalla/addaux.html", data)
                except Exception as ex:
                    pass

            if action == 'addauxdocente':
                try:
                    data['title'] = u'Registrar Actividad CRAI Docente'
                    data['idi'] = int(request.GET['idi'])
                    data['idp'] = int(request.GET['idp'])
                    data['idt'] = int(request.GET['idt'])
                    data['tiposerviciocrai'] = TipoServicioCrai.objects.filter(pk=int(request.GET['idt']))[0].descripcion
                    return render(request, "adm_crai_pantalla/addauxdocente.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Control de acceso al CRAI UNEMI'
            try:
                search = None
                ids = None
                inscripciones = None
                if 's' in request.GET:
                    search = request.GET['s'].strip()
                    ss = search.split(' ')
                    if len(ss) == 1:
                        inscripciones = Inscripcion.objects.filter(Q(persona__nombres__icontains=search) |
                                                                   Q(persona__apellido1__icontains=search) |
                                                                   Q(persona__apellido2__icontains=search) |
                                                                   Q(persona__cedula__icontains=search) |
                                                                   Q(persona__pasaporte__icontains=search) |
                                                                   Q(identificador__icontains=search) |
                                                                   Q(inscripciongrupo__grupo__nombre__icontains=search) |
                                                                   Q(persona__usuario__username__icontains=search), status=True, matricula__isnull=False).order_by('matricula')[0]
                        # .exclude(registraringresocrai__fecha=datetime.now().date(), registraringresocrai__horafin__isnull=True)
                    else:
                        inscripciones = Inscripcion.objects.filter((Q(persona__nombres__icontains=ss[0]) & Q(persona__nombres__icontains=ss[1])) | (
                                                                    Q(persona__apellido1__icontains=ss[0]) & Q(persona__apellido2__icontains=ss[1])), matricula__isnull=False).order_by('matricula')[0]

                data['search'] = search if search else ""
                data['ids'] = ids if ids else ""
                data['inscripcion'] = inscripciones
                data['actividadescrais'] = ActividadesCrai.objects.filter(status=True).order_by('orden')
                data['colores'] = [u"#ff0000", u"#ff8000", u"#ffff00", u"#80ff00", u"#00ffff", u"#0080ff", u"#8000ff", u"#b87333", u"#bf00ff", u"gold", u"#e5e4e2", u"FF3333", u"8AFF33", u"3370FF", u"D733FF", u"FF33A8"]
                return render(request, "adm_crai_pantalla/view.html", data)
            except Exception as ex:
                pass


