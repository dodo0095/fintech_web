from rest_framework import serializers
from apiserver.models import strategy_robot,history,now_chose

class strategy_robot_apiSerializer(serializers.ModelSerializer):
    class Meta:
        model = strategy_robot
        fields = '__all__'
        #fields = ("tag")


class history_apiSerializer(serializers.ModelSerializer):
    class Meta:
        model = history
        fields = '__all__'
        #fields = ("tag")


class now_chose_apiSerializer(serializers.ModelSerializer):
    class Meta:
        model = now_chose
        fields = '__all__'
        #fields = ("tag")
