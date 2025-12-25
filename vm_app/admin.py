from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import VirtualMachine, Access, VmUser, SiteSettings

User = get_user_model()


class AccessInlineForVM(admin.TabularInline):
    model = Access
    extra = 0
    autocomplete_fields = ["user"]
    fields = ("user", "vm_users_list")
    readonly_fields = ("vm_users_list",)

    def vm_users_list(self, obj):
        if not obj or not obj.pk:
            return "—"
        users = VmUser.objects.filter(vm=obj.vm, manager=obj.user).values_list("username", flat=True)
        return ", ".join(users) if users else "—"

    vm_users_list.short_description = "Пользователи VM"


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
    fields = ("vm", "vm_users_list")
    readonly_fields = ("vm_users_list",)

    def vm_users_list(self, obj):
        if not obj or not obj.pk:
            return "—"
        users = VmUser.objects.filter(vm=obj.vm, manager=obj.user).values_list("username", flat=True)
        return ", ".join(users) if users else "—"

    vm_users_list.short_description = "Пользователи VM"


@admin.register(Access)
class AccessAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "vm", "users_count")
    list_filter = ("user", "vm")
    search_fields = ("user__username", "vm__name", "vm__vm_users__username")
    list_select_related = ("user", "vm")

    def users_count(self, obj):
        return VmUser.objects.filter(vm=obj.vm, manager=obj.user).count()

    users_count.short_description = "Пользователей"


admin.site.unregister(User)


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    inlines = [AccessInlineForUser]


@admin.action(description="Выключить 2FA (для всех)")
def disable_2fa(modeladmin, request, queryset):
    s = SiteSettings.get_solo()
    s.twofa_enabled = False
    s.save(update_fields=["twofa_enabled"])


@admin.action(description="Включить 2FA (для всех)")
def enable_2fa(modeladmin, request, queryset):
    s = SiteSettings.get_solo()
    s.twofa_enabled = True
    s.save(update_fields=["twofa_enabled"])


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ("id", "twofa_enabled")
    actions = [disable_2fa, enable_2fa]

    def has_add_permission(self, request):
        return False
