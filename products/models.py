from django.db import models
from urllib.parse import quote

class Product(models.Model):
    
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=50)
    created_at = models.DateField()
    group = models.CharField(max_length=100)
    show_on_site = models.BooleanField(default=False)
    external_id = models.CharField(max_length=100, unique=True)
    
    @property
    def product_url(self):
        return f"https://www.esschertdesign.com/qr/{self.name}"
    
    @property
    def product_image_url(self):
        return f"https://dhznjqezv3l9q.cloudfront.net/report_Image/normal/{quote(self.name)}_01.png"

    def __str__(self):
        return self.name
