from cita.models import HorarioServicioCita

import datetime
def turnosdisponible(horario, fecha):
    try:
        # Convierte la fecha a una cadena en formato 'YYYY-MM-DD'
        fecha = fecha.strftime('%Y-%m-%d')
        turnos_disponibles = horario.citas_disponibles(fecha)
        if turnos_disponibles > 0:
            disponible = horario.horario_disponible(fecha)
            if disponible:
                return True
        return False
    except Exception as ex:
        return str(ex)


# def turnos_disponibles(lista,idresponsableservicio,fecha):
#     try:
#
#         horarios = HorarioServicioCita.objects.filter(id__in=lista, responsableservicio_id=idresponsableservicio,
#                                                       status=True, mostrar=True)
#         for horario in horarios:
#             turnos_disponibles = horario.citas_disponibles(fecha)
#             if turnos_disponibles > 0:
#                 disponible = horario.horario_disponible(fecha)
#                 if disponible:
#                     return True
#         return False
#     except Exception as ex:
#         return f'{ex}'
