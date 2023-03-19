from django.db import models
from django.db.models import Q, Case, When, Value, CharField, F
from django.conf import settings
from django.contrib.auth.models import User
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
from django.utils.html import strip_tags
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives
from django import forms
from django.urls import reverse

from django_countries.fields import CountryField
from django_countries import countries

import uuid as uuid_lib
import stripe
import math
from re import sub
import os

from main.models import RichTextWithPlugins
from .pdf import gen_form_pdf

stripe.api_key = settings.STRIPE_SECRET_KEY

def pretty_concat(strings):
    string_list = [str(s) for s in strings]
    if len(string_list) == 0:
        return ''
    elif len(string_list) == 1:
        return string_list[0]
    elif len(string_list) == 2:
        return ' and '.join(string_list)
    else:
        return ', '.join(string_list[:-1]) + ', and ' + string_list[-1]

# Create your models here.
class Form(models.Model):
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True, primary_key=True)
    title = models.CharField(max_length=200)
    short_description = models.CharField(max_length=500, null=True, blank=True)
    instructions = RichTextWithPlugins(config_name='default', null=True, blank=True)
    signature_instructions = models.TextField(null=True, blank=True)

    def __str__(self):
        return self.title

    @property
    def all_fields(self):
        return FormField.objects.filter(section__form=self).order_by('section__order', 'order')

    @property
    def affected_customers(self):
        return Customer.objects.filter(completed_forms__task__form=self).distinct()
        #return FilledForm.objects.filter(task__form=self)

    def check_no_affected_customers(self):
        filled_forms = FilledForm.objects.filter(task__form=self)
        if filled_forms.exists():
            affected_customers = pretty_concat(f.customer for f in filled_forms)
            raise ValidationError(f'This form is already being filled out by {affected_customers}. You cannot edit it.')

    def clean(self):
        self.check_no_affected_customers()

    def delete(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().save(*args, **kwargs)

    @property
    def structured_data(self):
        return {
            'title': self.title,
            'short_description': self.short_description,
            'instructions': self.instructions,
            'signature_instructions': self.signature_instructions,
            'countries': [{
                'code': country[0],
                'name': country[1]
            } for country in countries],
            'sections': [
                {
                    'title': section.title,
                    'instructions': section.instructions,
                    'fields': [
                        {
                            'title': field.title,
                            'name': f'{section.title}-{field.title}',
                            'instructions': field.instructions,
                            'required': field.required,
                            'type': field.field_type,
                            'options': [{
                                'value': option.value,
                            } for option in field.options.all()],
                        }
                    for field in section.fields.all()]
                }
            for section in self.sections.all()]
        }

    def field_from_name(self, name):
        section = name.split('-')[0]
        field = name.split('-')[1]
        return FormField.objects.get(section__form=self, section__title=section, title=field)


class FormSection(models.Model):
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    instructions = RichTextWithPlugins(config_name='default', null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    @property
    def affected_customers(self):
        if self.pk:
            return Customer.objects.filter(completed_forms__task__form=self.form).distinct()
        #return FilledForm.objects.filter(task__form=self.form)

    def check_no_affected_customers(self):
        filled_forms = FilledForm.objects.filter(task__form=self.form)
        if filled_forms.exists():
            affected_customers = pretty_concat(f.customer for f in filled_forms)
            raise ValidationError(f'This form is already being filled out by {affected_customers}. You cannot edit it.')

    def clean(self):
        self.check_no_affected_customers()

    def delete(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Section'
        verbose_name_plural = 'Sections'
        ordering = ['order']
        unique_together = ('form', 'title')


class FormField(models.Model):
    FIELD_TYPES = (
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('select', 'Select'),
        ('checkbox', 'Checkbox'),
        ('radio', 'Radio'),
        ('file', 'File'),
        ('countries', 'Countries'),
        ('date', 'Date'),
        ('number', 'Number'),
        ('email', 'Email'),
        ('url', 'URL'),
        ('tel', 'Telephone'),
    )

    section = models.ForeignKey(FormSection, on_delete=models.CASCADE, related_name='fields')
    title = models.CharField(max_length=200)
    instructions = models.CharField(max_length=500, blank=True, null=True)
    required = models.BooleanField(default=True)
    field_type = models.CharField(max_length=200, choices=FIELD_TYPES, default='text')
    order = models.PositiveIntegerField(default=0)

    @property
    def affected_customers(self):
        if self.pk:
            return Customer.objects.filter(completed_forms__task__form=self.section.form).distinct()
        #return FilledForm.objects.filter(task__form=self.section.form)

    def check_no_affected_customers(self):
        filled_forms = FilledForm.objects.filter(task__form=self.section.form)
        if filled_forms.exists():
            affected_customers = pretty_concat(f.customer for f in filled_forms)
            raise ValidationError(f'This form is already being filled out by {affected_customers}. You cannot edit it.')

    def clean(self):
        self.check_no_affected_customers()

    def delete(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Field'
        verbose_name_plural = 'Fields'
        unique_together = ('section', 'title')
        ordering = ['order']


class FormFieldOption(models.Model):
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name='options')
    value = models.CharField(max_length=200)
    order = models.PositiveIntegerField(default=0)

    @property
    def affected_customers(self):
        return Customer.objects.filter(completed_forms__task__form=self.field.section.form).distinct()
        #return FilledForm.objects.filter(task__form=self.field.section.form)

    def check_no_affected_customers(self):
        filled_forms = FilledForm.objects.filter(task__form=self.field.section.form)
        if filled_forms.exists():
            affected_customers = pretty_concat(f.customer for f in filled_forms)
            raise ValidationError(f'This form is already being filled out by {affected_customers}. You cannot edit it.')

    def clean(self):
        self.check_no_affected_customers()

    def delete(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().delete(*args, **kwargs)

    def save(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'Option'
        verbose_name_plural = 'Options'
        ordering = ['order']
        unique_together = ('field', 'value')


class FormGroup(models.Model):
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True, primary_key=True)
    title = models.CharField(max_length=200)

    def __str__(self):
        return self.title

def pretty_timedelta(td):
    if td.days > 365:
        years = td.days // 365
        days = td.days % 365
        if days > 0:
            return f'{years} year{"s" if years > 1 else ""}, {days} day{"s" if days > 1 else ""}'
        else:
            return f'{years} year{"s" if years > 1 else ""}'
    elif td.days > 365//12:
        months = math.floor(td.days // (365.0//12))
        print("months: ", months)
        weeks = math.floor(td.days % (365//12) // 7)
        if weeks > 0:
            return f'{months} month{"s" if months > 1 else ""}, {weeks} week{"s" if weeks > 1 else ""}'
        else:
            return f'{months} month{"s" if months > 1 else ""}'
    elif td.days > 7:
        weeks = td.days // 7
        days = td.days % 7
        if days > 0:
            return f'{weeks} week{"s" if weeks > 1 else ""}, {days} day{"s" if days > 1 else ""}'
        else:
            return f'{weeks} week{"s" if weeks > 1 else ""}'
    elif td.days > 0:
        days = td.days
        hours = td.seconds // 3600
        if hours > 0:
            return f'{days} day{"s" if days > 1 else ""}, {hours} hour{"s" if hours > 1 else ""}'
        else:
            return f'{days} day{"s" if days > 1 else ""}'
    elif td.seconds > 3600:
        hours = td.seconds // 3600
        minutes = td.seconds % 3600 // 60
        if minutes > 0:
            return f'{hours} hour{"s" if hours > 1 else ""}, {minutes} minute{"s" if minutes > 1 else ""}'
        else:
            return f'{hours} hour{"s" if hours > 1 else ""}'
    elif td.seconds > 60:
        minutes = td.seconds // 60
        seconds = td.seconds % 60
        if seconds > 0:
            return f'{minutes} minute{"s" if minutes > 1 else ""}, {seconds} second{"s" if seconds > 1 else ""}'
        else:
            return f'{minutes} minute{"s" if minutes > 1 else ""}'
    else:
        return 'Now'


class FormTask(models.Model):
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True, primary_key=True)
    form = models.ForeignKey(Form, on_delete=models.CASCADE, related_name='assignments')
    due = models.DateTimeField(blank=True, null=True)
    group = models.ForeignKey(FormGroup, on_delete=models.CASCADE, related_name='tasks', blank=True, null=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='tasks', blank=True, null=True)

    @property
    def due_in(self):
        if self.due:
            return self.due - timezone.now()
        else:
            return None

    @property
    def pretty_due_in(self):
        if self.due:
            due_in = self.due_in
            if due_in.days > 0 or due_in.days == 0 and due_in.seconds > 60:
                return f'Due in {pretty_timedelta(due_in)}'
            elif abs(due_in.seconds < 60):
                return 'Due now'
            else:
                return f'Overdue by {pretty_timedelta(due_in * -1)}'


    def __str__(self):
        if self.customer:
            return f'{self.form.title} - {self.customer.full_name}'
        elif self.group:
            return f'{self.form.title} - {self.group.title}'
        else:
            return f'{self.form.title} - Unassigned'

    def check_no_affected_customers(self):
        # Ensure no customer has already started filling in this form if changing anything other than due date
        filled_forms = FilledForm.objects.filter(task=self)
        if filled_forms.exists():
            affected_customers = ', '.join([f'{filled_form.customer}' for filled_form in filled_forms]).replace(', ', ' and ', 1)
            validation_error = lambda message: ValidationError(f'{message} as {affected_customers} {"has" if len(filled_forms) == 1 else "have"} already started filling in this form')
            if self.customer != self.__class__.objects.get(pk=self.pk).customer:
                raise validation_error('Cannot change customer')
            if self.group != self.__class__.objects.get(pk=self.pk).group:
                raise validation_error('Cannot change group')
            if self.form != self.__class__.objects.get(pk=self.pk).form:
                raise validation_error('Cannot change form')

    def clean(self):
        if self.customer and self.group:
            raise ValidationError('Cannot assign to both a customer and a group')
        if not self.customer and not self.group:
            raise ValidationError('Must assign to either a customer or a group')
        self.check_no_affected_customers()

    def save(self, *args, **kwargs):
        self.check_no_affected_customers()
        super().save(*args, **kwargs)

    class Meta:
        unique_together = ('form', 'group')
        ordering = ['due']


class FilledForm(models.Model):
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True, primary_key=True)
    customer = models.ForeignKey('Customer', on_delete=models.CASCADE, related_name='completed_forms')
    task = models.ForeignKey(FormTask, on_delete=models.CASCADE, related_name='completed_forms')
    finalised = models.BooleanField(default=False)

    @property
    def structured_data(self):
        # Same as structured_data in Form model, but with values for fields
        return {
            'title': self.task.form.title,
            'short_description': self.task.form.short_description,
            'instructions': self.task.form.instructions,
            'finalised': self.finalised,
            'signature_instructions': self.task.form.signature_instructions,
            'countries': [{
                'code': country[0],
                'name': country[1]
            } for country in countries],
            'sections': [{
                'title': section.title,
                'instructions': section.instructions,
                'fields': [{
                        'title': field.title,
                        'name': f'{section.title}-{field.title}',
                        'instructions': field.instructions,
                        'required': field.required,
                        'type': field.field_type,
                        'options': [{
                            'value': option.value,
                        } for option in field.options.all()],
                        'value': self.fields.filter(field=field).first().value if self.fields.filter(field=field).first() else None,
                        'file': self.fields.filter(field=field).first().file if self.fields.filter(field=field).first() else None,
                        'filename': self.fields.filter(field=field).first().filename if self.fields.filter(field=field).first() else None,
                } for field in section.fields.all()]
            } for section in self.task.form.sections.all()]
        }

    def update_from_post(self, post, files):
        if self.finalised:
            return

        for field in self.task.form.all_fields:
            field_name = f'{field.section.title}-{field.title}'
            print(field_name)
            if field.field_type == 'file':
                print("File field")
                print("files: ", files)
                print("field_name: ", field_name)
                if field_name in files:
                    print("value: ", files.get(field_name))
                    try:
                        completed_field = self.fields.get(field=field)
                        print("Old file field path: ", completed_field.file.path)
                        completed_field.file = files.get(field_name)
                        print("File field path: ", completed_field.file.path)
                        completed_field.save()
                    except FilledFormField.DoesNotExist:
                        completed_field = FilledFormField.objects.create(form=self, field=field, file=files.get(field_name))
                        print("File field path: ", completed_field.file.path)
                    completed_field.save()
            else:
                if field_name in post:
                    try:
                        completed_field = self.fields.get(field=field)
                        completed_field.value = post.get(field_name)
                        completed_field.save()
                    except FilledFormField.DoesNotExist:
                        FilledFormField.objects.create(form=self, field=field, value=post.get(field_name))
        if 'finalise' in post and post.get('finalise') == 'true':
            self.finalised = True
            self.save()


    class Meta:
        unique_together = ('customer', 'task')


class FilledFormField(models.Model):
    def upload_location(self, filename):
        print("original filename: ", filename)
        return f'form_files/{self.form.customer.uuid}/{self.form.uuid}/{filename}'

    form = models.ForeignKey(FilledForm, on_delete=models.CASCADE, related_name='fields')
    field = models.ForeignKey(FormField, on_delete=models.CASCADE, related_name='completed_fields')
    value = models.CharField(max_length=500, blank=True, null=True)
    file = models.FileField(upload_to=upload_location, blank=True, null=True, max_length=511)

    @property
    def filename(self):
        if self.file:
            print(os.path.basename(self.file.name))
            return os.path.basename(self.file.name)
        else:
            return None

    class Meta:
        unique_together = ('form', 'field')


class Customer(models.Model):
    uuid = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True, verbose_name='Customer ID', primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE, blank=True, null=True)
    email = models.EmailField(max_length=254, blank=True, null=True, verbose_name='Email')
    first_name = models.CharField(max_length=30, blank=True, null=True, verbose_name='First name')
    last_name = models.CharField(max_length=30, blank=True, null=True, verbose_name='Last name')
    added = models.DateTimeField(auto_now_add=True)
    stripe_customer_id = models.CharField(max_length=500, blank=True, null=True, verbose_name='Stripe customer ID')
    assigned_formgroups = models.ManyToManyField('FormGroup', blank=True, related_name='assigned_customers')
    email_confirmed = models.BooleanField(default=False)
    verification_token = models.UUIDField(default=uuid_lib.uuid4, editable=False, unique=True)
    verification_token_expiry = models.DateTimeField(blank=True, null=True)

    @property
    def full_name(self):
        return ' '.join([self.first_name or '', self.last_name or ''])

    @property
    def display_name(self):
        return self.first_name or self.email

    def save(self, *args, **kwargs):
        print("saving customer")
        if Customer.objects.filter(email=self.email).exclude(uuid=self.uuid).exists():
            raise ValidationError('Customer with this email already exists')

        if not self.stripe_customer_id:
            stripe_id = stripe.Customer.create(
                name=self.full_name,
                email=self.email
            )
            print("Stripe ID: ", stripe_id)
            self.stripe_customer_id = stripe_id['id']

        if not self.user:
            # Create a user with the same email address
            self.user = User.objects.create_user(username=self.email, email=self.email, customer=self, first_name=self.first_name, last_name=self.last_name)
        elif self.user.email != self.email or self.user.first_name != self.first_name or self.user.last_name != self.last_name or self.user.username != self.email:
            self.user.email = self.email
            self.user.username = self.email
            self.user.first_name = self.first_name
            self.user.last_name = self.last_name
            self.user.save()

        
        # Invalidate email confirmation
        try:
            old_customer = Customer.objects.get(pk=self.pk)
            super(Customer, self).save(*args, **kwargs)
            if old_customer.email != self.email and self.user.has_usable_password():
                self.email_confirmed = False
                self.send_email_confirmation()
        except Customer.DoesNotExist:
            print("New customer")
            super(Customer, self).save(*args, **kwargs)


    @property
    def all_tasks(self):
        # Combine all forms from assigned formgroups and forms assigned directly to customer
        return FormTask.objects.filter(
            Q(group__in=self.assigned_formgroups.all()) | Q(customer=self)
        ).distinct()

    @property
    def annotated_tasks(self):
        tasks = self.all_tasks.annotate(
            progress=Case(
                # Customer has filled form and it is finalised
                When(completed_forms__finalised=True, completed_forms__customer=self, then=Value('complete')),
                # Customer has filled form and it is not finalised
                When(completed_forms__finalised=False, completed_forms__customer=self, then=Value('in_progress')),
                # Customer has no filled form
                When(completed_forms__customer__in=Customer.objects.exclude(pk=self.pk), then=Value(None)),
                default=Value('unstarted'),
                output_field=CharField(),
            )
        )

        return tasks

    @property
    def completed_tasks(self):
        return self.annotated_tasks.filter(progress='complete')

    @property
    def in_progress_tasks(self):
        return self.annotated_tasks.filter(progress='in_progress')

    @property
    def unstarted_tasks(self):
        return self.annotated_tasks.filter(progress='unstarted')

    @property
    def annotated_incomplete_tasks(self):
        return self.annotated_tasks.filter(~Q(progress='complete'))

    def __str__(self):
        if self.full_name and self.email:
            return f'{self.full_name} ({self.email})'
        elif self.full_name:
            return self.full_name
        elif self.email:
            return self.email
        else:
            return 'Customer'

    def send_email_confirmation(self):
        print("Sending email confirmation")
        self.verification_token = uuid_lib.uuid4()
        self.verification_token_expiry = timezone.now() + timezone.timedelta(hours=24)
        self.save()

        message = render_to_string('registration/activation_email.html', {
            'user': self,
            'uuid': self.uuid,
            'token': self.verification_token,
        })
        plain_message = strip_tags(message)

        print("Sending email to: ", self.user.email)
        self.user.email_user('Confirm your email address to activate your account', plain_message, 'noreply@saigatours.com', html_message=message)
        print("Sent email")

    def send_new_password_request(self):
        self.verification_token = uuid_lib.uuid4()
        self.verification_token_expiry = timezone.now() + timezone.timedelta(hours=24)
        self.save()

        message = render_to_string('registration/new_password_email.html', {
            'user': self,
            'uuid': self.uuid,
            'token': self.verification_token,
        })
        plain_message = strip_tags(message)

        self.user.email_user('Set your password to activate your account', plain_message, 'noreply@saigatours.com', html_message=message)

    def send_form_finalised_email(self, form: FilledForm):
        print("Sending form finalised email")

        if not form.customer.email_confirmed:
            pass
            #return

        form_title = form.task.form.title
        message = render_to_string('customers/form_finalised_email.html', {
            'user': self,
            'form': form,
            'title': form_title,
            'task_pk': form.task.pk,
        })
        plain_message = strip_tags(message)

        subject = f'Thank you for completing {form_title}'
        from_email = 'noreply@saigatours.com'
        to_email = self.user.email

        form_pdf = gen_form_pdf(form.structured_data).getvalue()

        email = EmailMultiAlternatives(
            subject,
            plain_message,
            from_email,
            [to_email],
        )

        email.attach_alternative(message, "text/html")
        email.attach('form.pdf', form_pdf, 'application/pdf')

        email.send()

        admin_message = render_to_string('customers/form_finalised_email_admin.html', {
            'user': self,
            'form': form,
            'title': form_title,
            'task_pk': form.task.pk,
        })

        admin_email = EmailMultiAlternatives(
            f'Form completed by {self.full_name} - {form_title}',
            strip_tags(admin_message),
            from_email,
            ['tours@saigatours.com'],
        )

        admin_email.attach_alternative(admin_message, "text/html")
        admin_email.attach('form.pdf', form_pdf, 'application/pdf')

        admin_email.send()

        #self.user.email_user(
            #f'Thank you for completing {form_title}',
            #plain_message,
            #'noreply@saigatours.com',
            #html_message=message
        #)


#@receiver(post_save, sender=User)
def create_user_customer(sender, instance, created, **kwargs):
    print("post-save User")
    if instance.is_staff or instance.is_superuser:
        return
    if not Customer.objects.filter(user=instance).exists():
        print('Creating customer')
        Customer.objects.create(user=instance, email=instance.email, first_name=instance.first_name, last_name=instance.last_name)
    elif instance.email != instance.customer.email or instance.username != instance.customer.email:
        print('Updating user email & username')
        instance.email = instance.customer.email
        instance.username = instance.customer.email
        instance.save()


#@receiver(pre_save, sender=User)
def invalidate_email_confirmation(sender, instance, **kwargs):
    print("pre-save User")
    if instance.is_staff or instance.is_superuser:
        return
    if instance.pk:
        old = User.objects.get(pk=instance.pk)
        if old.email != instance.email:
            instance.customer.email_confirmed = False

