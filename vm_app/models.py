from django.db import models
from django.conf import settings
import uuid


class TelegramRegisterToken(models.Model):
    token = models.UUIDField(default=uuid.uuid4, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chat_id = models.CharField(max_length=32, blank=True)
    is_confirmed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)


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
        unique_together = ("user", "vm")

    def __str__(self):
        return f"{self.user.username} → {self.vm.name}"


class VmUser(models.Model):

    vm = models.ForeignKey(VirtualMachine, on_delete=models.CASCADE, related_name="vm_users")
    manager = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_vm_users",
        help_text="Менеджер (Django user), который создал этого обычного пользователя",
    )

    username = models.CharField(max_length=64, help_text="Логин обычного пользователя (вводится вручную)")
    password8 = models.TextField()

    ssh_private_key = models.TextField(blank=True, null=True)
    ssh_public_key = models.TextField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "VmUser"
        unique_together = ("vm", "username")
        indexes = [
            models.Index(fields=["vm", "username"]),
            models.Index(fields=["manager"]),
        ]

    def __str__(self):
        return f"{self.username}@{self.vm.name}"


class TelegramProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    chat_id = models.CharField(max_length=32, unique=True)

    def __str__(self):
        return f"{self.user.username} → Telegram"


class TelegramLoginCode(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    code = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        from django.utils import timezone
        return (timezone.now() - self.created_at).seconds > 300


class SiteSettings(models.Model):

    twofa_enabled = models.BooleanField(default=True)

    class Meta:
        db_table = "SiteSettings"

    def __str__(self):
        return f"2FA enabled: {self.twofa_enabled}"

    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(id=1, defaults={"twofa_enabled": True})
        return obj
