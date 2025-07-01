# -*- coding: latin-1 -*-
from django.db import transaction
from django.shortcuts import render
from decorators import secure_module, last_access
from matricula.models import CostoOptimoMalla
from sga.commonviews import adduserdata, obtener_reporte
from sga.models import Periodo, Materia, Malla
from socioecon.models import GrupoSocioEconomico
from sga.templatetags.sga_extras import encrypt

@last_access
@transaction.atomic()
def view(request):
    data = {}
    if request.method == 'POST':
        action = request.GET['action']
    else:
        if 'action' in request.GET:
            action = request.GET['action']
            if action == 'detallecostocarrera':
                try:
                    data['title'] = u'simulador costo carrera'
                    id = int(encrypt(request.GET['id'])) if 'id' in request.GET and int(encrypt(request.GET['id'])) and int(encrypt(request.GET['id'])) != 0 else None
                    idp = int(encrypt(request.GET['idp'])) if 'idp' in request.GET and int(encrypt(request.GET['idp'])) and int(encrypt(request.GET['idp'])) != 0 else None
                    if not Malla.objects.values("id").filter(pk=id).exists():
                        raise NameError(u"No existe parametro de malla")
                    if not Periodo.objects.values("id").filter(pk=idp).exists():
                        raise NameError(u"No existe parametro de periodo")
                    eMalla = Malla.objects.get(pk=id)
                    ePeriodo = Periodo.objects.get(pk=idp)
                    if not CostoOptimoMalla.objects.values("id").filter(malla=eMalla, periodo=ePeriodo).exists():
                        raise NameError(u"No existe configuración de malla en periodo")
                    eCostoOptimoMalla = CostoOptimoMalla.objects.get(malla=eMalla, periodo=ePeriodo)
                    data['ePeriodo'] = ePeriodo
                    data['eMalla'] = eMalla
                    data['eCostoOptimoMalla'] = eCostoOptimoMalla
                    data['eGrupoSocioEconomicos'] = eGrupoSocioEconomicos = GrupoSocioEconomico.objects.filter(status=True)
                    return render(request, "simulador/detallecostocarrera.html", data)
                except Exception as ex:
                    pass
        else:
            data['title'] = u'Listado de actividades extracurriculares'
            data['ePeriodo'] = ePeriodo = Periodo.objects.get(pk=153)
            if ePeriodo.tipocalculo == 6:
                eMaterias = Materia.objects.filter(status=True, nivel__periodo=ePeriodo)
                eCostoOptimoMallas = CostoOptimoMalla.objects.filter(periodo=ePeriodo, malla__vigente=True,status=True)
                # eMallas = Malla.objects.filter(pk__in=eMaterias.values_list('asignaturamalla__malla__id', flat=True).union(eCostoOptimoMallas.values_list("malla__id", flat=True))).distinct().order_by('carrera__nombre')
                eMallas = Malla.objects.filter(pk__in=eMaterias.values_list('asignaturamalla__malla__id', flat=True)).exclude(pk=383).distinct('carrera__nombre').order_by('carrera__nombre','-inicio')
                data['eMallas'] = eMallas
            return render(request, "simulador/view.html", data)