import inspect
from django import forms
from . import models


class TaskForm(forms.ModelForm):

    def __init__(self, *args, **kwargs):
        super(TaskForm, self).__init__(*args, **kwargs)
        self.initial['queue'] = models.Queue.objects.filter(is_default=True).first() or models.Queue.objects.first()


class QueueForm(forms.ModelForm):

    class Meta:
        fields = '__all__'
