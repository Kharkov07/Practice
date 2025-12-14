from django.db import models
from django.conf import settings

class VirtualMachine(models.Model):
    name = models.CharField(max_length=150)
    image = models.ImageField(upload_to="images/", blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "VirtualMachine"

    def __str__(self):
        return self.name


class Access(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    vm = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE)
    ssh_key = models.TextField(blank=True, null=True)
    pak_code = models.TextField(blank=True, null=True)


    class Meta:
        db_table = "Access"

    def __str__(self):
        return f"{self.user.username} → {self.vm.name}"
