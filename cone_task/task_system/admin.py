from django.contrib import admin
from django.db.models import Exists, OuterRef, Q
from django.utils.html import format_html
from . import forms
from . import models
from .choices import ScheduleType, ScheduleTimingType
import uuid


class CategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'parent', 'name', 'update_time')
    fields = (
        "parent", "name"
    )


class TagAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'update_time')
    fields = ("name", )


class ScheduleAdmin(admin.ModelAdmin):
    schedule_put_name = 'schedule-put'
    list_display = ('id', 'schedule_type', 'schedule_sub_type', 'update_time')

    fields = (
        "schedule_type",
        "config"
    )

    def tasks(self, obj):
        return format_html('<a href="/admin/%s/%s/%s/change/">%s</a>' % (
            obj._meta.app_label, models.Task._meta.model_name, obj.task.id, obj.task.name
        ))
    tasks.short_description = '任务'

    def schedule_sub_type(self, obj):
        config = obj.config
        schedule_type = config.get("schedule_type", "-")
        type_config = config.get(schedule_type, {})
        if schedule_type == ScheduleType.CRONTAB:
            return type_config.get('crontab', '')
        elif schedule_type == ScheduleType.Interval:
            return "每%s秒" % type_config.get('period', '')
        elif schedule_type == ScheduleType.Timing:
            return ScheduleTimingType[config[schedule_type]['type']].label
        return '-'
    schedule_sub_type.short_description = '详细'


class ExchangeAdmin(admin.ModelAdmin):
    list_display = ('name', 'type', 'is_default', 'update_time')

    fields = (
        ('type', 'is_default'),
        'name'
    )


class QueueAdmin(admin.ModelAdmin):
    form = forms.QueueForm
    schedule_get_name = 'schedule-get'
    list_display = ('exchange', 'code', 'name', 'status', 'is_default', 'update_time')
    list_filter = ('exchange__name', )
    list_display_links = ('code', )

    fields = (
        'exchange',
        ('code', 'status', 'is_default'),
        'name',
        'connection',
        'config'
    )

    def get_queryset(self, request):
        return super(QueueAdmin, self).get_queryset(request).select_related('exchange')


class TaskParentFilter(admin.SimpleListFilter):

    title = '父任务'
    parameter_name = 'parent'
    other = (uuid.uuid4(), '其它')

    def lookups(self, request, model_admin):
        parent_tasks_with_children = models.Task.objects.annotate(
            has_children=Exists(models.Task.objects.filter(parent=OuterRef('id')))).filter(has_children=True)
        lookups = [(task.id, task.name) for task in parent_tasks_with_children]
        lookups.append(self.other)
        return lookups

    def queryset(self, request, queryset):
        value = self.value()
        if value == self.other[0]:
            queryset = queryset.filter(~Q(parent__id__in=[choice[0] for choice in self.lookup_choices]))
        elif value:
            queryset = queryset.filter(parent_id=value)
        return queryset


class TaskAdmin(admin.ModelAdmin):
    list_display = ('name', 'admin_parent', 'next_start_time', 'enabled', 'is_rigorous', 'queue', 'update_time')
    fields = (
        'category',
        'parent',
        'queue',
        ('preserve_log', 'is_rigorous', 'enabled',),
        ('name',),
        "function",
        'callback',
        "config",
        'description',
    )
    list_display_links = ['name']
    list_filter = ('category', 'tags', TaskParentFilter)
    filter_horizontal = ('tags',)

    def admin_parent(self, obj):
        if obj.parent:
            return format_html('<a href="/admin/%s/%s/%s/change/">%s</a>' % (
                obj._meta.app_label, self.model._meta.model_name, obj.parent.id, obj.parent
            ))
        return '-'

    admin_parent.short_description = '父任务'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('parent', 'category').prefetch_related('tags')


class TaskLogAdmin(admin.ModelAdmin):
    list_display = ('id', 'task', 'state', 'queue', 'start_time', 'create_time')
    list_filter = ('state', 'queue', 'task__name')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('task')


class QueueIPWhitelistAdmin(admin.ModelAdmin):
    list_display = ('id', 'queue', 'enabled', 'allowed_ip', 'update_time')
    fields = (
        ('queue', 'enabled'),
        'allowed_ip'
    )


admin.site.register(models.Exchange, ExchangeAdmin)
admin.site.register(models.Queue, QueueAdmin)
admin.site.register(models.Schedule, ScheduleAdmin)
admin.site.register(models.Task, TaskAdmin)
admin.site.register(models.TaskLog, TaskLogAdmin)
admin.site.register(models.QueueIPWhitelist, QueueIPWhitelistAdmin)

admin.site.site_header = '任务管理系统'
admin.site.site_title = '任务管理系统'
