from django.db import models


class User(models.Model):
    username = models.TextField(unique=True)
    password = models.TextField()

    class Meta:
        db_table = 'User'


class Virtualmachine(models.Model):
    name = models.TextField()

    class Meta:
        db_table = 'VirtualMachine'


class Access(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    vm = models.ForeignKey(Virtualmachine, on_delete=models.CASCADE)
    ssh_key = models.TextField()
    pak_code = models.TextField()

    class Meta:
        db_table = 'Access'
