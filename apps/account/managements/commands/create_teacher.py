"""
from apps.account.models import User

u = User.objects.get(email="brsegundo@gmail.com")

u.role = "TEACHER"
u.is_staff = True
u.is_active = True

u.set_password("brsegundo28")

u.save()

print("Usuario actualizado")


"""