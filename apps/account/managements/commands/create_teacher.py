from apps.account.models import User

u = User.objects.create(
    email="profesor@correo.com",
    role="TEACHER",
    is_staff=True,
    is_active=True,
)

u.set_password("12345678")
u.save()

print("Usuario creado")