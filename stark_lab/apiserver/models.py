from django.db import models

# Create your models here.


class bot(models.Model):

	monthly_return= models.TextField(default="")
	monthly_0050_return= models.TextField(default="")
	season_return= models.TextField(default="")
	season_0050_return= models.TextField(default="")
	year_return= models.TextField(default="")
	year_0050_return= models.TextField(default="")
	fundamental_return= models.TextField(default="")
	fundamental_amplitude= models.TextField(default="")
	technology_return= models.TextField(default="")
	technology_amplitude= models.TextField(default="")

	class Meta:
		db_table = "bot"



class basicHistory(models.Model):

	stock_name= models.TextField(default="")
	start_date= models.TextField(default="")
	buy_price= models.TextField(default="")
	over_date= models.TextField(default="")
	sell_price= models.TextField(default="")
	return_value= models.TextField(default="")
	type= models.TextField(default="")
	class Meta:
		db_table = "basicHistory"


class technicHistory(models.Model):

	stock_name= models.TextField(default="")
	start_date= models.TextField(default="")
	buy_price= models.TextField(default="")
	over_date= models.TextField(default="")
	sell_price= models.TextField(default="")
	return_value= models.TextField(default="")
	type= models.TextField(default="")
	class Meta:
		db_table = "technicHistory"




class basicCurrent(models.Model):

	final_update= models.TextField(default="")
	stock_name= models.TextField(default="")
	start_date= models.TextField(default="")
	start_price= models.TextField(default="")
	over_date= models.TextField(default="")
	current_price= models.TextField(default="")
	now_return= models.TextField(default="")
	type= models.TextField(default="")
	class Meta:
		db_table = "basicCurrent"


class technicCurrent(models.Model):

	final_update= models.TextField(default="")
	stock_name= models.TextField(default="")
	start_date= models.TextField(default="")
	start_price= models.TextField(default="")
	over_date= models.TextField(default="")
	current_price= models.TextField(default="")
	now_return= models.TextField(default="")
	type= models.TextField(default="")
	class Meta:
		db_table = "technicCurrent"



class article_1(models.Model):

	title= models.TextField(default="")
	title_picture= models.TextField(default="")
	abstract= models.TextField(default="")
	author_picture= models.TextField(default="")
	author_name= models.TextField(default="")
	date= models.TextField(default="")
	link= models.TextField(default="")

	class Meta:
		db_table = "article_1"



class article_2(models.Model):

	title= models.TextField(default="")
	title_picture= models.TextField(default="")
	abstract= models.TextField(default="")
	author_picture= models.TextField(default="")
	author_name= models.TextField(default="")
	date= models.TextField(default="")
	link= models.TextField(default="")

	class Meta:
		db_table = "article_2"


class MonthlyPerformance(models.Model):
	label = models.CharField(max_length=100, help_text="月份標籤，例如：2025年一月份績效")
	date_range = models.CharField(max_length=50, help_text="例如：2025-01-11~2025-02-10")
	etf0050_return = models.FloatField(help_text="ETF 0050 的績效（百分比）")
	strategy_return = models.FloatField(help_text="我的策略績效（百分比）")

	class Meta:
		db_table = "MonthlyPerformance"