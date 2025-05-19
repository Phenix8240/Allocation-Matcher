from django.contrib import admin
from django.urls import path, include
from core import views
from django.http import HttpResponse

def home(request):
    return HttpResponse("✅ Django server is running!")

urlpatterns = [
    path('', home),  # Root route handled directly
    path('core/', include('core.urls')),
    path('admin/', admin.site.urls),
]