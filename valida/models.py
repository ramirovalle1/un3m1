import json
from datetime import time, datetime
from hashlib import sha256

from django.db import models
from django.contrib.auth.models import ContentType
from django.forms import model_to_dict

from clrncelery.models import TYPE_APP_LABEL
from sga.funciones import ModeloBase

difficulty = 2

class ValidarCertificacion(ModeloBase):
    #archivo = models.FileField(upload_to='certificados/%Y/%m/%d', blank=True, null=True, verbose_name=u'certificado generado')
    app_label = models.IntegerField(choices=TYPE_APP_LABEL, null=True, blank=True, verbose_name=u'Tipo de Aplicación')
    content_type = models.ForeignKey(ContentType, on_delete=models.SET_NULL, verbose_name=u'Tipo de Contenido', blank=True, null=True)
    object_id = models.PositiveIntegerField(blank=True, null=True, verbose_name=u'object id')
    url = models.URLField(verbose_name=u"URL certificado", blank=True, null=True, max_length=500)
    verificador = models.TextField(default='', verbose_name='Código generado ')
    persona = models.ForeignKey('sga.Persona', verbose_name=u'Persona', blank=True, null=True, on_delete=models.PROTECT)
    encadenado = models.BooleanField(default=False, verbose_name='Estado de cadena blockchain')


# class Block(models.Model):
#     transaccion = models.OneToOneField(ValidarCertificacion, on_delete=models.PROTECT, verbose_name=u'Identificador de certficado', blank=True, null=True)
#     timestamp = models.DateTimeField(verbose_name=u'fecha de creacion del bloque')
#     previous_hash = models.TextField(verbose_name='Hash de bloque anterior', null=False, blank=False, default='', unique=True)
#     nonce = models.IntegerField(verbose_name='Comprobador', default=0)
#     hashfile = models.TextField(verbose_name='Hash del archivo', null=False, blank=False, default='', unique=True)
#     hashblokchain = models.TextField(verbose_name='Hash de la cadena de bloques', null=False, blank=False, default='', unique=True)
#     ordernumber = models.PositiveIntegerField(verbose_name=u'orden en la cadena', default=0, unique=True)
#
#     class Meta:
#         verbose_name = u"Block"
#         verbose_name_plural = u"Blockes"
#
#     def __str__(self):
#         return '{} {}'.format(self.transaccion.pk, self.previous_hash)
#
#     def dict(self):
#         item = model_to_dict(self)
#         item['timestamp'] = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
#         return item
#
#     def get_blockchain(self):
#         return self.blockchain_set.first()
#
#     def hash_file(self):
#         fileurl = str(self.transaccion.url[1:]) if str(self.transaccion.url[0]) == '/' else str(self.transaccion.url)
#         with open(fileurl, "rb") as f:
#             bytes = f.read()  # read entire file as bytes
#             readable_hash = sha256(bytes).hexdigest()
#             return readable_hash
#
#     def compute_hash(self):
#         """
#         A function that return the hash of the block contents.
#         """
#         block_string = json.dumps(self.dict(), sort_keys=True)
#         return sha256(block_string.encode()).hexdigest()
#
#
# class Blockchain(models.Model):
#     name = models.CharField(default='', verbose_name='Nombre de cadena', max_length=100)
#     chain = models.ManyToManyField(Block, verbose_name=u'bloques de cadena')
#     length = models.PositiveIntegerField(blank=True, null=True, verbose_name=u'largo de la cadena')
#
#     def compute_hash(self):
#         length = self.length
#         block_string = json.dumps({'id': self.id, 'name': self.name, 'length': length}, sort_keys=True)
#         return sha256(block_string.encode()).hexdigest()
#
#     def compute_hash_to_save(self):
#         length = self.length + 1
#         block_string = json.dumps({'id': self.id, 'name': self.name, 'length': length}, sort_keys=True)
#         return sha256(block_string.encode()).hexdigest()
#
#     def unconfirmed_transactions(self):
#         return ValidarCertificacion.objects.filter(encadenado=False).values_list('id', flat=True)
#
#     # def difficulty(self):
#     #     # difficulty of our PoW algorithm
#     #     return 2
#
#
#     @property
#     def last_block(self):
#         # return self.chain[-1]
#         return self.chain.all().order_by('-id')[:1][0]
#
#     def add_block(self, block, proof):
#         """
#         A function that adds the block to the chain after verification.
#         Verification includes:
#         * Checking if the proof is valid.
#         * The previous_hash referred in the block and the hash of latest block
#           in the chain match.
#         """
#
#         if not self.check_chain_validity():
#             return False
#
#         previous_hash = self.last_block.compute_hash()
#
#         if previous_hash != block.previous_hash:
#             return False
#
#         if not Blockchain.is_valid_proof(block, proof):
#             return False
#
#         # block.hash = proof
#         self.chain.add(block)
#         certificado = block.transaccion
#         certificado.encadenado = True
#         certificado.save()
#         self.length += 1
#         self.save()
#         return True
#
#     @staticmethod
#     def proof_of_work(self, block):
#         """
#         Function that tries different values of nonce to get a hash
#         that satisfies our difficulty criteria.
#         """
#         block.nonce = 0
#         block.hashfile = block.hash_file()
#         block.hashblokchain = self.compute_hash_to_save()
#         computed_hash = block.compute_hash()
#
#         while not computed_hash.startswith('0' * difficulty):
#             block.nonce += 1
#             computed_hash = block.compute_hash()
#         block.save()
#         return computed_hash
#
#     # def add_new_transaction(self, transaction):
#     #     self.unconfirmed_transactions.append(transaction)
#
#     @classmethod
#     def is_valid_proof(self, block, block_hash):
#         """
#         Check if block_hash is valid hash of block and satisfies
#         the difficulty criteria.
#         """
#         return block_hash.startswith('0' * difficulty) and block_hash == block.compute_hash()
#
#     def check_chain_validity(self):
#         return self.compute_hash() == self.last_block.hashblokchain and self.length == len(self.chain.values_list('id'))
#
#     def mine(self):
#         """
#         This function serves as an interface to add the pending
#         transactions to the blockchain by adding them to the block
#         and figuring out Proof Of Work.
#         """
#         if not self.unconfirmed_transactions():
#             return False
#
#         last_block = self.last_block
#
#         for unconfirmed in self.unconfirmed_transactions():
#             new_block = Block(transaccion_id=unconfirmed,
#                               timestamp=datetime.now(),
#                               previous_hash=last_block.compute_hash(),
#                               ordernumber=self.length + 1,
#                               hashfile=self.length + 1,
#                               hashblokchain=self.length + 1)
#             new_block.save()
#
#             proof = self.proof_of_work(self, new_block)
#             self.add_block(new_block, proof)
#
#             # self.unconfirmed_transactions = []
#
#         return True
#
#
# def create_genesis_block():
#     """
#     A function to generate genesis block and appends it to
#     the chain. The block has index 0, previous_hash as 0, and
#     a valid hash.
#     """
#     genesis_block = Block(transaccion_id=None, timestamp=datetime.now(), previous_hash='', nonce=0)
#     genesis_block.save()
#     Blockchain.chain.add(genesis_block)



