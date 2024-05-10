from datetime import datetime, timedelta
from django.core.validators import ValidationError
from ..choices import ScheduleTimingType, ScheduleType, IntervalPeriodType
from croniter import croniter


mdays = [0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]


def _get_next_time_of_crontab(config: dict, last_time, is_rigorous=False):
    crontab = config['crontab']
    start_time = last_time if is_rigorous else datetime.now()
    return croniter(crontab, start_time, datetime)


def _get_next_time_of_clocked(config: dict, last_time, is_rigorous=False):
    clocked = config['clocked']
    for clock in clocked:
        if last_time < clock:
            return clock
    return None


def _get_next_time_of_interval(config: dict, last_time, is_rigorous=False):
    start_time, interval, period = config['start_time'], config['interval'], config['period']
    if period == IntervalPeriodType.Days:
        seconds = interval * 24 * 60 * 60
    elif period == IntervalPeriodType.Hours:
        seconds = interval * 60 * 60
    elif period == IntervalPeriodType.Minutes:
        seconds = interval * 60
    elif period == IntervalPeriodType.Seconds:
        seconds = interval
    else:
        raise ValidationError(f'不支持的周期类型: {period}')
    if is_rigorous:
        next_time = last_time + timedelta(seconds=seconds)
    else:
        # 不是简单的由now + interval是因为这样如果由延迟的话可以根据日志看出遗漏了多少
        next_time = last_time + timedelta(seconds=seconds)
        now = datetime.now()
        while next_time <= now:
            next_time += timedelta(seconds=seconds)
    return next_time


def _get_next_time_of_timing(config: dict, last_time, is_rigorous=False):
    last_time = last_time if is_rigorous else datetime.now()
    timing_type = config['type']
    timing_config = config[timing_type]
    hour, minute, second = timing_config['time'].split(':')
    hour, minute, second = int(hour), int(minute), int(second)
    timing_period = timing_config.get('period', 1)
    next_time = datetime(last_time.year, last_time.month, last_time.day, hour, minute, second)
    if timing_type == ScheduleTimingType.DAY:
        while next_time <= last_time:
            next_time += timedelta(days=timing_period)
    elif timing_type == ScheduleTimingType.WEEKDAY:
        weekdays = timing_config['weekdays']
        weekday = last_time.isoweekday()
        for i in weekdays:
            if i > weekday:
                days = i - weekday
                delta = timedelta(days=days)
                break
        else:
            days = weekday - weekdays[0]
            delta = timedelta(days=timing_period * 7 - days)
        next_time = next_time + delta
    elif timing_type == ScheduleTimingType.MONTHDAY:
        monthdays = timing_config['monthdays']
        day = 1
        for day in monthdays:
            if day == 0:
                day = 1
            elif day == 32:
                day = mdays[last_time.month]
            next_time = datetime(last_time.year, last_time.month, day, hour, minute, second)
            if next_time > last_time:
                break
        else:
            month = (last_time.month + timing_period) % 12
            if month == 0:
                month = 1
            year = last_time.year + (last_time.month + timing_period) // 12
            next_time = datetime(year, month, day, hour, minute, second)
    else:
        raise ValidationError("unsupported timing type: %s" % timing_type)
    return next_time


def _get_next_time_of_nlp(config: dict, last_time, is_rigorous=False):
    pass


_next_time_get_mapping = {
    ScheduleType.CRONTAB: _get_next_time_of_crontab,
    ScheduleType.Clocked: _get_next_time_of_clocked,
    ScheduleType.Interval: _get_next_time_of_interval,
    ScheduleType.Timing: _get_next_time_of_timing,
    ScheduleType.NLP: _get_next_time_of_nlp
}


def get_next_schedule_time(schedule_type, config: dict, last_time, is_rigorous=False):
    return _next_time_get_mapping[schedule_type](config, last_time, is_rigorous)


class ScheduleConfig:
    """
        :sample
        {
            "schedule_type": "crontab|clocked|interval|timing|nlp",
            "crontab": {
                "crontab": "1 * * * *"
            },
            "clocked": {
                "clocked": ["2024-05-08 12:00:00", "2024-05-09 12:00:00"]
            },
            "interval": {
                "start_time": "2024-05-08 12:00:00",
                "interval": 10,
                "period": "days|hours|minutes|seconds",
            },
            "timing": {
                "type": "day",
                "time": "09:00",
                "period": 1,
                "day": {
                    "comment": "每天早上X点的意思“
                },
                "weekday": {
                    "weekdays": [1, 2, 3, 4, 5, 6, 7],
                },
                "month": {
                    "monthdays": [1, 2, 3],
                }
            },
            "nlp": {
                "nlp": "每天早上九点"
            }
        }

    """

    def __init__(self, schedule_type, crontab=None, clocked=None, interval=None, timing=None, config=None, **kwargs):
        self.schedule_type = schedule_type
        self.crontab = crontab
        self.clocked = clocked
        self.interval = interval
        self.timing = timing
        self.config = config

    def parse_config(self, config):
        schedule_type = self.schedule_type = config['schedule_type']
        detail_config = config[schedule_type]
        self.crontab = detail_config.get('crontab')
        self.interval = detail_config.get('interval')
        self.clocked = detail_config.get('clocked')
        self.timing = detail_config.get('timing')
        assert any([self.crontab, self.interval, self.clocked, self.timing]), \
            'crontab, interval, clocked, timing至少选择一个'

    def get_next_time(self, last_time: datetime, is_rigorous=False):
        schedule_type = self.schedule_type
        config = self.config[schedule_type]
        if is_rigorous:
            last_time = datetime.now()
        return _next_time_get_mapping[schedule_type](config, last_time, is_rigorous)
