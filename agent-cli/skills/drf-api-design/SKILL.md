---
name: drf-api-design
description: DRF conventions for models, serializers, viewsets, permissions. Use when building or reviewing a Django REST Framework backend.
---

# DRF API Design

## Project Scaffold (always run these, never write manually)
```bash
django-admin startproject config .
python manage.py startapp <app_name>
```
- `config` as the project package name (not the project name repeated)
- One app per domain concept: `products/`, `orders/`, `users/`
- Register every new app in `INSTALLED_APPS`

---

## settings.py Best Practices
- Move `SECRET_KEY` to env: `os.environ.get('SECRET_KEY')`
- `DEBUG = os.environ.get('DEBUG', 'True') == 'True'`
- Always add to `INSTALLED_APPS`:
```python
  'rest_framework',
  'rest_framework_simplejwt',
  'corsheaders',
  '<app_name>',
```
- Add `corsheaders.middleware.CorsMiddleware` as the **first** middleware
- DRF config block:
```python
  REST_FRAMEWORK = {
      'DEFAULT_AUTHENTICATION_CLASSES': (
          'rest_framework_simplejwt.authentication.JWTAuthentication',
      ),
      'DEFAULT_PERMISSION_CLASSES': (
          'rest_framework.permissions.IsAuthenticated',
      ),
      'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
      'PAGE_SIZE': 20,
  }
```
- JWT config:
```python
  from datetime import timedelta
  SIMPLE_JWT = {
      'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
      'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
  }
```

---

## config/urls.py Best Practices
```python
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/<resource>/', include('<app>.urls')),
]
```

---

## App Structure Best Practices

**serializers.py** — `ModelSerializer` for 1:1 model mapping, plain `Serializer` otherwise. Always declare `read_only_fields = ('id', 'created_at', 'updated_at')`.

**views.py** — `ModelViewSet` for CRUD, `APIView` only for one-off endpoints. Never put permission logic inline — use permission classes.

**urls.py (app-level)** — Always use `DefaultRouter`:
```python
router = DefaultRouter()
router.register(r'<resource>', <Model>ViewSet, basename='<model>')
urlpatterns = [path('', include(router.urls))]
```

**permissions.py** — Custom permission classes here, never inside views:
```python
class IsOwner(BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.owner == request.user
```

---

## Naming Conventions
| Layer | Convention |
|---|---|
| Model | `PascalCase` singular (`Order`) |
| Serializer | `OrderSerializer` |
| ViewSet | `OrderViewSet` |
| URL prefix | `kebab-case` plural (`/api/orders/`) |

---

## requirements.txt
```
django>=4.2,<5.0
djangorestframework>=3.15
djangorestframework-simplejwt>=5.3
django-cors-headers>=4.3
```