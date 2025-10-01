from django.db import models
from .utils import sanitize_text

class ScrapedData(models.Model):
    content = models.TextField()

    def save(self, *args, **kwargs):
        self.content = sanitize_text(self.content)
        super().save(*args, **kwargs)
