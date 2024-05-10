from rest_framework import serializers
from . import models


class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.Task
        fields = ('name', )


class CategorySerializer(serializers.ModelSerializer):
    parent = serializers.SerializerMethodField()

    @staticmethod
    def get_parent(obj):
        if obj.parent:
            return CategorySerializer(obj.parent).data

    class Meta:
        model = models.Category
        fields = ('name', 'parent')


class QueueSerializer(serializers.ModelSerializer):
    class Meta:
        include = ('code', 'name', 'is_default')
        model = models.Queue


class ScheduleSerializer(serializers.ModelSerializer):

    class Meta:
        include = ('schedule_type', 'config')
        model = models.Schedule


class TaskSerializer(serializers.ModelSerializer):
    category = CategorySerializer()
    tags = TagSerializer(many=True)
    parent = serializers.SerializerMethodField()

    def get_parent(self, obj):
        if obj.parent:
            return self.__class__(obj.parent).data

    class Meta:
        exclude = ('update_time', )
        model = models.Task


class TaskLogSerializer(serializers.ModelSerializer):
    schedule = ScheduleSerializer()

    class Meta:
        fields = '__all__'
        model = models.TaskLog
