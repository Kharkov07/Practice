import secrets
import string
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
from django.shortcuts import render, redirect
from django.views.decorators.http import require_http_methods, require_POST
from .models import Access, TelegramRegisterToken, TelegramProfile, TelegramLoginCode, VirtualMachine, VmUser, SiteSettings
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from django.shortcuts import get_object_or_404
from django.contrib.auth.decorators import login_required


def generate_ssh_keypair() -> tuple[str, str]:

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.OpenSSH,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")

    public_openssh = key.public_key().public_bytes(
        encoding=serialization.Encoding.OpenSSH,
        format=serialization.PublicFormat.OpenSSH,
    ).decode("utf-8")

    return private_pem, public_openssh


def _bot_ok(request) -> bool:
    return request.headers.get("X-Bot-Secret") == getattr(settings, "TELEGRAM_BOT_SHARED_SECRET", "")


def _gen_code6() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(6))


@login_required
def home(request):
    accesses = Access.objects.filter(user=request.user).select_related("vm")
    return render(request, "home.html", {"accesses": accesses})


def logout_user(request):
    logout(request)
    return redirect("autor")


@require_http_methods(["GET", "POST"])
def register(request):

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("telegram_link_page")
    else:
        form = UserCreationForm()

    return render(request, "register.html", {"form": form})


@login_required
def telegram_link_page(request):
    tg_profile = TelegramProfile.objects.filter(user=request.user).first()
    return render(request, "telegram_link_page.html", {"tg_profile": tg_profile})


@login_required
def telegram_link_start(request):
    token_obj = TelegramRegisterToken.objects.create(user=request.user)
    bot_username = getattr(settings, "TELEGRAM_BOT_USERNAME", "VM_CIT_Bot")
    return redirect(f"https://t.me/{bot_username}?start=link_{token_obj.token}")


@require_http_methods(["GET", "POST"])
def autor(request):
    if request.method == "GET":
        return render(request, "autor.html")

    username = (request.POST.get("username") or "").strip()
    password = request.POST.get("password") or ""

    user = authenticate(request, username=username, password=password)
    if user is None:
        return render(request, "autor.html", {"error": "Неверный логин или пароль"})

    if not SiteSettings.get_solo().twofa_enabled:
        login(request, user)
        return redirect("home")

    tg_profile = TelegramProfile.objects.filter(user=user).first()
    if tg_profile is None:
        return render(request, "autor.html", {"error": "Сначала подтвердите аккаунт через Telegram"})

    TelegramLoginCode.objects.filter(user=user).delete()

    code = _gen_code6()
    TelegramLoginCode.objects.create(user=user, code=code)

    request.session["pending_2fa_user_id"] = user.id
    return redirect("login_2fa_confirm")


@require_http_methods(["GET", "POST"])
def login_2fa_confirm(request):

    user_id = request.session.get("pending_2fa_user_id")
    if not user_id:
        return redirect("autor")

    if request.method == "GET":
        return render(request, "login_2fa_confirm.html", {
            "telegram_bot_username": getattr(settings, "TELEGRAM_BOT_USERNAME", "VM_CIT_Bot")
        })
    code = (request.POST.get("code") or "").strip()
    if not code:
        return render(request, "login_2fa_confirm.html", {"error": "Введите код"})

    obj = TelegramLoginCode.objects.filter(user_id=user_id).order_by("-created_at").first()
    if not obj:
        return render(request, "login_2fa_confirm.html", {"error": "Код не найден. Войдите заново."})

    if obj.is_expired():
        return render(request, "login_2fa_confirm.html", {"error": "Код истёк. Войдите заново."})

    if obj.code != code:
        return render(request, "login_2fa_confirm.html", {"error": "Неверный код"})

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = User.objects.get(id=user_id)

    login(request, user)
    request.session.pop("pending_2fa_user_id", None)
    TelegramLoginCode.objects.filter(user=user).delete()
    return redirect("home")


@csrf_exempt
@require_POST
def bot_confirm_link(request):

    if not _bot_ok(request):
        return HttpResponseForbidden("Forbidden")

    token = (request.POST.get("token") or "").strip()
    chat_id = (request.POST.get("chat_id") or "").strip()
    if not token or not chat_id:
        return HttpResponseBadRequest("token/chat_id required")

    try:
        t = TelegramRegisterToken.objects.select_related("user").get(token=token)
    except TelegramRegisterToken.DoesNotExist:
        return HttpResponseBadRequest("Token not found")

    TelegramProfile.objects.update_or_create(
        user=t.user,
        defaults={"chat_id": chat_id},
    )

    t.chat_id = chat_id
    t.is_confirmed = True
    t.save(update_fields=["chat_id", "is_confirmed"])

    return JsonResponse({"ok": True, "username": t.user.username})


@csrf_exempt
@require_http_methods(["GET"])
def bot_get_login_code(request):

    if not _bot_ok(request):
        return HttpResponseForbidden("Forbidden")

    chat_id = (request.GET.get("chat_id") or "").strip()
    if not chat_id:
        return HttpResponseBadRequest("chat_id required")

    tg = TelegramProfile.objects.filter(chat_id=chat_id).select_related("user").first()
    if not tg:
        return JsonResponse({"ok": False, "reason": "not_linked"})

    obj = TelegramLoginCode.objects.filter(user=tg.user).order_by("-created_at").first()
    if not obj:
        return JsonResponse({"ok": False, "reason": "no_code"})

    if obj.is_expired():
        return JsonResponse({"ok": False, "reason": "expired"})

    return JsonResponse({"ok": True, "code": obj.code, "username": tg.user.username})

def _require_vm_access(user, vm_id: int) -> bool:
    return Access.objects.filter(user=user, vm_id=vm_id).exists() or user.is_superuser


@login_required
@require_http_methods(["GET", "POST"])
def vm_users(request, vm_id: int):

    if not _require_vm_access(request.user, vm_id):
        return HttpResponseForbidden("Нет доступа к этой VM")

    vm = get_object_or_404(VirtualMachine, id=vm_id)

    if request.method == "POST":
        username = (request.POST.get("username") or "").strip()
        password8 = (request.POST.get("password8") or "").strip()

        if not username:
            return render(request, "vm_users.html", {
                "vm": vm,
                "users": VmUser.objects.filter(vm=vm).order_by("-created_at"),
                "error": "Введите имя пользователя",
            })

        if not password8:
            return render(request, "vm_users.html", {
                "vm": vm,
                "users": VmUser.objects.filter(vm=vm).order_by("-created_at"),
                "error": "Введите имя пользователя",
            })



        try:
            private_key, public_key = generate_ssh_keypair()
        except Exception as e:
            return render(request, "vm_users.html", {
                "vm": vm,
                "users": VmUser.objects.filter(vm=vm).order_by("-created_at"),
                "error": f"Ошибка генерации SSH-ключа: {e}",
            })

        try:
            VmUser.objects.create(
                vm=vm,
                manager=request.user,
                username=username,
                password8=password8,
                ssh_private_key=private_key,
                ssh_public_key=public_key,
            )
        except Exception:
            return render(request, "vm_users.html", {
                "vm": vm,
                "users": VmUser.objects.filter(vm=vm).order_by("-created_at"),
                "error": "Такой username уже существует в этой VM",
            })

        return redirect("vm_users", vm_id=vm.id)

    users = VmUser.objects.filter(vm=vm).order_by("-created_at")
    return render(request, "vm_users.html", {"vm": vm, "users": users})


@login_required
@require_POST
def vmuser_key(request, user_id: int, key_type: str):

    obj = get_object_or_404(VmUser.objects.select_related("vm"), id=user_id)

    if not _require_vm_access(request.user, obj.vm_id):
        return HttpResponseForbidden("Нет доступа")

    if key_type == "priv":
        return JsonResponse({"key": obj.ssh_private_key or ""})
    if key_type == "pub":
        return JsonResponse({"key": obj.ssh_public_key or ""})

    return HttpResponseBadRequest("Unknown key type")