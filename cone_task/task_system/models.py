from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from datetime import datetime
from django.core.validators import ValidationError
from django.utils import timezone
from .choices import TaskStatus
import re


UserModel = get_user_model()


def code_validator(value):
    if re.match(r'[a-zA-Z_-]+', value) is None:
        raise ValidationError('编码只能包含字母、数字、下划线和中划线')


class Category(models.Model):
    model = models.CharField(max_length=100, verbose_name='所属模型')
    parent = models.ForeignKey('self', blank=True, null=True, db_constraint=False, on_delete=models.CASCADE,
                               related_name='children', verbose_name='父类别')
    name = models.CharField(max_length=50, verbose_name='名称')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ts_category'
        verbose_name = verbose_name_plural = '任务类别'
        unique_together = ('name', 'user')

    def __str__(self):
        return self.name

    __repr__ = __str__


class Tag(models.Model):
    name = models.CharField(max_length=50, verbose_name='标签名')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ts_tag'
        verbose_name = verbose_name_plural = '任务标签'
        unique_together = ('user', 'name')

    def __str__(self):
        return self.name

    __repr__ = __str__


class Schedule(models.Model):
    config = models.JSONField(default=dict, verbose_name='参数')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(default=timezone.now, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '计划'
        db_table = 'ts_schedule'

    def generate_next_schedule(self):
        try:
            self.next_schedule_time = ScheduleConfig(config=self.config).get_next_time(self.next_schedule_time)
        except Exception as e:
            self.status = ScheduleStatus.ERROR.value
            self.save(update_fields=('status',))
            raise e
        if self.next_schedule_time > self.schedule_end_time:
            self.next_schedule_time = datetime.max
            self.status = ScheduleStatus.DONE.value
        self.save(update_fields=('next_schedule_time', 'status'))
        return self

    def __str__(self):
        return self.config.name

    __repr__ = __str__


class Task(models.Model):
    schedule = models.ForeignKey(Schedule, db_constraint=False, on_delete=models.SET_NULL, null=True, blank=True)
    parent = models.ForeignKey('self', db_constraint=False, on_delete=models.CASCADE,
                               null=True, blank=True, verbose_name='父任务')
    name = models.CharField(max_length=100, verbose_name='任务名')
    category = models.ForeignKey(Category, db_constraint=False, on_delete=models.DO_NOTHING, verbose_name='类别')
    tags = models.ManyToManyField(Tag, blank=True, db_constraint=False, verbose_name='标签')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    next_start_time = models.DateTimeField(default=datetime.max, verbose_name='下次运行时间', db_index=True)
    is_rigorous = models.BooleanField(default=False, verbose_name='严格模式')
    # callback = models.ForeignKey(ScheduleCallback, on_delete=models.SET_NULL,
    #                              null=True, blank=True, db_constraint=False, verbose_name='回调')
    preserve_log = models.BooleanField(default=True, verbose_name='保留日志')
    config = models.JSONField(blank=True, null=True, verbose_name='参数')
    enabled = models.BooleanField(default=True, verbose_name='启用')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '任务中心'
        unique_together = (('name', 'parent'), )
        db_table = 'ts_task'
        swappable = 'TASK_MODEL'

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority


class ScheduleCallback(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, verbose_name='回调')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    trigger_event = common_fields.CharField(default=ScheduleCallbackEvent.DONE, choices=ScheduleCallbackEvent.choices,
                                            verbose_name='触发事件')
    status = common_fields.CharField(default=ScheduleCallbackStatus.ENABLE.value, verbose_name='状态',
                                     choices=ScheduleCallbackStatus.choices)
    config = common_fields.ConfigField(blank=True, null=True, verbose_name='参数')
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, db_constraint=False, verbose_name='最后更新')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '计划回调'
        # unique_together = (('name', 'user'), )
        db_table = 'schedule_callback'

    def __str__(self):
        return self.name

    __repr__ = __str__


class AbstractSchedule(models.Model):
    id = models.AutoField(primary_key=True)
    task = models.OneToOneField(settings.TASK_MODEL, on_delete=models.CASCADE,
                                db_constraint=False, verbose_name='任务')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    next_schedule_time = models.DateTimeField(default=timezone.now, verbose_name='下次运行时间', db_index=True)
    schedule_start_time = models.DateTimeField(default=datetime.min, verbose_name='开始时间')
    schedule_end_time = models.DateTimeField(default=datetime.max, verbose_name='结束时间')
    config = common_fields.ConfigField(default=dict, verbose_name='参数')
    status = common_fields.CharField(default=ScheduleStatus.OPENING.value, verbose_name='状态',
                                     choices=ScheduleStatus.choices)
    is_strict = models.BooleanField(default=False, verbose_name='严格模式')
    callback = models.ForeignKey(ScheduleCallback, on_delete=models.SET_NULL,
                                 null=True, blank=True, db_constraint=False, verbose_name='回调')
    preserve_log = models.BooleanField(default=True, verbose_name='保留日志')
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, db_constraint=False, verbose_name='最后更新')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    # 这里的update_time不能使用auto_now，因为每次next_schedule_time更新时，都会更新update_time,
    # 这样会导致每次更新都会触发post_save且不知道啥时候更新了调度计划
    update_time = models.DateTimeField(default=timezone.now, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '计划中心'
        ordering = ('-priority', 'next_schedule_time')
        abstract = True

    def __str__(self):
        return self.task.name

    __repr__ = __str__

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority


class Queue(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='ID')
    name = models.CharField(max_length=100, verbose_name='队列名称', unique=True)
    code = models.CharField(max_length=100, verbose_name='队列编码', unique=True, validators=[code_validator])
    status = models.BooleanField(default=True, verbose_name='状态')
    module = models.CharField(max_length=100, verbose_name='队列类型',
                              default=ScheduleQueueModule.DEFAULT,
                              choices=ScheduleQueueModule.choices)
    config = models.JSONField(default=dict, verbose_name='配置', null=True, blank=True)
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, db_constraint=False, verbose_name='最后更新')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    queue = None

    class Meta:
        verbose_name = verbose_name_plural = '计划队列'
        db_table = 'schedule_queue'

    def __str__(self):
        return "%s(%s)" % (self.name, self.code)



class TaskLog(models.Model):
    id = models.AutoField(primary_key=True)
    schedule = models.ForeignKey(settings.SCHEDULE_MODEL, db_constraint=False, on_delete=models.CASCADE,
                                 verbose_name='任务计划', related_name='logs')
    status = common_fields.CharField(verbose_name='运行状态', choices=ExecuteStatus.choices)
    queue = models.CharField(max_length=100, verbose_name='队列', default='opening')
    result = common_fields.ConfigField(blank=True, null=True, verbose_name='结果')
    schedule_time = models.DateTimeField(verbose_name='计划时间')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        verbose_name = verbose_name_plural = '计划日志'
        ordering = ('-create_time',)
        db_table = 'schedule_log'
        swappable = 'SCHEDULE_LOG_MODEL'

    def __str__(self):
        return "schedule: %s, status: %s" % (self.schedule, self.status)

    __repr__ = __str__


class ScheduleQueuePermission(models.Model):
    id = models.AutoField(primary_key=True, verbose_name='ID')
    queue = models.ForeignKey(ScheduleQueue, db_constraint=False, on_delete=models.CASCADE, verbose_name='队列')
    type = models.CharField(max_length=1, verbose_name='类型',
                            default=PermissionType.IP_WHITE_LIST,
                            choices=PermissionType.choices)
    status = models.BooleanField(default=True, verbose_name='启用状态')
    config = models.JSONField(default=dict, verbose_name='配置', null=True, blank=True)
    user = models.ForeignKey(UserModel, on_delete=models.CASCADE, db_constraint=False, verbose_name='最后更新')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '队列权限'
        unique_together = ('queue', 'status')
        db_table = 'schedule_queue_permission'

    def __str__(self):
        return self.queue.name

    __repr__ = __str__

