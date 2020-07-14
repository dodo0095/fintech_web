from rest_framework import serializers
from apiserver.models import bot,technicHistory,technicCurrent,basicHistory,basicCurrent

class bot_apiSerializer(serializers.ModelSerializer):
    class Meta:
        model = bot
        fields = '__all__'
        #fields = ("tag")


class technicHistory_Serializer(serializers.ModelSerializer):
    class Meta:
        model = technicHistory
        fields = '__all__'
        #fields = ("tag")


class technicCurrent_Serializer(serializers.ModelSerializer):
    class Meta:
        model = technicCurrent
        fields = '__all__'
        #fields = ("tag")


class basicHistory_Serializer(serializers.ModelSerializer):
    class Meta:
        model = basicHistory
        fields = '__all__'
        #fields = ("tag")


class basicCurrent_Serializer(serializers.ModelSerializer):
    class Meta:
        model = basicCurrent
        fields = '__all__'
        #fields = ("tag")
