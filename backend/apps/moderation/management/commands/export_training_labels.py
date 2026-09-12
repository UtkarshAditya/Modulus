from django.core.management.base import BaseCommand

from apps.moderation.exports import EXPORT_PATH, write_export


class Command(BaseCommand):
    help = "Export moderator decisions into ml/data/exported_labels.jsonl for training."

    def handle(self, *args, **options):
        count = write_export()
        self.stdout.write(
            self.style.SUCCESS(f"Exported {count} labelled examples to {EXPORT_PATH}")
        )
