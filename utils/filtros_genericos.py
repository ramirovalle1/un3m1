import json

from django.db.models import Q

from sga.models import Persona


# DEVUELVE FILTRO DE PERSONA
def filtro_persona_principal(search, filtro):
    q = search.upper().strip()
    s = q.split(" ")
    if len(s) == 1:
        filtro = filtro & ((Q(nombres__icontains=q) |
                            Q(apellido1__icontains=q) |
                            Q(cedula__icontains=q) |
                            Q(cedula__icontains=q) |
                            Q(apellido2__icontains=q) |
                            Q(cedula__contains=q)))
    elif len(s) == 2:
        filtro = filtro & ((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                           (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                           (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1])))
    else:
        filtro = filtro & (
                (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(apellido1__contains=s[2])))

    return filtro


# DEVUELVE FILTRO DE PERSONA DE OBJETOS QUE TENGAN COMO HERENCIA Y NOMBRE DE ATRIBUTO persona
def filtro_persona(search, filtro):
    q = search.upper().strip()
    s = q.split(" ")
    if len(s) == 1:
        filtro = filtro & ((Q(persona__nombres__icontains=q) |
                            Q(persona__apellido1__icontains=q) |
                            Q(persona__cedula__icontains=q) |
                            Q(persona__cedula__icontains=q) |
                            Q(persona__apellido2__icontains=q) |
                            Q(persona__cedula__contains=q)))
    elif len(s) == 2:
        filtro = filtro & ((Q(persona__apellido1__contains=s[0]) & Q(persona__apellido2__contains=s[1])) |
                           (Q(persona__nombres__icontains=s[0]) & Q(persona__nombres__icontains=s[1])) |
                           (Q(persona__nombres__icontains=s[0]) & Q(persona__apellido1__contains=s[1])))
    else:
        filtro = filtro & (
                (Q(persona__nombres__contains=s[0]) & Q(persona__apellido1__contains=s[1]) & Q(persona__apellido2__contains=s[2])) |
                (Q(persona__nombres__contains=s[0]) & Q(persona__nombres__contains=s[1]) & Q(persona__apellido1__contains=s[2])))

    return filtro

def filtro_responsable(search, filtro):
    q = search.upper().strip()
    s = q.split(" ")
    if len(s) == 1:
        filtro = filtro & ((Q(responsable__nombres__icontains=q) |
                            Q(responsable__apellido1__icontains=q) |
                            Q(responsable__cedula__icontains=q) |
                            Q(responsable__cedula__icontains=q) |
                            Q(responsable__apellido2__icontains=q) |
                            Q(responsable__cedula__contains=q)))
    elif len(s) == 2:
        filtro = filtro & ((Q(responsable__apellido1__contains=s[0]) & Q(responsable__apellido2__contains=s[1])) |
                           (Q(responsable__nombres__icontains=s[0]) & Q(responsable__nombres__icontains=s[1])) |
                           (Q(responsable__nombres__icontains=s[0]) & Q(responsable__apellido1__contains=s[1])))
    else:
        filtro = filtro & (
                (Q(responsable__nombres__contains=s[0]) & Q(responsable__apellido1__contains=s[1]) & Q(responsable__apellido2__contains=s[2])) |
                (Q(responsable__nombres__contains=s[0]) & Q(responsable__nombres__contains=s[1]) & Q(responsable__apellido1__contains=s[2])))

    return filtro

# PARA BUSCAR PERSONA EN ELEMENTO SELECT2 SEGUN EL TIPO DE BUSQUEDA QUE ENVIEN DESDE EL TEMPLATE
def filtro_persona_select(request, idsexcluidas=[]):
    try:
        idsagregados = request.GET.get('idsagregados', '')
        tipos = request.GET.get('tipo', '').split(', ')
        if idsagregados:
            idsagregados = idsagregados.split(',')
            idsexcluidas += [idl for idl in idsagregados]
        q = request.GET['q'].upper().strip()
        s = q.split(" ")
        filtro = Q(status=True)
        for idx, tipo in enumerate(tipos, start=1):
            if idx == 1:
                if tipo == "administrativos":
                    filtro = filtro & Q(administrativo__isnull=False)
                elif tipo == "distributivos":
                    filtro = filtro & Q(distributivopersona__isnull=False)
                elif tipo == "estudiantes":
                    filtro = filtro & Q(inscripcion__isnull=False)
                elif tipo == "docentes":
                    filtro = filtro & Q(profesor__isnull=False)
            else:
                if tipo == "administrativos":
                    filtro = filtro | Q(administrativo__isnull=False)
                elif tipo == "distributivos":
                    filtro = filtro | Q(distributivopersona__isnull=False)
                elif tipo == "estudiantes":
                    filtro = filtro | Q(inscripcion__isnull=False)
                elif tipo == "docentes":
                    filtro = filtro | Q(profesor__isnull=False)
        qspersona = Persona.objects.filter(filtro).exclude(id__in=idsexcluidas).order_by('apellido1')
        if len(s) == 1:
            qspersona = qspersona.filter((Q(nombres__icontains=q) | Q(apellido1__icontains=q) | Q(
                cedula__icontains=q) | Q(apellido2__icontains=q) | Q(cedula__contains=q)),
                                         Q(status=True)).distinct()[:15]
        elif len(s) == 2:
            qspersona = qspersona.filter((Q(apellido1__contains=s[0]) & Q(apellido2__contains=s[1])) |
                                         (Q(nombres__icontains=s[0]) & Q(nombres__icontains=s[1])) |
                                         (Q(nombres__icontains=s[0]) & Q(apellido1__contains=s[1]))).filter(
                status=True).distinct()[:15]
        else:
            qspersona = qspersona.filter(
                (Q(nombres__contains=s[0]) & Q(apellido1__contains=s[1]) & Q(apellido2__contains=s[2])) |
                (Q(nombres__contains=s[0]) & Q(nombres__contains=s[1]) & Q(
                    apellido1__contains=s[2]))).filter(status=True).distinct()[:15]

        resp = [{'id': qs.pk, 'text': f"{qs.nombre_completo_inverso()}",
                 'documento': qs.documento(),
                 'departamento': qs.departamentopersona() if not qs.departamentopersona() == 'Ninguno' else '',
                 'foto': qs.get_foto()} for qs in qspersona]
        return resp
    except Exception as ex:
        pass

# PARA BUSCAR PERSONA EN ELEMENTO SELECT2 SEGUN EL TIPO DE BUSQUEDA QUE ENVIEN DESDE EL TEMPLATE
# otrosfiltros: se envian los filtros que se desean agregar a la consulta desde el .py
# ejemplo: otrosfiltros = 'Q(id__in=[1,2,3], inscripcion__status=True)'

def filtro_persona_select_v2(request, idsexcluidas=[], otrosfiltros=''):
    try:
        idsagregados = request.GET.get('idsagregados', '')
        tipos = request.GET.get('tipo', '').split(', ')
        if idsagregados:
            idsagregados = idsagregados.split(',')
            idsexcluidas += [idl for idl in idsagregados]
        q = request.GET['q'].upper().strip()
        filtro = Q(status=True)
        if q:
            ss = q.split(" ")
            q_objects = [
                Q(nombres__icontains=term) | Q(apellido1__icontains=term) | Q(cedula__icontains=term) |
                Q(apellido2__icontains=term) for term in ss if term]
            filtro = filtro & Q(*q_objects)

        for idx, tipo in enumerate(tipos, start=1):
            if idx == 1:
                if tipo == "administrativos":
                    filtro = filtro & Q(administrativo__isnull=False)
                elif tipo == "distributivos":
                    filtro = filtro & Q(distributivopersona__isnull=False)
                elif tipo == "estudiantes":
                    filtro = filtro & Q(inscripcion__isnull=False)
                elif tipo == "docentes":
                    filtro = filtro & Q(profesor__isnull=False)
            else:
                if tipo == "administrativos":
                    filtro = filtro | Q(administrativo__isnull=False)
                elif tipo == "distributivos":
                    filtro = filtro | Q(distributivopersona__isnull=False)
                elif tipo == "estudiantes":
                    filtro = filtro | Q(inscripcion__isnull=False)
                elif tipo == "docentes":
                    filtro = filtro | Q(profesor__isnull=False)

        if otrosfiltros:
            filtro = filtro & Q(otrosfiltros)

        qspersona = Persona.objects.filter(filtro).exclude(id__in=idsexcluidas).distinct().order_by('apellido1')[:15]
        resp = [{'id': qs.pk, 'text': f"{qs.nombre_completo_inverso()}",
                 'documento': qs.documento(),
                 'departamento': qs.departamentopersona() if not qs.departamentopersona() == 'Ninguno' else '',
                 'foto': qs.get_foto()} for qs in qspersona]
        return resp
    except Exception as ex:
        pass


# PERMITE BUSCAR LA EXISTENCIA DE LA PERSONA EN LA PLATAFORMA POR MEDIO DE LA CEDULA O PASAPORTE
def consultarPersona(identificacion):
    cedula = identificacion.upper().strip()
    return Persona.objects.filter(Q(pasaporte=cedula) | Q(cedula=cedula) | Q(pasaporte=('VS' + cedula)) | Q(cedula=cedula[2:]), status=True).first()