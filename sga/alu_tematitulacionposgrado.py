# -*- coding: latin-1 -*-
import json
from datetime import datetime

from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from django.template.context import Context
from django.template.loader import get_template

from decorators import secure_module, last_access
from sga.commonviews import adduserdata
from sga.forms import IngresarTemaTitulacionPosgradoForm, ComplexivoSubirPropuesta1Form, \
    ComplexivoEditarArchivoPropuestaForm, CorrecionArchivoFinalSustentacionPosgradoForm, ExamenComplexivoEnsayoForm
from sga.funciones import log, generar_nombre, variable_valor
from sga.funciones_templatepdf import actaaprobacionexamencomplexivoposgrado
from sga.models import TemaTitulacionPosgradoMatricula, TemaTitulacionPosgradoMatriculaHistorial, \
    ConfiguracionTitulacionPosgrado, AsignaturaMalla, RevisionTutoriasTemaTitulacionPosgradoProfesor, \
    TIPO_ARCHIVO_COMPLEXIVO_PROPUESTA, ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor, TIPO_ARCHIVO_PORSGRADO, \
    TemaTitulacionPosArchivoFinal, GrupoTitulacionPostgrado, DetalleGrupoTitulacionPostgrado, \
    TemaTitulacionPosgradoMatriculaCabecera, ArchivoRevisionPropuestaComplexivoPosgrado, \
    RevisionPropuestaComplexivoPosgrado, TemaTitulacionPosgradoProfesor, SolicitudTutorTemaHistorial, Profesor, \
    TutoriasTemaTitulacionPosgradoProfesor, HistorialFirmaActaAprobacionComplexivo, EtapaTemaTitulacionPosgrado
from sga.templatetags.sga_extras import encrypt

@login_required(redirect_field_name='ret', login_url='/loginsga')
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
    if inscripcion.mi_coordinacion().id != 7:
        return HttpResponseRedirect("/?info=Módulo solo para estudiantes de posgrado.")
    malla = inscripcion.malla_inscripcion().malla
    matricula = inscripcion.matricula_periodo(periodo)
    carrera = inscripcion.carrera
    if periodo.tipo.id == 3 or periodo.tipo.id == 4:
        a=1
    else:
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes de Maestrías pueden ingresar al modulo.")
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']
            if action == 'add':
                try:
                    f = IngresarTemaTitulacionPosgradoForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        if f.cleaned_data['pareja'] ==True: #si hace en pareja
                            if TemaTitulacionPosgradoMatricula.objects.filter(status=True,matricula_id=f.cleaned_data['companero']).exists():
                                teamanteriorcompaniero=TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=f.cleaned_data['companero'])[0]
                                return JsonResponse( {"result": "bad", "mensaje": u"El compañero que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (teamanteriorcompaniero.propuestatema,teamanteriorcompaniero.mecanismotitulacionposgrado)})

                            if f.cleaned_data['companero'] == matricula.pk:
                                return JsonResponse({"result": "bad","mensaje": u"No puede seleccionarse usted mismo"})


                            cabecera = TemaTitulacionPosgradoMatriculaCabecera(
                                sublinea=f.cleaned_data['sublinea'],
                                mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                convocatoria=f.cleaned_data['convocatoria'],
                                propuestatema=f.cleaned_data['propuestatema'],
                                tutor=None,
                                variabledependiente=f.cleaned_data['variabledependiente'],
                                variableindependiente=f.cleaned_data['variableindependiente'])

                            cabecera.save(request)
                            #guardar las dos parejas

                            if f.cleaned_data['mecanismotitulacionposgrado'].id == 15:#por examen complexivo
                                tematitulacionposgradomatriculaestudiante1 = TemaTitulacionPosgradoMatricula(matricula=matricula,
                                                                                                  sublinea=f.cleaned_data['sublinea'],
                                                                                                  mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                                                                                  propuestatema=f.cleaned_data['propuestatema'],
                                                                                                  convocatoria=f.cleaned_data['convocatoria'],
                                                                                                  variabledependiente="NO APLICA",
                                                                                                  variableindependiente="NO APLICA",
                                                                                                  tutor=None,
                                                                                                  moduloreferencia=f.cleaned_data['moduloreferencia'],
                                                                                                  cabeceratitulacionposgrado=cabecera
                                                                                                  )
                                tematitulacionposgradomatriculaestudiante2 = TemaTitulacionPosgradoMatricula(
                                    matricula_id = f.cleaned_data['companero'],
                                    sublinea=f.cleaned_data['sublinea'],
                                    mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                    propuestatema=f.cleaned_data['propuestatema'],
                                    convocatoria=f.cleaned_data['convocatoria'],
                                    variabledependiente="NO APLICA",
                                    variableindependiente="NO APLICA",
                                    tutor=None,
                                    moduloreferencia=f.cleaned_data['moduloreferencia'],
                                    cabeceratitulacionposgrado=cabecera
                                )
                            else:#por proyecto de investigacion y desarrollo
                                tematitulacionposgradomatriculaestudiante1 = TemaTitulacionPosgradoMatricula(
                                    matricula=matricula,
                                    sublinea=f.cleaned_data['sublinea'],
                                    mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                    propuestatema=f.cleaned_data['propuestatema'],
                                    convocatoria=f.cleaned_data['convocatoria'],
                                    variabledependiente=f.cleaned_data['variabledependiente'],
                                    variableindependiente=f.cleaned_data['variableindependiente'],
                                    tutor=None,
                                    cabeceratitulacionposgrado=cabecera
                                )
                                tematitulacionposgradomatriculaestudiante2 = TemaTitulacionPosgradoMatricula(
                                    matricula_id=f.cleaned_data['companero'],
                                    sublinea=f.cleaned_data['sublinea'],
                                    mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                    propuestatema=f.cleaned_data['propuestatema'],
                                    convocatoria=f.cleaned_data['convocatoria'],
                                    variabledependiente=f.cleaned_data['variabledependiente'],
                                    variableindependiente=f.cleaned_data['variableindependiente'],
                                    tutor=None,
                                    cabeceratitulacionposgrado=cabecera
                                )
                            tematitulacionposgradomatriculaestudiante1.save(request)
                            tematitulacionposgradomatriculaestudiante2.save(request)

                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile2 = request.FILES['archivo']
                                newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)
                                tematitulacionposgradomatriculaestudiante1.archivo = newfile

                                newfile2._name = generar_nombre(str(tematitulacionposgradomatriculaestudiante2.matricula.inscripcion.persona.id), newfile2._name)
                                tematitulacionposgradomatriculaestudiante2.archivo = newfile2

                            tematitulacionposgradomatriculaestudiante1.save(request)
                            tematitulacionposgradomatriculaestudiante2.save(request)
                            #Guaddar Historial estudiante 1
                            tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=tematitulacionposgradomatriculaestudiante1,
                                                                                                                observacion = 'NINGUNA',
                                                                                                                estado = 1)
                            # Guardar Historial estudiante 2
                            tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                tematitulacionposgradomatricula=tematitulacionposgradomatriculaestudiante2,
                                observacion='NINGUNA',
                                estado=1)

                            tematitulacionposgradomatriculahistorialestudiante1.save(request)

                            log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatriculahistorialestudiante1,
                                request, "add")
                            tematitulacionposgradomatriculahistorialestudiante2.save(request)

                            log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatriculahistorialestudiante2,
                                request, "add")


                        else:#individual
                            if f.cleaned_data['mecanismotitulacionposgrado'].id == 15:
                                tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula(matricula=matricula,
                                                                                                  sublinea=f.cleaned_data['sublinea'],
                                                                                                  mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                                                                                  propuestatema=f.cleaned_data['propuestatema'],
                                                                                                  convocatoria=f.cleaned_data['convocatoria'],
                                                                                                  variabledependiente="NO APLICA",
                                                                                                  variableindependiente="NO APLICA",
                                                                                                  tutor=None,
                                                                                                  moduloreferencia=f.cleaned_data['moduloreferencia']
                                                                                                  )
                            else:
                                tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula(matricula=matricula,
                                                                                                  sublinea=f.cleaned_data['sublinea'],
                                                                                                  mecanismotitulacionposgrado=f.cleaned_data['mecanismotitulacionposgrado'],
                                                                                                  propuestatema=f.cleaned_data['propuestatema'],
                                                                                                  convocatoria=f.cleaned_data['convocatoria'],
                                                                                                  variabledependiente=f.cleaned_data['variabledependiente'],
                                                                                                  variableindependiente=f.cleaned_data['variableindependiente'],
                                                                                                  tutor=None)
                            tematitulacionposgradomatricula.save(request)
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)
                                tematitulacionposgradomatricula.archivo = newfile
                            tematitulacionposgradomatricula.save(request)
                            #Guardar Historial
                            tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=tematitulacionposgradomatricula,
                                                                                                                observacion = 'NINGUNA',
                                                                                                                estado = 1)
                            tematitulacionposgradomatriculahistorial.save(request)
                            log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatricula, request, "add")

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos %s." % ex})

            elif action == 'edit':
                try:

                    f = IngresarTemaTitulacionPosgradoForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        arch = request.FILES['archivo']
                        extension = arch._name.split('.')
                        tam = len(extension)
                        exte = extension[tam - 1]
                        if arch.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, el tamaño del archivo es mayor a 10 Mb."})
                        if not exte.lower() == 'pdf':
                            return JsonResponse({"result": "bad", "mensaje": u"Solo se permiten archivos .pdf"})

                    if f.is_valid():
                        tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'], status =True)
                        if f.cleaned_data['pareja'] == True: #es en pareja
                            maestrante_actual = tema
                            companiero = None
                            nuevo_companiero = None

                            if maestrante_actual.cabeceratitulacionposgrado:#si tiene companiero
                                companiero = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=maestrante_actual.cabeceratitulacionposgrado, status=True).exclude(id=maestrante_actual.pk)

                            if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=f.cleaned_data['companero']).exists():
                                nuevo_companiero = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=f.cleaned_data['companero'])[0]


                            if companiero:
                                if nuevo_companiero:
                                    if not nuevo_companiero.pk == companiero[0].pk:
                                        if nuevo_companiero:
                                            return JsonResponse({"result": "bad",
                                                                 "mensaje": u"El compañero que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                 nuevo_companiero.propuestatema,
                                                                 nuevo_companiero.mecanismotitulacionposgrado)})


                                        if nuevo_companiero:
                                            if maestrante_actual.pk == nuevo_companiero.pk:
                                                return JsonResponse({"result": "bad",
                                                                         "mensaje": u"usted ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                             maestrante_actual.propuestatema,
                                                                             maestrante_actual.mecanismotitulacionposgrado)})

                            else:
                                if nuevo_companiero:
                                    if maestrante_actual.pk == nuevo_companiero.pk:
                                        return JsonResponse({"result": "bad",
                                                             "mensaje": u"usted ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                 maestrante_actual.propuestatema,
                                                                 maestrante_actual.mecanismotitulacionposgrado)})
                                    else:
                                        if nuevo_companiero:
                                            return JsonResponse({"result": "bad", "mensaje": u"El compañero que ha elegido ya tiene una solicitud de titulación %s con el mecanismo %s." % (
                                                                     nuevo_companiero.propuestatema,
                                                                     nuevo_companiero.mecanismotitulacionposgrado)})

                            if tema.cabeceratitulacionposgrado:#si tiene pareja


                                tema.sublinea = f.cleaned_data['sublinea']
                                tema.mecanismotitulacionposgrado = f.cleaned_data['mecanismotitulacionposgrado']
                                tema.propuestatema = f.cleaned_data['propuestatema']
                                tema.variabledependiente = f.cleaned_data['variabledependiente']
                                tema.variableindependiente = f.cleaned_data['variableindependiente']
                                tema.convocatoria = f.cleaned_data['convocatoria']

                                if f.cleaned_data['mecanismotitulacionposgrado'].id == 15:  # examen omplexivo
                                    tema.moduloreferencia = f.cleaned_data['moduloreferencia']
                                    tema.variabledependiente = "NO APLICA"
                                    tema.variableindependiente = "NO APLICA"

                                else:  # proyecto desarrollo e investigacion
                                    tema.moduloreferencia = ""
                                tema.save(request)
                                if 'archivo' in request.FILES:
                                    newfile = request.FILES['archivo']
                                    newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)
                                    # newfile._name = generar_nombre(inscripcion.persona.nombre_completo_inverso(), newfile._name)
                                    tema.archivo = newfile
                                tema.save(request)

                                #edito la cabecera
                                cabecera  = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk = tema.cabeceratitulacionposgrado.pk, status = True)
                                cabecera.sublinea = tema.sublinea
                                cabecera.mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado
                                cabecera.convocatoria = tema.convocatoria
                                cabecera.propuestatema = tema.propuestatema
                                cabecera.tutor = None
                                cabecera.variabledependiente = tema.variabledependiente
                                cabecera.variableindependiente = tema.variableindependiente
                                cabecera.save(request)



                                #asigno nuevo companero
                                # copio lo mismo para el integrante 2

                                # si cambia de pareja
                                maestrante_actual = tema
                                companiero = None
                                nuevo_companiero = None

                                if maestrante_actual.cabeceratitulacionposgrado:  # si tiene companiero
                                    companiero = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=maestrante_actual.cabeceratitulacionposgrado,status=True).exclude(id=maestrante_actual.pk)

                                if TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id=f.cleaned_data['companero']).exists():
                                    nuevo_companiero = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula_id= f.cleaned_data['companero'])[0]

                                if companiero:
                                    if nuevo_companiero:
                                        if not nuevo_companiero.pk == companiero[0].pk:
                                            for com in companiero:
                                                com.status = False
                                                com.save(request)

                                            matriculaestudiante2 = TemaTitulacionPosgradoMatricula(
                                                matricula_id=f.cleaned_data['companero'],
                                                sublinea=tema.sublinea,
                                                mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                                propuestatema=tema.propuestatema,
                                                convocatoria=tema.convocatoria,
                                                variabledependiente=tema.variabledependiente,
                                                variableindependiente=tema.variableindependiente,
                                                tutor=None,
                                                moduloreferencia=tema.moduloreferencia,
                                                cabeceratitulacionposgrado=cabecera,
                                                archivo=tema.archivo,

                                            )
                                            matriculaestudiante2.save(request)
                                            # guardo el historial 1
                                            if not tema.get_ultimo_estado() == 1:
                                                tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(
                                                tematitulacionposgradomatricula=tema,
                                                observacion='NINGUNA',
                                                estado=1)
                                                tematitulacionposgradomatriculahistorialestudiante1.save(request)
                                                log(u'Edito Tema Titulación PosGrado Pareja: %s' % tematitulacionposgradomatriculahistorialestudiante1, request,"add")
                                                # guardo el historial del estudiante 2
                                            if not matriculaestudiante2.get_ultimo_estado() == 1:
                                                tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                                    tematitulacionposgradomatricula=matriculaestudiante2,
                                                    observacion='NINGUNA',
                                                    estado=1)
                                                tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                                log(u'Modifico compañero de titulación: compañero actual: %s' % matriculaestudiante2, request,
                                                    "add")
                                        else:
                                                companiero[0].sublinea = tema.sublinea
                                                companiero[0].mecanismotitulacionposgrado = tema.mecanismotitulacionposgrado
                                                companiero[0].propuestatema = tema.propuestatema
                                                companiero[0].convocatoria = tema.convocatoria
                                                companiero[0].variabledependiente = tema.variabledependiente
                                                companiero[0].variableindependiente = tema.variableindependiente
                                                companiero[0].tutor = None
                                                companiero[0].moduloreferencia = tema.moduloreferencia
                                                companiero[0].cabeceratitulacionposgrado = cabecera
                                                companiero[0].archivo = tema.archivo
                                                companiero[0].save(request)
                                                # guardo el historial 1
                                                if not maestrante_actual.get_ultimo_estado() == 1:
                                                    tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=maestrante_actual,observacion='NINGUNA',estado=1)
                                                    tematitulacionposgradomatriculahistorialestudiante1.save(request)
                                                    log(u'Edito Tema Titulación PosGrado pareja: %s' % tematitulacionposgradomatriculahistorialestudiante1,request, "add")

                                                # guardo el historial del estudiante 2
                                                if not companiero[0].get_ultimo_estado() == 1:
                                                    tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=companiero[0], observacion='NINGUNA',estado=1)
                                                    tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                                    log(u'Edito compañero de titulación posgrado pareja: compañero actual: %s' % tematitulacionposgradomatriculahistorialestudiante2, request,"add")


                            else: #si no tiene es indivudual y quiere en pareja
                                tema.sublinea = f.cleaned_data['sublinea']#edito la info
                                tema.mecanismotitulacionposgrado = f.cleaned_data['mecanismotitulacionposgrado']
                                tema.propuestatema = f.cleaned_data['propuestatema']
                                tema.variabledependiente = f.cleaned_data['variabledependiente']
                                tema.variableindependiente = f.cleaned_data['variableindependiente']
                                tema.convocatoria = f.cleaned_data['convocatoria']
                                if f.cleaned_data['mecanismotitulacionposgrado'].id == 15:  # examen omplexivo
                                    tema.moduloreferencia = f.cleaned_data['moduloreferencia']
                                    tema.variabledependiente = "NO APLICA"
                                    tema.variableindependiente = "NO APLICA"

                                else:  # proyecto desarrollo e investigacion
                                    tema.moduloreferencia = ""
                                tema.save(request)
                                if 'archivo' in request.FILES:
                                    newfile = request.FILES['archivo']
                                    newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)
                                    # newfile._name = generar_nombre(inscripcion.persona.nombre_completo_inverso(), newfile._name)
                                    tema.archivo = newfile
                                tema.save(request)

                                #creoo la cabecera

                                if not TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True,
                                    sublinea=tema.sublinea,
                                    mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                    convocatoria=tema.convocatoria,
                                    propuestatema=tema.propuestatema).exists():


                                    cabecera = TemaTitulacionPosgradoMatriculaCabecera(
                                        sublinea=tema.sublinea,
                                        mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                        convocatoria=tema.convocatoria,
                                        propuestatema=tema.propuestatema,
                                        tutor=None,
                                        variabledependiente=tema.variabledependiente,
                                        variableindependiente=tema.variableindependiente)

                                    cabecera.save(request)
                                else:
                                    cabecera=TemaTitulacionPosgradoMatriculaCabecera.objects.filter(status=True,
                                                                                           sublinea=tema.sublinea,
                                                                                           mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                                                                           convocatoria=tema.convocatoria,
                                                                                           propuestatema=tema.propuestatema)[0]
                                # asigno las parejas las dos parejas
                                tema.cabeceratitulacionposgrado = cabecera#integrante 1
                                tema.save(request)
                                #copio lo mismo para el integrante 2
                                matriculaestudiante2 = TemaTitulacionPosgradoMatricula(
                                    matricula_id=f.cleaned_data['companero'],
                                    sublinea=tema.sublinea,
                                    mecanismotitulacionposgrado=tema.mecanismotitulacionposgrado,
                                    propuestatema=tema.propuestatema,
                                    convocatoria=tema.convocatoria,
                                    variabledependiente=tema.variabledependiente,
                                    variableindependiente=tema.variableindependiente,
                                    tutor=None,
                                    moduloreferencia=tema.moduloreferencia,
                                    cabeceratitulacionposgrado=cabecera,
                                    archivo=tema.archivo,

                                )
                                matriculaestudiante2.save(request)
                                # guardo el historial 1
                                if TemaTitulacionPosgradoMatriculaHistorial.objects.filter(tematitulacionposgradomatricula=tema, status=True,).exists():
                                    if not tema.get_ultimo_estado() == 1:
                                        tematitulacionposgradomatriculahistorialestudiante1 = TemaTitulacionPosgradoMatriculaHistorial(
                                            tematitulacionposgradomatricula=tema,
                                            observacion='NINGUNA',
                                            estado=1)
                                        tematitulacionposgradomatriculahistorialestudiante1.save(request)
                                        log(u'Adiciono Tema Titulación PosGrado: %s' % tematitulacionposgradomatriculahistorialestudiante1,
                                            request,
                                            "add")

                                # guardo el historial 2
                                if TemaTitulacionPosgradoMatriculaHistorial.objects.filter(tematitulacionposgradomatricula=matriculaestudiante2,status=True).exists():
                                    if not matriculaestudiante2.get_ultimo_estado() == 1:
                                        tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                            tematitulacionposgradomatricula=matriculaestudiante2,
                                            observacion='NINGUNA',
                                            estado=1)
                                        tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                        log(u'Adiciono Tema Titulación PosGrado: %s' % matriculaestudiante2,
                                            request,
                                            "add")
                                else:
                                    tematitulacionposgradomatriculahistorialestudiante2 = TemaTitulacionPosgradoMatriculaHistorial(
                                        tematitulacionposgradomatricula=matriculaestudiante2,
                                        observacion='NINGUNA',
                                        estado=1)
                                    tematitulacionposgradomatriculahistorialestudiante2.save(request)
                                    log(u'Adiciono Tema Titulación PosGrado: %s' % matriculaestudiante2,
                                        request,
                                        "add")

                        else:#individual check
                            tema = TemaTitulacionPosgradoMatricula.objects.get(pk=request.POST['id'], status=True)
                            if tema.cabeceratitulacionposgrado:#si hizo en pareja pero ahora quiere individual
                                #eliminar companero y quitar
                                companero_anterior = TemaTitulacionPosgradoMatricula.objects.filter(
                                    cabeceratitulacionposgrado=tema.cabeceratitulacionposgrado, status=True).exclude(id=tema.pk)
                                for com in companero_anterior:
                                    com.status = False
                                    com.save(request)

                                id_cabecera = tema.cabeceratitulacionposgrado.pk
                                tema.cabeceratitulacionposgrado = None
                                tema.save(request)
                                # eliminar cabecera
                                cab = TemaTitulacionPosgradoMatriculaCabecera.objects.filter(pk=id_cabecera, status = True)[0]
                                cab.status=False
                                cab.save(request)

                                log(u'Quito a su compañero de titulación, ahora va hacer individual: %s' % tema, request, "edit")
                            else:
                                # si se registra individual
                                tema.sublinea = f.cleaned_data['sublinea']
                                tema.mecanismotitulacionposgrado = f.cleaned_data['mecanismotitulacionposgrado']
                                tema.propuestatema = f.cleaned_data['propuestatema']
                                tema.variabledependiente = f.cleaned_data['variabledependiente']
                                tema.variableindependiente = f.cleaned_data['variableindependiente']
                                tema.convocatoria = f.cleaned_data['convocatoria']
                                if f.cleaned_data['mecanismotitulacionposgrado'].id == 15: #examen omplexivo
                                   tema.moduloreferencia = f.cleaned_data['moduloreferencia']
                                   tema.variabledependiente = "NO APLICA"
                                   tema.variableindependiente = "NO APLICA"

                                else:#proyecto desarrollo e investigacion
                                    tema.moduloreferencia = ""
                                tema.save(request)
                                if 'archivo' in request.FILES:
                                    newfile = request.FILES['archivo']
                                    newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)
                                    # newfile._name = generar_nombre(inscripcion.persona.nombre_completo_inverso(), newfile._name)
                                    tema.archivo = newfile
                                tema.save(request)
                                #Guaddar Historial
                                if TemaTitulacionPosgradoMatriculaHistorial.objects.filter(tematitulacionposgradomatricula=tema, status = True).exists():
                                    if not tema.get_ultimo_estado() == 1:
                                        tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoMatriculaHistorial(tematitulacionposgradomatricula=tema,
                                                                                                                            observacion = 'NINGUNA',
                                                                                                                            estado = 1)
                                        tematitulacionposgradomatriculahistorial.save(request)
                                        log(u'Modifico Tema Titulación PosGrado: %s' % tema, request, "edit")
                                else:
                                    tematitulacionposgradomatriculahistorial = TemaTitulacionPosgradoMatriculaHistorial(
                                        tematitulacionposgradomatricula=tema,
                                        observacion='NINGUNA',
                                        estado=1)
                                    tematitulacionposgradomatriculahistorial.save(request)
                                    log(u'Modifico Tema Titulación PosGrado: %s' % tema, request, "edit")

                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'delete':
                try:
                    solicitud = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']), status=True)
                    if solicitud.cabeceratitulacionposgrado:#si es en pareja boora la solicitud del companero y la cabecera

                        companero = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=solicitud.cabeceratitulacionposgrado)
                        log(u'Eliminó la solicitud de los estudiantes de posgrado: %s' % companero, request, "del")
                        companero.delete()
                        cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=solicitud.cabeceratitulacionposgrado.pk)
                        cabecera.delete()

                    else:
                        log(u'Eliminó la solicitud estudiante posgrado: %s' % solicitud, request, "del")
                        solicitud.delete()
                    return JsonResponse({"result": "ok"})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            if action == 'detalleaprobacion':
                try:
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    if tema.cabeceratitulacionposgrado:
                        data['temapareja'] = cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=tema.cabeceratitulacionposgrado.pk)
                        temaparejas = cabecera.obtener_parejas()[0]
                        data['historialaprobacionpareja'] = temaparejas.tematitulacionposgradomatriculahistorial_set.filter(
                            status=True).order_by('-id')
                        template = get_template("alu_tematitulacionposgrado/detalleaprobacionpareja.html")

                    else:
                        data['tema'] = tema
                        data['historialaprobacion'] = tema.tematitulacionposgradomatriculahistorial_set.filter(status=True).order_by('-id')
                        template = get_template("alu_tematitulacionposgrado/detalleaprobacion.html")

                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            if action == 'adddoc':
                try:
                    f = ComplexivoSubirPropuesta1Form(request.POST, request.FILES)
                    newfilep = None
                    newfilex = None
                    if 'propuesta' in request.FILES:
                        newfilep = request.FILES['propuesta']
                        if newfilep:
                            if newfilep.size > 22582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilep.size <= 0:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                            else:
                                newfilesd = newfilep._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc':
                                    newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                elif ext == '.docx':
                                    newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo de Propuesta Práctica solo en .doc, docx."})
                    if 'extracto' in request.FILES:
                        newfilex = request.FILES['extracto']
                        if newfilex:
                            if newfilex.size > 22582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilex.size <= 0:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío."})
                            else:
                                newfilesd = newfilex._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc':
                                    newfilex._name = generar_nombre("extracto_", newfilex._name)
                                elif ext == '.docx':
                                    newfilex._name = generar_nombre("extracto_", newfilex._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx."})
                    if newfilep and newfilex:
                        es_pareja = request.POST['es_pareja']
                        if es_pareja == 'True':
                            grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.POST['id']))
                            if f.is_valid():
                                cabecera = RevisionTutoriasTemaTitulacionPosgradoProfesor(
                                    tematitulacionposgradomatriculacabecera=grupo, fecharevision=datetime.now())
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(
                                        revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=1,
                                        archivo=newfilep, fecha=datetime.now())
                                    propuesta.save(request)
                                if newfilex:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(
                                        revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=2,
                                        archivo=newfilex, fecha=datetime.now())
                                    propuesta.save(request)
                                log(u"Añade archivo propuesta en pareja version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (
                                    grupo.id, grupo.propuestatema), request, "add")
                                return JsonResponse({'result': 'ok'})
                            else:
                                return JsonResponse({'result': 'bad', 'mensaje': u'Error, al guardar los archivos'})
                        else:
                            grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                            if f.is_valid():
                                cabecera = RevisionTutoriasTemaTitulacionPosgradoProfesor(
                                    tematitulacionposgradomatricula=grupo, fecharevision=datetime.now())
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=1, archivo=newfilep,fecha=datetime.now())
                                    propuesta.save(request)
                                if newfilex:
                                    propuesta = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor(revisiontutoriastematitulacionposgradoprofesor=cabecera, tipo=2, archivo=newfilex,fecha=datetime.now())
                                    propuesta.save(request)
                                log(u"Añade archivo propuesta version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (grupo.id, grupo.propuestatema), request, "add")
                                return JsonResponse({'result': 'ok'})
                            else:
                                return JsonResponse({'result': 'bad', 'mensaje': u'Error, al guardar los archivos'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ingrese almenos un archivo'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al guardar archivos'})

            if action == 'adddocensayo':
                try:
                    f = ExamenComplexivoEnsayoForm(request.POST, request.FILES)
                    newfilep = None
                    newfilex = None
                    if 'propuesta' in request.FILES:
                        newfilep = request.FILES['propuesta']
                        if newfilep:
                            if newfilep.size > 22582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilep.size <= 0:
                                return JsonResponse(
                                    {"result": "bad", "mensaje": u"Error, el archivo Propuesta Práctica esta vacío."})
                            else:
                                newfilesd = newfilep._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc':
                                    newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                elif ext == '.docx':
                                    newfilep._name = generar_nombre("propuesta_", newfilep._name)

                                elif ext == '.pdf':
                                    newfilep._name = generar_nombre("propuesta_", newfilep._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo de Propuesta Práctica solo en .doc, docx. y .pdf"})

                    if 'extracto' in request.FILES:
                        newfilex = request.FILES['extracto']
                        if newfilex:
                            if newfilex.size > 22582912:
                                return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                            elif newfilex.size <= 0:
                                return JsonResponse({"result": "bad",
                                                     "mensaje": u"Error, el archivo Propuesta Práctica (Desde introducción hasta conclusión) esta vacío."})
                            else:
                                newfilesd = newfilex._name
                                ext = newfilesd[newfilesd.rfind("."):]
                                if ext == '.doc':
                                    newfilex._name = generar_nombre("extracto_", newfilex._name)
                                elif ext == '.docx':
                                    newfilex._name = generar_nombre("extracto_", newfilex._name)
                                elif ext == '.pdf':
                                    newfilep._name = generar_nombre("extracto_", newfilep._name)
                                else:
                                    return JsonResponse({"result": "bad",
                                                         "mensaje": u"Error, archivo Propuesta Práctica Antiplagio solo en .doc, docx. y .pdf"})

                    if newfilep:
                        es_pareja = request.POST['es_pareja']
                        if es_pareja == 'True':
                            grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(request.POST['id']))
                            if f.is_valid():
                                cabecera = RevisionPropuestaComplexivoPosgrado(
                                    tematitulacionposgradomatriculacabecera=grupo, fecharevision=datetime.now())
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(
                                        revisionpropuestacomplexivoposgrado=cabecera, tipo=5,
                                        archivo=newfilep, fecha=datetime.now())
                                    propuesta.save(request)
                                if newfilex:
                                    propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(
                                        revisionpropuestacomplexivoposgrado=cabecera, tipo=2,
                                        archivo=newfilex, fecha=datetime.now())
                                    propuesta.save(request)
                                log(u"Añade archivo propuesta en pareja version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (
                                    grupo.id, grupo.propuestatema), request, "add")
                                return JsonResponse({'result': 'ok'})
                            else:
                                return JsonResponse({'result': 'bad', 'mensaje': u'Error, al guardar los archivos'})
                        else:
                            grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.POST['id']))
                            if f.is_valid():
                                cabecera = RevisionPropuestaComplexivoPosgrado(
                                    tematitulacionposgradomatricula=grupo, fecharevision=datetime.now())
                                cabecera.save(request)
                                if newfilep:
                                    propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(
                                        revisionpropuestacomplexivoposgrado=cabecera, tipo=5, archivo=newfilep,
                                        fecha=datetime.now())
                                    propuesta.save(request)
                                if newfilex:
                                    propuesta = ArchivoRevisionPropuestaComplexivoPosgrado(
                                        revisionpropuestacomplexivoposgrado=cabecera, tipo=2, archivo=newfilex,
                                        fecha=datetime.now())
                                    propuesta.save(request)
                                log(u"Añade archivo propuesta version urkund a  grupo [%s] con línea de investigación: %s, de posgrado" % (
                                grupo.id, grupo.propuestatema), request, "add")
                                return JsonResponse({'result': 'ok'})
                            else:
                                return JsonResponse({'result': 'bad', 'mensaje': u'Error, al guardar los archivos'})


                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Ingrese almenos un archivo'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrio un problema al guardar archivos'})

            elif action == 'editdoc':
                try:
                    f = ComplexivoEditarArchivoPropuestaForm(request.POST, request.FILES)
                    if f.is_valid():
                        archivo = ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.POST['id'])
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if archivo.tipo == 1:
                                nombre = "propuesta"
                            else:
                                nombre = "propuesta version urkund"
                            newfile._name = generar_nombre(nombre, newfile._name)
                            archivo.archivo = newfile
                            archivo.fecha = datetime.now()
                            archivo.save(request)
                            if archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatricula:
                                vista_grupo =archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatricula.id
                                vista_revision_grupo=archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatricula.propuestatema
                            else:
                                vista_grupo = archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatriculacabecera.id
                                vista_revision_grupo = archivo.revisiontutoriastematitulacionposgradoprofesor.tematitulacionposgradomatriculacabecera.propuestatema
                            log(u"Edita archivo %s del grupo [%s] con línea de investigación: %s, de posgrado" % (nombre, vista_grupo ,vista_revision_grupo),request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Revise la extension del archivos'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al guardar archivos'})

            elif action == 'editdocensayo':
                try:
                    f = ComplexivoEditarArchivoPropuestaForm(request.POST, request.FILES)
                    if f.is_valid():
                        archivo = ArchivoRevisionPropuestaComplexivoPosgrado.objects.get(pk=request.POST['id'])
                        if 'archivo' in request.FILES:
                            newfile = request.FILES['archivo']
                            if archivo.tipo == 5:
                                nombre = "propuesta_ensayo"
                            else:
                                nombre = "propuesta_ensayo"
                            newfile._name = generar_nombre(nombre, newfile._name)
                            archivo.archivo = newfile
                            archivo.fecha = datetime.now()
                            archivo.save(request)
                            if archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatricula:
                                vista_grupo =archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatricula.id
                                vista_revision_grupo=archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatricula.propuestatema
                            else:
                                vista_grupo = archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatriculacabecera.id
                                vista_revision_grupo = archivo.revisionpropuestacomplexivoposgrado.tematitulacionposgradomatriculacabecera.propuestatema
                            log(u"Edita archivo propuesta ensayo %s del grupo [%s] con línea de investigación: %s, de posgrado" % (nombre, vista_grupo ,vista_revision_grupo),request, "edit")
                        return JsonResponse({'result': 'ok'})
                    else:
                        return JsonResponse({'result': 'bad', 'mensaje': u'Revise la extension del archivos'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad', 'mensaje': u'Ocurrió un problema al guardar archivos'})

            elif action == 'deldoc':
                try:
                    revision = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(pk=request.POST['id'])
                    revision.delete()
                    log(u"Elimina archivo de propuesta de tutoría de posgrado %s" % (revision), request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad'})

            elif action == 'deldocensayo':
                try:
                    revision = RevisionPropuestaComplexivoPosgrado.objects.filter(pk=request.POST['id'])
                    revision.delete()
                    log(u"Elimina archivo de propuesta de ensayo de posgrado %s" % (revision), request, "delete")
                    return JsonResponse({'result': 'ok'})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({'result': 'bad'})

            elif action == 'addarchivofinaltitulacion':
                try:
                    form = CorrecionArchivoFinalSustentacionPosgradoForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        d = request.FILES['archivo']
                        newfile = d._name
                        ext = newfile[newfile.rfind("."):]
                        if ext == '.doc' or ext == '.docx':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .doc, .docx."})
                        if d.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                    if form.is_valid():
                        grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(encrypt(request.POST['id'])))
                        if not grupo.tematitulacionposarchivofinal_set.filter(status=True):
                            if 'archivo' in request.FILES:
                                subirarchivo = TemaTitulacionPosArchivoFinal(tematitulacionposgradomatricula=grupo)
                                subirarchivo.save()
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("archivofinalpos", newfile._name)
                                subirarchivo.archivo = newfile
                                subirarchivo.estado = 1
                                subirarchivo.save(request)
                        else:
                            subirarchivo = grupo.tematitulacionposarchivofinal_set.filter(status=True)[0]
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("archivofinalpos", newfile._name)
                                subirarchivo.archivo = newfile
                                subirarchivo.estado = 1
                                subirarchivo.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'addarchivofinaltitulacionpareja':
                try:
                    form = CorrecionArchivoFinalSustentacionPosgradoForm(request.POST, request.FILES)
                    if 'archivo' in request.FILES:
                        d = request.FILES['archivo']
                        newfile = d._name
                        ext = newfile[newfile.rfind("."):]
                        if ext == '.doc' or ext == '.docx':
                            a = 1
                        else:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, solo archivos .doc, .docx."})
                        if d.size > 10485760:
                            return JsonResponse({"result": "bad", "mensaje": u"Error, archivo mayor a 12 Mb."})
                    if form.is_valid():
                        grupo = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(encrypt(request.POST['id'])))
                        if not grupo.tematitulacionposarchivofinal_set.filter(status=True):
                            if 'archivo' in request.FILES:
                                subirarchivo = TemaTitulacionPosArchivoFinal(tematitulacionposgradomatriculacabecera=grupo)
                                subirarchivo.save()
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("archivofinalpos", newfile._name)
                                subirarchivo.archivo = newfile
                                subirarchivo.estado = 1
                                subirarchivo.save(request)
                        else:
                            subirarchivo = grupo.tematitulacionposarchivofinal_set.filter(status=True)[0]
                            if 'archivo' in request.FILES:
                                newfile = request.FILES['archivo']
                                newfile._name = generar_nombre("archivofinalpos", newfile._name)
                                subirarchivo.archivo = newfile
                                subirarchivo.estado = 1
                                subirarchivo.save(request)
                        return JsonResponse({"result": "ok"})
                    else:
                        raise NameError('Error')
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": "Error al guardar los datos."})

            elif action == 'aprobar_rechazar_tutor_por_estudiante':
                try:
                    if 'id' in request.POST and 'st' in request.POST and 'obs' in request.POST:
                        profesor = TemaTitulacionPosgradoProfesor.objects.get(pk=int(request.POST['id']))
                        if variable_valor('APROBAR_SILABO') == int(request.POST['st']):
                            profesor.estado_estudiante = 2 #aprobado
                            profesor.save(request)
                            log(u'Aprobó la solicitud del docente para ser su tutor en su proceso de titulación %s' % (profesor), request, "add")
                            if profesor.tematitulacionposgradomatricula:
                                temamatricula = profesor.tematitulacionposgradomatricula
                                temamatricula.tutor = profesor.profesor
                                temamatricula.save(request)
                                #rechazo el resto
                                otras_solicitudes = TemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatricula= profesor.tematitulacionposgradomatricula,status=True).exclude(pk=profesor.pk)
                                for solicitud in otras_solicitudes:
                                    solicitud.estado_estudiante = 3#rechazo
                                    solicitud.save(request)
                                    log(u'Rechazó la solicitud del docente para ser su tutor en su proceso de titulación %s' % (solicitud), request, "update")
                                    historial = SolicitudTutorTemaHistorial(
                                        tematitulacionposgradoprofesor=solicitud,
                                        persona=persona,
                                        estado=3,  # rechazado
                                        observacion= "Rechazó la solicitud del docente para ser su tutor en su proceso de titulación."

                                    )
                                    historial.save(request)


                            else:
                                temamatricula = profesor.tematitulacionposgradomatriculacabecera
                                temamatricula.tutor = profesor.profesor
                                temamatricula.save(request)
                                # rechazo el resto
                                otras_solicitudes = TemaTitulacionPosgradoProfesor.objects.filter(tematitulacionposgradomatriculacabecera=temamatricula,status=True).exclude(pk=profesor.pk)
                                for solicitud in otras_solicitudes:
                                    solicitud.estado_estudiante = 3  # rechazo
                                    solicitud.save(request)
                                    log(u'Rechazó la solicitud del docente para ser tutor en su proceso de titulación %s' % ( solicitud), request, "update")
                                    historial = SolicitudTutorTemaHistorial(
                                        tematitulacionposgradoprofesor=solicitud,
                                        persona=persona,
                                        estado=3,  # rechazado
                                        observacion="Rechazó la solicitud del docente porque ya seleccionó otro tutor en su proceso de titulación."

                                    )
                                    historial.save(request)


                            historial = SolicitudTutorTemaHistorial(
                                tematitulacionposgradoprofesor=profesor,
                                persona=persona,
                                estado=2, #aprobado
                                observacion=request.POST['obs']

                            )
                            historial.save(request)
                            aprobo = True
                        else:
                            profesor.estado_estudiante = 3  # rechazado
                            profesor.save(request)
                            log(u'Rechazó la solicitud del docente para ser su tutor en su proceso de titulación %s' % (profesor), request, "add")
                            historial = SolicitudTutorTemaHistorial(
                                tematitulacionposgradoprofesor=profesor,
                                persona=persona,
                                estado=3,# rechazado
                                observacion=request.POST['obs']

                            )
                            historial.save(request)
                            aprobo=False

                    return JsonResponse({"result": "ok",'profesor':profesor.profesor.__str__(),"aprobo":aprobo})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al guardar los datos."})

            elif action == 'subir_avance_tutoria':
                try:

                    if 'archivo' in request.FILES:

                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)

                        id = request.POST['id']
                        if newfile:
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if exte in ['doc', 'docx']:
                                newfile._name = generar_nombre("tutoria_avance", newfile._name)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, solo archivos .doc, .docx"})
                            tutoria = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=id)
                            tutoria.avance_propuesta = newfile
                            tutoria.save()
                            return JsonResponse({"result": False, "mensaje": u"Archivo subido correctamente."},
                                                safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Seleccione una archivo"})
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action== 'subir_acta_firmada':
                try:

                    if 'archivo' in request.FILES:

                        newfile = request.FILES['archivo']
                        newfile._name = generar_nombre(str(inscripcion.persona_id), newfile._name)

                        id = request.POST['id']
                        if newfile:
                            extension = newfile._name.split('.')
                            tam = len(extension)
                            exte = extension[tam - 1]
                            if newfile.size > 4194304:
                                return JsonResponse(
                                    {"result": True, "mensaje": u"Error, el tamaño del archivo es mayor a 4 Mb."})
                            if exte in ['pdf', 'PDF']:
                                newfile._name = generar_nombre("acta_firmada", newfile._name)
                            else:
                                transaction.set_rollback(True)
                                return JsonResponse({"result": True, "mensaje": u"Error, solo archivos .pdf"})

                            tema_titulacion = TemaTitulacionPosgradoMatricula.objects.get(pk=id)

                            tema_titulacion.actaaprobacionexamen = newfile
                            tema_titulacion.estado_acta_firma = 2
                            tema_titulacion.save(request)
                            log(u"El maestrante subió acta de aprobación firmada %s" % (tema_titulacion), request, "change")
                            historial = HistorialFirmaActaAprobacionComplexivo(
                                tema = tema_titulacion,
                                persona = persona,
                                actaaprobacionfirmada = newfile,
                                estado_acta_firma = 2
                            )
                            historial.save(request)

                            return JsonResponse({"result": False, "mensaje": u"Archivo subido correctamente."},safe=False)
                    else:
                        return JsonResponse({"result": True, "mensaje": u"Seleccione una archivo"})
                except Exception as ex:
                    transaction.set_rollback(True)

            elif action == 'pdfactaaprobacionexamencomplexivo':
                try:
                    actaaprobacionexamencomplexivo = actaaprobacionexamencomplexivoposgrado(request.POST['id'])
                    return actaaprobacionexamencomplexivo
                except Exception as ex:
                    pass


            return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        if 'action' in request.GET:
            action = request.GET['action']

            if action == 'add':
                try:
                    data['title'] = u'Ingresar Tema Titulación PosGrado'
                    form = IngresarTemaTitulacionPosgradoForm()
                    form.ingresar(carrera, malla, periodo)
                    data['carrera'] = carrera
                    data['periodo'] = periodo
                    data['form'] = form
                    return render(request, "alu_tematitulacionposgrado/add.html", data)
                except Exception as ex:
                    pass

            elif action == 'edit':
                try:
                    data['title'] = u'Editar Tema Titulación PosGrado'
                    data['carrera'] = carrera
                    data['periodo'] = periodo
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    form = IngresarTemaTitulacionPosgradoForm(initial={'sublinea': tema.sublinea,
                                                                       'mecanismotitulacionposgrado': tema.mecanismotitulacionposgrado,
                                                                       'propuestatema': tema.propuestatema,
                                                                       'convocatoria': tema.convocatoria,
                                                                       'variabledependiente': tema.variabledependiente,
                                                                       'variableindependiente': tema.variableindependiente,
                                                                        'moduloreferencia': tema.moduloreferencia} )

                    if tema.cabeceratitulacionposgrado:
                        pareja = True
                        companerotema = TemaTitulacionPosgradoMatricula.objects.filter(cabeceratitulacionposgrado=tema.cabeceratitulacionposgrado,status=True).exclude(pk=tema.pk)
                        data['companero'] = companerotema[0]
                    else:
                        pareja = False
                        data['companero'] = False
                    form.editar(carrera, malla, periodo, tema.convocatoria_id,pareja)
                    data['tema'] = tema
                    data['form'] = form
                    return render(request, "alu_tematitulacionposgrado/edit.html", data)
                except Exception as ex:
                    pass

            if action == 'delete':
                try:
                    data['title'] = u'Eliminar solicitud de tema titulación'
                    data['solicitud'] = TemaTitulacionPosgradoMatricula.objects.get(pk=request.GET['id'])
                    return render(request, 'alu_tematitulacionposgrado/delete.html', data)
                except Exception as ex:
                    pass

            if action == 'adddoc':
                try:
                    grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    if grupo.cabeceratitulacionposgrado:
                        cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=grupo.cabeceratitulacionposgrado_id)
                        data['grupo'] = cabecera
                        data['es_pareja'] = True
                    else:
                        data['grupo'] = grupo
                        data['es_pareja'] = False
                    data['title'] = u"SUBIR DOCUMENTOS PARA REVISIÓN TUTORÍAS"
                    data['form'] = ComplexivoSubirPropuesta1Form()
                    return render(request, "alu_tematitulacionposgrado/adddoc.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar formulario."})


            if action == 'adddocensayo':
                try:
                    grupo = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    if grupo.cabeceratitulacionposgrado:
                        cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(
                            pk=grupo.cabeceratitulacionposgrado_id)
                        data['grupo'] = cabecera
                        data['es_pareja'] = True
                    else:
                        data['grupo'] = grupo
                        data['es_pareja'] = False
                    data['title'] = u"SUBIR DOCUMENTOS PARA REVISIÓN DE ENSAYO"
                    data['form'] = ExamenComplexivoEnsayoForm()
                    return render(request, "alu_tematitulacionposgrado/adddocensayo.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar formulario."})

            elif action == 'editdoc':
                try:
                    data['archivo']= archivo =ArchivoRevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=int(request.GET['id']))
                    tipo = archivo.tipo
                    tiparchivo = TIPO_ARCHIVO_PORSGRADO.__getitem__(tipo - 1)[1]
                    data['title'] = u"MODIFICAR %s" % (tiparchivo)
                    data['form'] = ComplexivoEditarArchivoPropuestaForm()
                    return render(request, "alu_tematitulacionposgrado/editdoc.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar formulario."})

            elif action == 'editdocensayo':
                try:
                    data['archivo'] = archivo = ArchivoRevisionPropuestaComplexivoPosgrado.objects.get(
                        pk=int(request.GET['id']))
                    tipo = archivo.tipo
                    tiparchivo = TIPO_ARCHIVO_PORSGRADO.__getitem__(tipo - 1)[1]
                    data['title'] = u"MODIFICAR %s" % (tiparchivo)
                    data['form'] = ComplexivoEditarArchivoPropuestaForm()
                    return render(request, "alu_tematitulacionposgrado/editdocensayo.html", data)
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al cargar formulario."})

            elif action == 'instruccionformaldocente':
                try:
                    if 'id' in request.GET:
                        data['title'] = u'Instrucción formal del profesor'
                        data['personadocente'] =  profesor = Profesor.objects.get(pk=request.GET['id'],status =True)
                        template = get_template("adm_configuracionpropuesta/instruccionformaldocente.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'lista_profesores_disponibles':
                try:
                    tema = TemaTitulacionPosgradoMatricula.objects.get(pk=int(request.GET['id']))
                    data['aprobar'] = variable_valor('APROBAR_SILABO')
                    data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                    data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                    if tema.cabeceratitulacionposgrado:
                        data['tema'] = tema.cabeceratitulacionposgrado
                        data['profesores_disponibles'] = tema.cabeceratitulacionposgrado.tematitulacionposgradoprofesor_set.filter(status=True, aprobado=True).order_by(
                            '-id')
                        data['tutor_aprobado'] = tema.cabeceratitulacionposgrado.tematitulacionposgradoprofesor_set.filter(status=True,   aprobado=True, estado_estudiante=2).exists()


                    else:
                        data['tema'] = tema
                        data['profesores_disponibles'] = tema.tematitulacionposgradoprofesor_set.filter(status=True,aprobado = True ).order_by('-id')
                        data['tutor_aprobado'] = tema.tematitulacionposgradoprofesor_set.filter(status=True,aprobado = True ,estado_estudiante = 2).exists()

                    template = get_template("alu_tematitulacionposgrado/lista_profesores_disponibles.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detalleTutoria':
                try:
                    data['detalles' ] = detalles = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['idd'])

                    template = get_template("alu_tematitulacionposgrado/detalletutoriaposgrado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass

            elif action == 'detalleTutoriaPareja':
                try:
                    data['detalles' ] = detalles = TutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['idd'])

                    template = get_template("alu_tematitulacionposgrado/detalletutoriaposgrado.html")
                    json_content = template.render(data)
                    return JsonResponse({"result": "ok", 'data': json_content})
                except Exception as ex:
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})
                    pass


            elif action == 'deldoc':
                try:
                    data['title'] = u"Eliminar Propuesta Tutoría"
                    revision = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                    if revision.tematitulacionposgradomatricula:
                        grupo = revision.tematitulacionposgradomatricula

                    else:
                        grupo = revision.tematitulacionposgradomatriculacabecera

                    data['mensaje'] = u"¿Está seguro que desea eliminar los archivos de la Propuesta Tutoría?"
                    data['grupo'] = grupo
                    data['revision'] = revision
                    return render(request, "alu_tematitulacionposgrado/deletedoc.html", data)
                except Exception as ex:
                    pass

            elif action == 'deldocensayo':
                try:
                    data['title'] = u"Eliminar Propuesta Ensayo"
                    revision = RevisionPropuestaComplexivoPosgrado.objects.get(pk=request.GET['id'])
                    if revision.tematitulacionposgradomatricula:
                        grupo = revision.tematitulacionposgradomatricula

                    else:
                        grupo = revision.tematitulacionposgradomatriculacabecera

                    data['mensaje'] = u"¿Está seguro que desea eliminar el archivos de la Propuesta de ensayo?"
                    data['grupo'] = grupo
                    data['revision'] = revision
                    return render(request, "alu_tematitulacionposgrado/deletedocensayo.html", data)
                except Exception as ex:
                    pass

            elif action == 'addarchivofinaltitulacion':
                try:
                    data['title'] = u"Archivo final"
                    data['grupo'] = TemaTitulacionPosgradoMatricula.objects.get(pk=int(encrypt(request.GET['id_grupo'])))
                    data['form'] = CorrecionArchivoFinalSustentacionPosgradoForm()
                    data['action'] = 'addarchivofinaltitulacion'
                    return render(request, 'alu_tematitulacionposgrado/addarchivofinaltitulacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'addarchivofinaltitulacionpareja':
                try:
                    data['title'] = u"Archivo final"
                    data['grupo'] = TemaTitulacionPosgradoMatriculaCabecera.objects.get(pk=int(encrypt(request.GET['id_grupo'])))
                    data['form'] = CorrecionArchivoFinalSustentacionPosgradoForm()
                    data['action'] = 'addarchivofinaltitulacionpareja'

                    return render(request, 'alu_tematitulacionposgrado/addarchivofinaltitulacion.html', data)
                except Exception as ex:
                    pass

            elif action == 'asignar_grupo_complexivo':
                try:
                    se_encuentra_inscrito = False
                    data['id_tema']=request.GET['id']
                    data['grupos'] = GrupoTitulacionPostgrado.objects.filter(status=True,configuracion=request.GET['id_configuracion'])
                    if DetalleGrupoTitulacionPostgrado.objects.filter(inscrito=int(request.GET['id']),status=True).exists():
                        grupo_seleccionado = DetalleGrupoTitulacionPostgrado.objects.get(inscrito=int(request.GET['id']),status=True)
                        se_encuentra_inscrito = True
                    else:
                        grupo_seleccionado=""
                        se_encuentra_inscrito = False
                    data['se_encuentra_inscrito'] = se_encuentra_inscrito
                    data['grupo_seleccionado'] = grupo_seleccionado

                    template = get_template("alu_tematitulacionposgrado/elejirgrupotitposgrado.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'asignar_cupo_grupo_complexivo':
                try:
                    res_json = []
                    with transaction.atomic():

                        if(DetalleGrupoTitulacionPostgrado.objects.filter(grupoTitulacionPostgrado =int(request.GET['id_grupo']),inscrito=int(request.GET['id_tema']),status=True).exists()):
                            return JsonResponse({"result": "bad", "mensaje": "Usted ya se encuentra inscrito en este grupo."})


                        inscripcion = DetalleGrupoTitulacionPostgrado(
                            grupoTitulacionPostgrado_id=int(request.GET['id_grupo']),
                            inscrito_id=int(request.GET['id_tema'])
                        )
                        inscripcion.save()
                        log(u"Inscripcion a grupo titulacion posgrador %s" % (inscripcion), request, "add")
                        res_json = {"result": True,"mensaje":"Usted ha seleccionado grupo correctamente"}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'editar_cupo_grupo_complexivo':
                try:
                    res_json = []
                    with transaction.atomic():

                        inscrito = DetalleGrupoTitulacionPostgrado.objects.get(id=int(request.GET['id_grupo_anterior']), inscrito=int(request.GET['id_tema']), status=True)
                        inscrito.grupoTitulacionPostgrado_id = int(request.GET['id_grupo'])
                        inscrito.save()
                        log(u"Cambio de grupo  inscripcion titulacion posgrador %s" % (inscrito), request, "edit")
                        res_json = {"result": True, "mensaje":"Usted ha cambiado de grupo correctamente"}
                except Exception as ex:
                    res_json = {'error': True, "message": "Error: {}".format(ex)}
                return JsonResponse(res_json, safe=False)

            elif action == 'subir_avance_tutoria':
                try:
                    if 'id' in request.GET:
                        data['id'] = id = request.GET['id']
                        data['action'] = action = 'subir_avance_tutoria'
                        template = get_template("alu_tematitulacionposgrado/modal/formSubirAvanceTutoria.html")
                        return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            elif action == 'historial_aprobacion_tutor':
                try:
                    if 'id' in request.GET:
                        data['title'] = u'Historial de solicitud de tutor'
                        temaProfesor = TemaTitulacionPosgradoProfesor.objects.get(pk=request.GET['id'])
                        data['historial'] = historial = temaProfesor.solicitudtutortemahistorial_set.filter(status=True).order_by("-id")
                        template = get_template("adm_configuracionpropuesta/historial_aprobacion_tutor.html")
                        return JsonResponse({"result": 'ok', 'data': template.render(data)})
                except Exception as ex:
                    transaction.set_rollback(True)
                    return JsonResponse({"result": "bad", "mensaje": u"Error al obtener los datos."})

            elif action == 'subir_acta_firmada':
                try:
                    data['title'] = u'Subir Acta firmada'
                    data['id'] = request.GET['id']
                    template = get_template("alu_tematitulacionposgrado/modal/formsubir_acta_firmada.html")
                    return JsonResponse({"result": True, 'data': template.render(data)})
                except Exception as ex:
                    pass

            return HttpResponseRedirect(request.path)
        else:
            try:
                # propuesta
                data['aprobar'] = variable_valor('APROBAR_SILABO')
                data['rechazar'] = variable_valor('RECHAZAR_SILABO')
                data['pendiente'] = variable_valor('PENDIENTE_SILABO')
                puede = False
                puede2 = True
                mensaje1 = ''
                mensaje2 = ''
                mensaje3 = ''
                mensajesmaterias = ''
                data['title'] = u'Tema Titulación'
                data['idalu'] = inscripcion.id
                data['tematitulacionposgradomatricula'] = tematitulacionposgradomatricula = TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=matricula)
                tiene_notas_complexivo = False
                historial_firma = None
                if tematitulacionposgradomatricula:
                    if tematitulacionposgradomatricula[0].tiene_calificacion_ensayo_complexivoposgrado() or tematitulacionposgradomatricula[0].tiene_calificacion_examen_complexivoposgrado():
                        tiene_notas_complexivo = True
                    else:
                        tiene_notas_complexivo= False
                    historial_firma = tematitulacionposgradomatricula[0].obtener_historial_firma_acta_aprobacion_complexivo()
                data['tiene_notas_complexivo'] =tiene_notas_complexivo
                data['historial_acta_firma_posgrado_complexivo'] =historial_firma

                if tematitulacionposgradomatricula:
                    if tematitulacionposgradomatricula[0].cabeceratitulacionposgrado:
                        data[
                            'tematitulacionposgradomatriculaCabecera'] = tematitulacionposgradomatriculacabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(
                            status=True, pk=tematitulacionposgradomatricula[0].cabeceratitulacionposgrado.pk)
                        data['temaestudiante'] = tematitulacionposgradomatricula[0]
                    else:
                        data['tematitulacionposgradomatriculaCabecera'] = False

                if not inscripcion.inscripcionmalla_set.filter(status=True):
                    return HttpResponseRedirect("/?info=Debe tener malla asociada para poder inscribirse.")
                mensaje1 = 'No existe configuración de su periodo para ingreso de Tema de Titulación'
                if ConfiguracionTitulacionPosgrado.objects.filter(status=True, periodo=periodo, carrera=carrera).exists():
                    puede = True
                    mensaje1 = ''

                idasignaturasmalla = malla.asignaturamalla_set.values_list('id', flat=True).filter(status=True,validarequisitograduacion=True)
                cantidadmalla = idasignaturasmalla.count()
                cantidadaprobadas = inscripcion.recordacademico_set.filter(status=True, asignaturamalla_id__in=idasignaturasmalla,aprobada=True).count()
                totalmateriasparatesis = cantidadmalla - 3
                # if cantidadmalla > cantidadaprobadas:
                mostrar_aviso = False
                if totalmateriasparatesis > cantidadaprobadas:

                    puede = False
                    mensaje2 = 'Aun no tiene aprobado curso como requisito de titulación'
                    asignaturasmallas = AsignaturaMalla.objects.filter(status=True, pk__in=idasignaturasmalla)
                    for a in asignaturasmallas:
                        if inscripcion.recordacademico_set.filter(status=True, asignaturamalla=a, aprobada=True).exists():
                            mensajesmaterias = mensajesmaterias + a.asignatura.nombre + ' - APROBADA <br>'
                        else:
                            mensajesmaterias = mensajesmaterias + a.asignatura.nombre + ' - PENDIENTE <br>'
                            mostrar_aviso = True
                else:
                    asignaturasmallas = AsignaturaMalla.objects.filter(status=True, pk__in=idasignaturasmalla)
                    for a in asignaturasmallas:
                        if inscripcion.recordacademico_set.filter(status=True, asignaturamalla=a, aprobada=True).exists():
                            mensajesmaterias = mensajesmaterias + a.asignatura.nombre + ' - APROBADA <br>'
                        else:
                            mensajesmaterias = mensajesmaterias + a.asignatura.nombre + ' - PENDIENTE <br>'
                            mostrar_aviso = True

                if puede:
                    historial = TemaTitulacionPosgradoMatriculaHistorial.objects.filter(status=True, tematitulacionposgradomatricula__matricula=matricula, tematitulacionposgradomatricula__status=True)
                    if historial:
                        puede2 = False
                        estado = historial.order_by('-id')[0].estado
                        if estado == 1:
                            puede = False
                            mensaje1 = 'Su propuesta esta en revisión'
                        if estado == 2:
                            puede = False
                            mensaje1 = 'Su propuesta esta aprobada'
                        if estado == 3:
                            puede = True
                            mensaje1 = 'Su propuesta esta rechazada'
                    else:
                        cabecera = TemaTitulacionPosgradoMatricula.objects.filter(matricula = matricula, status = True)
                        if cabecera:
                            puede2 = False
                            estado=cabecera.order_by('-id')[0].estado
                            if estado == 1:
                                puede = False
                                mensaje1 = 'Su propuesta esta en revisión'
                            if estado == 2:
                                puede = False
                                mensaje1 = 'Su propuesta esta aprobada'
                            if estado == 3:
                                puede = True
                                mensaje1 = 'Su propuesta esta rechazada'
                        else:
                            puede = True
                            puede2 = True

                # debe = inscripcion.adeuda_a_la_fecha()

                # if debe:
                #     puede = False
                #     mensaje3 = 'Tiene deudas pendientes, reviselo en su modulo MIS FINANZAS'
                listarubros = persona.rubro_set.filter(cancelado=False, status=True)
                contadorrubrosdebe = 0
                for lrubro in listarubros:
                    if lrubro.vencido():
                        contadorrubrosdebe = contadorrubrosdebe + 1
                if contadorrubrosdebe > 2:
                    puede = False
                    mensaje3 = 'Tiene deudas pendientes, reviselo en su modulo MIS FINANZAS'
                data['puede'] = puede
                data['puede2'] = puede2
                data['mensaje1'] = mensaje1
                data['mensaje2'] = mensaje2
                data['mensaje2'] = mensaje3
                data['mensajesmaterias'] = mensajesmaterias
                data['mostrar_aviso'] = mostrar_aviso
                # fin propuesta-----------------------------------------------------------

                # tutorias
                matricula = inscripcion.matricula2()
                data['disponible'] = True
                data['disponible_elejirTutor'] = False

                data['estudiante'] = inscripcion.persona
                # data['archivos'] = ArchivoTitulacion.objects.filter(vigente=True, status=True).distinct()
                pexamen = 0
                ppropuesta = 0
                if ConfiguracionTitulacionPosgrado.objects.filter(periodo=matricula.nivel.periodo,carrera=inscripcion.carrera, status =True).exists():
                    data['cronograma'] = cronograma = ConfiguracionTitulacionPosgrado.objects.filter(periodo=matricula.nivel.periodo,carrera=inscripcion.carrera, status =True)[0]
                    if cronograma.fechafintutoria and cronograma.fechainiciotutoria:
                        # if datetime.now().date() <= cronograma.fechafintutoria and datetime.now().date() >= cronograma.fechainiciotutoria:
                        #     data['disponible'] = True

                        if cronograma.fechainiciotutoria:
                            if datetime.now().date() < cronograma.fechainiciotutoria:
                                data['disponible_elejirTutor'] = True
                detallecalificacion = None
                if TemaTitulacionPosgradoMatricula.objects.values('id').filter(status=True, matricula=matricula).exists():
                    data['grupo'] = grupo = TemaTitulacionPosgradoMatricula.objects.get(status=True, matricula=matricula)
                    data['detallecalificacion'] = detallecalificacion = grupo.calificaciontitulacionposgrado_set.filter(status=True).order_by('tipojuradocalificador')
                    data['tipoarchivo'] = TIPO_ARCHIVO_COMPLEXIVO_PROPUESTA

                    data['tutor'] = grupo.tutor if not grupo.tutor else ''
                    data['numerointegrantes'] = 1
                    if not TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=matricula)[0].mecanismotitulacionposgrado.id == 15:
                        if not TemaTitulacionPosgradoMatricula.objects.filter(status=True, matricula=matricula)[0].tutor:
                            data['disponible'] = False
                    estado = 0
                    # ---PAREJA PROPUESTA
                    if tematitulacionposgradomatricula:
                        if tematitulacionposgradomatricula[0].cabeceratitulacionposgrado:
                            cabecera = TemaTitulacionPosgradoMatriculaCabecera.objects.get(status=True, pk=
                            tematitulacionposgradomatricula[0].cabeceratitulacionposgrado.pk)
                            if not cabecera.tutor:
                                if not cabecera.mecanismotitulacionposgrado.id == 15:
                                    data['disponible'] = False
                            else:
                                data['disponible'] = True

                            if cabecera.mecanismotitulacionposgrado.id == 15:
                                if RevisionPropuestaComplexivoPosgrado.objects.filter(
                                        tematitulacionposgradomatriculacabecera=cabecera, status=True).order_by('-id'):
                                    estado = RevisionPropuestaComplexivoPosgrado.objects.filter(
                                        tematitulacionposgradomatriculacabecera=cabecera, status=True).order_by('-id')[0].estado
                                if estado == 1:
                                    data['disponible'] = False

                                if estado == 2:
                                    data['disponible'] = False

                            else:
                                if RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                                        tematitulacionposgradomatriculacabecera=cabecera, status=True).order_by('-id'):
                                    estado = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                                        tematitulacionposgradomatriculacabecera=cabecera, status=True).order_by('-id')[
                                        0].estado

                                if estado == 1:
                                    data['disponible'] = False

                                if estado == 2:
                                    data['disponible'] = False

                            data['propuestas'] = cabecera.revisiontutoriastematitulacionposgradoprofesor_set.filter(
                                status=True).order_by('id')

                            data['propuestas_ensayo'] = cabecera.revisionpropuestacomplexivoposgrado_set.filter(
                                status=True).order_by('id')

                            data['lista_tutorias_pareja'] = cabecera.tutoriastematitulacionposgradoprofesor_set.filter(
                                status=True).order_by('id')
                        else:
                            if tematitulacionposgradomatricula[0].mecanismotitulacionposgrado.id == 15:
                                if RevisionPropuestaComplexivoPosgrado.objects.filter(
                                        tematitulacionposgradomatricula=grupo, status=True).order_by('-id'):
                                    estado = RevisionPropuestaComplexivoPosgrado.objects.filter(
                                        tematitulacionposgradomatricula=grupo, status=True).order_by('-id')[0].estado
                                if estado == 1:
                                    data['disponible'] = False

                                if estado == 2:
                                    data['disponible'] = False
                            else:
                                if RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                                        tematitulacionposgradomatricula=grupo, status=True).order_by('-id'):
                                    estado = RevisionTutoriasTemaTitulacionPosgradoProfesor.objects.filter(
                                        tematitulacionposgradomatricula=grupo, status=True).order_by('-id')[0].estado

                                if estado == 1:
                                    data['disponible'] = False

                                if estado == 2:
                                    data['disponible'] = False

                            data['propuestas'] = grupo.revisiontutoriastematitulacionposgradoprofesor_set.filter(
                                status=True).order_by('id')

                            data['propuestas_ensayo'] = grupo.revisionpropuestacomplexivoposgrado_set.filter(
                                status=True).order_by('id')

                            data['lista_tutorias_individuales'] = grupo.tutoriastematitulacionposgradoprofesor_set.filter(status=True).order_by('id')

                else:
                    data['disponible'] = False


                data['matricula'] = matricula
                data['detallecalificacion'] = detallecalificacion
                # fin tutorias
                data['etapas'] = EtapaTemaTitulacionPosgrado.objects.filter(status=True).order_by('orden')

                return render(request, "alu_tematitulacionposgrado/view.html", data)
            except Exception as ex:
                pass