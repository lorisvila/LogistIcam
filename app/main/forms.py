from django import forms

from .models import Stock, Transaction, Client


class StockForm(forms.ModelForm):
    """
    Represents a form for the Stock model.

    This class provides a model-based form for interacting with the Stock data.
    It allows creating and updating Stock instances through a form representation.

    :ivar model: The model class associated with the form.
    :type model: Type[Stock]
    :ivar fields: The fields from the Stock model included in the form, which
        are `produit`, `quantity`, `prix_vente`, and `prix_achat`.
    :type fields: List[str]
    """
    class Meta:
        model = Stock
        fields = ['produit', 'quantity', 'prix_vente', 'prix_achat']


class TransactionForm(forms.ModelForm):
    """
    Represents a form for creating or updating Transaction instances.

    This class is a Django ModelForm that maps to the Transaction model. It allows
    for creating or updating transaction records with the specified fields such as
    type, product, quantity, and client. The form ensures the validation and integrity
    of the input data according to the constraints defined in the Transaction model.

    :ivar type: The type of the transaction (e.g., sale or purchase).
    :type type: str
    :ivar produit: The product involved in the transaction.
    :type produit: str
    :ivar quantity: The quantity of the product in the transaction.
    :type quantity: int
    :ivar client: The client involved in the transaction.
    :type client: str
    """
    class Meta:
        model = Transaction
        fields = ['type', 'produit', 'quantity', 'client']


class ClientForm(forms.ModelForm):
    """
    Represents a form for creating or updating a Client instance.

    This form is a Django ModelForm connected to the Client model. It is used to
    create or update instances of the Client model based on user input. The form
    automatically applies validation and mappings for the specified fields:
    'name', 'surname', and 'type'.

    :ivar Meta.model: The model associated with this form.
    :type Meta.model: Client
    :ivar Meta.fields: List of fields to include in the form.
    :type Meta.fields: list
    """
    class Meta:
        model = Client
        fields = ['name', 'surname', 'type']
