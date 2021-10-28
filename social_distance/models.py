from django.db import models

# https://www.rootstrap.com/blog/simple-dynamic-settings-for-django/
class DynamicSettings(models.Model):
    register_needs_approval = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = "Dynamic Settings"

    def save(self, *args, **kwargs):
        self.pk = 1
        super(DynamicSettings, self).save(*args, **kwargs)

    @classmethod
    def load(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj