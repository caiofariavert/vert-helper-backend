from django.core.management.base import BaseCommand

from apps.helper.schedules import create_global_schedules


class Command(BaseCommand):
    help = "Cria ou reativa os schedules globais do Helper no Django-Q2."

    def handle(self, *args, **options):
        self.stdout.write("Configurando schedules globais do Helper...")
        create_global_schedules()
        self.stdout.write(self.style.SUCCESS("Schedules globais do Helper configurados."))
