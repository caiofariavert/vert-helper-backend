from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string


def send_template_mailer(subject, template, mails, context):

    email_html_message = render_to_string(template, context)

    send_mailer(subject, email_html_message, mails)


def send_mailer(subject, message, mails):

    msg = EmailMultiAlternatives(
        # title:
        subject,
        # message:
        "",
        # from:
        settings.EMAIL_FROM,
        # to:
        mails,
    )

    msg.attach_alternative(message, "text/html")
    msg.send()
