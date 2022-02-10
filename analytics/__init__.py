from .forms import SubscriptionForm


def analytics_context(request):
    return {'subscription_form': SubscriptionForm()}
