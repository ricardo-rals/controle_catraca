"""Regras de visibilidade por perfil (admin vs gestor).

Centraliza o que cada perfil enxerga dos dados sensíveis, para telas de
consulta e relatórios usarem a MESMA regra:

- admin  → credencial completa, foto liberada
- gestor → credencial mascarada, sem foto
"""

from apps.importacoes.utils.pseudonimizacao import descriptografar_valor


def is_admin(user):
    return getattr(user, "perfil", None) == "admin"


def credencial_para(user, valor_cifrado):
    """Admin ve a credencial completa; gestor ve valor mascarado."""
    if not valor_cifrado:
        return "—"
    try:
        credencial = descriptografar_valor(valor_cifrado)
    except ValueError:
        return "—"
    if is_admin(user):
        return credencial
    if len(credencial) <= 4:
        return "*" * len(credencial)
    return f"{'*' * (len(credencial) - 4)}{credencial[-4:]}"


def identificador_para(user, valor_cifrado):
    """Alias de compatibilidade para chamadas antigas."""
    return credencial_para(user, valor_cifrado)


def pode_ver_foto(user):
    return is_admin(user)
