# Book--Mart

Book--Mart is an e-commerce store for all kinds of books.

People can search for their favourite books, add them into their cart and can make payment via cards only.

book-mart uses **google book api** for searching and showing different kinds of books and their respective data.  

## Demo

https://github.com/SwayamInSync/Book-Mart/assets/74960567/99a29f6b-d8a0-4ad9-9d0c-a3ee90eb848c



## Technology used:

- Flask
- Bootstrap
- SQLAlchemy (ORM for sqlite database)
- Stripe (for making payments)
## Installation

Use the package manager [pip](https://pip.pypa.io/en/stable/) to install requirements for book-mart.
```bash
pip install -r requirements.txt
```
Before running it on your local environment, create your google developer account and get `api_key` for books, create account on stripe and get hold of `public` and `secret` key and store all of the above information inside `.env` file. You also need to replace `secret_key` and `database url` with your own.

## Contributing
Pull requests are welcome. For major changes, please open an issue first to discuss what you would like to change.
