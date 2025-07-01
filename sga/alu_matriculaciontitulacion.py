# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.db.models import Sum
from django.db.models.query_utils import Q
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from sga.funciones import log
from decorators import secure_module, last_access
from settings import NOTA_ESTADO_APROBADO, ESTADO_GESTACION
from sga.commonviews import adduserdata
from sga.funciones import generar_nombre
from sga.models import AlternativaTitulacion, Malla, ModuloMalla, RecordAcademico, PracticasPreprofesionalesInscripcion, \
    EstadoGestacion, MatriculaTitulacion, ParticipantesMatrices, AsignaturaMalla, PropuestaTitulacion_Matricula, \
    ComplexivoMateriaAsignada, TIPO_CELULAR, ArchivoTitulacion


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    global ex
    data = {}
    lista=""
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        action = request.POST['action']
        if action == 'addmatricular':
            try:
                newfilecedula = None
                newfilevotacion = None
                if MatriculaTitulacion.objects.filter(Q(alternativa=int(request.POST['alter_id'])),Q(inscripcion_id=inscripcion.id), Q(estado=6)|Q(estado=1)).exists():
                    return JsonResponse({"result": "bad", "mensaje": u" Ya tiene Una Matricula Vigente."})
                if 'cedula' in request.FILES and 'votacion' in request.FILES:
                    newfilecedula = request.FILES['cedula']
                    newfilecedula._name = generar_nombre("DocumentoPersonal_", newfilecedula._name)
                    newfilevotacion = request.FILES['votacion']
                    newfilevotacion._name = generar_nombre("DocumentoPersonal_", newfilevotacion._name)
                    alter = AlternativaTitulacion.objects.get(pk=int(request.POST['alter_id']))
                    # examen = True
                    # if alter.tipotitulacion.tipo==1:
                    #     examen = False
                    matricula = MatriculaTitulacion(alternativa_id=int(request.POST['alter_id']),
                                                    inscripcion=inscripcion,
                                                    documento_cedula=newfilecedula,
                                                    documento_certificado_votacion=newfilevotacion,
                                                    fechainscripcion=datetime.now().date(),
                                                    estado=1)
                    matricula.save(request)
                    # if alter.tipotitulacion.tipo==1:
                    #     matricula.estado = 6
                    # else:
                    #     matricula.estado = 1
                    #     examen=True
                    # matricula.save(request)
                    # inicio matricular alumno en las materias
                    materias = alter.complexivomateria_set.filter(status=True)
                    for materia in materias:
                        matriculamat = ComplexivoMateriaAsignada()
                    log(u'Matricularse :%s' % matricula, request, "add")
                    display = request.POST.get("estadogestion", None)
                    if display in ["True"]:
                        matricula = MatriculaTitulacion.objects.get(Q(alternativa=int(request.POST['alter_id'])),Q(inscripcion_id=inscripcion.id), (Q(estado=6) | Q(estado=1)))
                        # matricula = MatriculaTitulacion.objects.get(alternativa=int(request.POST['alter_id']),inscripcion_id=inscripcion.id, estado=6)
                        esta_gestacion = EstadoGestacion(matriculatitulacion_id=matricula.id, estadogestacion=True)
                        esta_gestacion.save(request)
                        log(u'Matricularse :%s' % esta_gestacion, request, "add")
                    # return JsonResponse({"result": "ok", "mensaje": u"En hora buena ustad esta matriculado en el proceso titulacion",'examen':examen})
                    return JsonResponse({"result": "ok", "mensaje": u"En hora buena ustad esta matriculado en el proceso titulacion"})
                else:
                    return JsonResponse({"result": "bad", "mensaje": u" No a subido la copia de cédula o certificado de votación."})
            except Exception as ex:
                transaction.set_rollback(True)
                return JsonResponse({'result': 'bad', 'mensaje': u'Error al guardar los datos'})

    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'aptoprocesotitulacion':
                try:
                    vali_alter=0
                    vali_tenido=0
                    data['title']=  u'Matriculación al Proceso de Titulación'
                    data['item'] =alter=  AlternativaTitulacion.objects.get(pk=int(request.GET['id']))
                    data['grupo']=alter.grupotitulacion
                    data['inscripcion']=inscripcion
                    alucarrera = inscripcion.carrera
                   # malla= Malla.objects.get(carrera_id=alucarrera)
                    malla= inscripcion.mi_malla()
                    perfil = inscripcion.persona.mi_perfil()
                    fechainicioprimernivel = inscripcion.fechainicioprimernivel if inscripcion.fechainicioprimernivel else datetime.now().date()
                    excluiralumnos = datetime(2009, 1, 21, 23, 59, 59).date()
                    data['tiene_discapidad'] = perfil.tienediscapacidad
                    if alter.estadofichaestudiantil:
                        vali_alter +=1
                        ficha=0
                        if inscripcion.persona.nombres and inscripcion.persona.apellido1 and inscripcion.persona.apellido2 and inscripcion.persona.nacimiento and inscripcion.persona.cedula and inscripcion.persona.nacionalidad and inscripcion.persona.email and inscripcion.persona.estado_civil and inscripcion.persona.sexo:
                            data['datospersonales'] = True
                            ficha+=1
                        if persona.paisnacimiento and persona.provincianacimiento and persona.cantonnacimiento and persona.parroquianacimiento:
                            data['datosnacimientos'] = True
                            ficha += 1
                        examenfisico = persona.datos_examen_fisico()
                        if persona.sangre and examenfisico.peso and examenfisico.talla:
                            data['datosmedicos'] = True
                            ficha += 1
                        if inscripcion.persona.pais and inscripcion.persona.provincia and inscripcion.persona.canton and inscripcion.persona.parroquia and inscripcion.persona.direccion and inscripcion.persona.direccion2 and inscripcion.persona.num_direccion and inscripcion.persona.telefono_conv or inscripcion.persona.telefono:
                            data['datosdomicilio'] = True
                            ficha += 1
                        if perfil.raza:
                            data['etnia'] = True
                            ficha += 1
                        if ficha==5:
                            vali_tenido+=1
                    if alter.estadopracticaspreprofesionales:
                        vali_alter+=1
                        totalhoras = 0
                        practicaspreprofesionalesinscripcion = PracticasPreprofesionalesInscripcion.objects.filter(inscripcion=perfilprincipal.inscripcion, status= True, culminada= True)
                        data['malla_horas_practicas']= malla.horas_practicas
                        if fechainicioprimernivel > excluiralumnos:
                            if practicaspreprofesionalesinscripcion.exists():
                                for practicas in practicaspreprofesionalesinscripcion:
                                    if practicas.tiposolicitud == 3:
                                        totalhoras += practicas.horahomologacion if practicas.horahomologacion else 0
                                    else:
                                        totalhoras+=practicas.numerohora
                                if totalhoras >=malla.horas_practicas:
                                    data['practicaspreprofesionales'] = True
                                    vali_tenido+=1
                            data['practicaspreprofesionalesvalor'] = totalhoras
                        else:
                            data['practicaspreprofesionales'] = True
                            vali_tenido += 1
                            data['practicaspreprofesionalesvalor'] = malla.horas_practicas
                    if alter.estadocredito:
                        vali_alter+=1
                        # data['creditos']= inscripcion.tiene_porciento_cumplimiento_malla()
                        data['creditos'] = inscripcion.aprobo_asta_penultimo_malla()
                        if inscripcion.aprobo_asta_penultimo_malla() and inscripcion.esta_matriculado_ultimo_nivel():
                            vali_tenido+=1
                        data['cantasigaprobadas'] = inscripcion.cantidad_asig_aprobada_penultimo_malla()
                        data['cantasigaprobar'] = inscripcion.cantidad_asig_aprobar_penultimo_malla()
                        data['esta_mat_ultimo_nivel'] = inscripcion.esta_matriculado_ultimo_nivel()
                        # malla = inscripcion.malla_inscripcion().malla
                        # total_materias_malla = malla.cantidad_materiasaprobadas()
                        # cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura__in=[x.asignatura for x in malla.asignaturamalla_set.filter(status=True)]).count()
                        # data['creditoporcentaje'] = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
                    if alter.estadoadeudar:
                        vali_alter+=1
                        ## mario solicitado por mario
                        # if inscripcion.adeuda_a_la_fecha()==0:
                        data['deudas'] = True
                        vali_tenido+=1
                        data['deudasvalor']=inscripcion.adeuda_a_la_fecha()
                    if alter.estadoingles:
                        vali_alter+=1
                        modulo_ingles = ModuloMalla.objects.filter(malla=malla, status=True).exclude(asignatura_id=782)
                        numero_modulo_ingles = modulo_ingles.count()
                        lista = []
                        listaid = []
                        for modulo in modulo_ingles:
                            if inscripcion.estado_asignatura(modulo.asignatura) == NOTA_ESTADO_APROBADO:
                                lista.append(modulo.asignatura.nombre)
                                listaid.append(modulo.asignatura.id)
                        data['modulo_ingles_aprobados']=lista
                        data['modulo_ingles_faltante']=modulo_ingles.exclude(asignatura_id__in=[int(i) for i in listaid])
                        ## mario solicitado por mario
                        # if numero_modulo_ingles == len(listaid):
                        data['modulo_ingles'] = True
                        vali_tenido+=1
                    if alter.estadonivel:
                        vali_alter+=1
                        if inscripcion.itinerario:
                            total_materias_malla = malla.cantidad_materiasaprobadas(itinerario=inscripcion.itinerario)
                            asignaturas_sin_itinerario = malla.asignaturamalla_set.values_list("asignatura_id", flat=True).filter(opcional=False, status=True, itinerario=0)
                            asignaturas_con_itinerario = malla.asignaturamalla_set.values_list("asignatura_id", flat=True).filter(status=True, itinerario=inscripcion.itinerario).exclude(itinerario=0)
                            asignaturas_ax = asignaturas_con_itinerario | asignaturas_sin_itinerario
                        else:
                            total_materias_malla = malla.cantidad_materiasaprobadas()
                            # asignaturas_ax = [x.asignatura.id for x in malla.asignaturamalla_set.filter(status=True, opcional=False)]
                            asignaturas_ax = malla.asignaturamalla_set.values_list("asignatura_id", flat=True).filter(status=True, opcional=False)
                        cantidad_materias_aprobadas_record = inscripcion.recordacademico_set.filter(aprobada=True, status=True, asignatura_id__in=asignaturas_ax).count()
                        poraprobacion = round(cantidad_materias_aprobadas_record * 100 / total_materias_malla, 0)
                        data['mi_nivel'] = nivel = inscripcion.mi_nivel()
                        inscripcionmalla = inscripcion.malla_inscripcion()
                        niveles_maximos = inscripcionmalla.malla.niveles_regulares
                        if poraprobacion>=100:
                            data['nivel'] = True
                            vali_tenido += 1
                        else:
                            if niveles_maximos==nivel.nivel.id:
                                data['septimo']=True
                    if perfil.tienediscapacidad:
                        data['discapacidad'] = perfil
                    if inscripcion.persona.sexo.id == ESTADO_GESTACION:
                        data['femenino']=True
                    if alter.estadovinculacion:
                        vali_alter += 1
                        data['malla_horas_vinculacion'] = malla.horas_vinculacion
                        # horastotal = ParticipantesMatrices.objects.filter(matrizevidencia_id=2, status=True, proyecto__status=True, inscripcion_id=inscripcion.id).aggregate(horastotal=Sum('horas'))['horastotal']
                        horastotal = inscripcion.numero_horas_proyectos_vinculacion()
                        # horastotal = horastotal if horastotal else 0
                        if fechainicioprimernivel > excluiralumnos:
                            if horastotal >= malla.horas_vinculacion:
                                    data['vinculacion']= True
                                    vali_tenido += 1
                            data['horas_vinculacion']= horastotal
                        else:
                            data['horas_vinculacion'] = malla.horas_vinculacion
                            data['vinculacion'] = True
                            vali_tenido += 1
                    if alter.estadocomputacion:
                        vali_alter+=1
                        asignatura = AsignaturaMalla.objects.values_list('asignatura__id', flat=True).filter(malla__id=32)
                        data['record_computacion']= record = RecordAcademico.objects.filter(inscripcion__id=inscripcion.id, asignatura__id__in=asignatura, aprobada=True)
                        creditos_computacion = 0
                        data['malla_creditos_computacion']=malla.creditos_computacion
                        for comp in record:
                            creditos_computacion += comp.creditos
                        if creditos_computacion >= malla.creditos_computacion:
                            data['computacion'] = True
                            vali_tenido += 1
                        data['creditos_computacion'] = creditos_computacion
                    # if alter.actividadcomplementaria:
                    #     vali_alter += 1
                    #     data['actividadescomplementarias'] = inscripcion.aprueba_actividades_complementarias(alter.acperiodo.id)
                    #     if inscripcion.aprueba_actividades_complementarias(alter.acperiodo.id):
                    #         vali_tenido += 1
                    #     data['actividades_x_cumplir'] = inscripcion.cantidad_actividadcomplementaria_cumplir(alter.acperiodo.id)
                    #     data['cantidad_actividades_registradas'] = inscripcion.cantidad_actividadescomplementarias_registradas(alter.acperiodo.id)
                    #     data['lista_actividades'] = inscripcion.lista_actividades_x_periodo(alter.acperiodo.id)
                    if vali_alter == vali_tenido:
                        data['aprueba']=True
                    if inscripcion.persona.tipocelular == 0:
                        data['tipocelular'] = '-'
                    else:
                        data['tipocelular'] = TIPO_CELULAR[int(persona.tipocelular) - 1][1]
                    return render(request, "alu_matriculaciontitulacion/aptoprocesotitulacion.html", data)
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            data['title'] = u'Registro al proceso de titulación'
            if inscripcion.graduado():
                return HttpResponseRedirect("/?info=Ingreso no permitido a graduados.")

            mattitu = MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=2)|Q(estado=5)| Q(estado=9)))

            if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=2)|Q(estado=5)| Q(estado=9))).exclude(alternativa__grupotitulacion__periodogrupo_id__in=[14,15,17,18]).count()>=3:
                # return HttpResponseRedirect("/?info=Tiene más de 3 matriculas")
                data['msg_error'] = 'Usted tiene más de 3 matriculas y no puede acceder al módulo'
                return render(request, "alu_matriculaciontitulacion/error.html", data)
            else:
                if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=1)).exists():
                    if not MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=6) | Q(estado=1) | Q(estado=7)), (Q(alternativa__fechamatriculacion__lte=datetime.now()) & Q(alternativa__fechamatriculacionfin__gte=datetime.now()))).exists():
                        if MatriculaTitulacion.objects.filter(inscripcion=inscripcion, estado=6).exists():
                            data['mat_cerrada'] = True
                    if not MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=6) | Q(estado=1) | Q(estado=7))).exists():
                        data['title'] = u'Matriculación al Proceso de Titulación'
                        if inscripcion.graduado():
                            return HttpResponseRedirect("/?info=Ingreso no permitido a graduados.")
                        if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), (Q(estado=2) | Q(estado=5))).count() >= 3:
                            return HttpResponseRedirect("/?info=Tiene más de 3 matriculas")
                        else:
                            if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=1)).exists():
                                return render(request, "alu_propuestatitulacion/view.html", data)
                                # return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente.")
                            if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=7)).exists():
                                return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente de confirmar.")
                            alucarrera = inscripcion.carrera
                            data['inscripcion'] = inscripcion
                            data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera) & (Q(fechamatriculacion__lte=datetime.now().date()) & Q(fechamatriculacionfin__gte=datetime.now().date()))).exclude(status=False)
                            # data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera)& ((Q(fechamatriculacion__lte=datetime.now().date())& Q(fechamatriculacionfin__gte=datetime.now().date())) | (Q(fechaordinariainicio__lte=datetime.now().date())& Q(fechaordinariafin__gte=datetime.now().date()))| (Q(fechaextraordinariainicio__lte=datetime.now().date())& Q(fechaextraordinariafin__gte=datetime.now().date()))| (Q(fechaespecialinicio__lte=datetime.now().date())& Q(fechaespecialfin__gte=datetime.now().date())))).exclude(status=False)
                            return render(request, "alu_matriculaciontitulacion/view.html", data)
                    data['matricula'] = matricula = MatriculaTitulacion.objects.get(Q(inscripcion=inscripcion) & (Q(estado=6) | Q(estado=1) | Q(estado=7)))
                    data['propuestas'] = PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True)
                    if MatriculaTitulacion.objects.filter(inscripcion_id=inscripcion.id, estado=7).exists():
                        try:
                            data['title'] = u'Confirmación'
                            pro_mat = PropuestaTitulacion_Matricula.objects.get(matricula=matricula, matricula__estado=7, status=True)
                            data['tema'] = pro_mat.propuesta.tema
                            # if pro_mat.matricula.inscripcion==inscripcion:
                            data['estudiante'] = pro_mat.matricula.inscripcion
                            return render(request, "alu_propuestatitulacion/confirmacionestudiante.html", data)
                        except Exception as ex:
                            pass
                    data['title'] = u'Propuesta de Titulación'
                    data['alternativa'] = matricula.alternativa
                    data['examen'] = True if matricula.alternativa.tipotitulacion.tipo == 2 else False
                    data['estudiante'] = inscripcion.persona
                    # lista = PropuestaTitulacion.objects.values_list("matricula").filter(Q(matricula__alternativa__carrera=inscripcion.carrera), Q(matricula__alternativa_id=matricula.alternativa.id),(Q(estado=1) | Q(estado=2)))
                    data['add'] = True
                    if PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True).exists():
                        data['add'] = False
                    return render(request, "alu_propuestatitulacion/view.html", data)
                    # return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente.")
                if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),Q(estado=7)).exists():
                    # return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente de confirmar.")
                    if not MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=6) | Q(estado=1) | Q(estado=7)), (Q(alternativa__fechamatriculacion__lte=datetime.now()) & Q(alternativa__fechamatriculacionfin__gte=datetime.now()))).exists():
                        if MatriculaTitulacion.objects.filter(inscripcion=inscripcion, estado=6).exists():
                            data['mat_cerrada'] = True
                    if not MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion),(Q(estado=6) | Q(estado=1) | Q(estado=7))).exists():
                        data['title'] = u'Matriculación al Proceso de Titulación'
                        if inscripcion.graduado():
                            return HttpResponseRedirect("/?info=Ingreso no permitido a graduados.")
                        if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), (Q(estado=2) | Q(estado=5))).count() >= 3:
                            return HttpResponseRedirect("/?info=Tiene más de 3 matriculas")
                        else:
                            if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=1)).exists():
                                return render(request, "alu_propuestatitulacion/view.html", data)
                                # return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente.")
                            if MatriculaTitulacion.objects.filter(Q(inscripcion=inscripcion), Q(estado=7)).exists():
                                return HttpResponseRedirect("/?info=Usted ya cuenta con un proyecto vigente de confirmar.")
                            alucarrera = inscripcion.carrera
                            data['inscripcion'] = inscripcion
                            data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera) & (Q(fechamatriculacion__lte=datetime.now().date()) & Q(fechamatriculacionfin__gte=datetime.now().date()))).exclude(Q(status=False)| Q(verestudiantes=False))
                            # data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera)& ((Q(fechamatriculacion__lte=datetime.now().date())& Q(fechamatriculacionfin__gte=datetime.now().date())) | (Q(fechaordinariainicio__lte=datetime.now().date())& Q(fechaordinariafin__gte=datetime.now().date()))| (Q(fechaextraordinariainicio__lte=datetime.now().date())& Q(fechaextraordinariafin__gte=datetime.now().date()))| (Q(fechaespecialinicio__lte=datetime.now().date())& Q(fechaespecialfin__gte=datetime.now().date())))).exclude(status=False)
                            return render(request, "alu_matriculaciontitulacion/view.html", data)
                    data['matricula'] = matricula = MatriculaTitulacion.objects.get(Q(inscripcion=inscripcion) & (Q(estado=6) | Q(estado=1) | Q(estado=7)))
                    data['propuestas'] = PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True)
                    if MatriculaTitulacion.objects.filter(inscripcion_id=inscripcion.id, estado=7).exists():
                        try:
                            data['title'] = u'Confirmación'
                            pro_mat = PropuestaTitulacion_Matricula.objects.get(matricula=matricula, matricula__estado=7, status=True)
                            data['tema'] = pro_mat.propuesta.tema
                            # if pro_mat.matricula.inscripcion==inscripcion:
                            data['estudiante'] = pro_mat.matricula.inscripcion
                            return render(request, "alu_propuestatitulacion/confirmacionestudiante.html", data)
                        except Exception as ex:
                            pass
                    data['title'] = u'Propuesta de Titulación'
                    data['alternativa'] = matricula.alternativa
                    data['examen'] = True if matricula.alternativa.tipotitulacion.tipo == 2 else False
                    data['estudiante'] = inscripcion.persona
                    # lista = PropuestaTitulacion.objects.values_list("matricula").filter(Q(matricula__alternativa__carrera=inscripcion.carrera), Q(matricula__alternativa_id=matricula.alternativa.id),(Q(estado=1) | Q(estado=2)))
                    data['add'] = True
                    if PropuestaTitulacion_Matricula.objects.filter(matricula=matricula, status=True).exists():
                        data['add'] = False
                    return render(request, "alu_propuestatitulacion/view.html", data)
                alucarrera=inscripcion.carrera
                data['inscripcion'] = inscripcion
                data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera) & (Q(fechamatriculacion__lte=datetime.now().date()) & Q(fechamatriculacionfin__gte=datetime.now().date()))).exclude(Q(status=False)| Q(verestudiantes=False))
                # data['alternativa'] = AlternativaTitulacion.objects.filter(Q(carrera=alucarrera)& ((Q(fechamatriculacion__lte=datetime.now().date())& Q(fechamatriculacionfin__gte=datetime.now().date())) | (Q(fechaordinariainicio__lte=datetime.now().date())& Q(fechaordinariafin__gte=datetime.now().date()))| (Q(fechaextraordinariainicio__lte=datetime.now().date())& Q(fechaextraordinariafin__gte=datetime.now().date()))| (Q(fechaespecialinicio__lte=datetime.now().date())& Q(fechaespecialfin__gte=datetime.now().date())))).exclude(status=False)
                data['archivos'] = ArchivoTitulacion.objects.filter(vigente=True, status=True).distinct()
                return render(request, "alu_matriculaciontitulacion/view.html", data)
