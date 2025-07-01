from django.db.models import Q
from rest_framework import generics
from api.serializers.pagination import CustomPageNumberPagination
from sagest.models import DistributivoPersona
from api.serializers.telefonia.directorio import DistributivoPersonaSerializer


class DistributivoPersonaLista(generics.ListAPIView):  # Cambiamos a ListAPIView
    serializer_class = DistributivoPersonaSerializer
    pagination_class = CustomPageNumberPagination

    def get_queryset(self):
        filtro = Q(estadopuesto_id=1) & Q(nivelocupacional__status=True) & Q(status=True)

        search = self.request.query_params.get('search', None)  # Obtener el parámetro de búsqueda de la solicitud
        if search:
            ss = search.split(' ')
            if len(ss) == 1:
                filtro = filtro & Q(Q(persona__nombres__icontains=search) |
                                    Q(persona__apellido1__icontains=search) |
                                    Q(persona__apellido2__icontains=search) |
                                    Q(persona__cedula__icontains=search) |
                                    Q(denominacionpuesto__descripcion__icontains=search) |
                                    Q(unidadorganica__nombre__icontains=search) |
                                    Q(persona__telefonoextension__icontains=search) |
                                    Q(persona__emailinst__icontains=search) |
                                    Q(persona__pasaporte__icontains=search))
            else:
                filtro = filtro & Q((Q(persona__apellido1__icontains=ss[0]) &
                                     Q(persona__apellido2__icontains=ss[1])) |
                                    Q(denominacionpuesto__descripcion__icontains=search) |
                                    Q(unidadorganica__nombre__icontains=search) |
                                    Q(persona__telefonoextension__icontains=search) |
                                    Q(persona__emailinst__icontains=search))

        queryset = DistributivoPersona.objects.filter(filtro)

        return queryset
