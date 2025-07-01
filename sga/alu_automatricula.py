# -*- coding: UTF-8 -*-
from datetime import datetime, timedelta
import json
from decimal import Decimal

from django.contrib.auth.decorators import login_required
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.db import transaction
from django.db.models import Sum
from django.template.context import Context
from django.template.loader import get_template
from sga.forms import SesionMatriculacionForm
from sga.funciones import log, variable_valor, convertir_fecha, existen_requisitos_becas, remover_caracteres_especiales
from decorators import secure_module, last_access
from sagest.models import Rubro
from settings import MAXIMO_MATERIA_ONLINE, MODALIDAD_DISTANCIA, \
    MATRICULA_ONLINE_SOLODISTANCIA, MATRICULACION_LIBRE, UTILIZA_GRATUIDADES, PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD, \
    NIVEL_MALLA_CERO, PORCIENTO_PERDIDA_TOTAL_GRATUIDAD, MATRICULAR_CON_DEUDA, NOTA_ESTADO_APROBADO, RUBRO_ARANCEL, \
    RUBRO_MATRICULA
from sga.commonviews import adduserdata, materias_abiertas, matricular, nivel_matriculacion, contar_nivel, conflicto_materias_estudiante, matricularpre
from sga.models import Nivel, Materia, Asignatura, Matricula, ConfirmarMatricula, AsignaturaMalla, TipoProfesor, \
    ProfesorMateria, Periodo, Inscripcion, RecordAcademico, InscripcionMalla, Malla, ParticipantesMatrices, \
    PracticasPreprofesionalesInscripcion, ModuloMalla, BecaAsignacion, ConfirmaCapacidadTecnologica, BecaRequisitos, \
    BecaSolicitud, BecaDetalleSolicitud, miinstitucion, BecaSolicitudRecorrido, AuditoriaMatricula
from sga.tasks import send_html_mail, conectar_cuenta


# @login_required(redirect_field_name='ret', login_url='/loginsga')
# @secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    periodo = request.session['periodo']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    # if inscripcion.mi_coordinacion().id == 9:
    #     return HttpResponseRedirect(u"/?info=Proceso no habilitado para estudiantes de admisión.")
    if inscripcion.bloqueomatricula:
        if inscripcion.mi_coordinacion().id == 9:
            return HttpResponseRedirect("/?info=Estimado estudiante, su matrícula se encuentra bloqueada. El procesos solo está aperturado para los que cursarán su segunda matrícula")
        else:
            return HttpResponseRedirect("/?info=Estimado estudiante, su matrícula se encuentra bloqueada, por favor contactarse a secretaria de facultad")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'materiasabiertas':
                return materias_abiertas(request, True)

            elif action == 'matricular':
                acepta_t = int(request.POST['acepta_t']) if 'acepta_t' in request.POST and request.POST['acepta_t'] else 0
                if acepta_t==0:
                    return JsonResponse({"result": "bad", "reload": False, "mensaje": u"Favor acepte los terminos"})
                validartodo = True if (int(request.POST['rtlv']) if request.POST['rtlv'] != '' else 0) == 1 else False
                return matricular(request, validartodo, True)

            elif action == 'sesionmatricula':
                try:
                    f = SesionMatriculacionForm(request.POST)
                    if f.is_valid():
                        inscripcion.sesion = f.cleaned_data['sesion']
                        inscripcion.save(request)
                        log(u'Edito seccion matricula: %s - secciÃ³n %s' % (inscripcion, inscripcion.sesion), request, "edit")
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'conflictohorario':
                validar_todo = True if (int(request.POST['rtlv']) if request.POST['rtlv'] != '' else 0) == 1 else False

                mismaterias = json.loads(request.POST['mismaterias'])
                mispracticas= json.loads(request.POST['mispracticas'])
                excluidas = Asignatura.objects.filter(historicorecordacademico__inscripcion=inscripcion, historicorecordacademico__aprobada=False, historicorecordacademico__asistencia__gte=70).distinct()
                materias = Materia.objects.filter(id__in=[int(x) for x in mismaterias]).exclude(asignatura__id__in=excluidas)
                #extraermos los datos de la lista profesormnaterias y paralelo
                listaprofemateriaid_singrupo = []
                listaprofemateriaid_congrupo = []
                for x in mispracticas:
                    if not int(x[1]) > 0:
                        listaprofemateriaid_singrupo.append(int(x[0]))
                    else:
                        listaprofemateriaid_congrupo.append([int(x[0]), int(x[1])])
                profemate = ProfesorMateria.objects.filter(id__in=listaprofemateriaid_singrupo, materia__in=materias)
                nivel = contar_nivel(mismaterias)


                conflicto = ''
                if validar_todo:
                    conflicto = conflicto_materias_estudiante(materias, profemate, listaprofemateriaid_congrupo)


                if conflicto:
                    return JsonResponse({"result": "bad", "mensaje": conflicto})
                #EXTRAMOS LOS DATOS DE LA MATERIA SELECCIONADA
                datos = {}
                if 'idm' in request.POST:
                    if validar_todo:
                        datos = Materia.objects.get(pk=int(request.POST['idm'])).datos_practicas_materia(inscripcion)

                return JsonResponse({"result": "ok", "nivel": nivel, "datos": datos})

            elif action == 'conflictohorario_aux':
                mismaterias = json.loads(request.POST['mismaterias'])

                nivel = contar_nivel(mismaterias)
                return JsonResponse({"result": "ok", "nivel" : nivel})

            elif action == 'addconfirmarmatricula':
                confirmarmatricula = ConfirmarMatricula(matricula_id=request.POST['idmatriculaconfirmar'], estado=True)
                confirmarmatricula.save(request)
                auditoria = AuditoriaMatricula(inscripcion=confirmarmatricula.matricula.inscripcion,
                                               periodo=confirmarmatricula.matricula.nivel.periodo,
                                               tipo=1)
                auditoria.save(request)
                return JsonResponse({"result": "ok"})

            elif action == 'delconfirmarmatricula':
                try:
                    matricula = Matricula.objects.get(pk=request.POST['idmatriculaeliminar'])
                    rubro = Rubro.objects.filter(matricula=matricula, status=True)
                    if rubro:
                        #if rubro.filter(bloqueado=True).exists():
                        #    return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque su deuda fue generada al banco."})
                        if Rubro.objects.filter(matricula=matricula, status=True)[0].tiene_pagos():
                            return JsonResponse({"result": "bad", "mensaje": u"No puede eliminar la matricula, porque existen rubros de la matricula ya cancelados."})
                    delpersona = matricula
                    auditoria = AuditoriaMatricula(inscripcion=matricula.inscripcion,
                                                   periodo=matricula.nivel.periodo,
                                                   tipo=2)
                    auditoria.save(request)
                    matricula.delete()
                    log(u'Elimino matricula: %s' % delpersona, request, "del")
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al eliminar la matricula"})

            elif action == 'addmatriculapagopreunemi':
                return matricularpre(request, True)

            elif action == 'confirmarymatricular':
                try:
                    internet = True if request.POST['internet'] == 'S' else False
                    if not ConfirmaCapacidadTecnologica.objects.filter(persona=inscripcion.persona).exists():
                        conf = ConfirmaCapacidadTecnologica(
                                                persona=inscripcion.persona,
                                                tienepcinternet=internet,
                                                aplicabeca=False,
                                                becaasignada=False,
                                                confirmado=False,
                                                domicilioactualizado=False
                        )
                        conf.save(request)
                    else:
                        ConfirmaCapacidadTecnologica.objects.filter(persona=inscripcion.persona).update(tienepcinternet=internet)

                    if not internet:
                        if periodo is None:
                            return JsonResponse({"result": "bad", "mensaje": "Solo puedan aplicar estudiantes que vayan a matricularse a partir de SEGUNDO NIVEL"})
                        elif existen_requisitos_becas(90, 18):
                            return JsonResponse({"result": "ok"})
                        else:
                            return JsonResponse({"result": "bad", "mensaje": "No existen requisitos de becas configurados para el Periodo %s" % (str(periodo))})
                    else:
                        return JsonResponse({"result": "ok"})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'solicitarbeca':
                try:
                    if not BecaSolicitud.objects.filter(inscripcion=inscripcion, periodocalifica=periodo).exclude(estado=5).exists():
                        requisitos = json.loads(request.POST['lista_items1'])
                        equipo = True if request.POST['equipo'] == 'true' else False
                        internet = True if request.POST['internet'] == 'true' else False
                        beca = BecaSolicitud(inscripcion=inscripcion,
                                             becatipo_id=18,
                                             periodo_id=110,
                                             periodocalifica=periodo,
                                             estado=1,
                                             observacion='SEMESTRE ABRIL-OCTUBRE 2020 MODALIDAD VIRTUAL - ADQUISICIÓN DE UNA TABLET Y/O PLAN DE DATOS'
                        )

                        beca.save(request)

                        for r in requisitos:
                            detalle = BecaDetalleSolicitud(solicitud=beca,
                                                           requisito_id=int(r['id']),
                                                           cumple=True if r['cumple'] == 'SI' else False,
                                                           archivo=None,
                                                           estado=1 if int(r['id']) in [15, 16] else 2,
                                                           observacion='' if int(r['id']) in [15, 16] else 'APROBACIÓN AUTOMÁTICA',
                                                           personaaprueba=None,
                                                           fechaaprueba=None)
                            detalle.save(request)

                        recorrido = BecaSolicitudRecorrido(solicitud=beca,
                                                           observacion="SOLICITADO POR ESTUDIANTE",
                                                           estado=1
                                                           )
                        recorrido.save(request)

                        ConfirmaCapacidadTecnologica.objects.filter(persona=inscripcion.persona).update(tienepcinternet=False,
                                                                                                        aplicabeca=True,
                                                                                                        confirmado=True,
                                                                                                        necesitaequipo=equipo,
                                                                                                        necesitainternet=internet)

                        tituloemail = "Registro de Solicitud de Beca - Semestre ABRIL A OCTUBRE 2020"

                        send_html_mail(tituloemail,
                                       "emails/solicitudbecaestudiante.html",
                                       {'sistema': u'SGA - UNEMI',
                                        'fase': 'SOL',
                                        'fecha': datetime.now().date(),
                                        'hora': datetime.now().time(),
                                        'estudiante': persona,
                                        'autoridad2': '',
                                        't': miinstitucion()
                                        },
                                       persona.lista_emails_envio(),
                                       [],
                                       cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                       )

                        log(u'Agregó solicitud de beca: %s' % persona, request, "add")

                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"La solicitud de la beca ya ha sido creada."})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'enviarmensaje':
                try:
                    asunto = request.POST['asunto'].strip()
                    mensaje = request.POST['mensaje'].strip()
                    destinatario = "soportebienestar@unemi.edu.ec"

                    tituloemail = asunto
                    remitente = inscripcion.persona.nombre_completo_inverso()
                    emailpers = inscripcion.persona.email
                    emailinst = inscripcion.persona.emailinst
                    celular = inscripcion.persona.telefono
                    convencional = inscripcion.persona.telefono_conv

                    send_html_mail(tituloemail,
                                   "emails/solicitudbecaestudiante.html",
                                   {'sistema': u'SGA - UNEMI',
                                    'fase': 'MEN',
                                    'fecha': datetime.now().date(),
                                    'hora': datetime.now().time(),
                                    'mensaje': mensaje,
                                    'remitente': remitente,
                                    'emailpers': emailpers,
                                    'emailinst': emailinst,
                                    'celular': celular,
                                    'convencional' : convencional,
                                    't': miinstitucion()
                                    },
                                   [destinatario],
                                   [],
                                   cuenta=variable_valor('CUENTAS_CORREOS')[0]
                                   )

                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al enviar el mensaje."})

            elif action == 'diferirarancel':
                try:
                    idmatricula=int(request.POST['phase'])

                    mat = Matricula.objects.values('aranceldiferido').get(pk=idmatricula)
                    if mat['aranceldiferido'] == 1:
                        return JsonResponse({"result": "bad", "mensaje": u"El rubro arancel ya ha sido diferido. Verifique módulo Mis Finanzas"})

                    if Rubro.objects.filter(matricula_id=idmatricula, tipo_id=RUBRO_ARANCEL).exists():
                        arancel = Rubro.objects.get(matricula_id=idmatricula, tipo_id=RUBRO_ARANCEL)
                        nombrearancel = arancel.nombre
                        valorarancel = Decimal(arancel.valortotal).quantize(Decimal('.01'))
                        c1 = (valorarancel/3).quantize(Decimal('.01'))
                        c2 = c1
                        c3 = valorarancel - (c1 + c2)

                        rubromatricula = Rubro.objects.get(matricula_id=idmatricula, tipo_id=RUBRO_MATRICULA)
                        rubromatricula.relacionados = None
                        rubromatricula.save(request)

                        lista = [[1, c1, convertir_fecha('30-06-2021')],
                                 [2, c2, convertir_fecha('31-07-2021')],
                                 [3, c3, convertir_fecha('31-08-2021')]]

                        for item in lista:
                            rubro = Rubro(tipo_id=RUBRO_ARANCEL,
                                          persona=persona,
                                          relacionados=None,
                                          matricula_id=idmatricula,
                                          # contratorecaudacion = None,
                                          nombre=nombrearancel,
                                          cuota=item[0],
                                          fecha=datetime.now().date(),
                                          fechavence=item[2],
                                          valor=item[1],
                                          iva_id=1,
                                          valoriva=0,
                                          valortotal=item[1],
                                          saldo=item[1],
                                          cancelado=False)
                            rubro.save(request)

                            if item[0] == 1:
                                rubromatricula.relacionados = rubro
                                rubromatricula.save(request)

                        arancel.delete()

                        Matricula.objects.filter(pk=idmatricula).update(aranceldiferido=1)

                        return JsonResponse({"result": "ok"})
                    else:
                        return JsonResponse({"result": "bad", "mensaje": u"No se puede procesar el registro."})

                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos del diferido."})

            elif action == 'verdetalle':
                try:
                    data = {}
                    data = valida_matricular_requisitotitulacion(data, inscripcion)
                    template = get_template("alu_automatricula/detalle.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'verificarequisitos':
                try:
                    periodoultimamat = Matricula.objects.values('nivel__periodo_id').filter(inscripcion=inscripcion, status=True).order_by('-fecha_creacion')[0]
                    if periodoultimamat['nivel__periodo_id'] != periodo.id:
                        return HttpResponseRedirect(u"/?info=El periodo seleccionado no coincide con el de su último registro de matrícula.")

                    umat = Matricula.objects.get(inscripcion=inscripcion, nivel__periodo=periodo, status=True)

                    requisitos = BecaRequisitos.objects.filter(Q(becatipo__isnull=True) | Q(becatipo_id=18)
                                                               , periodo_id=90, status=True, vigente=True).exclude(numero=7).order_by('numero')

                    lista_requisitos = []
                    cumple_todos = True
                    evaluado = False
                    contador = 1
                    lista_nocumplen = ""
                    cnc = 0

                    for req in requisitos:
                        idrequisito = req.id
                        numero = req.numero
                        nombre = req.nombre
                        tipo = req.becatipo.nombre if req.becatipo else ''
                        valor = req.valoresrequisito
                        camposeleccion = 'N'

                        cumple = True

                        if numero == 1 or numero == 2:
                            if evaluado is False:
                                if persona.paisnacimiento_id != 1 and persona.pais_id != 1:
                                    cumple = False
                                    cumple_todos = False
                        elif numero == 3:
                            if not inscripcion.matriculado_periodo(periodo):
                                cumple = False
                                cumple_todos = False
                        elif numero == 4:
                            if umat.tipomatriculalumno() != 'REGULAR':
                                cumple = False
                                cumple_todos = False
                        elif numero == 5:
                            if inscripcion.tiene_sancion():
                                cumple = False
                                cumple_todos = False
                        elif numero == 6:
                            if inscripcion.recordacademico_set.values('id').filter(aprobada=False, valida=True).exists():
                                cumple = False
                                cumple_todos = False
                        elif numero == 8:
                            if persona.tiene_becas_externas_activas():
                                cumple = False
                                cumple_todos= False
                        elif numero == 9:
                            # Campo no existe
                            camposeleccion = 'S'
                            cumple = True
                        elif numero == 10:
                            # Campo no existe
                            camposeleccion = 'S'
                            cumple = True
                        elif numero == 22:
                            if umat.promedio_nota_sin_modulo() < Decimal(valor):
                                cumple = False
                                cumple_todos = False
                        elif numero == 23:
                            if umat.promedio_asistencias_sin_modulo() < Decimal(valor):
                                cumple = False
                                cumple_todos = False
                        elif numero == 24:
                            if persona.mi_ficha().grupoeconomico:
                                if not persona.mi_ficha().grupoeconomico.codigo == valor:
                                    cumple = False
                                    cumple_todos = False
                            else:
                                cumple = False
                                cumple_todos = False


                        if numero == 1 or numero == 2:
                            if evaluado is False:
                                if cumple:
                                    lista_requisitos.append([idrequisito, tipo, nombre, 'SI', numero, camposeleccion])
                                else:
                                    lista_requisitos.append([idrequisito, tipo, nombre, 'NO', numero, camposeleccion])
                                    lista_nocumplen = "No. " + str(numero) + ", " + nombre if lista_nocumplen == '' else lista_nocumplen + ", " + "No. " + str(numero) + ", " + nombre
                                    cnc += 1
                                contador += 1
                                evaluado = True
                        else:
                            if cumple:
                                lista_requisitos.append([idrequisito, tipo, nombre, 'SI', numero, camposeleccion])
                            else:
                                lista_requisitos.append([idrequisito, tipo, nombre, 'NO', numero, camposeleccion])
                                lista_nocumplen = "No. " + str(contador) + ", " + nombre if lista_nocumplen == '' else lista_nocumplen + ", " + "No. " + str(contador) + ", " + nombre
                                cnc += 1
                            contador += 1

                    # cumple_todos = True

                    data['title'] = u'Matriculación online'
                    data['title2'] = "Check List de Requisitos y Condiciones"
                    data['requisitos'] = lista_requisitos

                    if cumple_todos:
                        return render(request, "alu_automatricula/solicitudbeca.html", data)
                    else:
                        data['lista_nocumplen'] = lista_nocumplen
                        data['cantidadnocumple'] = cnc
                        return render(request, "alu_automatricula/requisitosbeca.html", data)

                except Exception as ex:
                    pass

            elif action == 'verrequisitos':
                try:
                    data['inscripcion'] = inscripcion
                    # data['malla'] = inscripcionmalla.malla
                    # data['nivel'] = nivel
                    data['title'] = u'Matriculación online'
                    # data['title2'] = "Listado de Requisitos para Aplicar a Beca por Situación Económica Insuficiente"
                    data['title2'] = "Check List de Requisitos y Condiciones"
                    return render(request, "alu_automatricula/requisitosbeca.html", data)
                    # return render(request, "alu_automatricula/solicitudbeca.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                if 'mostrarmatricula' in request.GET:
                    paso_matricular = True
                else:
                    paso_matricular = False

                validar_tercera_matricula = False

                if inscripcion.graduado() or inscripcion.egresado() or inscripcion.estainactivo() or inscripcion.retiro_carrera():
                    return HttpResponseRedirect("/?info=Solo podrán matricularse estudiantes activos.")

                modalidad_alumno = inscripcion.modalidad_id
                # SI ES MODALIDAD EN LINEA VA DIRECTO A REALIZAR LAS VALIDACIONES YA EXISTENTES
                if modalidad_alumno == 3:
                    permitir_matricular = True
                else:
                    if variable_valor('VALIDAR_CAPACIDAD_TECNOLOGICA'):
                        periodoultimamat = Matricula.objects.values('nivel__periodo_id').filter(inscripcion=inscripcion, status=True).order_by('-fecha_creacion')[0]
                        if periodoultimamat['nivel__periodo_id'] != periodo.id:
                            return HttpResponseRedirect(u"/?info=El periodo seleccionado no coincide con el de su último registro de matrícula.")

                        nivelid = nivel_matriculacion(inscripcion)
                        if nivelid == -1:
                            log(u"El periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()), request, "add")
                            return HttpResponseRedirect(u"/?info=El periodo de matriculación no se encuentra activo")
                        elif nivelid == -2:
                            return HttpResponseRedirect("/?info=No existen niveles con cupo para matricularse")
                        elif nivelid == -3:
                            return HttpResponseRedirect("/?info=No existen paralelos disponibles.")
                        elif nivelid == -4:
                            return HttpResponseRedirect("/?info=No existen paralelos para su nivel.")
                        #
                        # nivel = Nivel.objects.get(pk=nivelid)
                        # inscripcionmalla = InscripcionMalla.objects.db_manager('sga_select').filter(inscripcion_id=inscripcion.id)[0]

                        conf = None
                        if ConfirmaCapacidadTecnologica.objects.filter(persona=inscripcion.persona, status=True).exists():
                            conf = ConfirmaCapacidadTecnologica.objects.get(persona=inscripcion.persona)

                        if conf is None:
                            data['title'] = u'Matriculación online'
                            data['title2'] = "Información Modalidad y Validación de Datos"
                            return render(request, "alu_automatricula/confirmamodalidad.html", data)
                        elif conf.aplicabeca:
                            sol = BecaSolicitud.objects.get(inscripcion=inscripcion, periodocalifica=periodo, estado=1)
                            if sol.estado == 3: # SOLICITUD DE BECA RECHAZADA
                                # VA QUEMADO SI FECHA ACTUAL > = '2020-05-04'
                                # CONSULTAR COMO DETERMINO SI ESTOY EN RABGO DE FECHAS DE MATRICULAS EXTRAORDINARIAS
                                return HttpResponseRedirect(u"/?info=Estimado estudiante usted aún no son fechas de matriculas extraordinarias.")
                                # permitir_matricular = True
                            elif sol.estado == 1 or sol.estado == 4:
                                return HttpResponseRedirect(u"/?info=Estimado estudiante usted tiene una solicitud de beca pendiente de revisión.")
                            else:
                                if conf.becaasignada is False:
                                    return HttpResponseRedirect(u"/?info=Estimado estudiante su beca no ha sido asignada todavía.")
                                else:
                                    # CONSULTAR COMO DETERMINO SI ESTOY EN RABGO DE FECHAS DE MATRICULAS EXTRAORDINARIAS
                                    # VA QUEMADO SI FECHA ACTUAL > = '2020-05-04'
                                    return HttpResponseRedirect(u"/?info=Estimado estudiante usted aún no son fechas de matriculas extraordinarias.")
                                    # permitir_matricular = True
                        elif paso_matricular or conf.confirmado:
                            permitir_matricular = True
                        elif paso_matricular is False:
                            data['inscripcion'] = inscripcion
                            # data['malla'] = inscripcionmalla.malla
                            # data['nivel'] = nivel
                            data['title'] = u'Matriculación online'
                            data['title2'] = "Información Modalidad y Validación de Datos"
                            return render(request, "alu_automatricula/confirmamodalidad.html", data)

                    else:
                        permitir_matricular = True

                if permitir_matricular:
                    data['title'] = u'Matriculación online'
                    hoy = datetime.now().date()
                    if not variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ'):
                        if inscripcion.mi_coordinacion().id != 9:
                            asignaturaid = AsignaturaMalla.objects.db_manager('sga_select').values_list('asignatura__id',flat=True).filter(Q(malla__id=22) | Q(malla__carrera_id=37))
                            if inscripcion.recordacademico_set.db_manager('sga_select').values('id').filter(status=True, aprobada=False).exclude(asignatura__id__in=asignaturaid).count() > 0:
                                return HttpResponseRedirect(u"/?info=La matriculación se encuentra activa solo para estudiantes que han aprobado todas sus asignaturas, por favor ingresar a partir del 10/04/2019.")

                    # VERIFICACION DE MATRICULA EN CUALQUIER CARRERA, PARA QUE NO TENGA MAS DE UNA MATRICULA EN EL PERIODO
                    periodomat = None
                    matri = None
                    if Periodo.objects.filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=datetime.now().date(), limite_agregacion__gte=datetime.now().date(), tipo__id=2).exists():
                        if Periodo.objects.filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=datetime.now().date(), limite_agregacion__gte=datetime.now().date(), tipo__id=2).count() > 1:
                            return HttpResponseRedirect(u"/?info=No esta habilitada la matricula")
                        else:
                            periodomat = Periodo.objects.filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=datetime.now().date(), limite_agregacion__gte=datetime.now().date(), tipo__id=2)[0]
                            if periodo and periodomat and periodomat.id == periodo.id and inscripcion.persona.tiene_matricula_periodo(periodo):
                                matri = inscripcion.matricula_periodo2(periodo)
                                if ConfirmarMatricula.objects.values('id').filter(matricula=matri).exists():
                                    # return HttpResponseRedirect("/?info=Ya se encuentra matriculado, verificar en el módulo Mis Materias")
                                    return HttpResponseRedirect("/?info=Ya se encuentra matriculado en el Periodo %s , verificar en el módulo Mis Materias" % (str(periodo)))

                    """"# VERIFICACION DE MATRICULA EN CUALQUIER CARRERA, PARA QUE NO TENGA MAS DE UNA MATRICULA EN EL PERIODO
                    if inscripcion.persona.tiene_matricula_periodo(periodo):
                        matri = inscripcion.matricula_periodo2(periodo)
                        if ConfirmarMatricula.objects.values('id').filter(matricula=matri).exists():
                            # return HttpResponseRedirect("/?info=Ya se encuentra matriculado, verificar en el módulo Mis Materias")
                            return HttpResponseRedirect("/?info=Ya se encuentra matriculado en el Periodo %s , verificar en el módulo Mis Materias" % (str(periodo)))"""

                    # YA MATRICULADO
                    #if inscripcion.matriculado3() and inscripcion.mi_coordinacion().id != 9:
                    if matri and inscripcion.mi_coordinacion().id != 9:
                        vareliminar = True
                        data['title'] = u'Confirmación de matrícula (proceso automático)'
                        data['periodo'] = periodo = request.session['periodo']
                        if not periodo:
                            return HttpResponseRedirect("/?info=Seleccione un periodo")
                        if not periodo.matriculacionactiva:
                            return HttpResponseRedirect(u"/?info=No esta habilitada la matricula")
                        listamatricula = Matricula.objects.get(inscripcion=inscripcion, nivel__periodo=periodo, status=True)
                        # if Rubro.objects.values('id').filter(matricula=listamatricula, cancelado=False, status=True).exists():
                        #     # return HttpResponseRedirect("/?info=Ya se encuentra matriculado, y se han generado rubros por matrÃ­cula y arancel consultar en el mÃ³dulo Mis Finanzas")
                        #     return HttpResponseRedirect("/alu_addmatematri")
                        # data['matricula'] = matricula = inscripcion.ultima_matricula3()
                        data['matricula'] = matricula = inscripcion.matricula_periodo(periodo)
                        # if hoy >= matricula.nivel.periodo.inicio_agregacion:
                        #     return HttpResponseRedirect("/?info=Ya se encuentra matriculado, verificar en el mÃ³dulo Mis Materias")
                        if not matricula:
                            return HttpResponseRedirect("/?info=Ud. aun no ha sido matriculado")
                        if ConfirmarMatricula.objects.filter(matricula=matricula,status=True,estado=True):
                            return HttpResponseRedirect("/?info=Ya se encuentra matriculado, verificar en el módulo Mis Materias")
                        data['materiasasignadas'] = matricula.materiaasignada_set.all().order_by('materia__inicio')
                        return render(request, "alu_automatricula/asignaturasmatriculas.html", data)
                        return HttpResponseRedirect("/?info=Ya se encuentra Matriculado.")
                    # EXCLUYE GRADUADOS, EGRESADOS Y RETIRADOS DE LA CARRERA
                    if inscripcion.graduado() or inscripcion.egresado() or inscripcion.estainactivo() or inscripcion.retiro_carrera():
                        return HttpResponseRedirect("/?info=Solo podrán matricularse estudiantes activos.")
                    # NO PUEDE TENER DEUDAS
                    if not MATRICULAR_CON_DEUDA:
                        if inscripcion.persona.tiene_deuda():
                            return HttpResponseRedirect("/?info=Debe de cancelar los valores pendientes para poder matricularse.")
                    # NO PUEDE TENER MATERIAS MAS DE 5 AÃ±OS
                    if not inscripcion.mi_coordinacion().id == 9:
                        if not inscripcion.recordacademico_set.db_manager('sga_select').filter(status=True, fecha__gte=hoy - timedelta(days=1825)).exclude(noaplica=True).exists() and inscripcion.recordacademico_set.filter(status=True).exists():
                            return HttpResponseRedirect("/?info=Debe de acercarse a secretaria para matricularse, por no haber tomado materias hace mas de 5 años.")
                    # MATRICULACION SOLO DISTANCIA
                    if MATRICULA_ONLINE_SOLODISTANCIA:
                        if not inscripcion.modalidad.id == MODALIDAD_DISTANCIA:
                            return HttpResponseRedirect("/?info=Matriculación online solo para modalidad a distancia.")
                    if not inscripcion.inscripcionmalla_set.filter(status=True):
                        return HttpResponseRedirect("/?info=Debe tener malla asociada para poder matricularse.")

                    if not inscripcion.sesion:
                        data['title'] = 'Selección de Sección'
                        data['inscripcion'] = inscripcion
                        form = SesionMatriculacionForm()
                        # if Periodo.objects.filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=datetime.now().date(),fin__gte=datetime.now().date(), tipo__id=2).order_by('-inicio'):
                        #     periodo_aux=Periodo.objects.filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=datetime.now().date(),fin__gte=datetime.now().date(), tipo__id=2).order_by('-inicio')[0]
                        periodo_aux=Periodo.objects.db_manager('sga_select').filter(status=True, matriculacionactiva=True, activo=True, inicio_agregacion__lte=datetime.now().date(),limite_agregacion__gte=datetime.now().date(), tipo__id=2).order_by('-inicio')[0]
                        form.adicionar(periodo_aux, inscripcion.carrera)
                        # form.adicionar()
                        data['form'] = form
                        return render(request, "alu_automatricula/sesion.html", data)


                    nivel = None
                    nivelid = nivel_matriculacion(inscripcion)


                    if nivelid < 0:
                        # comentado por kerly 21 de abril 2020
                        if nivelid == -1:
                            # return HttpResponseRedirect("/?info=Su carrera no tiene coordinacion, o no se ha abierto un nivel para su carrera.")
                            log(u"El periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()),request, "add")
                            return HttpResponseRedirect(u"/?info=El periodo de matriculación no se encuentra activo")
                        if nivelid == -2:
                            return HttpResponseRedirect("/?info=No existen niveles con cupo para matricularse")
                        if nivelid == -3:
                            return HttpResponseRedirect("/?info=No existen paralelos disponibles.")
                        if nivelid == -4:
                            return HttpResponseRedirect("/?info=No existen paralelos para su nivel.")
                    else:
                        nivel = Nivel.objects.get(pk=nivelid)

                        # CONSULTA DE PREMATRICULACION
                        # if not inscripcion.tiene_prematricula(nivel.periodo):
                        #     return HttpResponseRedirect("/?info=Ud no se ha Pre-Matriculado, se podrÃ¡ Matricular despuÃ©s de dos dÃ­as de haber iniciado la matricula ordinaria.")
                        # FECHA TOPE PARA MATRICULACION
                        if datetime.now().date() > nivel.fechatopematriculaes:
                            return HttpResponseRedirect("/?info=Ya terminó la fecha de matriculación...")
                        # CRONOGRAMA DE MATRICULACION SEGUN FECHAS
                        a = inscripcion.puede_matricularse_seguncronograma(nivel.periodo)
                        if a[0] == 2:
                            return HttpResponseRedirect(u"/?info=Aún no está habilitado el cronograma de matriculación de su carrera.")
                        if a[0] == 3:
                            return HttpResponseRedirect(u"/?info=Usted no realizó su Pre-Matrícula (matricularse después de dos días de haber iniciado matrícula ordinaria).")
                        if a[0] == 4:
                            # return HttpResponseRedirect(u"/?info=Fin de MatrÃ­cula Ordinaria, debe acercarse a ventanilla a Matricularse.")
                            log(u"El periodo de matriculación no se encuentra activo.... %s" % (inscripcion.info()), request, "add")
                            return HttpResponseRedirect(u"/?info=El periodo de matriculación no se encuentra activo")

                    if not nivel.periodo.matriculacionactiva:
                        return HttpResponseRedirect(u"/?info=No esta habilitada la matricula")
                    # PERIODO ACTIVO PARA MATRICULACION
                    # cometado por kerñy 21 abril 2020
                    if not nivel.periodo.matriculacionactiva:
                        return HttpResponseRedirect("/?info=El periodo de matriculación no se encuentra activo......")
                    # PASO TODOS LOS FILTRO DE LIMITACIONES
                    data['inscripcion'] = inscripcion

                    if InscripcionMalla.objects.db_manager('sga_select').filter(inscripcion_id=inscripcion.id).exists():
                        inscripcionmalla = InscripcionMalla.objects.db_manager('sga_select').filter(inscripcion_id=inscripcion.id)[0]
                    else:
                        if Malla.objects.db_manager('sga_select').filter(carrera_id=inscripcion.carrera_id, modalidad_id=inscripcion.modalidad_id).exists():
                            malla = Malla.objects.db_manager('sga_select').filter(carrera_id=inscripcion.carrera_id, modalidad_id=inscripcion.modalidad_id).order_by('-inicio')[0]
                        elif Malla.objects.db_manager('sga_select').filter(carrera_id=inscripcion.carrera_id).exists():
                            malla = Malla.objects.db_manager('sga_select').filter(carrera_id=inscripcion.carrera_id).order_by('-inicio')[0]
                        if malla:
                            im = InscripcionMalla(inscripcion_id=inscripcion.id, malla_id=malla.id)
                            im.save()
                        if InscripcionMalla.objects.db_manager('sga_select').filter(inscripcion_id=inscripcion.id).exists():
                            inscripcionmalla = InscripcionMalla.objects.db_manager('sga_select').filter(inscripcion_id=inscripcion.id)[0]




                    #  COBRO DE MATRICULAS PARA REPETIDORES DEL PRE
                    """if inscripcion.mi_coordinacion().id == 9 and  variable_valor('PUEDE_MATRICULARSE_ADMISION'):
                        vareliminar = True
                        data['title'] = u'Confirmación de matrícula'
                        periodoanterior = Periodo.objects.filter(pk__in=[95]).order_by('-id')[0]

                        if inscripcion.malla_inscripcion().malla.inicio.year == 2019:
                            return HttpResponseRedirect("/?info=Matricula solo es permitido para los alumnos que obtuvieron un CUPO y reprobaron el PROCESO DE ADMISIÓN 1S 2020")

                        if not Matricula.objects.filter(inscripcion=inscripcion, nivel__periodo=periodoanterior).exists():
                            return HttpResponseRedirect("/?info=Matricula solo es permitido para los alumnos que reprobaron el PROCESO DE ADMISIÓN 1S 2020")

                        matriculaold = Matricula.objects.get(inscripcion=inscripcion, nivel__periodo=periodoanterior)
                        data['periodo'] = periodo = nivel.periodo
                        if not periodo:
                            return HttpResponseRedirect("/?info=Seleccione un periodo")
                        data['mimalla'] = mimalla = inscripcion.mi_malla()
                        asignaturasmalla = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(status=True, malla=mimalla)

                        # ultimamateriaaprobada = inscripcion.recordacademico_set.filter(status=True, asignatura__id__in=asignaturasmalla, aprobada=True).exclude(noaplica=True).order_by('-fecha')
                        ultimamateriaaprobada = matriculaold.materiaasignada_set.filter(status=True, retiramateria=False, notafinal__gte=70)
                        # if inscripcion.sesion_id == 13:
                        #     if inscripcion.total_estudiante_sobre_ponderacion_migrada(periodoanterior) >=70:
                        #         return HttpResponseRedirect("/?info=Matricula solo es permitido para los alumnos del Pre Virtual que hayan reprobado materias en el periodo OCTUBRE 2018 A MARZO 2019")
                        data['materiasmalla'] = materiasmalla = inscripcionmalla.malla.asignaturamalla_set.select_related().filter(vigente=True).exclude(reemplazo__asignatura__in=[x.materia.asignatura for x in ultimamateriaaprobada]).exclude(asignatura__in=[x.materia.asignatura for x in ultimamateriaaprobada]).order_by('nivelmalla', 'ejeformativo')
                        if materiasmalla.count() == 0:
                            return HttpResponseRedirect("/?info=No tiene materias pendientes, este proceso solo es para alumnos con materias reprobadas")
                        cantidad = 0
                        if materiasmalla.filter(asignatura_id=4837).exists():
                            cantidad = materiasmalla.count() - 1
                        else:
                            cantidad = materiasmalla.count()
                        data['valorpago'] = cantidad * periodo.costomateriapre
                        return render(request, "alu_automatricula/materiaspendiente.html", data)
                    else:
                        return HttpResponseRedirect("/?info=Aún no se encuentra habilitado el proceso de matriculación.")"""



                    # PERDIDA DE CARRERA POR 4TA MATRICULA
                    # if inscripcion.tiene_perdida_carrera():
                    #     return HttpResponseRedirect("/?info=Atencion: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                    # MATRICULACION OBLIGATORIA POR SECRETARIA SI ES 3RA MATRICULA
                    # if inscripcion.tiene_tercera_matricula():
                    #     return HttpResponseRedirect("/?info=Atencion: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria para mas informacion.")
                    # MATRICULACION OBLIGATORIA POR SECRETARIA SI ES 3RA MATRICULA QUITANDO LOS PERIODOS SON CONTAR
                    if inscripcion.tiene_tercera_matriculasincontar():
                        return HttpResponseRedirect("/?info=Atencion: Su limite de matricula por perdida de una o mas asignaturas correspondientes a su plan de estudios, ha excedido. Por favor, acercarse a Secretaria de la facultad para mas informacion.")


                    if validar_tercera_matricula:
                        data['tercera_matricula'] = inscripcion.tiene_tercera_matriculasincontar()
                    else:
                        data['tercera_matricula'] = False

                    if inscripcion.tiene_tercera_matricula():
                        data['mensajeterceramatriculamateria'] = "Sólo puede seleccionar materias en las que se va a matricular por Tercera vez"


                    if variable_valor('VALIDAR_QUE_SEA_PRIMERA_MATRICULA'):
                        if inscripcion.matricula_set.db_manager('sga_select').values('id').filter(status=True).exists():
                            return HttpResponseRedirect(u"/?info=No puede matricularse, solo apto para primer nivel(nuevos).")
                    if not inscripcionmalla:
                        return HttpResponseRedirect("/?info=Debe tener malla asociada para poder matricularse.")
                    minivel = None
                    asignaturasmalla = AsignaturaMalla.objects.db_manager('sga_select').values_list('asignatura__id', flat=True).filter(status=True, malla_id=inscripcion.mi_malla().id)
                    fechaultimamateriaprobada = None
                    ultimamateriaaprobada = RecordAcademico.objects.db_manager('sga_select').filter(inscripcion_id=inscripcion.id,status=True, asignatura__id__in=asignaturasmalla).exclude(noaplica=True).order_by('-fecha')
                    if ultimamateriaaprobada:
                        # sumo 5 aÃ±os
                        fechaultimamateriaprobada = ultimamateriaaprobada[0].fecha+timedelta(days=1810)
                    if fechaultimamateriaprobada:
                        if fechaultimamateriaprobada < nivel.periodo.inicio:
                            return HttpResponseRedirect(u"/?info=Reglamento del Régimen Académico - DISPOSICIONES GENERALES: QUINTA.- Si un estudiante no finaliza su carrera o programa y se retira, podrá reingresar a la misma carrera o programa en el tiempo máximo de 5 años contados a partir de la fecha de su retiro. Si no estuviere aplicándose el mismo plan de estudios deberá completar todos los requisitos establecidos en el plan de estudios vigente a la fecha de su reingreso. Cumplido este plazo máximo para el referido reingreso, deberá reiniciar sus estudios en una carrera o programa vigente. En este caso el estudiante podrá homologar a través del mecanismo de validación de conocimientos, las asignaturas, cursos o sus equivalentes, en una carrera o programa vigente, de conformidad con lo establecido en el presente Reglamento.")
                    if inscripcion.matricula_periodo(periodo):
                        minivel = inscripcion.matricula_periodo(periodo).nivelmalla
                    data['semestre'] = semestre = inscripcion.avance_semestre(minivel)
                    data['materiasmalla'] = inscripcionmalla.malla.asignaturamalla_set.db_manager('sga_select').select_related().all().exclude(nivelmalla__id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
                    data['matriculacion_libre'] = MATRICULACION_LIBRE
                    data['materiasmaximas'] = MAXIMO_MATERIA_ONLINE
                    data['nivel'] = nivel
                    data['malla'] = inscripcionmalla.malla
                    data['total_materias_nivel'] = inscripcion.total_materias_nivel()
                    data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
                    data['materiasmodulos'] = inscripcionmalla.malla.modulomalla_set.all()
                    data['utiliza_gratuidades'] = UTILIZA_GRATUIDADES
                    data['porciento_perdida_parcial_gratuidad'] = PORCIENTO_PERDIDA_PARCIAL_GRATUIDAD
                    data['porciento_perdida_total_gratuidad'] = PORCIENTO_PERDIDA_TOTAL_GRATUIDAD
                    data['NOTIFICACIÃ“N_NO_MATRICULARSE_OTRA_VEZ'] = 'Aun no esta habilitada la matriculación por mas de una vez en las materia'
                    data['PUEDE_MATRICULARSE_OTRA_VEZ'] = variable_valor('PUEDE_MATRICULARSE_OTRA_VEZ')
                    # if RecordAcademico.objects.filter(aprobada=False, inscripcion=inscripcion).exists():
                    #     data['tiene_reprobada'] = True
                    # else:
                    #     data['tiene_reprobada'] = False
                    data['fichasocioeconomicainec'] = persona.fichasocioeconomicainec()
                    data['validartodo'] = 1
                    # data = valida_matricular_requisitotitulacion(data, inscripcion)
                    return render(request, "alu_automatricula/view.html", data)

            except Exception as ex:
                pass

def valida_matricular_requisitotitulacion(data, inscripcion):
    vali_alter = 0
    vali_tenido = 0
    requisitosaprobados = False
    data['inscripcion'] = inscripcion
    malla = inscripcion.inscripcionmalla_set.filter(status=True)[0].malla
    perfil = inscripcion.persona.mi_perfil()
    data['tiene_discapidad'] = perfil.tienediscapacidad

    # PASO 1
    vali_alter += 1
    data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
    if inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivelrequisito():
        vali_tenido += 1
    data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
    data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
    data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivelrequisito()
    # PASO 2
    vali_alter += 1
    total_materias_malla = malla.cantidad_materiasaprobadas()
    cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True,asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
    poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
    data['mi_nivel'] = nivel = inscripcion.mi_nivel()
    inscripcionmalla = inscripcion.malla_inscripcion()
    niveles_maximos = inscripcionmalla.malla.niveles_regulares
    if poraprobacion >= 100:
        data['nivel'] = True
        vali_tenido += 1
    # PASO 3
    vali_alter += 1
    if inscripcion.adeuda_a_la_fecha() == 0:
        data['deudas'] = True
        vali_tenido += 1
    data['deudasvalor'] = inscripcion.adeuda_a_la_fecha()
    # PASO 4
    vali_alter += 1
    ficha = 0
    if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
        data['datospersonales'] = True
        ficha += 1
    if inscripcion.persona.paisnacimiento and inscripcion.persona.provincianacimiento and inscripcion.persona.cantonnacimiento and inscripcion.persona.parroquianacimiento:
        data['datosnacimientos'] = True
        ficha += 1
    examenfisico = inscripcion.persona.datos_examen_fisico()
    if inscripcion.persona.sangre and examenfisico.peso and examenfisico.talla:
        data['datosmedicos'] = True
        ficha += 1
    if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
        data['datosdomicilio'] = True
        ficha += 1
    if perfil.raza:
        data['etnia'] = True
        ficha += 1
    if ficha == 5:
        vali_tenido += 1
    # PASO 5
    vali_alter += 1
    modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
    numero_modulo_ingles = modulo_ingles.count()
    lista = []
    listaid = []
    for modulo in modulo_ingles:
        if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
            lista.append(modulo.asignatura.nombre)
            listaid.append(modulo.asignatura.id)
    data['modulo_ingles_aprobados'] = lista
    data['modulo_ingles_faltante'] = modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
    if numero_modulo_ingles == len(listaid):
        data['modulo_ingles'] = True
        vali_tenido += 1
    # PASO 6
    vali_alter += 1
    totalhoras = 0
    practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=inscripcion, status=True, culminada=True)
    data['malla_horas_practicas'] = malla.horas_practicas
    if practicaspreprofesionalesinscripcion.exists():
        for practicas in practicaspreprofesionalesinscripcion:
            if practicas.tiposolicitud == 3:
                totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
            else:
                totalhoras += practicas.numerohora
        if totalhoras >= malla.horas_practicas:
            data['practicaspreprofesionales'] = True
            vali_tenido += 1
    data['practicaspreprofesionalesvalor'] = totalhoras
    # PASO 7
    vali_alter += 1
    data['malla_horas_vinculacion'] = malla.horas_vinculacion
    horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True,inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
    horastotal = horastotal if horastotal else 0
    if horastotal >= malla.horas_vinculacion:
        data['vinculacion'] = True
        vali_tenido += 1
    data['horas_vinculacion'] = horastotal
    # PASO 8
    vali_alter += 1
    asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
    data['record_computacion'] = record = RecordAcademico.objects.filter(inscripcion__id=inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
    creditos_computacion = 0
    data['malla_creditos_computacion'] = malla.creditos_computacion
    for comp in record:
        creditos_computacion += comp.creditos
    if creditos_computacion >= malla.creditos_computacion:
        data['computacion'] = True
        vali_tenido += 1
    data['creditos_computacion'] = creditos_computacion
    if vali_alter == vali_tenido:
        data['aprueba'] = True
        requisitosaprobados = True
    data['requisitosaprobados'] = requisitosaprobados
    data['validartodo'] = 0

    data['modulo_ingles'] = True
    data['computacion'] = True
    return data
