from django.db import models
from django.db.models import Func


class Stock(models.Model):
    """
    Represents a Stock model for managing product inventory in a database.

    This class is used to keep track of stock details such as product name, quantity,
    selling price, and purchase price. It is part of the inventory management system
    and interacts with the database table defined by the Meta subclass.

    :ivar produit: The name of the product in stock. Has a maximum length of
        255 characters and must be unique.
    :type produit: str
    :ivar quantity: The quantity of the product available in stock. Must be a
        positive integer.
    :type quantity: int
    :ivar prix_vente: The selling price of the product, expressed as a decimal
        value with up to 10 digits and 2 decimal places.
    :type prix_vente: Decimal
    :ivar prix_achat: The purchase price of the product, expressed as a decimal
        value with up to 10 digits and 2 decimal places.
    :type prix_achat: Decimal
    """
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
    """
    Represents a client or a supplier in the system.

    This model stores information regarding clients or suppliers, including
    their name, surname, and type. The type specifies whether the entity is
    a client or a supplier.

    :ivar name: First name of the client or supplier.
    :type name: str
    :ivar surname: Surname of the client or supplier.
    :type surname: str
    :ivar type: Specifies the entity type, which can be either "Client" or
        "Fournisseur". Defaults to "Client".
    :type type: str
    """
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
    """
    Represents a transaction performed on a stock item involving a client.

    The Transaction model captures details about stock changes due to purchases
    or sales, as well as associated metadata such as time, client, and price.
    It supports tracking stock levels, client interactions, and pricing details
    for better inventory and sales management.

    :ivar produit: The specific stock item associated with the transaction.
    :type produit: Stock
    :ivar quantity: The quantity of items involved in the transaction.
    :type quantity: int
    :ivar new_stock_qt: The updated stock quantity after the transaction.
    :type new_stock_qt: int
    :ivar time: Timestamp representing when the transaction occurred.
    :type time: datetime
    :ivar client: The client associated with the transaction, optional.
    :type client: Client or None
    :ivar price: The price involved in the transaction, used primarily for
        stock entry operations. Optional.
    :type price: Decimal or None
    :ivar type: The type of transaction, either purchase ("Achat") or sale
        ("Vente").
    :type type: str
    """
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
    """
    Represents a SQL function to extract the month part from a given date or datetime field.

    This class is a Django database function used to generate SQL expressions that extract
    the month component of a date or datetime field in a query.

    :ivar function: The SQL function name used in the query.
    :type function: str
    :ivar template: The SQL template for formatting the function string.
    :type template: str
    :ivar output_field: The type of output returned by the function, corresponding to a Django
        model field (IntegerField in this case).
    :type output_field: models.IntegerField
    """
    function = 'EXTRACT'
    template = '%(function)s(MONTH from %(expressions)s)'
    output_field = models.IntegerField()


class ExtractYear(Func):
    """
    Represents a database function to extract the year from a date or
    datetime field. This class extends Django's `Func` expression to
    create a SQL `EXTRACT(YEAR FROM ...)` statement. It is typically
    used for filtering or annotating querysets based on the year
    component of a date or datetime field.

    This class is constructed automatically by Django ORM query
    expressions when used in annotations or filters.

    :ivar function: The SQL function name, fixed to 'EXTRACT'.
    :type function: str
    :ivar template: The SQL template string used to render the
        expression. Defaults to '%(function)s(YEAR from %(expressions)s)'.
    :type template: str
    :ivar output_field: The expected return type of the function,
        set to `models.IntegerField()` to indicate that this function
        returns an integer.
    :type output_field: models.IntegerField
    """
    function = 'EXTRACT'
    template = '%(function)s(YEAR from %(expressions)s)'
    output_field = models.IntegerField()
