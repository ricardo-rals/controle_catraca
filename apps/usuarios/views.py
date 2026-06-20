from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def dashboard(request):
    return render(request, "dashboard.html")


@login_required
def upload_arquivo(request):
    pass  # ... código existente da view ...
