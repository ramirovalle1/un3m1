from datetime import datetime
from django.db import transaction
from django.db.models import Q
from django.forms import model_to_dict
from django.http import JsonResponse, HttpResponseRedirect
from django.shortcuts import render

from bib.models import Documento, ConsultaBiblioteca, OtraBibliotecaVirtual, ReferenciaWeb


@transaction.atomic()
def view(request):
    if request.method == 'POST':
        try:
            busqueda = request.POST['search'].strip()
            terminos = filter(len, busqueda.split(" "))
            documentos = Documento.objects.all()
            for t in terminos:
                documentos = documentos.filter(Q(codigo__icontains=t) |
                                               Q(documentocoleccion__codigo__icontains=t) |
                                               Q(nombre__icontains=t) |
                                               Q(autor__icontains=t) |
                                               Q(emision__icontains=t) |
                                               Q(palabrasclaves__icontains=t) |
                                               Q(anno__icontains=t)).distinct()
            fisicos = documentos.filter(fisico=True)[:30]
            digitales = documentos.filter(fisico=False)[:30]
            data = {}
            data["busqueda"] = ", ".join(terminos)
            data['fisicos'] = fisicos
            data['digitales'] = digitales
            nconsulta = ConsultaBiblioteca(fecha=datetime.now().date(),
                                           hora=datetime.now().time(),
                                           persona=request.session['persona'],
                                           busqueda=",".join(terminos))
            nconsulta.save()
            request.session['consulta'] = nconsulta
            resultado = render(request, "biblioteca/bibliosearch.html", data)
            return JsonResponse({"result": "ok", "pagina": resultado.content})
        except Exception as ex:
            transaction.set_rollback(True)
            return JsonResponse({"result": "bad", "mensaje": u"Busqueda incorrecta."})
    return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})


@transaction.atomic()
def consulta(request):
    if request.method == 'POST':
        if "action" in request.POST:
            action = request.POST['action']

            if action == "consulta":
                try:
                    busqueda = request.POST['busqueda']
                    busqueda = busqueda.upper()
                    documento = Documento.objects.filter(Q(palabrasclaves=busqueda) |
                                                         Q(codigo__icontains=busqueda) |
                                                         Q(nombre__icontains=busqueda) |
                                                         Q(autor__icontains=busqueda) |
                                                         Q(documentocoleccion__codigo__icontains=busqueda) |
                                                         Q(anno__icontains=busqueda))[:10]
                    lista = {}
                    for i in documento:
                        lista.update({"id" + i.id.__str__(): {"ejemplares": [x.codigo for x in i.documentocoleccion_set.all()] if i.documentocoleccion_set.exists() else "", "portada": i.portada.url if i.portada else "", "codigo": i.codigo, "nombre": i.nombre, "descripcion": i.resumen, "autor": i.autor, "editora": i.editora, "anno": i.anno, "indice": i.indice.url if i.indice else "", "ubicacion": i.ubicacionfisica if i.ubicacionfisica else "", "percha": i.percha if i.percha else "", "hilera": i.hilera if i.hilera else "", "disponible": i.disponibilidad_reserva(), "reserva": i.reservadocumento_set.filter(entregado=False, anulado=False, limitereserva__gte=datetime.now()).count()}})
                    return JsonResponse({"result": "ok", "data": lista, "cantidad": documento.count()})
                except Exception as ex:
                    pass

        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})
    else:
        return render(request, "biblioteca/consulta.html")


def otras():
    try:
        data = {}
        data['otras'] = OtraBibliotecaVirtual.objects.all()
        return render("biblioteca/otrasbibliotecas.html", data)
    except Exception as ex:
        return HttpResponseRedirect("/")


@transaction.atomic()
def gourl(request):
    try:
        persona = request.session['persona']
        action = request.GET['action']

        if action == 'ref':
            try:
                referencia = ReferenciaWeb.objects.get(pk=request.GET['id'])
                nconsulta = ConsultaBiblioteca(fecha=datetime.now().date(),
                                               hora=datetime.now().time(),
                                               persona=persona,
                                               busqueda="")
                nconsulta.save()
                nconsulta.referenciasconsultadas.add(referencia)
                nconsulta.save()
                return HttpResponseRedirect(referencia.url)
            except Exception as ex:
                transaction.set_rollback(True)

        elif action == 'otra':
            try:
                otrabiblio = OtraBibliotecaVirtual.objects.get(pk=request.GET['id'])
                nconsulta = ConsultaBiblioteca(fecha=datetime.now().date(),
                                               hora=datetime.now().time(),
                                               persona=persona,
                                               busqueda="")
                nconsulta.save()
                nconsulta.otrabibliotecaconsultadas.add(otrabiblio)
                nconsulta.save()
                return HttpResponseRedirect(otrabiblio.url)
            except Exception as ex:
                transaction.set_rollback(True)

        return HttpResponseRedirect("/")
    except Exception as ex:
        return HttpResponseRedirect("/")


@transaction.atomic()
def book(request, id):
    try:
        documento = Documento.objects.get(pk=id)
        if 'consulta' in request.session:
            nconsulta = request.session['consulta']
            nconsulta.documentosconsultados.add(documento)
            nconsulta.save()
        data = model_to_dict(documento, exclude=['digital', 'portada', 'indice', 'fecha'])
        data['tipo'] = documento.tipo.nombre
        if documento.digital:
            data['digital'] = documento.digital.url
        if documento.portada:
            data['portada'] = documento.portada.url
        data['disponibles'] = documento.disponibilidad_reserva()
        data['disponiblesreserva'] = documento.disponibilidad_reserva() > int(documento.copias_total() / 2) and documento.copias_total() > 1
        data['reservas'] = documento.reservadocumento_set.filter(entregado=False, anulado=False, limitereserva__gte=datetime.now()).count()
        data['resumen'] = documento.resumen[:150]
        data['ubicacion'] = documento.ubicacionfisica + " - " + documento.percha + " - " + documento.hilera
        return JsonResponse(data)
    except Exception as ex:
        transaction.set_rollback(True)
        return JsonResponse({"result": "bad", "mensaje": u"Solicitud Incorrecta."})