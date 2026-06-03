# Factories de dados de teste com factory-boy.
# Serao implementadas apos a criacao dos models (HU-009 e HU-010).
# Exemplo de como ficara:
#
# import factory
# from apps.usuarios.models import UsuarioSistema
#
# class UsuarioSistemaFactory(factory.django.DjangoModelFactory):
#     class Meta:
#         model = UsuarioSistema
#     nome = factory.Faker("name", locale="pt_BR")
