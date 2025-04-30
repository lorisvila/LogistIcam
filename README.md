# Projet de Programmation - EC 06 Prog 2

## Actors :
- NELLENBACH Quentin 
- LAURIE Téo
- VILA Loris

## Project specifications

- ### Pages / Templates :
    The website / app will inherit a global layout, then insert pages data into the website

  - **Layout :** The page will contain 3 zones :    
    - _Header :_ At the top of the page where there will be informations about the state of the client authentification, the app title and page location ;
    - _Lateral Navbar & controls :_ Contains the app main menu. Each page can also have multiple sections and needs inputs ;
    - _Content zone :_ Content of the current page rendered by the internal django router & rendering engine.

  - **Pages :**
    - _Landing page :_ Needs to give a quick looks to all important KPIs to the client (low stocks, daily transactions...) ;
    - _Stocks page :_ Needs to show a table of all the company current stocks & be able to search and filter trough them ;
    - _Transactions page :_ : Like to Stocks page, it needs to display all the past transactions and be able to search and filter through them.
    - _Maybe :_ If we decide to add customer records into the database and to link transactions to a client. It may be interesting to have :
      - a client managing page, where it could be possible to modify the records of a client ;
      - a sum-up of all the transactions of a client + other stats.

- ### Functionalities :
  - **Authentification :**
    - The user must authentificate to access to the website / app ;
    - The auth should be handle via the LDAP AD DS server, with user and roles attributions.