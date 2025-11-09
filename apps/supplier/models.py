from django.db import models

class Supplier(models.Model):
    name = models.CharField(max_length=100, unique=True)
    contact = models.CharField(max_length=20)
    manager = models.CharField(max_length=50)
    email = models.EmailField()
    address = models.CharField(max_length=255)
    
    def __str__(self):
        return self.name