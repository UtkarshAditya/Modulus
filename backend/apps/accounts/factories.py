import factory

from .models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")
    role = User.Role.EMPLOYER

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or "password123!")
        if create:
            self.save()


class EmployerFactory(UserFactory):
    role = User.Role.EMPLOYER


class ModeratorFactory(UserFactory):
    role = User.Role.MODERATOR
    is_staff = True


class AdminFactory(UserFactory):
    role = User.Role.ADMIN
    is_staff = True
    is_superuser = True
