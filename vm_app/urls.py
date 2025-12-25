from django.urls import path
from . import views


urlpatterns = [
    path("", views.home, name="home"),
    path("register/", views.register, name="register"),
    path("autor/", views.autor, name="autor"),
    path("logout/", views.logout_user, name="logout"),
    path("telegram/link/", views.telegram_link_page, name="telegram_link_page"),
    path("telegram/link/start/", views.telegram_link_start, name="telegram_link_start"),
    path("login/2fa/", views.login_2fa_confirm, name="login_2fa_confirm"),
    path("bot/confirm-link/", views.bot_confirm_link, name="bot_confirm_link"),
    path("bot/get-login-code/", views.bot_get_login_code, name="bot_get_login_code"),
    path("vm/<int:vm_id>/users/", views.vm_users, name="vm_users"),
    path("vmuser/<int:user_id>/key/<str:key_type>/", views.vmuser_key, name="vmuser_key"),

]
