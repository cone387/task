from django.db.models import TextChoices


class TaskState(TextChoices):
    PENDING = 'PENDING'
    RECEIVED = 'RECEIVED'
    STARTED = 'STARTED'
    SUCCESS = 'SUCCESS'
    FAILURE = 'FAILURE'
    RETRY = 'RETRY'
    REVOKED = 'REVOKED'


class ScheduleStatus(TextChoices):
    OPENING = 'O', '开启'
    AUTO = 'A', '自动'
    CLOSED = 'C', '关闭'
    DONE = 'D', '已完成'
    TEST = 'T', '测试'
    ERROR = 'E', '调度错误'


class ScheduleType(TextChoices):
    CRONTAB = 'crontab', 'Crontab'
    Clocked = 'clocked', '指定时间'
    Interval = 'interval', '连续性'
    Timing = 'timing', '指定时间'
    NLP = 'nlp', 'NLP'


class IntervalPeriodType(TextChoices):
    Days = 'days', '天'
    Hours = 'hours', '小时'
    Minutes = 'minutes', '分钟'
    Seconds = 'seconds', '秒'


class ScheduleTimingType(TextChoices):
    DAY = 'DAY', '按天'
    WEEKDAY = 'WEEKDAY', '按周'
    MONTHDAY = 'MONTHDAY', '按月'
    YEAR = 'YEAR', "按年"
    DATETIME = 'DATETIME', '自选日期'


class ExchangeType(TextChoices):
    Direct = 'direct'
    Topic = 'topic'
    Fanout = 'fanout'
