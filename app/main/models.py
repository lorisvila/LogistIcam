from django.db import models
from django.db.models import Func


class Stock(models.Model):
    produit = models.CharField(max_length=255, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    prix_vente = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    prix_achat = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        db_table = 'stock'  # Pour correspondre au nom de table existant
        app_label = 'main'

    def __str__(self):
        return self.produit


class Client(models.Model):
    name = models.CharField(max_length=255)
    surname = models.CharField(max_length=255)
    type = models.CharField(max_length=255, choices=(("Client", "Client"), ("Fournisseur", "Fournisseur")),
                            default="Client")

    class Meta:
        db_table = 'clients'
        app_label = 'main'

    def __str__(self):
        return f"{self.name} {self.surname}"


class Transaction(models.Model):
    produit = models.ForeignKey(Stock, on_delete=models.CASCADE, db_column='produit_id')
    quantity = models.IntegerField(default=1)
    new_stock_qt = models.IntegerField(default=1, db_column='stock_quantity')
    time = models.DateTimeField(auto_now_add=True)
    client = models.ForeignKey(Client, on_delete=models.DO_NOTHING, db_column='client_id', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0,
                                null=True)  # Utilisé seulement dans le cas d'entrée en stock
    type = models.CharField(max_length=16, choices=(("Achat", "Achat"), ("Vente", "Vente")), default="Vente")

    class Meta:
        db_table = 'transactions'
        app_label = 'main'

    def __str__(self):
        return f"{self.produit.produit} - {self.quantity}"

    """
        Page d'accueil --> KPI sur les produits les + vendus
        Notifications sur dépassement seuils d'alterte stocks
        Génration de PDF structurtés --> tableaux transactions + graphiques
        + Esthétique du site
        --> Nombre de transactions par période --> compte -rendu / extraction / coût d'achats / vente
        --> Rajouter les calculs de marge (cout d'achat et de vente)

        --> Pourquoi pas ajouter les clients aux transactions --> Historique clients / rapports par clients
    """


class ExtractMonth(Func):
    function = 'EXTRACT'
    template = '%(function)s(MONTH from %(expressions)s)'
    output_field = models.IntegerField()


class ExtractYear(Func):
    function = 'EXTRACT'
    template = '%(function)s(YEAR from %(expressions)s)'
    output_field = models.IntegerField()
