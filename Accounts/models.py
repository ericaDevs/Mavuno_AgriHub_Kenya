from django.db import models

# Create your models here.
class Users(models.Model):
    username = models.CharField(max_length = 100)
    email = models.EmailField(max_length = 200, unique = True)
    password_1 = models.CharField(max_length = 200)
    password_2 = models.CharField(max_length = 200)

    def __str__(self):
        return self.username