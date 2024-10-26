from datetime import datetime
import os
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from forms import RegisterForm, DrugForm, EditDrugForm
from flask import session
import hashlib

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def hash_file(file):
    sha256 = hashlib.sha256()
    for chunk in iter(lambda: file.read(4096), b""):
        sha256.update(chunk)
    file.seek(0)
    return sha256.hexdigest()

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:Root123!@localhost/farm'
app.config['SQLALCHEMY_ECHO'] = False
app.config['SECRET_KEY'] = '223dseww323redw32rfgvw2wcvgf3vg3'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

db = SQLAlchemy(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


def has_role(role_name):
    user_role = session.get('user_role')
    return user_role == role_name


@app.context_processor
def utility_processor():
    return dict(has_role=has_role)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role_id = db.Column(db.Integer, db.ForeignKey('role.id'), nullable=False)
    delivery_address = db.Column(db.String(200))
    phone_number = db.Column(db.String(20), nullable=False)

    role = db.relationship('Role', back_populates='users')
    orders = db.relationship('Orders', backref='user')

class Role(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    role_name = db.Column(db.String(50), nullable=False)

    users = db.relationship('User', back_populates='role')

class Drug(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    price = db.Column(db.Float, nullable=False)
    stock = db.Column(db.Integer, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('cat.id'), nullable=False)
    
    images = db.relationship('Image', backref='product')
    category = db.relationship('Cat', backref='drugs')

class Image(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    image_hash = db.Column(db.String(64), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey('drug.id'), nullable=False)

class Cat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)

class Orders(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='Pending')
    order_date = db.Column(db.DateTime, nullable=False, default=datetime.now)

    order_items = db.relationship('OrderItem', backref='orders')

class OrderItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    drug_id = db.Column(db.Integer, db.ForeignKey('drug.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

    product = db.relationship('Drug', backref='order_items')

@app.route('/')
@app.route('/page/<int:page>')
def index(page=1):
    cats = Cat.query.all()

    category_id = request.args.get('category_id')

    drug_query = Drug.query

    if category_id:
        drug_query = drug_query.filter(Drug.category_id == category_id)

    search = request.args.get('psear', '')
    if search:
        drug_query = drug_query.filter(Drug.name.ilike(f"%{search}%"))

    drugs = drug_query.paginate(page=page, per_page=12)
    cart = session.get('cart', {})

    return render_template('index.html', drugs=drugs, cats=cats, cart=cart)


@app.route('/drug/add', methods=['GET', 'POST'])
@login_required
def add_drug():
    if has_role('Пользователь'):
        return redirect(url_for('index'))

    form = DrugForm()

    form.category_id.choices = [(cat.id, cat.name) for cat in Cat.query.all()]

    if form.validate_on_submit():
        drug = Drug(
            name=form.name.data,
            description=form.description.data,
            price=form.price.data,
            stock=form.stock.data,
            category_id=form.category_id.data
        )
        db.session.add(drug)
        db.session.commit() #коммит здесь чтобы получить drug.id

        new_images = request.files.getlist('images') 
        for file in new_images:
            if file and allowed_file(file.filename):
                filename = hash_file(file)
                cover_path = os.path.join('static', 'images', filename)
                file.save(cover_path)

                new_image = Image(image_hash=filename, drug_id=drug.id)
                db.session.add(new_image)

        db.session.commit()
        flash('Препарат успешно добавлен!', 'success')
        return redirect(url_for('index'))

    return render_template('add_drug.html', form=form)



def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in {'png', 'jpg', 'jpeg', 'gif', 'webp'}


@app.route('/drug/<int:drug_id>')
def view_drug(drug_id):
    drug_item = Drug.query.get_or_404(drug_id)
    cart = session.get('cart', {})
    return render_template('view_drug.html', drug=drug_item, cart=cart)


@app.route('/drug/edit/<int:drug_id>', methods=['GET', 'POST'])
@login_required
def edit_drug(drug_id):
    if has_role('Пользователь'):
        return redirect(url_for('index'))
    
    drug = Drug.query.get_or_404(drug_id)
    form = EditDrugForm(obj=drug)

    form.category_id.choices = [(cat.id, cat.name) for cat in Cat.query.all()]

    if form.validate_on_submit():
        drug.name = form.name.data
        drug.description = form.description.data
        drug.price = form.price.data
        drug.stock = form.stock.data
        drug.category_id = form.category_id.data

        new_images = request.files.getlist('images')
        for file in new_images:
            if file and allowed_file(file.filename):
                filename = hash_file(file)
                cover_path = os.path.join('static', 'images', filename)
                file.save(cover_path)

                new_image = Image(image_hash=filename, drug_id=drug.id)
                db.session.add(new_image)

        db.session.commit()
        flash('Препарат успешно изменён!', 'success')
        return redirect(url_for('index'))

    if request.method == 'POST' and 'delete_image' in request.form:
        image_id = request.form['delete_image']
        image = Image.query.get_or_404(image_id)
        db.session.delete(image)
        db.session.commit()
        flash('Изображение успешно удалено!', 'success')
        return redirect(request.url)

    return render_template('edit_drug.html', form=form, drug=drug)


@app.route('/drug/<int:drug_id>/delete', methods=['GET', 'POST'])
@login_required
def delete_drug(drug_id):
    if has_role('Пользователь'):
        return redirect(url_for('index'))
    
    drug = Drug.query.get_or_404(drug_id)

    covers = Image.query.filter_by(drug_id=drug.id)

    for cover in covers:
        if cover:
            cover_path = os.path.join('static', 'images', cover.image_hash)
            if os.path.exists(cover_path):
                os.remove(cover_path)

            db.session.delete(cover)

    db.session.delete(drug)
    db.session.commit()

    flash('Препарат успешно удален!', 'success')
    return redirect(url_for('index'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        user = User.query.filter_by(email=email).first()

        if user and user.password_hash == hash_password(password):
            login_user(user)
            session['user_role'] = user.role.role_name
            flash('Вы успешно вошли!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Неправильное имя пользователя или пароль', 'danger')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    #form.role_id.choices = [(role.id, role.name) for role in Role.query.all()]

    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            flash('Пользователь с таким Email уже существует!', 'danger')
            return redirect(url_for('register'))
        
        new_user = User(
            email=form.email.data,
            password_hash=hash_password(form.password.data),
            name=form.name.data,
            role_id=form.role_id,
            phone_number=form.phone.data
        )

        db.session.add(new_user)
        db.session.commit()

        flash('Вы успешно зарегистрированы!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html', form=form)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/add_to_cart/<int:drug_id>', methods=['POST'])
def add_to_cart(drug_id):
    if 'cart' not in session:
        session['cart'] = {}
    
    str_drug_id = str(drug_id)
    if str_drug_id in session['cart']:
        session['cart'][str_drug_id] += 1
    else:
        session['cart'][str_drug_id] = 1
    
    session.modified = True
    return jsonify(quantity=session['cart'][str_drug_id])

@app.route('/update_cart/<int:drug_id>', methods=['POST'])
def update_cart(drug_id):
    action = request.args.get('action')

    if 'cart' not in session:
        session['cart'] = {}
    
    str_drug_id = str(drug_id)
    if action == 'increase':
        if str_drug_id in session['cart']:
            session['cart'][str_drug_id] += 1
        else:
            session['cart'][str_drug_id] = 1
    elif action == 'decrease':
        if str_drug_id in session['cart'] and session['cart'][str_drug_id] > 0:
            session['cart'][str_drug_id] -= 1
            if session['cart'][str_drug_id] == 0:
                del session['cart'][str_drug_id]

    session.modified = True
    return jsonify(quantity=session['cart'].get(str_drug_id, 0))

@app.route('/cart')
def view_cart():
    cart = session.get('cart', {})

    drugs = Drug.query.all()

    cart_items = []

    total_price = 0

    for drug in drugs:
        quantity = cart.get(str(drug.id), 0)
        if quantity > 0:

            cart_items.append({
                'drug': drug,
                'quantity': quantity,
                'total_price': drug.price * quantity
            })
            total_price += drug.price * quantity

    return render_template('cart.html', cart_items=cart_items, total_price=total_price)

@app.route('/create_order', methods=['GET', 'POST'])
def create_order():
    cart = session.get('cart', {})
    
    if not cart:
        flash('Корзина пуста!', 'warning')
        return redirect(url_for('view_cart'))

    user_id = current_user.id

    new_order = Orders(user_id=user_id, status='Pending')
    db.session.add(new_order)
    db.session.flush()

    for drug_id, quantity in cart.items():
        order_item = OrderItem(order_id=new_order.id, drug_id=int(drug_id), quantity=quantity)
        db.session.add(order_item)

    session['cart'] = {}

    db.session.commit()
    flash('Заказ успешно создан!', 'success')

    return redirect(url_for('view_orders'))


@app.route('/orders')
def view_orders():
    orders = Orders.query.filter_by(user_id=current_user.id).all()

    return render_template('orders.html', orders=orders)

@app.route('/order/<int:order_id>')
def order_details(order_id):
    order = Orders.query.get_or_404(order_id)
    order_items = OrderItem.query.filter_by(order_id=order.id).all()

    # Вычисляем полную стоимость заказа
    total_cost = sum(item.product.price * item.quantity for item in order_items)

    return render_template('order_details.html', order=order, order_items=order_items, total_cost=total_cost)


@app.route('/account')
@login_required
def view_account():

    user = current_user

    return render_template('account.html', user=user)

@app.route('/save_address', methods=['GET','POST'])
@login_required
def save_address():
    data = request.get_json()
    current_user.delivery_address = data['delivery_address']
    db.session.commit() 

    return jsonify(success=True)

@app.route('/clear_cart')
def clear_cart():
    session['cart'] = {}
    return render_template('cart.html', cart_items=[], total_price=0)

if __name__ == '__main__':
    app.run(debug=True)
