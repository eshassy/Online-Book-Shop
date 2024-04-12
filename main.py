import os
from dotenv import load_dotenv
from datetime import datetime
import requests
from flask import Flask, request, redirect, render_template, url_for, jsonify, flash
from flask_bootstrap import Bootstrap
import stripe
from smtplib import SMTP
from flask_sqlalchemy import SQLAlchemy
from forms import RegisterForm
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user

load_dotenv()

app = Flask(__name__, static_url_path='')

app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL').replace("://", "ql://", 1)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get("SECRET_KEY")

db = SQLAlchemy(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)

stripe.api_key = os.environ.get('STRIPE_SECRET_API')
api_key = os.environ.get('BOOK_API')
stripe_public_key = os.environ.get('STRIPE_API')

default_endpoint = f'https://www.googleapis.com/books/v1/volumes?q=fantasy+intitle:&filter=paid-ebooks&maxResults=40&key={api_key}'

title = "fantasy"
payable_amount = 0
cart_list = ''


# creating tables

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    email = db.Column(db.String, nullable=False, unique=True)
    password = db.Column(db.String, nullable=False)
    address = db.Column(db.String, nullable=False)
    pincode = db.Column(db.String, nullable=False)
    city = db.Column(db.String, nullable=False)
    state = db.Column(db.String, nullable=False)
    country = db.Column(db.String, nullable=False)

db.create_all()


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    product_id = db.Column(db.String, nullable=False)
    image = db.Column(db.String, nullable=False)
    price = db.Column(db.Integer, nullable=False)
    is_purchased = db.Column(db.Boolean, nullable=False)
    buyer = db.Column(db.String, nullable=False)


db.create_all()


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route("/", methods=['GET', 'POST'])
def home():
    global books
    if request.method == 'POST':
        title = request.form.get('book_name')
        endpoint = f'https://www.googleapis.com/books/v1/volumes?q={title}+intitle:&filter=paid-ebooks&key={api_key}&maxResults=40'
        data = requests.get(endpoint).json()
        book_data = data.get('items')
        books = [book for book in book_data if 'description' in book['volumeInfo']]
        return render_template('index.html', books=books, year=datetime.now().year)
    data = requests.get(default_endpoint).json()
    book_data = data.get('items')
    books = [book for book in book_data if 'description' in book['volumeInfo']]
    return render_template('index.html', books=books, year=datetime.now().year,
                           authenticated=current_user.is_authenticated)


@app.route("/register", methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if request.method == 'POST':
        if form.validate_on_submit():
            already_exist = User.query.filter_by(email=request.form.get('email')).first()
            if not already_exist:
                hash_pass = generate_password_hash(request.form.get('password'), method='pbkdf2:sha256', salt_length=10)
                new_user = User(
                    name=request.form.get('name'),
                    email=request.form.get('email'),
                    password=hash_pass,
                    address=request.form.get('address'),
                    city=request.form.get('city'),
                    pincode=request.form.get('pincode'),
                    state=request.form.get('state'),
                    country=request.form.get('country')
                )
                db.session.add(new_user)
                db.session.commit()
                login_user(new_user)
                return redirect(url_for('home'))
            else:
                flash("You've already signed up with that email, log in instead! ")
                return redirect(url_for('login'))
    return render_template('register1.html', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        hash_password = request.form.get('password')
        found_user = User.query.filter_by(email=email).first()
        if found_user and check_password_hash(found_user.password, hash_password):
            login_user(found_user)
            return redirect(url_for('home'))
        else:
            flash("Check your email / password and try again")
            return redirect(url_for('login'))
    return render_template('login1.html')


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route("/show-book/<id>")
def show_single_book(id):
    get_book = [book for book in books if book['id'] == id]
    if current_user.is_authenticated:
        book = Cart.query.filter_by(buyer=current_user.email, is_purchased=False, product_id=id).first()
        if book:
            message = "Added to cart"
        else:
            message = ""
    else:
        message = ""
    return render_template('single_book.html', year=datetime.now().year, book=get_book[0],
                           authenticated=current_user.is_authenticated, message=message)


@app.route("/add-to-cart/<id>")
def add_to_cart(id):
    if not current_user.is_authenticated:
        return redirect(url_for('login'))

    get_book = [book for book in books if book['id'] == id]
    book = get_book[0]
    new_cart_item = Cart(
        product_id=book["id"],
        title=book['volumeInfo']['title'],
        image=book['volumeInfo']['imageLinks']['thumbnail'],
        price=int(book['saleInfo']['retailPrice']['amount']),
        is_purchased=False,
        buyer=current_user.email
    )
    db.session.add(new_cart_item)
    db.session.commit()
    return redirect(url_for('show_single_book', id=id))


@app.route("/dashboard")
def dashboard():
    cart_books = Cart.query.filter_by(buyer=current_user.email, is_purchased=False).all()
    purchased_books = Cart.query.filter_by(buyer=current_user.email, is_purchased=True).all()
    return render_template('dashboard.html', user=current_user, cart_books=cart_books, purchased_books=purchased_books, authenticated=current_user.is_authenticated)


@app.route("/cart")
def show_cart():
    if not current_user.is_authenticated:
        return redirect(url_for('login'))
    global payable_amount
    global cart_list
    cart_list = ""
    total_price = 0
    all_items = Cart.query.filter_by(buyer=current_user.email, is_purchased=False).all()
    for item in all_items:
        total_price += item.price
    payable_amount = total_price + (0.05 * total_price) - 1
    payable_amount = int(payable_amount)
    cart_list = ', '.join([item.title for item in all_items])
    return render_template('cart.html', cart=all_items, total_price=total_price, payable_amount=payable_amount,
                           public_key=stripe_public_key, authenticated=current_user.is_authenticated)


@app.route("/delete-item/<id>")
def delete_item(id):
    item = Cart.query.get(int(id))
    db.session.delete(item)
    db.session.commit()
    return redirect(url_for('show_cart'))


@app.route('/create-checkout-session', methods=['POST'])
@login_required
def create_checkout_session():
    session = stripe.checkout.Session.create(
        payment_method_types=['card'],
        line_items=[{
            'price_data': {
                'currency': 'inr',
                'product_data': {
                    'name': cart_list,
                },
                'unit_amount': payable_amount * 100,
            },
            'quantity': 1,
        }],
        mode='payment',
        success_url="https://book--mart.herokuapp.com/success",
        cancel_url="https://book--mart.herokuapp.com/failed"

    )
    response = jsonify({'id': session.id})
    return response


@app.route("/success")
@login_required
def success():
    global cart_list
    non_purchased_items = Cart.query.filter_by(buyer=current_user.email, is_purchased=False).all()
    for item in non_purchased_items:
        id = item.id
        book = Cart.query.get(int(id))
        book.is_purchased = True
        db.session.commit()
    cart_list = ""
    return render_template('success.html', authenticated=current_user.is_authenticated)


@app.route("/failed")
@login_required
def failed():
    return render_template('cancel.html', authenticated=current_user.is_authenticated)


if __name__ == '__main__':
    app.run(debug=True)
