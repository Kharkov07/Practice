from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import logout
from .models import Access
from django.http import JsonResponse, HttpResponseBadRequest, HttpResponseForbidden
import secrets, string, base64


@login_required
def home(request):
    accesses = Access.objects.filter(user=request.user).select_related("vm")
    return render(request, "home.html", {"accesses": accesses})


def get_or_generate_key(request, access_id, key_type):
    if request.method != "POST":
        return HttpResponseBadRequest("Invalid method")
    try:
        access = Access.objects.select_related("vm", "user").get(pk=access_id)
    except Access.DoesNotExist:
        return HttpResponseBadRequest("Access not found")
    user = request.user
    if access.user_id != user.id:
        return HttpResponseForbidden("Forbidden")
    if key_type == "ssh":
        if not access.ssh_key:
            raw = secrets.token_bytes(32)
            b64 = base64.b64encode(raw).decode("ascii")
            access.ssh_key = f"ssh-rsa {b64} {user.username}@{access.vm.name}"
            access.save(update_fields=["ssh_key"])
        return JsonResponse({"key": access.ssh_key})
    elif key_type == "puk":
        if not access.pak_code:
            digits = "".join(secrets.choice(string.digits) for _ in range(8))
            access.pak_code = digits
            access.save(update_fields=["pak_code"])
        return JsonResponse({"key": access.pak_code})
    else:
        return HttpResponseBadRequest("Invalid key type")


def register(request):

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("autor")
    else:
        form = UserCreationForm()

    return render(request, "register.html", {"form": form})


def logout_user(request):
    logout(request)
    return redirect("autor")
