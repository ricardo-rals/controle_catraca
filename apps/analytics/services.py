"""Serviço central de métricas analíticas (HU-027).

Contrato comum das funções deste módulo — sigam este molde nas HUs 028-031:

1. Cada função recebe um QuerySet de RegistroAcesso já filtrado pela view.
   A view é responsável por aplicar recorte de datas, permissão, etc.
2. Nenhuma função consulta o banco "do zero" nem aplica filtro de data.
3. O retorno é sempre uma estrutura serializável (int, dict, list[dict]),
   pronto para virar JSON no endpoint.
4. Sem side-effects: as funções são puras, testáveis com factory.
"""

from django.db.models import QuerySet

from apps.acessos.models import RegistroAcesso


def total_de_acessos(queryset: QuerySet[RegistroAcesso]) -> int:
    """Total de registros no queryset informado.

    Exemplo:
        >>> total_de_acessos(RegistroAcesso.objects.filter(tipo_acesso="Entrada"))
        1234
    """
    return queryset.count()
