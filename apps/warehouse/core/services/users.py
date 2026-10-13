from __future__ import annotations

from io import BytesIO
from uuid import uuid4

from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest

from PIL import Image, ImageOps, UnidentifiedImageError

from apps.warehouse.core.exceptions import UserValidationError
from apps.warehouse.models.printer import UserAppSettings
from apps.warehouse.core.schemas.users import (
    ChangePasswordSchema,
    UserCreateSchema,
    UserSchema,
    UserUpdateSchema,
)

AVATAR_MAX_UPLOAD_BYTES = 5 * 1024 * 1024
AVATAR_MAX_SOURCE_PIXELS = 25_000_000
AVATAR_SIZE = 256
AVATAR_WEBP_QUALITY = 80


def user_orm_to_schema(user: User) -> UserSchema:
    return UserSchema(
        id=user.pk,
        username=user.username,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        is_active=user.is_active,
        is_superuser=user.is_superuser,
        last_login=user.last_login,
        date_joined=user.date_joined,
    )


class UsersService:
    @staticmethod
    def get_users(search_term: str | None = None) -> QuerySet[User]:
        qs = User.objects.all()
        if search_term:
            qs = qs.filter(
                Q(username__icontains=search_term)
                | Q(email__icontains=search_term)
                | Q(first_name__icontains=search_term)
                | Q(last_name__icontains=search_term)
            )
        return qs.order_by("username")

    @staticmethod
    def _validate_password(password: str, user: User | None = None) -> None:
        try:
            validate_password(password, user=user)
        except ValidationError as exc:
            raise UserValidationError(" ".join(exc.messages)) from exc

    @staticmethod
    def _validate_username(username: str, exclude_pk: int | None = None) -> str:
        username = username.strip()
        if not username:
            raise UserValidationError("Username must not be empty")
        duplicates = User.objects.filter(username__iexact=username)
        if exclude_pk is not None:
            duplicates = duplicates.exclude(pk=exclude_pk)
        if duplicates.exists():
            raise UserValidationError("User with this username already exists")
        return username

    @classmethod
    @transaction.atomic
    def create_user(cls, params: UserCreateSchema) -> UserSchema:
        username = cls._validate_username(params.username)
        user = User(
            username=username,
            email=params.email.strip(),
            first_name=params.first_name.strip(),
            last_name=params.last_name.strip(),
            is_active=params.is_active,
            is_superuser=params.is_superuser,
            is_staff=params.is_superuser,
        )
        cls._validate_password(params.password, user)
        user.set_password(params.password)
        user.save()
        return user_orm_to_schema(user)

    @classmethod
    @transaction.atomic
    def update_user(
        cls, actor: User, user_id: int, params: UserUpdateSchema
    ) -> UserSchema:
        user = User.objects.select_for_update().get(pk=user_id)

        if user.pk == actor.pk and not (params.is_active and params.is_superuser):
            raise UserValidationError(
                "You cannot deactivate or demote your own account"
            )

        user.username = cls._validate_username(params.username, exclude_pk=user.pk)
        user.email = params.email.strip()
        user.first_name = params.first_name.strip()
        user.last_name = params.last_name.strip()
        user.is_active = params.is_active
        user.is_superuser = params.is_superuser
        user.is_staff = params.is_superuser
        if params.password:
            cls._validate_password(params.password, user)
            user.set_password(params.password)
        user.save()
        return user_orm_to_schema(user)

    @staticmethod
    @transaction.atomic
    def delete_user(actor: User, user_id: int) -> UserSchema:
        user = User.objects.get(pk=user_id)
        if user.pk == actor.pk:
            raise UserValidationError("You cannot delete your own account")
        schema = user_orm_to_schema(user)
        user.delete()
        return schema

    @classmethod
    @transaction.atomic
    def change_password(
        cls, request: HttpRequest, user: User, params: ChangePasswordSchema
    ) -> None:
        if not user.check_password(params.current_password):
            raise UserValidationError("Current password is incorrect")
        if params.current_password == params.new_password:
            raise UserValidationError(
                "New password must differ from the current password"
            )
        cls._validate_password(params.new_password, user)
        user.set_password(params.new_password)
        user.save(update_fields=["password"])
        # keep the current session alive
        update_session_auth_hash(request, user)

    @staticmethod
    def get_avatar_url(user: User) -> str | None:
        settings_obj = UserAppSettings.objects.filter(user=user).first()
        if not settings_obj or not settings_obj.avatar:
            return None
        return settings_obj.avatar.url

    @staticmethod
    def _compress_avatar(upload: UploadedFile) -> bytes:
        """Center-crop to a square, downscale and encode as WebP."""
        if upload.size is not None and upload.size > AVATAR_MAX_UPLOAD_BYTES:
            raise UserValidationError("Avatar image is too large (max 5 MB)")
        try:
            with Image.open(upload) as img:
                if img.width * img.height > AVATAR_MAX_SOURCE_PIXELS:
                    raise UserValidationError("Avatar image resolution is too high")
                image = ImageOps.exif_transpose(img)
                side = min(image.width, image.height)
                left = (image.width - side) // 2
                top = (image.height - side) // 2
                image = image.crop((left, top, left + side, top + side))
                if side > AVATAR_SIZE:
                    image = image.resize(
                        (AVATAR_SIZE, AVATAR_SIZE), Image.Resampling.LANCZOS
                    )
                has_alpha = "A" in image.getbands() or "transparency" in image.info
                image = image.convert("RGBA" if has_alpha else "RGB")
                buffer = BytesIO()
                image.save(buffer, format="WEBP", quality=AVATAR_WEBP_QUALITY)
        except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as exc:
            raise UserValidationError("File is not a valid image") from exc
        return buffer.getvalue()

    @classmethod
    @transaction.atomic
    def set_avatar(cls, user: User, upload: UploadedFile) -> None:
        content = cls._compress_avatar(upload)
        settings_obj, _ = UserAppSettings.objects.get_or_create(user=user)
        if settings_obj.avatar:
            settings_obj.avatar.delete(save=False)
        # unique name => no stale browser cache after a change
        settings_obj.avatar.save(
            f"{uuid4().hex}.webp", ContentFile(content), save=False
        )
        settings_obj.save(update_fields=["avatar", "changed"])

    @staticmethod
    @transaction.atomic
    def remove_avatar(user: User) -> None:
        settings_obj = UserAppSettings.objects.filter(user=user).first()
        if not settings_obj or not settings_obj.avatar:
            return
        settings_obj.avatar.delete(save=False)
        settings_obj.avatar = None
        settings_obj.save(update_fields=["avatar", "changed"])


users_service = UsersService()
