from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils.translation import gettext_lazy as _


class UserManager(BaseUserManager):
    use_in_migrations = True

    @classmethod
    def normalize_email(cls, email):
        """
        normalize_email customizado para formatar o email em lowercase e evitar emails duplicados (lower e uppercase.
        """
        email = email or ""
        try:
            email_name, domain_part = email.strip().rsplit("@", 1)
        except ValueError:
            pass
        else:
            email = email_name + "@" + domain_part
        return email.lower()

    def _create_user(self, email, senha, **extra_fields):

        if not email:
            raise ValueError(_("Preencha com um email válido"))

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(senha)
        user.save(using=self._db)

        return user

    # TODO - Checar porque esta função estava comentada
    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")
        if not password:
            raise ValueError("User must have a password")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(
        _("email"),
        max_length=150,
        unique=True,
        help_text=_(
            "Obrigatório. 150 caracteres ou menos. São permitidos números, letras e @ /. / + / - / _ ."
        ),
        error_messages={
            "unique": _("Já existe um usuario cadastrado com este email."),
        },
    )

    name = models.CharField(_("Nome"), max_length=150)
    date_joined = models.DateTimeField(_("data de cadastro"), auto_now_add=True)

    image = models.ImageField(
        _("upload de foto"),
        blank=True,
        null=True,
        help_text=_("Arquivo vazio. Você precisa submeter um arquivo."),
    )

    is_staff = models.BooleanField(
        _("Staff status"),
        default=False,
        help_text=_("Define se esse usuário pode logar no site admin"),
    )

    is_active = models.BooleanField(
        _("Ativo"),
        default=True,
        help_text=_(
            "Define se o usuário está ativo ou não. "
            "Desmarque este campo ao invés de deletar a conta do usuário."
        ),
    )

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = [
        "name",
    ]

    class Meta:
        verbose_name = _("usuário")
        verbose_name_plural = _("usuários")

    def save(self, *args, **kwargs):
        self.email = self.email.lower()
        return super().save(*args, **kwargs)
