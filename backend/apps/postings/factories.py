import factory

from apps.accounts.factories import EmployerFactory

from .models import JobPosting


class JobPostingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JobPosting
        skip_postgeneration_save = True

    submitter = factory.SubFactory(EmployerFactory)
    company_name = factory.Sequence(lambda n: f"Acme Co {n}")
    title = "Software Engineer"
    description = "We are looking for a software engineer to join our team."
    location = "Remote"
    employment_type = JobPosting.EmploymentType.FULL_TIME

    salary_min = 80_000
    salary_max = 120_000
    currency = "USD"
    salary_disclosed = True

    apply_url = "https://example.com/apply"
    contact_email = "hiring@example.com"

    status = JobPosting.Status.DRAFT

    @factory.post_generation
    def set_content_hash(self, create, extracted, **kwargs):
        self.content_hash = self.compute_content_hash()
        if create:
            self.save(update_fields=["content_hash"])
