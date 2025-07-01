from django.db import models
from django.utils.text import capfirst

from sga.funciones import ModeloBase
from sga.models import Empleador, Persona

ESTADO = (
    (0, 'ACTIVO'),
    (1, 'INACTIVO'),
)

TIPO_CONTACTO = (
        (1, u'MOVIL'),
        (2, u'CONVENCIONAL'),
        (3, u'EMAIL'),
)


class CargoEmpresa(ModeloBase):
    descripcion = models.CharField(default='', max_length=200, verbose_name=u"Cargo")

    def __str__(self):
        return u'%s' % self.descripcion

    class Meta:
        verbose_name = u"Cargo Empresa"
        verbose_name_plural = u"Cargos Empresa"
        unique_together = ('descripcion',)


class RepresentantesEmpresa(ModeloBase):
    empresa = models.ForeignKey(Empleador, verbose_name=u"Empresa", on_delete=models.CASCADE, null=True, blank=True)
    persona = models.ForeignKey(Persona, verbose_name=u"Empleador", on_delete=models.CASCADE, null=True, blank=True)
    cargo = models.ForeignKey(CargoEmpresa, verbose_name=u"Cargo", on_delete=models.CASCADE, null=True, blank=True)
    estado = models.IntegerField(choices=ESTADO, verbose_name=u"Estado", default=0)

    def __str__(self):
        nombre = self.persona.nombre_completo_minus() if self.persona else 'Sin nombre'
        return '{} - {} - {}'.format(capfirst(self.empresa.nombrecorto.lower()), nombre, self.cargo.descripcion.lower())

    class Meta:
        verbose_name = u"Representante"
        verbose_name_plural = u"Representante"

    def save(self, *args, **kwargs):
        super(RepresentantesEmpresa, self).save(*args, **kwargs)


class DetalleContactosEmpresa(ModeloBase):
    empleador = models.ForeignKey(Empleador, verbose_name=u"Empleador", blank=True, null=True, on_delete=models.CASCADE)
    tipo = models.IntegerField(default=1, choices=TIPO_CONTACTO, verbose_name=u'Estado detalle')
    telefono = models.CharField(default='', max_length=50, verbose_name=u"Telefono movil")
    telefono_conv = models.CharField(default='', max_length=50, verbose_name=u"Telefono fijo")
    email = models.CharField(default='', max_length=200, verbose_name=u"Correo electronico")
    extension = models.CharField(default='', max_length=10, verbose_name=u"Extension telefonica")

    def __str__(self):

        return u'%s' % self.empleador

    class Meta:
        verbose_name = u"Detalle de contactos de la empresa"
        verbose_name_plural = u"Detalles de contactos de la empresa"
