from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.accounts.models import User
from apps.policies.models import Policy
from apps.postings.models import JobPosting


class Command(BaseCommand):
    help = (
        "Seed a default policy, demo users, and a handful of job postings for local/manual testing."
    )

    def handle(self, *args, **options):
        policy = self._seed_policy()
        employer, moderator, admin = self._seed_users()
        postings = self._seed_postings(employer)

        self.stdout.write(self.style.SUCCESS(f"Active policy: v{policy.version}"))
        self.stdout.write(
            self.style.SUCCESS(
                f"Users: {employer.username} (employer), {moderator.username} (moderator), "
                f"{admin.username} (admin) — password for all: password123!"
            )
        )
        for posting in postings:
            self.stdout.write(f"  - [{posting.status}] {posting.title} @ {posting.company_name}")

    def _seed_policy(self) -> Policy:
        policy = Policy.objects.get_active()
        if policy is not None:
            return policy
        return Policy.objects.create_version(notes="Seeded default policy.")

    def _seed_users(self) -> tuple[User, User, User]:
        employer, _ = User.objects.get_or_create(
            username="demo_employer",
            defaults={"email": "employer@example.com", "role": User.Role.EMPLOYER},
        )
        moderator, _ = User.objects.get_or_create(
            username="demo_moderator",
            defaults={
                "email": "moderator@example.com",
                "role": User.Role.MODERATOR,
                "is_staff": True,
            },
        )
        admin, created = User.objects.get_or_create(
            username="demo_admin",
            defaults={
                "email": "admin@example.com",
                "role": User.Role.ADMIN,
                "is_staff": True,
                "is_superuser": True,
            },
        )
        # Always (re-)set the password rather than guarding on
        # has_usable_password(): a user created via get_or_create()
        # without going through create_user() ends up with an empty
        # password field, which has_usable_password() treats as usable
        # (it only special-cases Django's own "!"-prefixed unusable
        # marker) — so the guard silently never fired and demo_employer's
        # password was never actually set. Re-setting every run is
        # idempotent and costs nothing.
        for user in (employer, moderator, admin):
            user.set_password("password123!")
            user.save(update_fields=["password"])
        return employer, moderator, admin

    def _seed_postings(self, employer: User) -> list[JobPosting]:
        specs = [
            dict(
                title="Backend Engineer",
                company_name="Northwind Traders",
                description=(
                    "We're hiring a backend engineer to help build our payments platform. "
                    "5+ years of Python experience preferred. Fully remote, flexible hours."
                ),
                location="Remote",
                salary_min=110_000,
                salary_max=150_000,
                salary_disclosed=True,
                status=JobPosting.Status.AUTO_APPROVED,
            ),
            dict(
                title="Data Entry Clerk — Work From Home",
                company_name="QuickCash Global",
                description=(
                    "Earn money from home! To secure your position, please pay a fully "
                    "refundable deposit of $75 to cover your starter kit before you start. "
                    "Contact us on WhatsApp for details."
                ),
                location="Remote",
                salary_disclosed=False,
                status=JobPosting.Status.AUTO_REJECTED,
            ),
            dict(
                title="Independent Sales Representative",
                company_name="Bright Horizons Marketing",
                description=(
                    "Be your own boss! Build your team and earn unlimited earning potential "
                    "through our downline commission structure. No experience necessary."
                ),
                location="Austin, TX",
                salary_disclosed=False,
                status=JobPosting.Status.IN_REVIEW,
            ),
            dict(
                title="Junior Product Designer",
                company_name="Northwind Traders",
                description="Draft posting, not yet submitted for review.",
                location="New York, NY",
                salary_disclosed=False,
                status=JobPosting.Status.DRAFT,
            ),
        ]

        postings = []
        for spec in specs:
            posting, created = JobPosting.objects.get_or_create(
                title=spec["title"],
                company_name=spec["company_name"],
                defaults={
                    "submitter": employer,
                    **{k: v for k, v in spec.items() if k not in ("title", "company_name")},
                },
            )
            if created:
                posting.content_hash = posting.compute_content_hash()
                if posting.status != JobPosting.Status.DRAFT:
                    posting.submitted_at = timezone.now()
                posting.save()
            postings.append(posting)
        return postings
