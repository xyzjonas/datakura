"""Base models and mixins"""

from django.db import models


class TimestampMixin(models.Model):
    """Abstract model mixin providing datetime fields"""

    created = models.DateTimeField(auto_now_add=True)
    changed = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class BaseModel(TimestampMixin):
    """Base model for all"""

    class Meta:
        abstract = True
