# -*- coding: UTF-8 -*-
import sys
from datetime import datetime, timedelta

from django.db import models
from django.db.models import Q
from settings import DOCUMENTOS_COLECCION
from sga.funciones import ModeloBase


def bib_list_classes():
    listclass = []
    current_module = sys.modules[__name__]
    for key in dir(current_module):
        if isinstance(getattr(current_module, key), type):
            try:
                a = eval(key + '.objects')
                listclass.append(key)
            except:
                pass
    return listclass


class AreaConocimiento(ModeloBase):
    nombre = models.CharField(default='', max_length=300, verbose_name=u'Nombre')
    codigo = models.CharField(default='', max_length=10, verbose_name=u'Codigo')

    def __str__(self):
        return u'%s - %s' % (self.codigo, self.nombre)

    class Meta:
        verbose_name = u"Area de conocimiento"
        verbose_name_plural = u"Areas de conocimientos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return AreaConocimiento.objects.filter(Q(nombre__contains=q) | Q(codigo__contains=q))[:limit]

    def flexbox_repr(self):
        return self.nombre + " - " + self.codigo + " - " + self.id.__str__()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        self.codigo = self.codigo.upper()
        super(AreaConocimiento, self).save(*args, **kwargs)


class TipoDocumento(ModeloBase):
    nombre = models.CharField(default='', max_length=100, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Tipo documento"
        verbose_name_plural = u"Tipos documentos"
        ordering = ['nombre']
        unique_together = ('nombre',)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return TipoDocumento.objects.filter(Q(nombre__contains=q))[:limit]

    def flexbox_repr(self):
        return self.nombre + " - " + self.id.__str__()

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(TipoDocumento, self).save(*args, **kwargs)


class Idioma(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Idioma"
        verbose_name_plural = u"Idiomas"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(Idioma, self).save(*args, **kwargs)


class TipoIngreso(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Tipo de ingreso"
        verbose_name_plural = u"Tipos de ingresos"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(TipoIngreso, self).save(*args, **kwargs)


class NivelLibro(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Nivel de libro"
        verbose_name_plural = u"Niveles de libros"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(NivelLibro, self).save(*args, **kwargs)


class EstadoIntegridad(ModeloBase):
    nombre = models.CharField(default='', max_length=200, verbose_name=u'Nombre')

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Estado de integridad"
        verbose_name_plural = u"Estados de integridad"
        unique_together = ('nombre',)

    def save(self, *args, **kwargs):
        self.nombre = self.nombre.upper()
        super(EstadoIntegridad, self).save(*args, **kwargs)


class Documento(ModeloBase):
    codigo = models.CharField(default='', max_length=20, verbose_name=u"Codigo coleción")
    codigoisbnissn = models.CharField(default='', max_length=20, blank=True, null=True, verbose_name=u"codigo (ISBN/ISSN)")
    nombre = models.CharField(default='', max_length=400, verbose_name=u"Titulo")
    nombre2 = models.CharField(default='', max_length=400, verbose_name=u"2do Titulo", blank=True, null=True)
    ubicacionfisica = models.CharField(default='', max_length=40, verbose_name=u"Ubicación")
    percha = models.CharField(default='', blank=True, null=True, max_length=40, verbose_name=u"Percha")
    hilera = models.CharField(default='', blank=True, null=True, max_length=40, verbose_name=u"Hilera")
    tomo = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u'Tomo')
    volumen = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u'Volumen')
    autor = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Emision")
    autorcorporativo = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Autor coorporativo")
    lugarpublicacion = models.CharField(default='', blank=True, null=True, max_length=200, verbose_name=u"Lugar publicación")
    tipo = models.ForeignKey(TipoDocumento, verbose_name=u"Tipo documento",on_delete=models.CASCADE)
    tipoingreso = models.ForeignKey(TipoIngreso, blank=True, null=True, verbose_name=u"Tipo ingreso",on_delete=models.CASCADE)
    donadopor = models.CharField(default='', max_length=300, blank=True, null=True, verbose_name=u'Donado')
    nivel = models.ForeignKey(NivelLibro, blank=True, null=True, verbose_name=u'Nivel Libro',on_delete=models.CASCADE)
    estado = models.ForeignKey(EstadoIntegridad, blank=True, null=True, verbose_name=u'Estado integridad',on_delete=models.CASCADE)
    areaconocimiento = models.ForeignKey(AreaConocimiento, blank=True, null=True, verbose_name=u'Area de conocimiento',on_delete=models.CASCADE)
    anno = models.IntegerField(default=0, verbose_name=u"Año")
    fecha = models.DateField(verbose_name=u"Fecha ingreso")
    emision = models.CharField(default='', blank=True, null=True, max_length=40, verbose_name=u"Emision")
    edicion = models.CharField(default='', blank=True, null=True, max_length=40, verbose_name=u"Edicion")
    numerofactura = models.IntegerField(default=0, blank=True, null=True, verbose_name=u'Numero factura')
    palabrasclaves = models.TextField(default='', verbose_name=u"Palabras claves")
    digital = models.FileField(upload_to='biblioteca/%Y/%m/%d', null=True, blank=True, default='', verbose_name=u"Documento digital")
    fisico = models.BooleanField(default=True, verbose_name=u"Documento fisico")
    referencia = models.BooleanField(default=False, verbose_name=u"Documento referencia")
    copias = models.IntegerField(default=0, verbose_name=u"Copias")
    paginas = models.IntegerField(default=0, verbose_name=u"Paginas")
    portada = models.FileField(upload_to='biblioteca/portadas/%Y/%m/%d', null=True, blank=True, verbose_name=u"Portada")
    indice = models.FileField(upload_to='biblioteca/indice/%Y/%m/%d', null=True, blank=True, verbose_name=u"Indice")
    editora = models.CharField(default='', max_length=200, verbose_name=u"Editora")
    sede = models.ForeignKey('sga.Sede', verbose_name=u"Sede",on_delete=models.CASCADE)
    codigodewey = models.CharField(default='', max_length=200, null=True, blank=True, verbose_name=u"Codigo EWEY")
    idioma = models.ForeignKey(Idioma, verbose_name=u"Idioma",on_delete=models.CASCADE)
    tutor = models.CharField(default='', max_length=200, verbose_name=u"Tutor")
    resumen = models.TextField(default='', verbose_name=u"Resumen")
    codigocutter = models.CharField(default='', max_length=20, verbose_name=u"Codigo CUTTER")
    preciocosto = models.FloatField(default=0, editable=False, verbose_name=u"Precio de costo")
    descripcionfisica = models.CharField(default='', max_length=200, verbose_name=u"Descripción fisica")
    establecimientoresponsable = models.CharField(default='', max_length=200, verbose_name=u"Establecimiento responsable")
    prestamosala = models.BooleanField(default=False, verbose_name=u"Prestamo en sala")

    def __str__(self):
        return u"[%s] %s %s - %s" % (self.codigo, self.nombre, self.nombre2, self.autor)

    class Meta:
        verbose_name = u"Documento"
        verbose_name_plural = u"Documentos"
        ordering = ['nombre', 'codigo']
        unique_together = ('codigo',)

    @staticmethod
    def flexbox_query(q, extra=None, limit=25):
        return Documento.objects.filter(Q(nombre__contains=q))[:limit]

    def flexbox_repr(self):
        return self.nombre + " - " + self.codigo + " - " + self.id.__str__()

    def nombre_completo(self):
        return u"%s %s" % (self.nombre, self.nombre2)

    def copias_prestadas(self):
        return self.prestamodocumento_set.filter(recibido=False).count()

    def prestamos(self):
        return self.prestamodocumento_set.exists()

    def copias_total(self):
        if DOCUMENTOS_COLECCION:
            return self.documentocoleccion_set.filter(habilitado=True).count()
        return self.copias

    def copias_restantes(self):
        return self.copias_total() - self.copias_prestadas()

    def disponibilidad_reserva(self):
        return self.copias_restantes() - self.reservadocumento_set.filter(entregado=False, anulado=False, limitereserva__gte=datetime.now()).count()

    def documento_carrera(self):
        if self.documentocarrera_set.exists():
            documentocarrera = self.documentocarrera_set.all()[0]
        else:
            documentocarrera = DocumentoCarrera(documento=self)
            documentocarrera.save()
        return documentocarrera

    def documento_general(self):
        documentocarrera = self.documento_carrera()
        if not self.referencia and not documentocarrera.carrera.exists():
            return True
        return False

    def coleccion(self):
        return self.documentocoleccion_set.all()

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper().strip()
        self.codigodewey = self.codigodewey.upper().strip()
        self.codigocutter = self.codigocutter.strip()
        self.nombre = self.nombre.upper().strip()
        self.fisico = True if not self.digital else False
        self.nombre2 = self.nombre2.upper().strip()
        self.autor = self.autor.upper().strip()
        self.ubicacionfisica = self.ubicacionfisica.upper().strip()
        self.edicion = self.edicion.upper().strip()
        self.lugarpublicacion = self.lugarpublicacion.upper().strip()
        self.autorcorporativo = self.autorcorporativo.upper().strip()
        self.emision = self.emision.upper().strip()
        self.editora = self.editora.upper().strip()
        self.tutor = self.tutor.upper().strip()
        self.resumen = self.resumen.upper().strip()
        if not self.fisico:
            self.copias = 1
            self.prestamosala = False
        super(Documento, self).save(*args, **kwargs)


class DocumentoColeccion(ModeloBase):
    documento = models.ForeignKey(Documento, verbose_name=u"Documento",on_delete=models.CASCADE)
    codigo = models.CharField(default='', max_length=20, verbose_name=u"Codigo individual")
    habilitado = models.BooleanField(default=True, verbose_name=u"Libro habilitado")
    estado = models.ForeignKey(EstadoIntegridad, blank=True, null=True, verbose_name=u'Estado integridad',on_delete=models.CASCADE)

    def __str__(self):
        return u"%s" % self.codigo

    class Meta:
        verbose_name = u"Ejemplar"
        verbose_name_plural = u"Ejemplares"
        ordering = ['codigo']
        unique_together = ('documento', 'codigo',)

    def prestamos(self):
        return self.prestamodocumento_set.count()

    def tiene_prestamos(self):
        return self.prestamodocumento_set.exists()

    def en_prestamo(self):
        return self.prestamodocumento_set.filter(recibido=False).exists()

    def ultimo_prestamo(self):
        if self.prestamodocumento_set.exists():
            return self.prestamodocumento_set.order_by('-fechaentrega')[0].persona
        else:
            return None

    def save(self, *args, **kwargs):
        self.codigo = self.codigo.upper().strip()
        super(DocumentoColeccion, self).save(*args, **kwargs)


class ReservaDocumento(ModeloBase):
    documento = models.ForeignKey(Documento, verbose_name=u"Documento",on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona',on_delete=models.CASCADE)
    fechareserva = models.DateTimeField(verbose_name=u'Fecha Reserva')
    limitereserva = models.DateTimeField(verbose_name=u'Fecha Limite Reserva')
    fechaentrega = models.DateTimeField(blank=True, null=True, verbose_name=u'Fecha Entrega')
    entregado = models.BooleanField(default=False, verbose_name=u'Entregado')
    anulado = models.BooleanField(default=False, verbose_name=u'Anulado')

    def __str__(self):
        return u"%s" % self.documento

    class Meta:
        verbose_name = u"Ejemplar"
        verbose_name_plural = u"Ejemplares"
        ordering = ['documento']
        unique_together = ('documento', 'persona', 'fechareserva',)

    def save(self, *args, **kwargs):
        super(ReservaDocumento, self).save(*args, **kwargs)


class ReferenciaWeb(ModeloBase):
    url = models.CharField(default='', max_length=200, verbose_name=u"URL")
    nombre = models.CharField(default='', max_length=200, verbose_name=u"Nombre")
    logo = models.FileField(upload_to='referencias', verbose_name=u"Logo")

    def __str__(self):
        return self.nombre

    class Meta:
        verbose_name = u"Referencia web"
        verbose_name_plural = u"Referencias web"
        unique_together = ('id',)


class OtraBibliotecaVirtual(ModeloBase):
    url = models.CharField(default='', max_length=200, verbose_name=u"URL")
    nombre = models.CharField(default='', max_length=200, verbose_name=u"Nombre")
    logo = models.FileField(upload_to='referencias', verbose_name=u"Logo")
    descripcion = models.TextField(default='', verbose_name=u"Descripción")

    def __str__(self):
        return u'%s' % self.nombre

    class Meta:
        verbose_name = u"Otra biblioteca virtual"
        verbose_name_plural = u"Otras bibliotecas virtuales"
        unique_together = ('url',)


class DocumentoCarrera(ModeloBase):
    documento = models.ForeignKey(Documento, verbose_name=u"Documento",on_delete=models.CASCADE)
    carrera = models.ManyToManyField('sga.Carrera', verbose_name=u"Carreras")

    class Meta:
        unique_together = ('documento',)


class DocumentoAsignatura(ModeloBase):
    documento = models.ForeignKey(Documento, verbose_name=u"Documento",on_delete=models.CASCADE)
    materia = models.ManyToManyField('sga.Asignatura', verbose_name=u"Asignatura")

    class Meta:
        unique_together = ('documento',)


class PrestamoDocumento(ModeloBase):
    documento = models.ForeignKey(Documento, verbose_name=u"Documento",on_delete=models.CASCADE)
    documentocoleccion = models.ForeignKey(DocumentoColeccion, blank=True, null=True,on_delete=models.CASCADE)
    persona = models.ForeignKey('sga.Persona', verbose_name=u"Persona",on_delete=models.CASCADE)
    tiempo = models.IntegerField(default=24, verbose_name=u"Timepo")
    responsableentrega = models.ForeignKey('sga.Persona', related_name='entrega', verbose_name=u"Responsable de entrega",on_delete=models.CASCADE)
    fechaentrega = models.DateField(verbose_name=u"Fecha de entrega")
    horaentrega = models.TimeField(verbose_name=u"Hora de entrega")
    entregado = models.BooleanField(default=False, verbose_name=u"Entregado")
    responsablerecibido = models.ForeignKey('sga.Persona', related_name='recibe', null=True, blank=True, verbose_name=u"Responsable de recepción",on_delete=models.CASCADE)
    recibido = models.BooleanField(default=False, verbose_name=u"Recibido")
    fecharecibido = models.DateField(null=True, blank=True, verbose_name=u"Fecha de recepción")
    horarecibido = models.TimeField(null=True, blank=True, verbose_name=u"Hora de recepción")
    prestamosala = models.BooleanField(default=True, verbose_name=u"Prestamo en sala")

    def __str__(self):
        return u"%s - %s - tiempo: %s" % (self.documento.nombre, self.persona.nombre_completo(), self.tiempo)

    class Meta:
        verbose_name = u"Prestamo documento"
        verbose_name_plural = u"Prestamos documentos"
        unique_together = ('documento', 'documentocoleccion', 'persona', 'fechaentrega', 'horaentrega',)

    def tiempo_restante(self):
        entrega = datetime.combine(self.fechaentrega, self.horaentrega)
        deberecibir = entrega + timedelta(hours=self.tiempo)
        queda = deberecibir - datetime.now()
        if queda.days < 0:
            return 0
        return queda.seconds / 60

    def tiempo_pasado_dias(self):
        entrega = datetime.combine(self.fechaentrega, self.horaentrega)
        deberecibir = entrega + timedelta(hours=self.tiempo)
        return (datetime.now() - deberecibir).days

    def tiempo_pasado_horas(self):
        entrega = datetime.combine(self.fechaentrega, self.horaentrega)
        deberecibir = entrega + timedelta(hours=self.tiempo)
        horas = ((datetime.now() - deberecibir).seconds / 60) / 60
        return horas

    def tiempo_pasado_min(self):
        entrega = datetime.combine(self.fechaentrega, self.horaentrega)
        deberecibir = entrega + timedelta(hours=self.tiempo)
        minutos = ((datetime.now() - deberecibir).seconds / 60)
        return minutos


class ConsultaBiblioteca(ModeloBase):
    fecha = models.DateField(verbose_name=u'Fecha')
    hora = models.TimeField(verbose_name=u'Hora')
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona',on_delete=models.CASCADE)
    busqueda = models.CharField(default='', max_length=100, verbose_name=u'Busqueda')
    documentosconsultados = models.ManyToManyField(Documento, verbose_name=u'Documentos consultados')
    referenciasconsultadas = models.ManyToManyField(ReferenciaWeb, verbose_name=u'Referencia web')
    otrabibliotecaconsultadas = models.ManyToManyField(OtraBibliotecaVirtual, verbose_name=u'Otras bibliotecas')

    def __str__(self):
        return u'%s en %s' % (self.persona, self.fecha.strftime('%d-%m-%Y'))

    class Meta:
        verbose_name = u"Consulta biblioteca"
        verbose_name_plural = u"Consultas biblioteca"
        unique_together = ('persona', 'fecha', 'hora', 'busqueda',)