# -*- coding: latin-1 -*-
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import render
from decorators import secure_module, last_access
from settings import MATRICULACION_LIBRE, TIPO_PERIODO_REGULAR
from sga.commonviews import adduserdata, prematricularmodulo
from sga.models import Periodo


@login_required(redirect_field_name='ret', login_url='/loginsga')
@secure_module
@last_access
@transaction.atomic()
def view(request):
    data = {}
    adduserdata(request, data)
    persona = request.session['persona']
    perfilprincipal = request.session['perfilprincipal']
    if not perfilprincipal.es_estudiante():
        return HttpResponseRedirect("/?info=Solo los perfiles de estudiantes pueden ingresar al modulo.")
    inscripcion = perfilprincipal.inscripcion
    if request.method == 'POST':
        if 'action' in request.POST:
            action = request.POST['action']

            if action == 'prematricularmodulo':
                return prematricularmodulo(request, 1)

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        data['title'] = u'Prematriculación Modulo Ingles online'
        if not inscripcion.tiene_malla():
            return HttpResponseRedirect("/?info=No tiene malla asignada.")
        hoy = datetime.now().date()
        periodo = request.session['periodo']
        periodoid = periodo.id
        if not Periodo.objects.filter(id=periodoid, tipo__id=TIPO_PERIODO_REGULAR).exists():
            return HttpResponseRedirect("/?info=No existen periodos futuros para prematricularse en modulos.")
        data['periodoprematricula'] = periodo = Periodo.objects.filter(id=periodoid, tipo__id=TIPO_PERIODO_REGULAR)[0]
        # PERIODO ACTIVO PARA MATRICULACION
        if not periodo.prematriculacionactiva:
            return HttpResponseRedirect("/?info=El periodo no se encuentra activo para poder prematricularse en modulos.")
        if not inscripcion.puede_prematricularse_modulo_seguncronograma(periodo):
            return HttpResponseRedirect("/?info=Aun no esta activo el cronograma de prematriculacion de modulos para su carrera.")
        if inscripcion.verifica_modulo_ingles(periodo):
            return HttpResponseRedirect("/?info=Ya se encuenta matriculado en los modulos de Ingles en este Periodo Lectivo.")
        if inscripcion.prematriculamodulo_set.filter(periodo=periodo, tipo=1).exists():
            return HttpResponseRedirect("/?info=Ya se encuenta prematriculado en los modulos de Ingles.")
        if inscripcion.graduado() or inscripcion.egresado() or inscripcion.estainactivo():
            return HttpResponseRedirect("/?info=Solo podran matricularse estudiantes activos.")

        data['inscripcion'] = inscripcion
        inscripcionmalla = inscripcion.malla_inscripcion()
        if not inscripcionmalla:
            return HttpResponseRedirect("/?info=Debe tener malla asociada para poder prematricularse en los modulos.")
        # data['materiasmalla'] = inscripcionmalla.malla.asignaturamalla_set.all().exclude(nivelmalla__id=NIVEL_MALLA_CERO).order_by('nivelmalla', 'ejeformativo')
        data['matriculacion_libre'] = MATRICULACION_LIBRE
        data['materiasmaximas'] = inscripcionmalla.malla.modulomalla_set.values('id').all().count()
        data['malla'] = inscripcionmalla.malla
        # data['total_materias_nivel'] = inscripcion.total_materias_nivel()
        # data['total_materias_pendientes_malla'] = inscripcion.total_materias_pendientes_malla()
        data['materiasmodulos'] = inscripcionmalla.malla.modulomalla_set.all()
        return render(request, "alu_prematriculamodulo/view.html", data)