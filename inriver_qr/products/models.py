from django.db import models

class Product(models.Model):
    
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=50)
    created_at = models.DateField()
    group = models.CharField(max_length=100)
    show_on_site = models.BooleanField(default=False)
    external_id = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.name
