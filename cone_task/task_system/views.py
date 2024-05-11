from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from kombu import Connection, Exchange, Queue, Consumer, Producer, Message
from .choices import ExchangeType
from . import models
from django.core.cache import cache
from . import serializers


@receiver(post_save, sender=models.QueueIPWhitelist)
def add_queue_ip_whitelist(sender, instance: models.QueueIPWhitelist, created, **kwargs):
    cache.set(f'{instance.queue_id}:whitelist:{instance.allowed_ip}', 1)


@receiver(post_delete, sender=models.QueueIPWhitelist)
def delete_queue_ip_whitelist(sender, instance: models.QueueIPWhitelist, **kwargs):
    cache.delete(f'{instance.queue_id}:whitelist:{instance.allowed_ip}')


@receiver(post_delete, sender=models.Queue)
def delete_queue(sender, instance: models.Queue, **kwargs):
    cache.delete(f'queue:{instance.name}')


@receiver(post_save, sender=models.Queue)
def add_queue(sender, instance: models.Queue, created, **kwargs):
    cache.set(f'queue:{instance.name}', instance)


@receiver(post_delete, sender=models.Exchange)
def delete_exchange(sender, instance: models.Exchange, **kwargs):
    cache.delete(f'exchange:{instance.name}')


@receiver(post_save, sender=models.Exchange)
def add_exchange(sender, instance: models.Exchange, created, **kwargs):
    cache.set(f'exchange:{instance.name}', instance)


try:
    for obj in models.Exchange.objects.all():
        add_exchange('', obj, True)
    for obj in models.Queue.objects.all():
        add_queue('', obj, True)
    for obj in models.QueueIPWhitelist.objects.all():
        add_queue_ip_whitelist('', obj, True)
except Exception as e:
    pass


def direct_match(queue: models.Queue, routing_key, queue_str):
    return queue.routing_key == routing_key and queue.name == queue_str


def topic_match(queue: models.Queue, routing_key, queue_str):
    return queue.routing_key == routing_key and queue.name == queue_str


def fanout_match(queue: models.Queue, routing_key, queue_str):
    return queue.name == queue_str


def get_queue(exchange: models.Exchange, routing_key, queue_str):
    if exchange.type == ExchangeType.Direct:
        match = direct_match
    elif exchange.type == ExchangeType.Topic:
        match = topic_match
    else:
        match = fanout_match
    for q in exchange.queue_set.all():
        if match(q, routing_key, queue_str):
            return q


def get_exchange_and_queue(exchange, queue, routing_key) -> [Exchange, models.Queue]:
    exchange: models.Exchange = cache.get(f'exchange:{exchange}')
    if not exchange:
        raise NotFound
    queue: models.Queue = get_queue(exchange, routing_key, queue)
    if not queue:
        raise NotFound
    return Exchange(name=exchange.name, type=exchange.type), queue


class TaskAPI:

    @staticmethod
    @api_view(['GET'])
    def get(request: Request, exchange, queue: str, routing_key: str):
        exchange, queue = get_exchange_and_queue(exchange, queue, routing_key)
        with Connection(queue.connection) as conn:
            channel = conn.channel()
            message: Message = channel.basic_get(queue.name, no_ack=True)
            if not message:
                raise NotFound
        # ip = request.META.get('HTTP_X_FORWARDED_FOR') if request.META.get('HTTP_X_FORWARDED_FOR') else \
        #     request.META.get('REMOTE_ADDR')
        # cache_ip = cache.get(f'{queue}:whitelist:{ip}')
        # if not cache_ip:
        #     return Response({'error': f'IP {ip} Not Allowed'}, status=status.HTTP_403_FORBIDDEN)
        return Response({
            'properties': message.properties,
            'headers': message.headers,
            'task': message.payload
        })

    @staticmethod
    @api_view(['GET'])
    def put(request: Request, exchange, queue: str, routing_key: str):
        task_ids = request.query_params.get('task_id')
        if task_ids:
            task_ids = task_ids.split(',')
        else:
            task_ids = request.data
        tasks = models.Task.objects.filter(id__in=task_ids)
        exchange, queue_model = get_exchange_and_queue(exchange, queue, routing_key)
        with Connection(queue_model.connection) as conn:
            queue: Queue = Queue(channel=conn, name=queue_model.name, exchange=exchange, routing_key=routing_key)
            producer = Producer(conn, exchange=exchange)
            data = serializers.TaskSerializer(tasks, many=True).data
            for o in data:
                producer.publish(o, routing_key=routing_key, serializer='json', declare=[queue])
        return Response(data)
