from django.db import models

class Organization(models.Model):
    organization_name = models.CharField(max_length=255)
    # address = models.TextField(blank=True)
    contact_email = models.EmailField(blank=True)
    created_by = models.IntegerField(unique=False) 
    created_at = models.DateTimeField(auto_now_add=True)

    
    class Meta:
        unique_together=('created_by','organization_name')

    def __str__(self):
        return self.organization_name


class Company(models.Model):
    organization = models.ForeignKey('Organization', on_delete=models.CASCADE, related_name='companies')
    name = models.CharField(max_length=255) 
    region = models.CharField(max_length=100, blank=True)
    country = models.CharField(max_length=100, blank=True)
    sub_domain = models.CharField(max_length=100, blank=True)
    contact_email = models.EmailField(blank=True)
    created_by = models.IntegerField() 
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('organization', 'name')

    def __str__(self):
        return f"{self.name} ({self.organization.organization_name})"

class Entity(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='entities')
    name = models.CharField(max_length=255)  # Entity Name
    state = models.CharField(max_length=100, blank=True)
    region = models.CharField(max_length=100, blank=True)
    zone = models.CharField(max_length=100, blank=True)
    created_by = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('company', 'name')

    def __str__(self):
        return f"{self.name} ({self.company.name})"