from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    contact = models.CharField(max_length=50, blank=True, null=True)
    manager = models.CharField(max_length=50, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)

    
    def __str__(self):
        return self.name