from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import VirtualMachine, Access

User = get_user_model()


class AccessInlineForVM(admin.TabularInline):
    model = Access
    extra = 1
    autocomplete_fields = ["user"]


@admin.register(VirtualMachine)
class VirtualMachineAdmin(admin.ModelAdmin):
    list_display = ("id", "name")
    search_fields = ("name",)
    fields = ("name", "image", "description")
    inlines = [AccessInlineForVM]



class AccessInlineForUser(admin.TabularInline):
    model = Access
    extra = 0
    autocomplete_fields = ["vm"]


class AccessAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "vm", "ssh_key", "pak_code")
    list_filter = ("user", "vm")
    search_fields = ("user__username", "vm__name", "ssh_key", "pak_code")


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [AccessInlineForUser]


admin.site.register(Access, AccessAdmin)
