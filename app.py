from flask import Flask, render_template, redirect, request, url_for, session ,flash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import or_
import os

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = 'sqlite:///store.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = "mymarket"
db = SQLAlchemy(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(30))
    password = db.Column(db.String(30))
    is_seller = db.Column(db.Boolean, default=False)
    balance = db.Column(db.Integer, default=0)
    items_bought = db.Column(db.Integer, default=0)
    items_sold = db.Column(db.Integer, default = 0)
    cart = db.relationship('Cart', backref='user', uselist=False)

class Product(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    price = db.Column(db.Integer)
    name = db.Column(db.String(30))
    info = db.Column(db.String(400))
    image = db.Column(db.String(500))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('products', lazy=True))

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text)
    rating = db.Column(db.Integer) 
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))
    user = db.relationship('User', backref=db.backref('comments', lazy=True))
    product = db.relationship('Product', backref=db.backref('comments', lazy=True))


class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    items = db.relationship('CartItem', backref='cart', lazy=True)

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'))
    product_id = db.Column(db.Integer, db.ForeignKey('product.id'))


@app.route("/", methods=["GET"])
def products():
    query = request.args.get("query")
    if query:
        search_results = Product.query.filter(or_(Product.name.ilike(f"%{query}%"))).all()
        return render_template("products.html", products=search_results)
    else:
        return render_template("products.html", products=Product.query.all())

@app.route("/products", methods=["POST"])
def add_products():
    if 'user' not in session:
        return redirect(url_for("login"))
    
    user_id = session['user']['id']
    price = request.form['price']
    name = request.form['name']
    info = request.form["info"]
    image = request.files['image']
    if image.filename == "":
        return "No selected file"
    
    filename = "".join(image.filename.split())
    static_dir = os.path.join(app.root_path, "static")
    if not os.path.exists(static_dir):
        os.makedirs(static_dir)
    image_path = os.path.join(static_dir, filename)
    image.save(image_path)
    relative_path = os.path.join("static", filename)
    product = Product(name=name, price=price, image=relative_path, info=info, user_id=user_id)
    
    

    db.session.add(product)
    db.session.commit()
    return redirect(url_for("products"))

@app.route("/product/delete/<int:product_id>", methods=["POST"])
def delete_product(product_id):
    if 'user' not in session:
        return redirect(url_for("login"))
    
    user_id = session['user']['id']
    product = Product.query.get(product_id)
    
    if product and product.user_id == user_id:
        image_path = os.path.join(app.root_path, product.image)
        if os.path.exists(image_path):
            os.remove(image_path)
        db.session.delete(product)
        db.session.commit()
    
    return redirect(url_for('products'))

@app.route("/register")
def register():
    return render_template("register.html")

@app.route("/register", methods=["POST"])
def register_post():
    username = request.form["username"]
    password = request.form["password"]
    role = request.form["role"]
    if role == "Seller":
        user = User(username=username, password=password, is_seller=True, balance=10000000)
    else:
        user = User(username=username, password=password, is_seller=False, balance=9999999)
    db.session.add(user)
    db.session.commit()
    return redirect(url_for("login"))

@app.route("/login")
def login():
    return render_template("login.html")

@app.route("/login", methods=["POST"])
def login_post():
    username = request.form["username"]
    password = request.form["password"]
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['user'] = {'id': user.id, "is_seller": user.is_seller, "balance": user.balance}
        session.modified = True
        return redirect(url_for("products"))
    return redirect(url_for("login"))

@app.route("/logout")
def logout():
    del session["user"]
    session.modified = True
    return redirect(url_for("products"))

@app.route("/aboutus")
def aboutus():
    return render_template("aboutus.html")


@app.route("/profile")
def user_profile():
    if 'user' in session:
        user_id = session['user']['id']
        user = User.query.get(user_id)
        items_bought = user.items_bought
        if user:
            return render_template("profile.html", username=user.username,items_bought=items_bought,user=user)
    return redirect(url_for("login"))

@app.route("/add_to_cart/<int:product_id>", methods=["POST"])
def add_to_cart(product_id):
    if 'user' in session:
        user_id = session['user']['id']
        user = User.query.get(user_id)
        product = Product.query.get(product_id)
        if user and product:
            if not user.cart:
                cart = Cart(user_id=user.id)
                db.session.add(cart)
                db.session.commit()
            cart_item = CartItem(cart_id=user.cart.id, product_id=product.id)
            db.session.add(cart_item)
            db.session.commit()
            return redirect(url_for("cart"))
    return redirect(url_for("login"))

@app.route("/cart")
def cart():
    if 'user' in session:
        user_id = session['user']['id']
        user = User.query.get(user_id)
        if user and user.cart:
            cart_items = CartItem.query.filter_by(cart_id=user.cart.id).all()
            products = [Product.query.get(item.product_id) for item in cart_items]
            return render_template("cart.html", products=products)
    return redirect(url_for("products"))

@app.route("/remove_from_cart/<int:product_id>", methods=["POST"])
def remove_from_cart(product_id):
    if 'user' in session:
        user_id = session['user']['id']
        user = User.query.get(user_id)
        if user and user.cart:
            cart_item = CartItem.query.filter_by(cart_id=user.cart.id, product_id=product_id).first()
            if cart_item:
                db.session.delete(cart_item)
                db.session.commit()
    return redirect(url_for("cart"))

@app.route("/product/<int:product_id>", methods=["GET"])
def product_info(product_id):
    product = Product.query.get(product_id)
    user = User.query.get_or_404(product.user_id)
    if product:
        related_products = get_related_products(product_id)
        return render_template("productinfo.html", product=product, related_products=related_products,user=user)
    return redirect(url_for('products'))


@app.route("/buy_product/<int:product_id>", methods=["POST"])
def buy_product(product_id):
    if 'user' in session:
        user_id = session['user']['id']
        user = db.session.get(User, user_id) 
        product = db.session.get(Product, product_id)  
        
        if user and product:
            if user.balance >= product.price: 
                user.balance -= product.price  
                user.items_bought += 1
                db.session.commit()
                
                session['user']['balance'] = user.balance
                session.modified = True 
                
                cart_item = CartItem.query.filter_by(cart_id=user.cart.id, product_id=product_id).first()
                if cart_item:
                    db.session.delete(cart_item)
                    db.session.commit()

                return redirect(url_for("purchase"))
            else:
                return render_template("404.html")
    return redirect(url_for("cart"))

@app.route('/submit_comment/<int:product_id>', methods=['POST'])
def submit_comment(product_id):
    if 'user' in session:
        content = request.form['content']
        rating = request.form['rating'] 
        new_comment = Comment(content=content, rating=rating, user_id=session['user']['id'], product_id=product_id)
        db.session.add(new_comment)
        db.session.commit()
        flash('Comment added successfully!', 'success')
    else:
        flash('You need to be logged in to comment.', 'danger')
    return redirect(url_for('product_info', product_id=product_id))

@app.route("/product/comment/delete/<int:comment_id>", methods=["POST"])
def delete_comment(comment_id):
    if 'user' in session:
        user_id = session['user']['id']
        comment = Comment.query.get(comment_id)
        if comment and comment.user_id == user_id:
            db.session.delete(comment)
            db.session.commit()
    return redirect(url_for('product_info', product_id=comment.product_id))

def get_related_products(product_id, limit=4):
    product = Product.query.get(product_id)
    related_products = Product.query.filter(Product.id != product_id).limit(limit).all()
    return related_products

@app.route("/purchase_success")
def purchase():
    return render_template("purchase.html")

@app.route("/other_user_profile/<int:user_id>")
def other_user_profile(user_id):
    user = db.session.get(User, user_id) 
    product = Product.query.get(user_id)
    if user:
        return render_template("profile.html", user=user,product=product)
    else:
        return render_template("404.html")

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
