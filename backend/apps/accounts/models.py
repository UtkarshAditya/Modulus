from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user with a role.

    Started as a custom user model from day one per the project plan —
    retrofitting AUTH_USER_MODEL after other apps have migrations is
    painful, so this exists even though it only adds `role` on top of
    Django's built-in AbstractUser for now.
    """

    class Role(models.TextChoices):
        EMPLOYER = "EMPLOYER", "Employer"
        MODERATOR = "MODERATOR", "Moderator"
        ADMIN = "ADMIN", "Admin"

    role = models.CharField(max_length=16, choices=Role.choices, default=Role.EMPLOYER)

    @property
    def is_employer(self) -> bool:
        return self.role == self.Role.EMPLOYER

    @property
    def is_moderator(self) -> bool:
        return self.role == self.Role.MODERATOR

    @property
    def is_admin_role(self) -> bool:
        return self.role == self.Role.ADMIN

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"
