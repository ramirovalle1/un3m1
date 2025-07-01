# -*- coding: latin-1 -*-
import os
from datetime import datetime, date
import code128
import pyqrcode
from django.contrib.auth.decorators import login_required
from django.db.models import Q, F, Sum
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.loader import get_template
from django.template import Context
from decorators import secure_module, last_access
from matricula.funciones import valid_intro_module_estudiante, get_nivel_matriculacion
from matricula.models import PeriodoMatricula
from matricula.forms import MatriculaAdmisionDiscapacidadForm, MatriculaAdmisionPersonaPPLForm
from sagest.models import Rubro, TipoOtroRubro
from settings import SITE_STORAGE
from sga.commonviews import adduserdata, obtener_reporte
from sga.funciones import log, null_to_decimal, generar_nombre
from sga.models import Matricula, Inscripcion, Nivel, MESES_CHOICES, ConfirmarMatricula, AuditoriaMatricula, \
    MateriaAsignada, TipoArchivo, Archivo, HistorialPersonaPPL, Discapacidad, InstitucionBeca
from sga.funcionesxhtml2pdf import conviert_html_to_pdfsavecertificados
from django.db import connections, transaction
from sga.templatetags.sga_extras import encrypt


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    valid, msg_error = valid_intro_module_estudiante(request, 'admision')
    if not valid:
        return HttpResponseRedirect(f"/?info={msg_error}")
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    inscripcion = perfilprincipal.inscripcion
    hoy = datetime.now().date()

    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'loadCalendar':
                try:
                    if not 'idn' in request.POST:
                        raise NameError(u"Datos no enocntrados")
                    if not Nivel.objects.values('id').filter(pk=int(request.POST['idn'])).exists():
                        raise NameError(u"Datos del nivel no encontrado")
                    nivel = Nivel.objects.get(pk=int(request.POST['idn']))
                    if 'mover' in request.POST:
                        mover = request.POST['mover']
                        if mover == 'before':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            pmes = mes - 1
                            if pmes == 0:
                                pmes = 12
                                panio = anio - 1
                            else:
                                panio = anio

                        elif mover == 'after':
                            mes = int(request.POST['mes'])
                            anio = int(request.POST['anio'])
                            pmes = mes + 1
                            if pmes == 13:
                                pmes = 1
                                panio = anio + 1
                            else:
                                panio = anio
                        else:
                            pmes = hoy.month
                            panio = hoy.year
                    else:
                        pmes = hoy.month
                        panio = hoy.year
                    pdia = 1
                    lista = {}
                    for i in range(1, 43, 1):
                        dia = {i: 'no'}
                        lista.update(dia)
                        ff = {i: None}
                    comienzo = False
                    fin = False
                    for i in lista.items():
                        try:
                            fecha = date(panio, pmes, pdia)
                            if fecha.isoweekday() == i[0] and fin is False and comienzo is False:
                                comienzo = True
                        except Exception as ex:
                            pass
                        if comienzo:
                            try:
                                fecha = date(panio, pmes, pdia)
                            except Exception as ex:
                                fin = True
                        if comienzo and fin is False:
                            dia = {i[0]: pdia}
                            pdia += 1
                            lista.update(dia)
                    data['pdia'] = pdia
                    data['pmes'] = pmes
                    data['panio'] = panio
                    data['mes'] = MESES_CHOICES[pmes - 1]
                    data['ws'] = [0, 7, 14, 21, 28, 35]
                    data['dwnm'] = ['lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo']
                    data['dwn'] = [1, 2, 3, 4, 5, 6, 7]
                    data['lista'] = lista
                    data['nivel'] = nivel
                    template = get_template("matricula/pregrado/view_calendario_matricula.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", "json_content": json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Ocurrio un error. <br> %s" % ex})

            elif action == 'detalle_valores':
                try:
                    matricula = Matricula.objects.get(pk=int(request.POST['id']))
                    materias = MateriaAsignada.objects.filter(matricula=matricula, cobroperdidagratuidad=True)
                    cobro = 2
                    valor_x_materia = 15
                    valor_total = materias.count() * valor_x_materia
                    if matricula.inscripcion.estado_gratuidad == 3:
                        mensaje = u"Estimado estudiante registra perdida de gratuidad reportado por la SENESCYT. Debe cancelar por las asignaturas que se generó por concepto de matrícula, se detallan a continuación:"
                        cobro = 3
                    else:
                        mensaje = u"Estimado estudiante registra una deuda por concepto de matrícula. Debe cancelar por las asignaturas que se generó por concepto de matrícula, se detallan a continuación:"
                        cobro = 2
                    if matricula.inscripcion.sesion_id == 13:
                        tiporubromatricula = TipoOtroRubro.objects.get(pk=3019)
                    else:
                        tiporubromatricula = TipoOtroRubro.objects.get(pk=3011)
                    data['mensaje'] = mensaje
                    #data['valorgrupo'] = valorgrupo
                    data['matricula'] = matricula
                    tiporubromatricula = tiporubromatricula
                    valormatricula = null_to_decimal(Rubro.objects.filter(matricula=matricula, status=True, tipo=tiporubromatricula).aggregate(valor=Sum('valortotal'))['valor'])
                    data['valormatricula'] = valormatricula
                    data['valorpagar'] = valormatricula
                    data['valor_x_materia'] = valor_x_materia
                    data['materiasasignadas'] = materias
                    template = get_template("matriculas/detalle_matricula_admision.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'html': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos. %s" % ex})

            elif action == 'aceptarAutomatricula':
                try:
                    termino = int(request.POST['termino']) if 'termino' in request.POST and request.POST['termino'] else 0
                    if not termino:
                        raise NameError(u"Debe aceptar los terminos.")
                    if not 'admision_documento' in request.FILES:
                        raise NameError(u"Favor subir el archivo de la copia de cédula o pasaporte")
                    if not 'admision_bachiller' in request.FILES:
                        raise NameError(u"Favor subir el archivo de la acta de bachiller")
                    if not 'admision_tipo_documento' in request.POST or not request.POST['admision_tipo_documento']:
                        raise NameError(u"Favor seleccione el tipo de CÉDULA DE CIUDADANÍA")
                    if not 'admision_tipo_bachiller' in request.POST or not request.POST['admision_tipo_bachiller']:
                        raise NameError(u"Favor seleccione si es ACTA DE GRADO DE BACHILLER o TITULO DE BACHILLER")
                    if not inscripcion.matricula_set.values("id").filter(nivel__periodo=periodo, automatriculaadmision=True, termino=False).exists():
                        raise NameError(u"No existe matricula por confirmar")
                    if not 'admision_discapacidad' in request.POST:
                        raise NameError(u"Favor conteste si tiene discapacidad")
                    if not 'admision_ppl' in request.POST:
                        raise NameError(u"Favor conteste si es una persona privada de la libertad")

                    nfileDocumento = None
                    if 'admision_documento' in request.FILES:
                        nfileDocumento = request.FILES['admision_documento']
                        extensionDocumento = nfileDocumento._name.split('.')
                        tamDocumento = len(extensionDocumento)
                        exteDocumento = extensionDocumento[tamDocumento - 1]
                        if nfileDocumento.size > 4194304:
                            raise NameError(u"Error al cargar la cédula/pasaporte, el tamaño del archivo es mayor a 4 Mb.")
                        if not exteDocumento.lower() == 'pdf':
                            raise NameError(u"Error al cargar la cédula/pasaporte, solo se permiten archivos .pdf")
                    nfileBachiller = None
                    if 'admision_bachiller' in request.FILES:
                        nfileBachiller = request.FILES['admision_bachiller']
                        extensionBachiller = nfileBachiller._name.split('.')
                        tamBachiller = len(extensionBachiller)
                        exteBachiller = extensionBachiller[tamBachiller - 1]
                        if nfileBachiller.size > 4194304:
                            raise NameError(u"Error al cargar la acta de grado, el tamaño del archivo es mayor a 4 Mb.")
                        if not exteBachiller.lower() == 'pdf':
                            raise NameError(u"Error al cargar el acta de grado, solo se permiten archivos .pdf")

                    nfileDocumento._name = generar_nombre("dp_documento", nfileDocumento._name)
                    tdocum = TipoArchivo.objects.get(pk=int(request.POST['admision_tipo_documento']))
                    nombreDocumento = "Admisión tipo de documento %s de la persona: %s " % (tdocum.nombre, persona.__str__())
                    archivoDocumento = Archivo(nombre=nombreDocumento,
                                               fecha=datetime.now().date(),
                                               archivo=nfileDocumento,
                                               tipo=tdocum,  # ARCHIVO_TIPO_GENERAL,
                                               inscripcion=inscripcion)
                    archivoDocumento.save(request)

                    nfileBachiller._name = generar_nombre("dp_actagradobachiller", nfileBachiller._name)
                    tacta = TipoArchivo.objects.get(pk=int(request.POST['admision_tipo_bachiller']))
                    nombreBachiller = "Admisión tipo documento %s de la persona: %s " % (tacta.nombre, persona.__str__())
                    archivoBachiller = Archivo(nombre=nombreBachiller,
                                               fecha=datetime.now().date(),
                                               archivo=nfileDocumento,
                                               tipo=tacta,  # ARCHIVO_TIPO_GENERAL,
                                               inscripcion=inscripcion)
                    archivoBachiller.save(request)

                    if 'admision_discapacidad' in request.POST:
                        tiene_discapacidad = int(request.POST['admision_discapacidad'])
                        if tiene_discapacidad == 1:
                            if not 'documento_discapacidad' in request.FILES:
                                raise NameError(u"Favor suba documento de carné de discapacidad")
                            nfileDiscapacidad = None
                            nfileDiscapacidad = request.FILES['documento_discapacidad']
                            extensionDiscapacidad = nfileDiscapacidad._name.split('.')
                            tamDiscapacidad = len(extensionDiscapacidad)
                            exteDiscapacidad = extensionDiscapacidad[tamDiscapacidad - 1]
                            if nfileDiscapacidad.size > 4194304:
                                raise NameError(u"Error al cargar el documento de discapacidad, el tamaño del archivo es mayor a 4 Mb.")
                            if not exteDiscapacidad.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de discapacidad, solo se permiten archivos .pdf")

                            fDi = MatriculaAdmisionDiscapacidadForm(request.POST, request.FILES)
                            if not fDi.is_valid():
                                for k, v in fDi.errors.items():
                                    raise NameError(v[0])
                            perfil = persona.mi_perfil()
                            perfil.tienediscapacidad = True
                            perfil.tipodiscapacidad = fDi.cleaned_data['tipodiscapacidad']
                            perfil.porcientodiscapacidad = fDi.cleaned_data['porcientodiscapacidad']
                            perfil.carnetdiscapacidad = fDi.cleaned_data['carnetdiscapacidad']
                            perfil.institucionvalida = fDi.cleaned_data['institucionvalida']
                            nfileDiscapacidad._name = generar_nombre("archivosdiscapacidad_", nfileDiscapacidad._name)
                            perfil.archivo = nfileDiscapacidad
                            perfil.estadoarchivodiscapacidad = 1
                            perfil.save(request)
                            log(u'Modifico tipo de discapacidad en proceso de matrícula: %s' % persona, request, "edit")

                    if 'admision_ppl' in request.POST:
                        es_ppl = int(request.POST['admision_ppl'])
                        if es_ppl == 1:
                            if not 'archivoppl' in request.FILES:
                                raise NameError(u"Por favor suba documento de persona privadad de la libertad")
                            nfilePPL = None
                            nfilePPL = request.FILES['archivoppl']
                            extensionPPL = nfilePPL._name.split('.')
                            tamPPL = len(extensionPPL)
                            extePLL = extensionPPL[tamPPL - 1]
                            if nfilePPL.size > 4194304:
                                raise NameError(u"Error al cargar el documento de persona privada de libertad, el tamaño del archivo es mayor a 4 Mb.")
                            if not extePLL.lower() == 'pdf':
                                raise NameError(u"Error al cargar el documento de persona privada de libertad, solo se permiten archivos .pdf")
                            nfilePPL = request.FILES['archivoppl']
                            nfilePPL._name = generar_nombre("archivoppl_", nfilePPL._name)
                            fPPL = MatriculaAdmisionPersonaPPLForm(request.POST, request.FILES)
                            if not fPPL.is_valid():
                                for k, v in fPPL.errors.items():
                                    raise NameError(v[0])
                            if HistorialPersonaPPL.objects.values("id").filter(persona=inscripcion.persona, fechaingreso=fPPL.cleaned_data['fechaingresoppl']).exists():
                                historialppl = HistorialPersonaPPL.objects.filter(persona=inscripcion.persona, fechaingreso=fPPL.cleaned_data['fechaingresoppl'])[0]
                                historialppl.observacion = fPPL.cleaned_data['observacionppl'] if fPPL.cleaned_data['observacionppl'] else None,
                                historialppl.archivo = nfilePPL,
                                historialppl.centrorehabilitacion = fPPL.cleaned_data['centrorehabilitacion'] if fPPL.cleaned_data['centrorehabilitacion'] else None
                                historialppl.lidereducativo = fPPL.cleaned_data['lidereducativo'] if fPPL.cleaned_data['lidereducativo'] else None
                                historialppl.correolidereducativo = fPPL.cleaned_data['correolidereducativo'] if fPPL.cleaned_data['correolidereducativo'] else None
                                historialppl.telefonolidereducativo = fPPL.cleaned_data['telefonolidereducativo'] if fPPL.cleaned_data['telefonolidereducativo'] else None
                            else:
                                historialppl = HistorialPersonaPPL(persona=inscripcion.persona,
                                                                   observacion=fPPL.cleaned_data['observacionppl'] if fPPL.cleaned_data['observacionppl'] else None,
                                                                   archivo=nfilePPL,
                                                                   fechaingreso=fPPL.cleaned_data['fechaingresoppl'],
                                                                   fechasalida=None,
                                                                   centrorehabilitacion=fPPL.cleaned_data['centrorehabilitacion'] if fPPL.cleaned_data['centrorehabilitacion'] else None,
                                                                   lidereducativo=fPPL.cleaned_data['lidereducativo'] if fPPL.cleaned_data['lidereducativo'] else None,
                                                                   correolidereducativo=fPPL.cleaned_data['correolidereducativo'] if fPPL.cleaned_data['correolidereducativo'] else None,
                                                                   telefonolidereducativo=fPPL.cleaned_data['telefonolidereducativo'] if fPPL.cleaned_data['telefonolidereducativo'] else None,
                                                                   )
                                historialppl.save(request)
                                log(u'Adiciono registro PPL desde matrícula admisión: %s' % historialppl, request, "add")
                        else:
                            if persona.ppl:
                                persona.ppl = False
                                persona.observacionppl = None
                                log(u'Edito registro PPL desde matrícula admisión: %s' % persona, request, "edit")
                                persona.save(request)
                    matricula = inscripcion.matricula_set.filter(nivel__periodo=periodo, automatriculaadmision=True, termino=False)[0]
                    matricula.termino = True
                    matricula.fechatermino = datetime.now()
                    matricula.save(request)
                    log(u'Acepto los terminos de la matricula: %s' % matricula, request, "edit")
                    if not matricula.confirmarmatricula_set.filter(matricula=matricula):
                        confirmar = ConfirmarMatricula(matricula=matricula, estado=True)
                        confirmar.save(request)
                        log(u'Confirmo la matricula: %s' % confirmar, request, "add")
                    del request.session['matricula']
                    del request.session['periodos_estudiante']
                    del request.session['periodo']
                    return JsonResponse({'result': 'ok', 'mensaje': u"Se guardo correctamente la matrícula"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos. %s" % ex.__str__()})

            elif action == 'rechazoAutomatricula':
                try:
                    id = int(request.POST['id']) if 'id' in request.POST and request.POST['id'] else 0
                    if not Inscripcion.objects.filter(pk=id):
                        raise NameError(u"No se reconocio al estudiante.")
                    inscripcion = Inscripcion.objects.get(pk=id)
                    matricula = inscripcion.matricula_set.filter(automatriculaadmision=True, termino=False)[0]
                    rubro = Rubro.objects.filter(matricula=matricula, status=True)
                    if rubro:
                        if Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos():
                            raise NameError(u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados.")
                    delmatricula = matricula
                    auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                                   periodo=matricula.nivel.periodo,
                                                   tipo=3)
                    auditoria.save(request)
                    matricula.delete()
                    del request.session['matricula']
                    del request.session['periodos_estudiante']
                    del request.session['periodo']
                    log(u'Elimino matricula: %s' % delmatricula, request, "del")
                    return JsonResponse({"result": "ok", 'mensaje': u"Se elimino correctamente la matrícula"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al rechazar la matrícula"})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']
        else:
            try:
                periodomatricula = None
                matricula = None

                if not PeriodoMatricula.objects.values('id').filter(status=True, activo=True, tipo=1).exists():
                    raise NameError(u"Estimado/a aspirante, el periodo de matriculación se encuentra inactivo")
                periodomatricula = PeriodoMatricula.objects.filter(status=True, activo=True, tipo=1)
                if periodomatricula.count() > 1:
                    raise NameError(u"Estimado/a aspirante, proceso de matriculación no se encuentra activo")
                periodomatricula = periodomatricula[0]
                if not periodomatricula.esta_periodoactivomatricula():
                    raise NameError(u"Estimado/a aspirante, el periodo de matriculación se encuentra inactivo")
                # if inscripcion.tiene_perdida_carrera(periodomatricula.num_matriculas):
                #     raise NameError(u"ATENCIÓN: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                if periodomatricula.valida_coordinacion:
                    if not inscripcion.coordinacion in periodomatricula.coordinaciones():
                        raise NameError(u"Estimado/a aspirante, su coordinación/facultad no esta permitida para la matriculación")
                if periodomatricula.periodo and inscripcion.tiene_automatriculaadmision_por_confirmar(periodomatricula.periodo):
                    data['inscripcion'] = inscripcion
                    data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                    data['periodomatricula'] = periodomatricula
                    data['inscripcionmalla'] = inscripcion.malla_inscripcion()
                    data['matricula'] = matricula = inscripcion.matricula_set.filter(automatriculaadmision=True, termino=False, nivel__periodo=periodomatricula.periodo)[0]
                    data['valor_pendiente'] = matricula.total_saldo_rubro()
                    data['valor_pagados'] = matricula.total_pagado_rubro()
                    data['minivel'] = inscripcion.mi_nivel().nivel
                    data['title'] = "Confirmación de matrícula"
                    data['discapacidades'] = Discapacidad.objects.filter(status=True)
                    data['institucionesvalida'] = InstitucionBeca.objects.filter(tiporegistro=2, status=True)
                    data['materiassignadas'] = inscripcion.materias_automatriculaadmision_por_confirmar(periodomatricula.periodo)
                    return render(request, "matricula/admision/confirmar_automatricula.html", data)
                if periodo and periodomatricula and periodomatricula.periodo.id == periodo.id and inscripcion.persona.tiene_matricula_periodo(periodo):
                    matricula = inscripcion.matricula_periodo2(periodo)
                    if ConfirmarMatricula.objects.values('id').filter(matricula=matricula).exists():
                        raise NameError(f"Estimado/a aspirante, le informamos que ya se encuentra matriculado en el Periodo {periodo.__str__()}. <br>Verificar en el módulo <a href='/alu_materias' class='bloqueo_pantalla'>Mis Materias</a>")
                raise NameError(u"Funcionalidad no se encuentra activa para aspirantes")
                # return render(request, "matricula/pregrado/view.html", data)
            except Exception as ex:
                data['msg_error'] = ex.__str__()
                return render(request, "matricula/view.html", data)
