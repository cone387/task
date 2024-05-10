import inspect
from django import forms
from django.utils.module_loading import import_string


class QueueForm(forms.ModelForm):

    def clean(self):
        cleaned_data = super(QueueForm, self).clean()
        if not self.errors:
            module = cleaned_data.get('module')
            config = cleaned_data.get('config')
            config.setdefault('name', cleaned_data['code'])
            queueCls = import_string(module)
            validate_config = getattr(queueCls, 'validate_config', None)
            if validate_config:
                error = validate_config(config)
                if error:
                    self.add_error('config', error)
            if not self.errors:
                args = inspect.getfullargspec(getattr(queueCls, '__init__'))
                kwargs = {k: v for k, v in config.items() if k in args.args}
                if 'name' not in kwargs:
                    config.pop('name')
                # queue = queueCls(**kwargs)
                validate = getattr(queueCls, 'validate', None)
                if validate:
                    error = validate(**kwargs)
                    if error:
                        self.add_error('config', error)
        return cleaned_data

    class Meta:
        fields = '__all__'
