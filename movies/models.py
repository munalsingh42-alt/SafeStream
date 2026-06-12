from django.db import models
from django.core.exceptions import ValidationError


class Movie(models.Model):

    title = models.CharField(max_length=200)

    description = models.TextField()

    poster = models.ImageField(
        upload_to='posters/'
    )

    trailer_url = models.URLField()

    theater_name = models.CharField(
        max_length=200,
        default='PVR Cinemas'
    )

    screen_name = models.CharField(
        max_length=100,
        default='Screen 1'
    )

    genre = models.CharField(
        max_length=100,
        default='Action'
    )

    language = models.CharField(
        max_length=50,
        default='English'
    )

    def clean(self):

        if 'youtube.com/embed/' not in self.trailer_url:

            raise ValidationError(
                'Only YouTube embed URLs are allowed.'
            )

    def __str__(self):

        return self.title

    class Meta:

        indexes = [

            models.Index(
                fields=['genre']
            ),

            models.Index(
                fields=['language']
            )

        ]