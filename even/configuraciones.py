from .models import Evento, RegistroEvento, PeriodoEvento, DetallePeriodoEvento
from itertools import chain


def traerEventosDisponibles(request, persona, periodo):
    sinconfirmar = RegistroEvento.objects.filter(participante=persona, status=True, estado_confirmacion=0).values_list('periodo_id', flat=True)
    if sinconfirmar:
        # qsbase = PeriodoEvento.objects.filter(status=True, publicar=True, cerrado=False, periodo=periodo, id__in=sinconfirmar)
        qsbase = PeriodoEvento.objects.filter(status=True, publicar=True, cerrado=False, id__in=sinconfirmar)
    else:
        misinscripciones = RegistroEvento.objects.filter(participante=persona, status=True, estado_confirmacion__in=[1, 2]).values_list('periodo_id', flat=True)
        qsbase = PeriodoEvento.objects.filter(status=True, publicar=True, cerrado=False, periodo=periodo, permiteregistro=True).exclude(id__in=misinscripciones)
    listatodos = []
    listacanton = []
    if qsbase.filter(todos=True).exists():
        listatodos = qsbase.filter(todos=True).values_list('id', flat=True)
    if DetallePeriodoEvento.objects.filter(periodo__in=qsbase.values_list('id', flat=True), canton=persona.canton).exists():
        listacanton = DetallePeriodoEvento.objects.filter(periodo__in=qsbase.values_list('id', flat=True), canton=persona.canton).values_list('periodo_id', flat=True)
    listahabilitados = list(chain(listatodos, listacanton))
    return qsbase.filter(pk__in=listahabilitados).first()
