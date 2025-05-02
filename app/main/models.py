from django.db import models

class Stock(models.Model):
    produit = models.CharField(max_length=255, unique=True)
    quantity = models.IntegerField(default=0)
    prix_unitaire = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'stock'  # Pour correspondre au nom de table existant

    def __str__(self):
        return self.produit

class Transaction(models.Model):
    produit = models.ForeignKey(Stock, on_delete=models.CASCADE, db_column='produit_id')
    quantity = models.IntegerField()
    time = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'transactions'  # Pour correspondre au nom de table existant

    def __str__(self):
        return f"{self.produit.produit} - {self.quantity}"