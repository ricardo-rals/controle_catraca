from django.db.models import Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth

def volume_por_periodo(queryset, granularidade: str) -> list[dict]: 
    trunc_map = {
        "dia": TruncDay("timestamp"), 
        "semana": TruncWeek("timestamp"),
        "mes": TruncMonth("timestamp"),
    }

    if granularidade not in trunc_map:
        raise ValueError("Granularidade inválida. Use 'dia', 'semana' ou 'mes'.")

    resultados = (
        queryset
        .annotate(periodo=trunc_map[granularidade])
        .values("periodo")
        .annotate(total=Count("id"))
        .order_by("periodo")
    )

    return [{"periodo": linha["periodo"], "total": linha["total"]} for linha in resultados]