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