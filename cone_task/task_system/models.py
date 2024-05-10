from django.db import models
from datetime import datetime
from django.core.validators import ValidationError
from django.utils import timezone
from .choices import TaskState, ScheduleType, ExchangeType
from .schedule.config import get_next_schedule_time
import re
import uuid


def code_validator(value):
    if re.match(r'[a-zA-Z_-]+', value) is None:
        raise ValidationError('编码只能包含字母、数字、下划线和中划线')


class Category(models.Model):
    parent = models.ForeignKey('self', blank=True, null=True, db_constraint=False, on_delete=models.CASCADE,
                               related_name='children', verbose_name='父类别')
    name = models.CharField(max_length=50, verbose_name='名称', unique=True)
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ts_category'
        verbose_name = verbose_name_plural = '任务类别'

    def __str__(self):
        return self.name

    __repr__ = __str__


class Tag(models.Model):
    name = models.CharField(max_length=50, verbose_name='标签名', unique=True)
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        db_table = 'ts_tag'
        verbose_name = verbose_name_plural = '任务标签'

    def __str__(self):
        return self.name

    __repr__ = __str__


class Schedule(models.Model):
    schedule_type = models.CharField(verbose_name='计划类型', max_length=20,
                                     choices=ScheduleType.choices, default=ScheduleType.CRONTAB)
    config = models.JSONField(verbose_name='参数')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '计划中心'
        db_table = 'ts_schedule'

    def get_next_time(self, last_time: datetime, is_rigorous=False):
        return get_next_schedule_time(self.schedule_type, self.config, last_time, is_rigorous)

    def __str__(self):
        return f'{self.schedule_type}'

    __repr__ = __str__


class Exchange(models.Model):
    name = models.CharField(max_length=100, verbose_name='名称', unique=True)
    type = models.CharField(max_length=10, verbose_name='类型', choices=ExchangeType.choices,
                            default=ExchangeType.Direct)
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '路由交换'
        db_table = 'ts_exchange'

    @property
    def default(self):
        default = self.objects.filter(is_default=True).first() or self.objects.first()
        if not default:
            default = self.objects.create(name='task', is_default=True)
        return default

    def __str__(self):
        return self.name

    __repr__ = __str__


class Queue(models.Model):
    exchange = models.ForeignKey(Exchange, verbose_name='交换机', on_delete=models.DO_NOTHING, db_constraint=False)
    connection = models.CharField(max_length=200, verbose_name='链接')
    name = models.CharField(max_length=100, verbose_name='队列名称', unique=True)
    code = models.CharField(max_length=100, verbose_name='队列编码', primary_key=True, validators=[code_validator])
    status = models.BooleanField(default=True, verbose_name='状态')
    is_default = models.BooleanField(default=False, verbose_name='是否默认')
    config = models.JSONField(default=dict, verbose_name='配置', null=True, blank=True)
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '任务队列'
        db_table = 'ts_queue'

    @property
    def default(self):
        default = self.objects.filter(is_default=True).first() or self.objects.first()
        if not default:
            raise ValueError("还没有默认的Queue, 请配置")
        return default

    def __str__(self):
        return "%s(%s)" % (self.name, self.code)


class Task(models.Model):
    id = models.UUIDField(primary_key=True, editable=False, default=uuid.uuid4, verbose_name='UUID')
    schedule = models.ForeignKey(Schedule, db_constraint=False, on_delete=models.SET_NULL, null=True, blank=True)
    parent = models.ForeignKey('self', db_constraint=False, on_delete=models.CASCADE,
                               null=True, blank=True, verbose_name='父任务')
    name = models.CharField(max_length=100, verbose_name='任务名', unique=True)
    function = models.CharField(max_length=200, verbose_name='任务函数', null=True, blank=True)
    category = models.ForeignKey(Category, db_constraint=False, on_delete=models.DO_NOTHING, verbose_name='类别')
    tags = models.ManyToManyField(Tag, db_constraint=False, verbose_name='标签')
    description = models.TextField(blank=True, null=True, verbose_name='描述')
    priority = models.IntegerField(default=0, verbose_name='优先级')
    next_start_time = models.DateTimeField(default=datetime.max, verbose_name='下次运行时间', db_index=True)
    is_rigorous = models.BooleanField(default=False, verbose_name='严格模式')
    callback = models.CharField(max_length=500, null=True, blank=True, verbose_name='回调')
    preserve_log = models.BooleanField(default=True, verbose_name='保留日志')
    config = models.JSONField(blank=True, null=True, verbose_name='参数')
    enabled = models.BooleanField(default=True, verbose_name='启用')
    queue = models.ForeignKey(Queue, db_constraint=False, on_delete=models.SET_NULL, null=True, blank=True,
                              verbose_name='队列')
    last_run_at = models.DateTimeField(blank=True, null=True, editable=False, verbose_name='上次运行时间')
    total_run_count = models.PositiveIntegerField(default=0, editable=False,  verbose_name='运行次数')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = '任务中心'
        db_table = 'ts_task'

    def generate_next_task(self):
        if not self.schedule:
            return None
        next_time = self.schedule.get_next_time(self.last_run_at, self.is_rigorous)
        if not self.next_start_time:
            self.enabled = False
            # 优化数据库查询, 所以将时间置为最大
            self.next_start_time = datetime.max
        else:
            self.next_start_time = next_time
        self.save(update_fields=('next_start_time', 'enabled'))
        return self

    def __str__(self):
        return self.name

    __repr__ = __str__

    def __lt__(self, other):
        return self.priority < other.priority

    def __gt__(self, other):
        return self.priority > other.priority


class TaskLog(models.Model):
    task = models.ForeignKey(Task, db_constraint=False, on_delete=models.CASCADE,
                             verbose_name='任务', related_name='logs')
    state = models.CharField(verbose_name='运行状态', choices=TaskState.choices, max_length=20)
    queue = models.CharField(max_length=100, verbose_name='队列')
    result = models.JSONField(blank=True, null=True, verbose_name='结果')
    start_time = models.DateTimeField(verbose_name='运行时间')
    create_time = models.DateTimeField(default=timezone.now, verbose_name='创建时间')

    class Meta:
        verbose_name = verbose_name_plural = '计划日志'
        ordering = ('-create_time',)
        db_table = 'ts_task_log'

    def __str__(self):
        return "task: %s, status: %s" % (self.task, self.state)

    __repr__ = __str__


class QueueIPWhitelist(models.Model):
    queue = models.ForeignKey(Queue, db_constraint=False, on_delete=models.CASCADE, verbose_name='队列')
    enabled = models.BooleanField(default=True, verbose_name='启用状态')
    allowed_ip = models.GenericIPAddressField(verbose_name='白名单IP')
    create_time = models.DateTimeField(auto_now_add=True, verbose_name='创建时间')
    update_time = models.DateTimeField(auto_now=True, verbose_name='更新时间')

    class Meta:
        verbose_name = verbose_name_plural = 'IP白名单'
        unique_together = ('queue', 'allowed_ip')
        db_table = 'ts_queue_ip_whitelist'

    def __str__(self):
        return '%s: %s' % (self.queue, self.allowed_ip)

    __repr__ = __str__
