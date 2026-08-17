from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import redirect, render
from django.urls import reverse_lazy

from oif_site import notify
from .forms import SignUpForm, LoginForm, ProfileForm


def signup(request):
    if request.user.is_authenticated:
        return redirect("dashboard:home")
    if request.method == "POST":
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            notify.send_account_pending_approval(user)
            # New members are created inactive and are not signed in here -
            # staff must approve the account (Members -> is_active) before
            # Django's auth backend will allow it to sign in at all.
            messages.success(
                request,
                f"Thanks, {user.first_name}! Your account has been created "
                "and is pending approval. We'll email you as soon as it's "
                "ready — then you can sign in.",
            )
            return redirect("accounts:login")
    else:
        form = SignUpForm()
    return render(request, "accounts/signup.html", {"form": form})


class OIFLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = LoginForm
    redirect_authenticated_user = True


class OIFLogoutView(LogoutView):
    next_page = reverse_lazy("pages:home")


@login_required
def profile(request):
    if request.method == "POST":
        form = ProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(instance=request.user)
    return render(request, "accounts/profile.html", {"form": form})
