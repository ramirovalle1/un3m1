# -*- coding: UTF-8 -*-
from django.db import models
from sga.funciones import ModeloBase
from sga.models import Profesor, Periodo


class Perfil(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre', blank=True, null=True)
    descripcion = models.TextField(default='', verbose_name=u'Descripcion', blank=True, null=True)

    def __str__(self):
        return f"{self.nombre}"

    class Meta:
        verbose_name = u'Perfil'
        verbose_name_plural = u'Perfiles'
        ordering = ('nombre',)

    def save(self, *args, **kwargs):
        super(Perfil, self).save(*args, **kwargs)


class DetallePerfil(ModeloBase):
    perfil = models.ForeignKey(Perfil, blank=True, null=True, verbose_name=u'Perfil', on_delete=models.CASCADE)
    porcentajeacierto = models.DecimalField(verbose_name='Porcentaje acierto', null=True, blank=True, default=0, decimal_places=2, max_digits=10)
    niveldificultad = models.IntegerField(verbose_name=u'Nivel dificultad', default=0, blank=True, null=True)
    segundosinteraccion = models.IntegerField(verbose_name=u'Segundos interaccion', default=0, blank=True, null=True)
    zurdo = models.BooleanField(default=False, verbose_name=u'¿Zurdo?')
    contraste = models.BooleanField(default=False, verbose_name=u'¿Contraste?')

    def __str__(self):
        return f"{self.perfil.nombre} - {self.porcentajeacierto.__str__()}% - Dificultad: {self.niveldificultad.__str__()}"

    class Meta:
        verbose_name = u'Detalle Perfil'
        verbose_name_plural = u'Detalles Perfiles'
        ordering = ('porcentajeacierto',)

    def save(self, *args, **kwargs):
        super(DetallePerfil, self).save(*args, **kwargs)


class UsuarioPerfil(ModeloBase):
    usuario = models.ForeignKey(Profesor, blank=True, null=True, verbose_name='Usuario', on_delete=models.CASCADE)
    perfil = models.ForeignKey(Perfil, blank=True, null=True, verbose_name=u'Perfil', on_delete=models.CASCADE)
    tourguiado = models.BooleanField(default=False, verbose_name=u'¿Tour Guiado?')
    fechainicio = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha inicio')
    fechafin = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha fin')
    activo = models.BooleanField(default=False, verbose_name=u'¿Activo?')

    def __str__(self):
        return f"{self.usuario.__str__()} - {self.perfil.__str__()} ({self.fechainicio.strftime('%d-%m-%Y')} - {self.fechafin.strftime('%d-%m-%Y')})"

    class Meta:
        verbose_name = u"Usuario Perfil"
        verbose_name_plural = u"Usuarios Perfil"
        ordering = ('usuario',)

    def save(self, *args, **kwargs):
        super(UsuarioPerfil, self).save(*args, **kwargs)


# class PruebaUsuario(ModeloBase):
#     nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre', blank=True, null=True)
#     descripcion = models.TextField(default='', verbose_name=u'Descripción', blank=True, null=True)
#
#     def __str__(self):
#         return f"{self.nombre}"
#
#     class Meta:
#         verbose_name = u'Prueba Usuario'
#         verbose_name_plural = u'Pruebas Usuarios'
#         ordering = ('nombre',)
#
#     def save(self, *args, **kwargs):
#         super(PruebaUsuario, self).save(*args, **kwargs)

class Test(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre', blank=True, null=True)
    descripcion = models.TextField(default='', verbose_name=u'Descripción', blank=True, null=True)
    # profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name='Profesor', on_delete=models.CASCADE)
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')

    def __str__(self):
        return f"{self.nombre.__str__()}: {self.descripcion.__str__()}"

    def detalletest(self):
        return self.detalletest_set.filter(status=True).order_by('orden')

    def en_uso(self):
        return self.detalletest_set.values('id').filter(status=True).order_by('orden').exists()

    class Meta:
        verbose_name = u"Test"
        verbose_name_plural = u"Tests"
        ordering = ('nombre',)

    def save(self, *args, **kwargs):
        super(Test, self).save(*args, **kwargs)


class DetalleTest(ModeloBase):
    test = models.ForeignKey(Test, blank=True, null=True, verbose_name='Test', on_delete=models.CASCADE)
    descripcion = models.TextField(default='', verbose_name=u'Descripción', blank=True, null=True)
    # pregunta = models.FileField(upload_to='pregunta/%Y/%m/%d', blank=True, null=True, verbose_name=u'Pregunta')
    respuesta = models.IntegerField(blank=True, null=True, verbose_name=u'Respuesta correcta')
    valor = models.DecimalField(verbose_name='Valor', null=True, blank=True, default=0, decimal_places=2, max_digits=10)
    rgb = models.DecimalField(verbose_name='RGB', null=True, blank=True, default=0, decimal_places=3, max_digits=10)
    rotacion = models.CharField(default='', max_length=100, verbose_name=u'Rotacion', blank=True, null=True)
    orden = models.IntegerField(blank=True, null=True, verbose_name=u'Orden')

    def __str__(self):
        return f"{self.test.__str__()} - {self.valor.__str__()}"

    class Meta:
        verbose_name = u"Detalle Test"
        verbose_name_plural = u"Detalles Test"
        ordering = ('test',)

    def save(self, *args, **kwargs):
        super(DetalleTest, self).save(*args, **kwargs)


class IntentoUsuario(ModeloBase):
    usuario = models.ForeignKey(Profesor, blank=True, null=True, verbose_name='Usuario', on_delete=models.CASCADE)
    test = models.ForeignKey(Test, blank=True, null=True, verbose_name='Test', on_delete=models.CASCADE)
    numero = models.IntegerField(blank=True, null=True, verbose_name=u'Número intento')
    fecha = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha')
    finalizo = models.BooleanField(default=False, verbose_name=u'¿Finalizó?')

    def __str__(self):
        return f"{self.usuario.__str__()} - Intento {self.numero}"

    def totalrespuestausuario(self):
        return self.usuariorespuesta_set.values_list('id').filter(status=True).count()

    class Meta:
        verbose_name = u"Intento Usuario"
        verbose_name_plural = u"Intentos Usuarios"
        ordering = ('usuario', 'numero',)

    def save(self, *args, **kwargs):
        super(IntentoUsuario, self).save(*args, **kwargs)


class UsuarioRespuesta(ModeloBase):
    detalletest = models.ForeignKey(DetalleTest, blank=True, null=True, verbose_name='Detalle test', on_delete=models.CASCADE)
    intento = models.ForeignKey(IntentoUsuario, blank=True, null=True, verbose_name='Intento usuario', on_delete=models.CASCADE)
    # usuario = models.ForeignKey(Profesor, blank=True, null=True, verbose_name='Usuario', on_delete=models.CASCADE)
    correcto = models.BooleanField(default=False, verbose_name=u'¿Correcto?')
    valor = models.DecimalField(verbose_name='Valor', null=True, blank=True, default=0, decimal_places=2, max_digits=10)

    def __str__(self):
        return f"{self.detalletest.test.__str__()}: {self.valor.__str__()} - {'CORRECTA' if self.correcto else 'INCORRECTO'}"

    class Meta:
        verbose_name = u"Usuario Respuesta"
        verbose_name_plural = u"Usuarios Respuestas"
        ordering = ('detalletest',)

    def save(self, *args, **kwargs):
        super(UsuarioRespuesta, self).save(*args, **kwargs)


class ProcesoOpcionSistema(ModeloBase):
    descripcion = models.TextField(default='', verbose_name='descripcion', blank=True, null=True)

    def __str__(self):
        return f'{self.descripcion}'

    def en_uso(self):
        return True if self.laboratorioopcionsistema_set.values('id').filter(status=True) else False

    class Meta:
        verbose_name = u"Proceso de opción del Sistema "
        verbose_name_plural = u"Procesos de opción del Sistema"


class LaboratorioOpcionSistema(ModeloBase):
    modulo = models.ForeignKey('sga.Modulo', on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Modulo')
    nombre = models.TextField(default='', verbose_name='Nombre', blank=True, null=True)
    url = models.TextField(default='', verbose_name='URL', blank=True, null=True)
    descripcion = models.TextField(default='', verbose_name='Descripción', blank=True, null=True)
    imagen = models.FileField(upload_to='laboratorioopcion/%Y/%m/%d', blank=True, null=True, verbose_name=u'Archivo')
    proceso = models.ForeignKey(ProcesoOpcionSistema, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Proceso')
    pregunta = models.TextField(default='', verbose_name='Pregunta', blank=True, null=True)
    activo = models.BooleanField(default=False, verbose_name=u'¿Activo para prueba de mouse?')

    def __str__(self):
        return f'{self.nombre} - {self.modulo.__str__()}'

    class Meta:
        verbose_name = u"Laboratorio de opcion del Sistema "
        verbose_name_plural = u"Inventario de opciones del Sistema"

    def en_uso(self):
        return True if self.seguimientodocente_set.values('id').filter(status=True) else False

    def evaluado_uxplora(self, userid, identificacion):
        try:
            if self.id in ['list(idsvistos[0])']:
                return True
            return False
        except Exception as e:
            return False


ESTADO_INTENTO = ((0, 'En curso'), (1, 'Finalizado'))


class SeguimientoDocente(ModeloBase):
    profesor = models.ForeignKey(Profesor, blank=True, null=True, verbose_name='Usuario', on_delete=models.CASCADE)
    periodo = models.ForeignKey(Periodo, blank=True, null=True, verbose_name=u'Periodo', on_delete=models.CASCADE)
    fechainteraccion = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha interacción')
    numerointento = models.IntegerField(default=1, verbose_name=u'Intento numero')
    estado_intento = models.IntegerField(choices=ESTADO_INTENTO, default=0, verbose_name=u'porcentaje de calculo')
    tiempointeracciontotal = models.DecimalField(verbose_name='Tiempo interacción', null=True, blank=True, default=0, decimal_places=2, max_digits=10)


    def __str__(self):
        return f'{self.profesor.__str__()} - {self.fechainteraccion}'

    class Meta:
        verbose_name = u"Seguimiento Docente"
        verbose_name_plural = u"Seguimientos del docente"

    def detalle(self):
        return self.detalleseguimientodocente_set.filter(respondido=False).order_by('orden')

    def save(self, *args, **kwargs):
        self.numerointento = SeguimientoDocente.objects.filter(periodo=self.periodo, profesor=self.profesor).count() + 1
        super(SeguimientoDocente, self).save(*args, **kwargs)


class DetalleSeguimientoDocente(ModeloBase):
    seguimiento = models.ForeignKey(SeguimientoDocente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Laboratorio opcion Sistema')
    fechainteraccion = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha interacción')
    inventario = models.ForeignKey(LaboratorioOpcionSistema, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Laboratorio opcion Sistema')
    encontroopcion = models.BooleanField(default=False, verbose_name=u'¿Encontró la opción?')
    escaladificultad = models.IntegerField(blank=True, null=True, verbose_name=u'Escala dificultad')
    tiempointeraccion = models.DecimalField(verbose_name='Tiempo interacción', null=True, blank=True, default=0, decimal_places=2, max_digits=10)
    orden = models.IntegerField(default=1, verbose_name=u'Orden')
    respondido = models.BooleanField(default=False, verbose_name=u'Respondida')

    def __str__(self):
        return f'{self.seguimiento.__str__()} - {self.inventario.__str__()}'

    class Meta:
        verbose_name = u"Detalle seguimiento docente"
        verbose_name_plural = u"Detalles seguimientos del docente"


class ResultadoPerfilDocente(ModeloBase):
    seguimiento = models.ForeignKey(SeguimientoDocente, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Laboratorio opcion Sistema')
    testcontraste = models.ForeignKey(IntentoUsuario, on_delete=models.CASCADE, blank=True, null=True, verbose_name=u'Test de contraste')
    perfilasignado = models.IntegerField(default=0, verbose_name=u'Perfil asignado por prueba')
    perfilseleccionado = models.IntegerField(default=0, verbose_name=u'Perfil seleccionado por el usuario')

    def __str__(self):
        return f'{self.seguimiento} - {self.testcontraste} - {self.perfilasignado} - {self.perfilseleccionado}'

    class Meta:
        verbose_name = u"Resultado perfil docente"
        verbose_name_plural = u"Resultados perfiles docentes"