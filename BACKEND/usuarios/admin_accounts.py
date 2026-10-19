"""Administrative account mutations share validation, locks and session revocation."""
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from ecommerce.models import Location
from .account_views import NewPasswordSerializer
from .models import Usuario, Credenciales, Cargo, Niveles, Regional
from .permissions import IsAdminUser
from .serializers import UsuarioListadoSerializer


class AccountInput(serializers.Serializer):
    usuario = serializers.CharField(max_length=254, required=False)
    cedula = serializers.CharField(max_length=30, required=False)
    nombre_completo = serializers.CharField(max_length=100, required=False)
    correo = serializers.EmailField(max_length=254, allow_blank=True, allow_null=True, required=False)
    telefono = serializers.CharField(max_length=20, allow_blank=True, allow_null=True, required=False)
    sede = serializers.CharField(max_length=100, allow_blank=True, allow_null=True, required=False)
    cargo = serializers.PrimaryKeyRelatedField(queryset=Cargo.objects.all(), allow_null=True, required=False)
    nivel = serializers.PrimaryKeyRelatedField(queryset=Niveles.objects.all(), allow_null=True, required=False)
    regional = serializers.PrimaryKeyRelatedField(queryset=Regional.objects.all(), allow_null=True, required=False)
    location_id = serializers.PrimaryKeyRelatedField(queryset=Location.objects.all(), allow_null=True, required=False)
    tipo_usuario = serializers.ChoiceField(choices=range(5), required=False)
    estado = serializers.ChoiceField(choices=(0, 1), required=False)

    def validate(self, attrs):
        profile = self.context.get('profile')
        credentials = getattr(profile, 'credenciales', None)
        fields = {'cedula': Usuario.objects.all(), 'correo': Usuario.objects.all(), 'usuario': Credenciales.objects.all()}
        for field, qs in fields.items():
            value = attrs.get(field)
            if not value:
                continue
            if field == 'correo':
                attrs[field] = value = value.lower()
            exclude_id = credentials.pk if field == 'usuario' and credentials else profile.pk if field != 'usuario' and profile else None
            if qs.filter(**{field + '__iexact': value}).exclude(pk=exclude_id).exists():
                raise serializers.ValidationError({field: 'Este valor ya está registrado en otra cuenta.'})
        return attrs


def revoke(credentials):
    credentials.password_version += 1
    Token.objects.filter(user=credentials).delete()


def lock_accounts(ids):
    # Lock all administrators in a fixed order, including the target, before checking invariants.
    list(Credenciales.objects.select_for_update().filter(
        Q(tipo_usuario__in=(1, 4)) | Q(usuario_rel_id__in=ids)).order_by('pk'))


def authorize(actor, credentials, sensitive=False):
    if actor.tipo_usuario == 4:
        return
    if sensitive or (credentials and credentials.tipo_usuario in (1, 4) and actor.pk != credentials.pk):
        raise PermissionDenied('Solo un superadministrador puede realizar esta operación.')


def protect_admins(actor, credentials, state, role):
    if not credentials:
        return
    if state == 0 and actor.pk == credentials.pk:
        raise serializers.ValidationError({'estado': 'No puedes inactivar tu propia cuenta.'})
    for roles, message in (((1, 4), 'Debe quedar al menos un administrador activo.'),
                            ((4,), 'Debe quedar al menos un superadministrador activo.')):
        if credentials.estado == 1 and credentials.tipo_usuario in roles and (state != 1 or role not in roles):
            if not Credenciales.objects.filter(estado=1, tipo_usuario__in=roles).exclude(pk=credentials.pk).exists():
                raise serializers.ValidationError({'estado': message})


class AccountView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request, usuario_id):
        profile = get_object_or_404(Usuario.objects.select_related('credenciales', 'cargo', 'credenciales__location'), pk=usuario_id)
        return Response(UsuarioListadoSerializer(profile).data)

    @transaction.atomic
    def post(self, request):
        data = AccountInput(data=request.data)
        data.is_valid(raise_exception=True)
        values = data.validated_data
        for required in ('usuario', 'cedula', 'nombre_completo'):
            if not values.get(required):
                raise serializers.ValidationError({required: 'Este campo es obligatorio.'})
        role = values.pop('tipo_usuario', 0)
        if role in (1, 4):
            authorize(request.user, None, sensitive=True)
        username = values.pop('usuario')
        location = values.pop('location_id', None)
        state = values.pop('estado', 1)
        credentials = Credenciales(usuario=username, tipo_usuario=role, estado=state, location=location)
        password = NewPasswordSerializer(data={'new_password': request.data.get('password'),
            'confirm_password': request.data.get('confirm_password')}, context={'user': credentials})
        password.is_valid(raise_exception=True)
        try:
            with transaction.atomic():
                profile = Usuario.objects.create(**values, estado=state)
                credentials.usuario_rel = profile
                credentials.set_password(password.validated_data['new_password'])
                credentials.save()
        except IntegrityError:
            raise serializers.ValidationError({'error': 'Usuario o documento duplicado. Revisa los datos.'})
        return Response({'mensaje': 'Usuario creado correctamente', 'usuario_id': credentials.pk,
                         'usuario_rel_id': profile.pk}, status=201)

    @transaction.atomic
    def put(self, request, usuario_id):
        lock_accounts([usuario_id])
        profile = get_object_or_404(Usuario.objects.select_for_update(), pk=usuario_id)
        credentials = getattr(profile, 'credenciales', None)
        authorize(request.user, credentials)
        # Passwords have a separate endpoint; blank legacy fields are harmless.
        if request.data.get('password') or request.data.get('new_password'):
            raise serializers.ValidationError({'password': 'Utiliza la acción Cambiar contraseña.'})
        data = AccountInput(data=request.data, context={'profile': profile})
        data.is_valid(raise_exception=True)
        values = dict(data.validated_data)
        role = values.pop('tipo_usuario', credentials.tipo_usuario if credentials else 0)
        state = values.pop('estado', credentials.estado if credentials else profile.estado)
        if credentials and (role != credentials.tipo_usuario or state != credentials.estado):
            authorize(request.user, credentials, sensitive=True)
        protect_admins(request.user, credentials, state, role)
        location = values.pop('location_id', credentials.location if credentials else None)
        username = values.pop('usuario', credentials.usuario if credentials else None)
        try:
            with transaction.atomic():
                for field, value in values.items():
                    setattr(profile, field, value)
                profile.estado = state
                profile.save()
                if credentials:
                    if (state, role) != (credentials.estado, credentials.tipo_usuario):
                        revoke(credentials)
                    credentials.estado, credentials.tipo_usuario = state, role
                    credentials.location, credentials.usuario = location, username
                    credentials.save()
        except IntegrityError:
            raise serializers.ValidationError({'error': 'Usuario o documento duplicado. Revisa los datos.'})
        return Response(UsuarioListadoSerializer(profile).data)

    patch = put


class AccountCreate(AccountView):
    http_method_names = ['post', 'options']


class AccountDetail(AccountView):
    http_method_names = ['get', 'put', 'patch', 'options']


class AccountList(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        try:
            page = max(1, int(request.query_params.get('page', 1)))
            size = min(100, max(1, int(request.query_params.get('page_size', 10))))
        except (ValueError, TypeError):
            raise serializers.ValidationError({'page': 'La paginación debe ser numérica.'})
        qs = Usuario.objects.select_related('credenciales', 'cargo', 'credenciales__location').order_by('pk')
        state = request.query_params.get('estado', 'todos')
        if state not in ('todos', '0', '1'):
            raise serializers.ValidationError({'estado': 'Elige todos, 0 o 1.'})
        if state != 'todos':
            qs = qs.filter(estado=int(state))
        search = request.query_params.get('search', '').strip()
        if search:
            qs = qs.filter(Q(nombre_completo__icontains=search) | Q(cedula__icontains=search) |
                           Q(correo__icontains=search) | Q(telefono__icontains=search) | Q(credenciales__usuario__icontains=search))
        kind = request.query_params.get('tipo')
        if kind == 'normal':
            qs = qs.filter(credenciales__tipo_usuario=0)
        elif kind == 'trabajador':
            qs = qs.filter(credenciales__tipo_usuario__in=(1, 2, 3, 4))
        return Response({'count': qs.count(), 'page': page, 'page_size': size,
            'results': UsuarioListadoSerializer(qs[(page-1)*size:page*size], many=True).data})


class AccountState(AccountView):
    http_method_names = ['patch', 'post', 'options']
    def patch(self, request, usuario_id):
        if set(request.data) != {'estado'}:
            raise serializers.ValidationError({'estado': 'Indica únicamente el nuevo estado.'})
        authorize(request.user, None, sensitive=True)
        return self.put(request, usuario_id)

    @transaction.atomic
    def post(self, request):
        authorize(request.user, None, sensitive=True)
        if set(request.data) - {'usuario_ids', 'cedulas', 'estado'}:
            raise serializers.ValidationError({'estado': 'La operación masiva solo modifica el estado.'})
        ids, documents = request.data.get('usuario_ids', []), request.data.get('cedulas', [])
        if not isinstance(ids, list) or not isinstance(documents, list) or not (ids or documents):
            raise serializers.ValidationError({'usuario_ids': 'Selecciona las cuentas que deseas actualizar.'})
        if len(ids) + len(documents) > 1000:
            raise serializers.ValidationError({'usuario_ids': 'Actualiza un máximo de 1000 cuentas por solicitud.'})
        if len(set(map(str, documents))) != Usuario.objects.filter(cedula__in=documents).count():
            raise serializers.ValidationError({'cedulas': 'Alguno de los documentos no está registrado.'})
        try:
            ids = list({int(value) for value in ids} | set(Usuario.objects.filter(cedula__in=documents).values_list('pk', flat=True)))
        except (ValueError, TypeError):
            raise serializers.ValidationError({'usuario_ids': 'Identificadores inválidos.'})
        lock_accounts(ids)
        results = []
        for pk in sorted(ids):
            results.append(self.put(request, pk).data)
        return Response({'actualizados': len(results), 'encontrados': results})


class AccountRole(AccountView):
    http_method_names = ['patch', 'options']
    def patch(self, request, usuario_id):
        authorize(request.user, None, sensitive=True)
        if set(request.data) != {'tipo_usuario'}:
            raise serializers.ValidationError({'tipo_usuario': 'Indica únicamente el nuevo rol.'})
        return self.put(request, usuario_id)


class AccountPassword(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    @transaction.atomic
    def post(self, request, usuario_id):
        lock_accounts([usuario_id])
        credentials = get_object_or_404(Credenciales.objects.select_for_update(), usuario_rel_id=usuario_id)
        authorize(request.user, credentials, sensitive=True)
        data = NewPasswordSerializer(data=request.data, context={'user': credentials})
        data.is_valid(raise_exception=True)
        credentials.set_password(data.validated_data['new_password'])
        revoke(credentials)
        credentials.save(update_fields=['password', 'password_version'])
        return Response({'message': 'Contraseña actualizada. Las sesiones anteriores quedaron invalidadas.'})
