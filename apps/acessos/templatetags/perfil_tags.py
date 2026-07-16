"""Tags de visibilidade por perfil, para as telas de consulta (HU-perfis).

Delegam para apps.usuarios.perfis — a mesma regra usada nos relatórios.
"""

from django import template

from apps.usuarios import perfis

register = template.Library()


@register.simple_tag
def identificador_curto(valor, user):
    """Alias legado: usa a mascara de credencial por perfil."""
    return perfis.credencial_para(user, valor)


@register.simple_tag
def credencial_visivel(valor, user):
    return perfis.credencial_para(user, valor)


@register.simple_tag
def pode_ver_foto(user):
    return perfis.pode_ver_foto(user)
