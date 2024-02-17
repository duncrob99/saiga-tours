from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseForbidden, FileResponse, HttpResponseRedirect, Http404
from django.contrib.auth import login, authenticate
from email_validator import validate_email, EmailNotValidError
from zxcvbn import zxcvbn
from django.contrib import messages
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.contrib.staticfiles import finders
from django.utils import timezone
from django.utils.html import strip_tags
from django.urls import reverse
from django.shortcuts import get_object_or_404
from django.db.models import Q, QuerySet
from django.db.utils import IntegrityError

from typing import Dict
from dataclasses import dataclass
from silk.profiling.profiler import silk_profile
import io, os

from .models import Form, Customer, FormTask, FilledForm
from .forms import NewPasswordForm, NewUserForm
from customers.pdf import gen_form_pdf

def redirect_to_login(request):
    return HttpResponseRedirect(f'{reverse("login")}?next={request.path}')

# Create your views here.
def register(request):
    form = NewUserForm(request.POST or None)

    if request.GET.get('cid'):
        form.fields['username'].initial = request.GET.get('cid')

    if request.method == 'POST' and form.is_valid():
        try:
            user = form.save()
            user.refresh_from_db()
            user.username = user.email
            user.save()
        except IntegrityError:
            messages.add_message(request, messages.ERROR, f'An account with that email address already exists. Please <a href="{reverse("login")}" class="nice-link">log in</a> or <a href="{reverse("password_reset")}" class="nice-link">reset your password</a>')
            return render(request, 'registration/register.html', {'form': form})

        user = authenticate(username=user.username, password=form.cleaned_data['password1'])
        login(request, user)

        customer = Customer.objects.create(
            user=user,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
        )

        user.customer.send_email_confirmation()

        messages.add_message(request, messages.SUCCESS, 'Thanks for registering, please check your email to confirm you address')
        return redirect('dashboard')

    return render(request, 'registration/register.html', {'form': form})


def view_form(request, pk):
    if request.user.is_anonymous:
        messages.add_message(request, messages.ERROR, 'You must be logged in to view formsasdflkj')
        # redirect to login page with query parameter next=this form
        return HttpResponseRedirect(f'/login/?next={request.path}')
    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'You do not have access to this form')
        return redirect_to_login(request)
    
    task = get_object_or_404(FormTask, pk=pk)

    if task not in customer.all_tasks:
        messages.add_message(request, messages.ERROR, 'You do not have access to this form')
        return redirect('dashboard')

    try:
        filled_form = FilledForm.objects.get(task=task, customer=customer)
    except FilledForm.DoesNotExist:
        filled_form = None

    if request.method == 'POST':
        if not request.user.is_verified():  # Use hasn't turned on MFA
            pass
        elif filled_form is None:
            filled_form = FilledForm.objects.create(task=task, customer=customer)
            filled_form.update_from_post(request.POST, request.FILES)
            if filled_form.finalised:
                messages.add_message(request, messages.SUCCESS, 'Form has been finalised')
                request.user.customer.send_form_finalised_email(filled_form)
                return redirect('dashboard')
            else:
                if task.due:
                    messages.add_message(request, messages.SUCCESS, f'Thanks for starting this task, please complete it by {task.due.strftime("%d %b.")}')
                else:
                    messages.add_message(request, messages.SUCCESS, 'Thanks for starting this task.')
                return redirect('view_form', pk=pk)
        elif filled_form.finalised:
            messages.add_message(request, messages.ERROR, 'This form has already been finalised')
            return redirect('dashboard')
        else:
            filled_form.update_from_post(request.POST, request.FILES)
            if filled_form.finalised:
                messages.add_message(request, messages.SUCCESS, 'Form has been finalised')
                request.user.customer.send_form_finalised_email(filled_form)
                return redirect('dashboard')
            else:
                messages.add_message(request, messages.SUCCESS, 'Form has been saved')
                return redirect('view_form', pk=pk)

    if filled_form:
        form_data = filled_form.structured_data
        if filled_form.finalised:
            messages.add_message(request, messages.INFO, 'This form has been finalised. If you need to make changes, please contact us.')
    else:
        form_data = task.form.structured_data

    if not request.user.is_verified():
        form_data['mfa_required'] = True
        messages.add_message(request, messages.ERROR, f'You must enable MFA before you can submit forms. To do so, go to <a href="{reverse("two_factor:setup")}">this page</a>.', extra_tags='safe')

    return render(request, 'customers/form.html', {
        'form_data': form_data,
        'task': task,
    })


def view_form_template(request, pk):
    if not request.user.is_staff:
        raise Http404

    form = get_object_or_404(Form, pk=pk)

    return render(request, 'customers/form.html', {
        'form_data': form.structured_data,
        'pdf_link': reverse('view_form_template_pdf', kwargs={'pk': pk}),
    })


def view_filled_form(request, user_pk, task_pk):
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, 'You do not have access to this form')
        return redirect('dashboard')

    filled_form = get_object_or_404(FilledForm, customer__pk=user_pk, task__pk=task_pk)

    form_data = filled_form.structured_data
    form_data['finalised'] = True

    return render(request, 'customers/form.html', {
        'form_data': form_data,
        'task': filled_form.task,
        'user_pk': user_pk,
    })


def activate(request, uuid, token):
    error_response = HttpResponse('Invalid token', status=403)

    try:
        customer = Customer.objects.get(uuid=uuid)
    except Customer.DoesNotExist:
        return error_response

    if customer.user != request.user:
        return error_response

    if customer.verification_token_expiry < timezone.now():
        return error_response

    if customer.verification_token != token:
        return error_response

    customer.user.is_active = True
    customer.email_confirmed = True
    customer.user.save()
    customer.save()

    messages.add_message(request, messages.SUCCESS, 'Your account has been activated')

    return redirect('dashboard')


def send_registration_email(request, uuid):
    if not request.user.is_staff or not request.user.is_superuser:
        raise Http404

    customer = get_object_or_404(Customer, uuid=uuid)
    customer.send_new_password_request()

    return redirect('admin:customers_customer_change', uuid)


def set_new_password(request, uuid, token):
    error_response = HttpResponse('Invalid token', status=403)

    try:
        customer = Customer.objects.get(uuid=uuid)
    except Customer.DoesNotExist:
        return error_response

    if customer.verification_token_expiry < timezone.now():
        return error_response

    if customer.verification_token != token:
        return error_response

    form = NewPasswordForm(request.POST or None, instance=customer.user)

    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.add_message(request, messages.SUCCESS, 'Your password has been set')
        customer.email_confirmed = True
        customer.save()
        return redirect_to_login(request)

    return render(request, 'registration/new_password_form.html', {'form': form})


@dataclass
class CustomerTasks:
    tasks: QuerySet[FormTask]
    outstanding_count: int
    count: int


def tasks_by_customer() -> Dict[Customer, CustomerTasks]:
    tasks_by_customer = {}

    for customer in Customer.objects.all():
        tasks_by_customer[customer] = customer.annotated_tasks

    return {
        customer: CustomerTasks(
            tasks=customer.annotate_due_dates(tasks),
            outstanding_count=tasks.filter(~Q(progress='complete')).count(),
            count=tasks.count()
        )
    for customer, tasks in tasks_by_customer.items()}


def dashboard(request):
    if request.user.is_staff:
        customer_tasks = tasks_by_customer()
        return render(request, 'customers/admin_dashboard.html', {
            'customer_tasks': customer_tasks,
        })
    elif request.user.is_anonymous:
        messages.add_message(request, messages.ERROR, 'You must be logged in to view your dashboard')
        return redirect_to_login(request)

    customer = request.user.customer
    tasks = {
        'incomplete': customer.annotate_due_dates(customer.annotated_incomplete_tasks.all()),
        'complete': customer.annotate_due_dates(customer.completed_tasks.all()),
    }

    return render(request, 'customers/dashboard.html', {
        'tasks': tasks,
    })


def confirm_email(request):
    if request.user.is_anonymous:
        messages.add_message(request, messages.ERROR, 'You must be logged in to confirm your email address')
        return redirect_to_login(request)

    if request.user.customer.email_confirmed:
        messages.add_message(request, messages.INFO, 'Your email address has already been confirmed')
        return redirect('dashboard')

    request.user.customer.send_email_confirmation()
    messages.add_message(request, messages.INFO, 'A confirmation email has been sent to your email address')

    return redirect('dashboard')


def form_file(request, user_id, form_id, filename):
    if request.user.is_anonymous or not(request.user.is_staff or request.user.is_superuser or request.user.customer.pk == user_id):
        return HttpResponseForbidden("You don't have permission to view this file")

    filled_form = get_object_or_404(FilledForm, customer__pk=user_id, pk=form_id)
    field = filled_form.fields.get(file__endswith=filename)

    return FileResponse(field.file, filename=filename)


def link_callback(uri, rel):
        """
        Convert HTML URIs to absolute system paths so xhtml2pdf can access those
        resources
        """
        print("Getting path for: ", uri)
        print(uri, rel)
        result = finders.find(uri)
        print("Result: ", result)
        if result:
                if not isinstance(result, (list, tuple)):
                        result = [result]
                result = list(os.path.realpath(path) for path in result)
                path=result[0]
        else:
                sUrl = settings.STATIC_URL        # Typically /static/
                sRoot = settings.STATIC_ROOT      # Typically /home/userX/project_static/
                mUrl = settings.MEDIA_URL         # Typically /media/
                mRoot = settings.MEDIA_ROOT       # Typically /home/userX/project_static/media/

                if uri.startswith(mUrl):
                        path = os.path.join(mRoot, uri.replace(mUrl, ""))
                elif uri.startswith(sUrl):
                        path = os.path.join(sRoot, uri.replace(sUrl, ""))
                else:
                        return uri

        # make sure that file exists
        if not os.path.isfile(path):
                raise Exception(
                        'media URI must start with %s or %s' % (sUrl, mUrl)
                )
        return path


def customer_view_form_pdf(request, pk):
    if request.user.is_anonymous:
        messages.add_message(request, messages.ERROR, 'You must be logged in to view forms')
        return redirect_to_login(request)

    try:
        customer = Customer.objects.get(user=request.user)
    except Customer.DoesNotExist:
        messages.add_message(request, messages.ERROR, 'You do not have access to this form')
        return redirect_to_login(request)

    return view_form_pdf(request, customer, pk)


def admin_view_form_pdf(request, customer_pk, task_pk):
    if not request.user.is_staff:
        messages.add_message(request, messages.ERROR, 'You do not have access to this form')
        return redirect('dashboard')

    customer = get_object_or_404(Customer, pk=customer_pk)

    return view_form_pdf(request, customer, task_pk)


def view_form_pdf(request, customer, task_pk):
    task = get_object_or_404(FormTask, pk=task_pk)

    if task not in customer.all_tasks:
        messages.add_message(request, messages.ERROR, 'You do not have access to this form')
        return redirect('dashboard')

    try:
        filled_form = FilledForm.objects.get(task=task, customer=customer)
    except FilledForm.DoesNotExist:
        filled_form = None

    if filled_form:
        form_data = filled_form.structured_data
    else:
        form_data = task.form.structured_data

    return FileResponse(gen_form_pdf(form_data), as_attachment=False, filename=f'{form_data["title"]}.pdf')


def view_form_template_pdf(request, pk):
    if not request.user.is_staff:
        raise Http404

    form = get_object_or_404(Form, pk=pk)

    return FileResponse(gen_form_pdf(form.structured_data), as_attachment=False, filename=f'{form.structured_data["title"]}_template.pdf')


def new_form_version(request, form_pk):
    if not request.user.is_staff:
        raise Http404

    form = get_object_or_404(Form, pk=form_pk)
    form.create_new_version()

    return redirect('admin:customers_form_change', form_pk)

