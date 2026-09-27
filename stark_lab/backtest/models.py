from django.db import models


class PriceCache(models.Model):
    """個股完整日線快取（還原權息），避免每次回測都打 Yahoo。

    payload 為 JSON：{"d": [YYYY-MM-DD...], "o": [...], "h": [...], "l": [...], "c": [...], "v": [...]}
    """

    symbol = models.CharField(max_length=20, primary_key=True)  # 例：2330.TW
    updated_at = models.DateTimeField()
    first_date = models.DateField(null=True)
    last_date = models.DateField(null=True)
    rows = models.IntegerField(default=0)
    payload = models.TextField()

    class Meta:
        verbose_name = "回測行情快取"

    def __str__(self):
        return f"{self.symbol} {self.first_date}~{self.last_date}"
