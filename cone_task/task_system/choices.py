from django.db.models import TextChoices, IntegerChoices


class TaskStatus(TextChoices):
    ENABLE = 'E', '启用'
    DISABLE = 'D', '禁用'


class ScheduleStatus(TextChoices):
    OPENING = 'O', '开启'
    AUTO = 'A', '自动'
    CLOSED = 'C', '关闭'
    DONE = 'D', '已完成'
    TEST = 'T', '测试'
    ERROR = 'E', '调度错误'


class ScheduleType(TextChoices):
    CRONTAB = 'C', 'Crontab'
    ONCE = 'O', '一次性'
    CONTINUOUS = 'S', '连续性'
    TIMINGS = 'T', '指定时间'


class ScheduleTimingType(TextChoices):
    DAY = 'DAY', '按天'
    WEEKDAY = 'WEEKDAY', '按周'
    MONTHDAY = 'MONTHDAY', '按月'
    YEAR = 'YEAR', "按年"
    DATETIME = 'DATETIME', '自选日期'


class ScheduleCallbackStatus(TextChoices):
    ENABLE = 'E', '启用'
    DISABLE = 'D', '禁用'

