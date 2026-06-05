from django.db import models
from django.db.models import Q
from core.tenancy import get_current_tenant

class TenantQuerySet(models.QuerySet):
    def for_tenant(self, tenant):
        if self.model.__name__ == 'Company':
            return self.filter(Q(pk=tenant.pk) | Q(parent_company=tenant))
        elif hasattr(self.model, 'company'):
            return self.filter(Q(company=tenant) | Q(company__parent_company=tenant))
        elif hasattr(self.model, 'machine'):
            return self.filter(Q(machine__company=tenant) | Q(machine__company__parent_company=tenant))
        elif hasattr(self.model, 'ticket'):
            return self.filter(Q(ticket__company=tenant) | Q(ticket__company__parent_company=tenant))
        return self

class TenantManager(models.Manager):
    def get_queryset(self):
        queryset = TenantQuerySet(self.model, using=self._db)
        tenant = get_current_tenant()
        if tenant:
            return queryset.for_tenant(tenant)
        return queryset
