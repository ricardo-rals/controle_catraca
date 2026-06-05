# Create your models here.
from django.db import models

class PontoAcesso(models.Model):
    nome = models.CharField('Nome do Ponto', max_length=100)
    localizacao = models.CharField('Localização', max_length=150)

    class Meta:
        verbose_name = 'Ponto de Acesso'
        verbose_name_plural = 'Pontos de Acesso'

    def __str__(self):
        return f"{self.nome} - {self.localizacao}"

class RegistroAcesso(models.Model):
    TIPO_ACESSO_CHOICES = (
        ('entrada', 'Entrada'),
        ('saida', 'Saída'),
    )
    identificador_pseudonimizado = models.CharField('Identificador Pseudonimizado', max_length=255)
    ponto_acesso = models.ForeignKey(
        PontoAcesso, 
        on_delete=models.CASCADE, 
        verbose_name='Ponto de Acesso', 
        related_name='registros'
    )
    tipo_acesso = models.CharField('Tipo de Acesso', max_length=20, choices=TIPO_ACESSO_CHOICES)
    timestamp = models.DateTimeField('Data e Hora do Acesso')
    
    # Referência como string ('importacoes.Importacao') evita erro de importação circular
    importacao = models.ForeignKey(
        'importacoes.Importacao', 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        verbose_name='Importação Vinculada', 
        related_name='registros_importados'
    )

    class Meta:
        verbose_name = 'Registro de Acesso'
        verbose_name_plural = 'Registros de Acesso'

    def __str__(self):
        return f"{self.identificador_pseudonimizado} | {self.get_tipo_acesso_display()} | {self.timestamp.strftime('%d/%m/%Y %H:%M')}"