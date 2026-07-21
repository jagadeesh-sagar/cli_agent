---
name: drf-api-design
description: DRF conventions for models, serializers, viewsets, permissions. Use when building or reviewing a Django REST Framework backend.
---

# DRF API Design

## Structure
- One app per domain concept (products/, orders/, users/)
- ModelSerializer when schema maps 1:1 to a model, plain Serializer otherwise
- ViewSets + routers for CRUD, APIView for one-off endpoints

## Auth
- djangorestframework-simplejwt for JWT
- Custom permission classes over inline checks in views
...