from rest_framework.routers import DefaultRouter
from .views import SearchSessionViewSet

router = DefaultRouter()
router.register(r'sessions', SearchSessionViewSet, basename='session')

urlpatterns = router.urls