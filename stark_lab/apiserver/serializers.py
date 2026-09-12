from rest_framework import serializers
from apiserver.models import bot,technicHistory,technicCurrent,basicHistory,basicCurrent,article_1,article_2,MonthlyPerformance

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


class article_Serializer(serializers.ModelSerializer):
    class Meta:
        model = article_1
        fields = '__all__'
        #fields = ("tag")


class article2_Serializer(serializers.ModelSerializer):
    class Meta:
        model = article_2
        fields = '__all__'
        #fields = ("tag")


# 列表用：不夾帶肥大的 content 正文，讓 botBlog 卡片列表載入快。
_ARTICLE_LIST_FIELDS = (
    "id", "title", "title_picture", "abstract",
    "author_picture", "author_name", "date", "link",
)


class article_ListSerializer(serializers.ModelSerializer):
    class Meta:
        model = article_1
        fields = _ARTICLE_LIST_FIELDS


class article2_ListSerializer(serializers.ModelSerializer):
    class Meta:
        model = article_2
        fields = _ARTICLE_LIST_FIELDS

class MonthlyPerformance_Serializer(serializers.ModelSerializer):
    class Meta:
        model = MonthlyPerformance
        fields = '__all__'
        #fields = ("tag")
