from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.inventory.utils.monthly_snapshot import rollover_variant_status


class Command(BaseCommand):
    help = "전달 ProductVariantStatus를 기준으로 다음 달 상품 목록 생성"

    def handle(self, *args, **options):
        today = timezone.now().date()

        # 전달 기준
        if today.month == 1:
            year, month = today.year - 1, 12
        else:
            year, month = today.year, today.month - 1

        result = rollover_variant_status(year, month)

        self.stdout.write(
            self.style.SUCCESS(
                f"[OK] {result['year']}-{result['month']} "
                f"{result['created_count']} rows created"
            )
        )
