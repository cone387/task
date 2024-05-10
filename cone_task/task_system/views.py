from queue import Empty
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from rest_framework.exceptions import NotFound
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework import status
from . import models
from django.core.cache import cache


@receiver(post_save, sender=models.QueueIPWhitelist)
def add_queue_ip_whitelist(sender, instance: models.QueueIPWhitelist, created, **kwargs):
    cache.set(f'{instance.queue_id}:whitelist:{instance.allowed_ip}', 1)


@receiver(post_delete, sender=models.QueueIPWhitelist)
def delete_queue_ip_whitelist(sender, instance: models.QueueIPWhitelist, **kwargs):
    cache.delete(f'{instance.queue_id}:whitelist:{instance.allowed_ip}')


@receiver(post_delete, sender=models.Queue)
def delete_queue(sender, instance: models.Queue, **kwargs):
    cache.delete(f'queue:{instance.code}')


@receiver(post_save, sender=models.Queue)
def add_queue(sender, instance: models.Queue, created, **kwargs):
    cache.set(f'queue:{instance.code}', instance)

try:
    for obj in models.Queue.objects.all():
        add_queue('', obj, True)

    for obj in models.QueueIPWhitelist.objects.all():
        add_queue_ip_whitelist('', obj, True)
except Exception:
    pass


class TaskAPI:

    @staticmethod
    @api_view(['GET'])
    def get(request: Request, exchange, queue: str):
        queue_instance = cache.get(f'{exchange}:{queue}')
        if queue_instance is None:
            raise NotFound
        ip = request.META.get('HTTP_X_FORWARDED_FOR') if request.META.get('HTTP_X_FORWARDED_FOR') else \
            request.META.get('REMOTE_ADDR')
        cache_ip = cache.get(f'{queue}:whitelist:{ip}')
        if not cache_ip:
            return Response({'error': f'IP {ip} Not Allowed'}, status=status.HTTP_403_FORBIDDEN)
        try:
            task = queue_instance.get_schedule()
        except Empty:
            return Response({'message': 'no task for %s' % queue}, status=status.HTTP_202_ACCEPTED)
        return Response(task)
