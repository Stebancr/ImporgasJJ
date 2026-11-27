from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils.decorators import method_decorator
from django.views.decorators.debug import sensitive_post_parameters
from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.views import APIView

from .contacts import normalize_phone
from .models import ClienteVisita
from .permissions import IsAdminUser
from .serializers import ClienteVisitaSerializer, FichaClienteUpdateSerializer


@method_decorator(sensitive_post_parameters(), name='dispatch')
class ContactView(APIView):
    permission_classes = [IsAdminUser]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response['Cache-Control'] = 'private, no-store'
        return response


class ContactSearchSerializer(serializers.Serializer):
    term = serializers.CharField(min_length=2, max_length=100)


class ContactSearchView(ContactView):
    def post(self, request):
        serializer = ContactSearchSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        term = serializer.validated_data['term']
        query = Q(nombre__icontains=term) | Q(correo_clave__icontains=term)
        phone = normalize_phone(term)
        if phone.isascii() and phone.isdecimal():
            query |= Q(telefono_clave__contains=phone)
        matches = ClienteVisita.fichas().filter(query).order_by('nombre', 'pk')[:20]
        return Response(ClienteVisitaSerializer(matches, many=True).data)


class ContactDetailView(ContactView):
    def get(self, request, pk):
        profile = get_object_or_404(ClienteVisita.fichas(), pk=pk)
        return Response(ClienteVisitaSerializer(profile).data)

    @transaction.atomic
    def patch(self, request, pk):
        profile = get_object_or_404(ClienteVisita.fichas().select_for_update(), pk=pk)
        serializer = FichaClienteUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        return Response(ClienteVisitaSerializer(serializer.save()).data)


class ContactHistoryView(ContactView):
    def get(self, request, pk):
        profile = get_object_or_404(ClienteVisita.fichas(), pk=pk)
        visits = profile.historial_visitas.order_by('-fecha', '-hora', '-pk').values(
            'id', 'numero_tarea', 'fecha', 'estado',
        )
        pagination = PageNumberPagination()
        pagination.page_size = 20
        return pagination.get_paginated_response(list(pagination.paginate_queryset(visits, request)))
