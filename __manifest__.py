{
    'name': "Payment Provider: Chargily",
    'version': '1.0',
    'depends': ['payment'],
    'author': "Exocode",
    'category': 'Payment',
    'description': """
    Description text
    """,
    # data files always loaded at installation
    'data': [
        'views/payment_provider_views.xml',

        'data/provider_data.xml',
    ],

}
