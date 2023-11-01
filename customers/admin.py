from django.contrib import admin
from django.utils.html import format_html
from django.utils import timezone
from django.urls import reverse, resolve
from django.contrib import messages

import nested_admin
from hijack.contrib.admin import HijackUserAdminMixin

from .models import *


class NoChangePermissionMixin:
    message_prefix = "You cannot edit this form because it is in use by "
    message_suffix = "."

    def pretty_join(self, items):
        items_list = list(map(str, items))
        if len(items_list) == 0:
            return ''
        elif len(items_list) == 1:
            return items_list[0]
        elif len(items_list) == 2:
            return ' and '.join(items_list)
        return ', '.join(items_list[:-1]) + ', and ' + items_list[-1]

    def extract_users_from_message(self, message):
        users_list = message[len(self.message_prefix):-len(self.message_suffix)]
        return set(users_list.replace(', and ', ', ').replace(' and ', ', ').split(', '))

    def notify_cant_change(self, request, affected_users):
        current_messages = messages.get_messages(request)
        previous_users = set()
        for message in current_messages:
            if message.level == messages.ERROR and message.message.startswith(self.message_prefix) and message.message.endswith(self.message_suffix):
                previous_users.update(self.extract_users_from_message(message.message))

        for message in current_messages:
            # Remove previous messages
            if message.level == messages.ERROR and message.message.startswith(self.message_prefix) and message.message.endswith(self.message_suffix):
                message.extra_tags = 'hidden'

        all_affected_users = previous_users.union(map(str, affected_users))
        messages.add_message(request, messages.ERROR, self.message_prefix + self.pretty_join(all_affected_users) + self.message_suffix)

    def notify_outdated(self, request, next_version=None):
        outdated_message = "This form is outdated and cannot be edited."
        current_messages = messages.get_messages(request)
        for message in current_messages:
            # Remove previous messages
            if message.level == messages.ERROR and message.message.startswith(outdated_message):
                message.extra_tags = 'hidden'

        view_next_message = " View the new version <a href={}>here</a>".format(next_version) if next_version else ""

        messages.add_message(request, messages.ERROR, format_html(outdated_message + view_next_message))

    class Media:
        css = {
            'all': ('css/hidden_messages.css',)
        }

    def is_outdated(self, obj):
        if obj:
            try:
                return obj.form.outdated
            except AttributeError:
                try:
                    return obj.outdated
                except AttributeError:
                    return False
        return False

    def has_change_permission(self, request, obj=None):
        has_affected_customers = obj and obj.affected_customers
        if has_affected_customers:
            affected_users = obj.affected_customers
            self.notify_cant_change(request, affected_users)

        is_outdated = self.is_outdated(obj)
        if is_outdated:
            if hasattr(obj, 'next_version'):
                self.notify_outdated(request, reverse('admin:customers_form_change', args=[obj.next_version.pk]))
            else:
                self.notify_outdated(request)

        if obj:
            return not has_affected_customers and not is_outdated

        return super().has_change_permission(request, obj)

    def has_delete_permission(self, request, obj=None):
        if obj and obj.affected_customers or self.is_outdated(obj):
            return False
        return super().has_delete_permission(request, obj)

    def get_readonly_fields(self, request, obj=None):
        if obj and obj.affected_customers or self.is_outdated(obj):
            return [f.name for f in self.model._meta.fields]
        return self.readonly_fields


class InlineNoChangePermissionMixin(NoChangePermissionMixin):
    def has_add_permission(self, request, obj=None):
        resolution = resolve(request.path_info)
        if resolution.url_name != 'customers_form_change':
            return super().has_add_permission(request, obj)

        form_id = resolution.kwargs['object_id']
        form = Form.objects.get(pk=form_id)

        if form.affected_customers:
            return False

        return super().has_add_permission(request, obj)


class FormFieldOptionInline(InlineNoChangePermissionMixin, nested_admin.NestedTabularInline):
    model = FormFieldOption
    extra = 0
    classes = ('collapse',)

    def outdated(self, obj):
        return obj.section.form.outdated


class FormFieldInline(InlineNoChangePermissionMixin, nested_admin.NestedTabularInline):
    model = FormField
    extra = 0
    classes = ('collapse',)
    inlines = [FormFieldOptionInline]

    def outdated(self, obj):
        return obj.form.outdated


class FormSectionInline(InlineNoChangePermissionMixin, nested_admin.NestedStackedInline):
    model = FormSection
    extra = 0
    inlines = [FormFieldInline]
    classes = ('collapse',)

    def outdated(self, obj):
        return obj.outdated


class FormAdmin(NoChangePermissionMixin, nested_admin.NestedModelAdmin):
    list_display = ('title', 'version', 'short_description', 'finalised', 'new_version')
    inlines = [FormSectionInline]
    show_change_link = True
    readonly_fields = ('version', 'outdated', 'previous_version')

    def new_version(self, obj):
        if obj.outdated:
            return 'Outdated'
        url = reverse('new_form_version', args=[obj.pk])
        return format_html('<a class="button" href="{}">New Version</a>', url)

    def outdated(self, obj):
        return obj.outdated


class FormTaskGroupInline(admin.TabularInline):
    model = FormTask
    extra = 0


class FormGroupAdmin(admin.ModelAdmin):
    inlines = [FormTaskGroupInline]


class FormTaskCustomerInline(admin.TabularInline):
    model = FormTask
    extra = 0
    exclude = ('group',)


class CustomerForm(forms.ModelForm):
    def clean_email(self):
        print('cleaning email: ', self.cleaned_data['email'])
        if Customer.objects.filter(email=self.cleaned_data['email']).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Email address already in use')
        return self.cleaned_data['email']


class FormGroupAssignmentInline(admin.TabularInline):
    model = FormGroupAssignment
    extra = 0


class CustomerAdmin(HijackUserAdminMixin, admin.ModelAdmin):
    form = CustomerForm
    list_display = ('email', 'full_name', 'password_set', 'run_send_registration_email')
    readonly_fields = ('email_confirmed', 'uuid', 'stripe_customer_id', 'added')
    inlines = [FormTaskCustomerInline, FormGroupAssignmentInline]

    def password_set(self, obj):
        return obj.user.has_usable_password()

    def run_send_registration_email(self, obj):
        if obj.user.has_usable_password():
            return 'Password set'
        else:
            url = reverse('send_registration_email', args=[obj.pk])
            return format_html('<a class="button" href="{}">Send Registration Email</a>', url)

    run_send_registration_email.short_description = 'Send Registration Email'

    @admin.action(description='Send registration email')
    def send_registration_email(self, request, queryset):
        for customer in queryset:
            customer.send_email_confirmation()

    actions = ['send_registration_email']

    def get_hijack_user(self, obj):
        return obj.user

    def hijack_button(self, request, obj):
        """
        Render hijack button.

        Should the user only be a related object we include the username in the button
        to ensure deliberate action. However, the name is omitted in the user admin,
        as the table layout suggests that the button targets the current user.
        """
        user = self.get_hijack_user(obj)
        return render_to_string(
            "hijack/contrib/admin/button.html",
            {
                "request": request,
                "another_user": user,
                "username": obj.full_name,
                "is_user_admin": self.model == type(user),
                "next": self.get_hijack_success_url(request, obj),
            },
            request=request,
        )


class FormTaskAdmin(admin.ModelAdmin):
    list_display = ('form', 'due', 'group', 'customer')
    #readonly_fields = ('customer', 'form', 'group', 'status', 'completed')
    #list_filter = ('status', 'completed')

# Register your models here.
admin.site.register(Customer, CustomerAdmin)
admin.site.register(Form, FormAdmin)
admin.site.register(FormGroup, FormGroupAdmin)
admin.site.register(FormTask, FormTaskAdmin)
