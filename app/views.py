# Create your views here.
from django.template import RequestContext
from django.http import HttpResponse, HttpResponseRedirect
from django.conf import settings
from django.shortcuts import render_to_response, get_object_or_404
from app.forms import CreateUserForm, LoginForm, PasswordEmailForm
from app.utilities import reply_object, create_key
import simplejson
from django.contrib.auth import logout
from django.core.urlresolvers import reverse
import datetime
from app.models import UserProfile, SocialAuth
from app.forms import PasswordResetForm, PasswordEmailForm,\
PersonEmailForm, ShopEmailForm, StripePaymentForm
from django.contrib.auth import authenticate, login
import requests


def index(request):
    return render_to_response("index.html",
                              context_instance=RequestContext(request))


def home(request):
    """
    Home page after logging in
    """
    if request.user.is_authenticated():
        return render_to_response("home.html",
                                  context_instance=RequestContext(request))
    else:
        return HttpResponseRedirect(reverse('login'))


def user_register(request):
    """
    Registration page
    """
    form = CreateUserForm()
    return render_to_response(
        "register.html",
        context_instance=RequestContext(request, {"user_form": form}))


def add_user(request):
    """
    Registration request handler
    """
    response = reply_object()
    form = CreateUserForm(request.POST)
    if form.is_valid():
        response = form.save_user()
        response["success_page"] = reverse('registration_success')
    else:
        response["code"] = settings.APP_CODE["FORM ERROR"]
        response["errors"] = form.errors
    return HttpResponse(simplejson.dumps(response))


def registration_success(request):
    return render_to_response('registration_success.html',
                              context_instance=RequestContext(request,
                {"activation_email": settings.EMAIL_VERIFICATION_REQUIRED}))


def user_login(request):
    """
    Login page
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('home'))
    form = LoginForm(request=request)
    return render_to_response("login.html",
            context_instance=RequestContext(request,
                {"login_form": form}))


def login_user(request):
    """
    Login request handler
    """
    response = reply_object()
    form = LoginForm(request.POST, request=request)

    if form.is_valid():
        response["code"] = settings.APP_CODE["LOGIN"]
        response["next_view"] = reverse('home')
    else:
        response["code"] = settings.APP_CODE["FORM ERROR"]
        response["errors"] = form.errors

    return HttpResponse(simplejson.dumps(response))


def user_logout(request):
    """
    Logout request
    """
    # Logout function flushes all sessions.Save session variables to a local
    # variable for reuse
    logout(request)
    return HttpResponseRedirect(reverse('login'))


def activate(request, verification_key):
    """
    New account activation function
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('home'))
    user_profile = get_object_or_404(UserProfile,
                                     verification_key=verification_key)
    naive_date = user_profile.key_expires.replace(tzinfo=None)
    if naive_date < datetime.datetime.today():
        return render_to_response('expired.html',
                                  context_instance=RequestContext(request))
    user_account = user_profile.user
    user_account.is_active = True
    user_account.save()
    #remove activation key once account is activated
    user_profile.verification_key = ""
    user_profile.save()
    return render_to_response('activated.html',
                              context_instance=RequestContext(request))


def start_fbauth(request):
    """
    Starting point for facebook authentication
    """
    social_auth = SocialAuth(request=request)
    redirect_url = social_auth.facebook_step1()
    return HttpResponseRedirect(redirect_url)


def fbauth(request):
    """
    Redirect function after facebook authentication
    """
    social_auth = SocialAuth(request=request)
    social_auth.facebook_step2()
    return HttpResponseRedirect(reverse('home'))


def start_twauth(request):
    """
        The view function that initiates the entire handshake.
    """
    social_auth = SocialAuth(request=request)
    redirect_url = social_auth.twitter_step1()
    return HttpResponseRedirect(redirect_url)


def twauth(request):
    """
    Redirect function after twitter login
    """

    social_auth = SocialAuth(request=request)
    social_auth.twitter_step2()
    return HttpResponseRedirect(reverse('home'))


def start_googleauth(request):
    """
    Starting point for google authentication
    uses oauth2.0
    """
    social_auth = SocialAuth(request=request)
    redirect_url = social_auth.google_step1()
    return HttpResponseRedirect(redirect_url)


def googleauth(request):
    """
    Redirect after google auth
    """
    social_auth = SocialAuth(request=request)
    social_auth.google_step2()
    return HttpResponseRedirect(reverse('home'))


def password_reset(request):
    """
    Password reset step1
    """
    reset_form = PasswordEmailForm()

    return render_to_response('password_reset.html',
                                  context_instance=RequestContext(
            request, {"reset_form": reset_form}))


def password_reset_submit_email(request):
    response = reply_object()
    form = PasswordEmailForm(request.POST)
    if form.is_valid():
        response = form.send_reset_link()
    else:
        response["code"] = settings.APP_CODE["FORM ERROR"]
        response["errors"] = form.errors

    return HttpResponse(simplejson.dumps(response))


def password_reset_form(request, verification_key):
    """
    Password reset form
    """
    if request.user.is_authenticated():
        return HttpResponseRedirect(reverse('home'))
    user_profile = get_object_or_404(UserProfile,
                                     verification_key=verification_key)
    naive_date = user_profile.key_expires.replace(tzinfo=None)
    if naive_date < datetime.datetime.today():
        return render_to_response('expired.html',
                                  context_instance=RequestContext(request))

    user_account = user_profile.user
    temp_password = create_key(user_account.username, 2)
    user_account.set_password(temp_password)
    user_account.save()
    user = authenticate(username=user_account.username, password=temp_password)
    if user is not None:
        if user.is_active:
            login(request, user)
        else:
            return HttpResponse("This account is inactive.")
    #remove reset key
    user_profile.verification_key = ""
    user_profile.save()
    reset_form = PasswordResetForm()
    return render_to_response('password_reset_form.html',
                              context_instance=RequestContext(
            request, {"reset_form": reset_form}))


def password_reset_submit_password(request):
    response = reply_object()
    form = PasswordResetForm(request.POST, request=request)
    if form.is_valid():
        response = form.save_new_password()
        response["code"] = settings.APP_CODE["CALLBACK"]
        response["redirect"] = reverse('home')
    else:
        response["code"] = settings.APP_CODE["FORM ERROR"]
        response["errors"] = form.errors

    return HttpResponse(simplejson.dumps(response))


def person_email_submit(request):
    if not request.POST:
        return render_to_response("index.html",
                              context_instance=RequestContext(request))
    form = PersonEmailForm(request.POST)
    if form.is_valid():
        form.save_email()
        return render_to_response("local.html",
                              context_instance=RequestContext(request))
    else:
        return render_to_response("index.html",
                              context_instance=RequestContext(
                request, {"error": dict(form.errors.items())}))


def shop_email_submit(request):
    if not request.POST:
        return render_to_response("index.html",
                              context_instance=RequestContext(request))
    form = ShopEmailForm(request.POST)
    if form.is_valid():
        form.save_email()
        return render_to_response("local.html",
                              context_instance=RequestContext(request))
    else:
        return render_to_response("index.html",
                              context_instance=RequestContext(
                request, {"error": dict(form.errors.items())}))


def stripe_form(request):
    if not request.POST:
        return render_to_response("stripe_form.html",
                              context_instance=RequestContext(
                request,
                {"publishable_key": settings.STRIPE_TEST_PUBLISHABLE_KEY}))
    else:
        return stripe_charge(request)


def stripe_charge(request):
    form = StripePaymentForm(request.POST, request=request)
    if form.is_valid():
        form.charge()
        message = "test charged"
    else:
        message = form.errors

    return render_to_response("stripe_form.html",
                              context_instance=RequestContext(
            request,
            {"publishable_key": settings.STRIPE_TEST_PUBLISHABLE_KEY,
             "the_message": message}))


def stripe_oauth_callback(request):
    print settings.STRIPE_CLIENT_ID
    code = request.GET["code"]
    header = {'Authorization': 'Bearer %s' % settings.STRIPE_SECRET_KEY}
    data = {'grant_type': 'authorization_code',
            'client_id': settings.STRIPE_CLIENT_ID,
            'code': code
            }
    response = requests.post("https://connect.stripe.com/oauth/token",
                             params=data, headers=header)
    print response.content
    #in response access token is used as api_key and users publishable key in stripe.js
    return HttpResponse(response.content)


def test(request):
    """
    Test function
    """
    print "test"
    return HttpResponse("test")
