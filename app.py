from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
import os

app = Flask(__name__)

load_dotenv()
app.secret_key = os.getenv('SECRET_KEY')

# MySQL Config
app.config['MYSQL_HOST'] = os.getenv('MYSQL_HOST')
app.config['MYSQL_USER'] = os.getenv('MYSQL_USER')
app.config['MYSQL_PASSWORD'] = os.getenv('MYSQL_PASSWORD')
app.config['MYSQL_DB'] = os.getenv('MYSQL_DB')

mysql = MySQL(app)

@app.route('/')
def home():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM categories")
    categories = cur.fetchall()
    cur.close()
    return render_template('home.html', categories=categories)

# Admin Login Route
@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        if user:
            print(f"User found: {user}")
            print(f"Password check: {check_password_hash(user[5], password_input)}")
            print(f"Is admin: {user[6]}")
            if check_password_hash(user[5], password_input) and user[6]:
                session['username'] = username
                session['user_id'] = user[0]
                session['admin'] = True
                print("Admin login successful")
                return redirect(url_for('admin_dashboard'))
            else:
                flash('Invalid credentials or not an admin')
        else:
            flash('User not found')
        cur.close()
    return render_template('admin_login.html')

# Admin Dashboard Route
@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    total_users = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM products")
    total_products = cur.fetchone()[0]
    
    # Get order statistics
    cur.execute("SELECT COUNT(*) FROM orders")
    total_orders = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM orders WHERE status = 'pending'")
    pending_orders = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('admin_dashboard.html', 
        admin=session['username'],
        total_users=total_users,
        total_products=total_products,
        total_orders=total_orders,
        pending_orders=pending_orders)

# Admin Logout Route
@app.route('/admin/logout')
def admin_logout():
    session.pop('admin', None)
    session.pop('username', None)
    session.pop('user_id', None)
    return redirect(url_for('admin_login'))

# Admin Products Route
@app.route('/admin/products')
def admin_products():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT p.*, c.name as category_name FROM products p JOIN categories c ON p.category_id = c.id")
    products = cur.fetchall()
    
    # Get categories for the add product form
    cur.execute("SELECT id, name FROM categories")
    categories = cur.fetchall()
    cur.close()
    
    return render_template('admin_products.html', products=products, categories=categories)

# Admin Orders Route
@app.route('/admin/orders')
def admin_orders():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    # Get all orders with user details
    cur.execute("""
        SELECT 
            o.id as order_id,
            u.username,
            o.total_amount,
            o.status,
            o.payment_status,
            o.created_at,
            COUNT(oi.id) as item_count
        FROM orders o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN order_items oi ON o.id = oi.order_id
        GROUP BY o.id, u.username, o.total_amount, o.status, o.payment_status, o.created_at
        ORDER BY o.created_at DESC
    """)
    orders = cur.fetchall()
    
    # Get order statuses for filtering
    cur.execute("SELECT DISTINCT status FROM orders ORDER BY status")
    statuses = [status[0] for status in cur.fetchall()]
    
    cur.close()
    
    return render_template('admin_orders.html', orders=orders, statuses=statuses)

# Order Details Route
@app.route('/admin/orders/<int:order_id>')
def order_details(order_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    # Get order details
    cur.execute("""
        SELECT 
            o.*, 
            u.name as customer_name,
            u.email,
            u.phone,
            o.shipping_address,
            o.shipping_city,
            o.shipping_state,
            o.shipping_zip,
            o.payment_method
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = %s
    """, (order_id,))
    order = cur.fetchone()
    
    if not order:
        flash('Order not found')
        return redirect(url_for('admin_orders'))
    
    # Get order items
    cur.execute("""
        SELECT 
            oi.*, 
            p.name as product_name,
            p.price as product_price,
            p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cur.fetchall()
    
    cur.close()
    
    return render_template('order_details.html', order=order, items=items)

# Update Order Status Route
@app.route('/admin/orders/<int:order_id>/status', methods=['POST'])
def update_order_status(order_id):
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    new_status = request.form.get('status')
    if not new_status:
        flash('Please select a status')
        return redirect(url_for('order_details', order_id=order_id))
    
    cur = mysql.connection.cursor()
    cur.execute("UPDATE orders SET status = %s WHERE id = %s", (new_status, order_id))
    mysql.connection.commit()
    cur.close()
    
    flash('Order status updated successfully')
    return redirect(url_for('order_details', order_id=order_id))

# Add Product Route
@app.route('/admin/add_product', methods=['GET', 'POST'])
def add_product():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, name FROM categories")
    categories = cur.fetchall()
    
    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        price = request.form['price']
        image_url = request.form['image_url']
        category_id = request.form['category_id']
        
        cur.execute("""
            INSERT INTO products (name, description, price, image_url, category_id)
            VALUES (%s, %s, %s, %s, %s)
        """, (name, description, price, image_url, category_id))
        mysql.connection.commit()
        cur.close()
        flash('Product added successfully')
        return redirect(url_for('admin_products'))
    
    cur.close()
    return render_template('add_product.html', categories=categories)

# Checkout Route
@app.route('/checkout', methods=['GET', 'POST'])
def checkout():
    if 'username' not in session:
        flash('Please login to checkout')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        # Get shipping details
        shipping_address = request.form.get('shipping_address')
        shipping_city = request.form.get('shipping_city')
        shipping_state = request.form.get('shipping_state')
        shipping_zip = request.form.get('shipping_zip')
        payment_method = request.form.get('payment_method')
        
        if not all([shipping_address, shipping_city, shipping_state, shipping_zip, payment_method]):
            flash('Please fill in all shipping details')
            return redirect(url_for('checkout'))
            
        # Get user's cart items
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT c.product_id, c.quantity, p.price, p.name, p.image_url, p.description
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (session['user_id'],))
        cart_items = cur.fetchall()
        
        if not cart_items:
            flash('Your cart is empty')
            return redirect(url_for('cart'))
            
        # Calculate total amount
        total = sum(item[2] * item[1] for item in cart_items)
        
        # Create order
        cur.execute("""
            INSERT INTO orders (user_id, total_amount, status, payment_status, payment_method,
                              shipping_address, shipping_city, shipping_state, shipping_zip)
            VALUES (%s, %s, 'pending', 'pending', %s, %s, %s, %s, %s)
        """, (session['user_id'], total, payment_method,
              shipping_address, shipping_city, shipping_state, shipping_zip))
        order_id = cur.lastrowid
        
        # Create order items
        for item in cart_items:
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item[0], item[1], item[2]))
        
        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id = %s", (session['user_id'],))
        
        mysql.connection.commit()
        cur.close()
        
        flash('Order placed successfully!')
        return redirect(url_for('order_confirmation', order_id=order_id))
    
    # For GET request, show checkout form
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.product_id, c.quantity, p.name, p.price, p.image_url, p.description
        FROM cart c
        JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (session['user_id'],))
    cart_items = cur.fetchall()
    
    if not cart_items:
        flash('Your cart is empty')
        return redirect(url_for('cart'))
        
    total = sum(item[3] * item[1] for item in cart_items)
    
    cur.close()
    return render_template('checkout.html', cart_items=cart_items, total=total)

# User Orders Route
@app.route('/orders')
def user_orders():
    if 'username' not in session:
        flash('Please login to view your orders')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    # Get user's orders with status
    cur.execute("""
        SELECT 
            o.id as order_id,
            o.total_amount,
            o.status,
            o.payment_status,
            o.created_at,
            COUNT(oi.id) as item_count
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        WHERE o.user_id = %s
        GROUP BY o.id, o.total_amount, o.status, o.payment_status, o.created_at
        ORDER BY o.created_at DESC
    """, (session['user_id'],))
    orders = cur.fetchall()
    
    cur.close()
    
    return render_template('user_orders.html', orders=orders)

# Order Tracking Route
@app.route('/orders/<int:order_id>/tracking')
def order_tracking(order_id):
    if 'username' not in session:
        flash('Please login to track your order')
        return redirect(url_for('login'))
    
    cur = mysql.connection.cursor()
    # Get order details
    cur.execute("""
        SELECT 
            o.*, 
            u.name as customer_name,
            u.email,
            u.phone,
            o.shipping_address,
            o.shipping_city,
            o.shipping_state,
            o.shipping_zip,
            o.payment_method
        FROM orders o
        JOIN users u ON o.user_id = u.id
        WHERE o.id = %s AND o.user_id = %s
    """, (order_id, session['user_id']))
    order = cur.fetchone()
    
    if not order:
        flash('Order not found')
        return redirect(url_for('orders'))
    
    # Get order items
    cur.execute("""
        SELECT 
            oi.*, 
            p.name as product_name,
            p.price as product_price,
            p.image_url
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        WHERE oi.order_id = %s
    """, (order_id,))
    items = cur.fetchall()
    
    cur.close()
    
    return render_template('order_tracking.html', order=order, items=items)

# Admin Analytics Route
@app.route('/admin/analytics')
def admin_analytics():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    
    # Get total sales
    cur.execute("SELECT SUM(total_amount) as total_sales FROM orders")
    total_sales = cur.fetchone()[0] or 0
    
    # Get order statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN status = 'pending' THEN 1 ELSE 0 END) as pending_orders,
            SUM(CASE WHEN status = 'processing' THEN 1 ELSE 0 END) as processing_orders,
            SUM(CASE WHEN status = 'shipped' THEN 1 ELSE 0 END) as shipped_orders,
            SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END) as delivered_orders,
            SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_orders
        FROM orders
    """)
    order_stats = cur.fetchone()
    
    # Get payment statistics
    cur.execute("""
        SELECT 
            COUNT(*) as total_orders,
            SUM(CASE WHEN payment_status = 'pending' THEN 1 ELSE 0 END) as pending_payments,
            SUM(CASE WHEN payment_status = 'completed' THEN 1 ELSE 0 END) as completed_payments,
            SUM(CASE WHEN payment_status = 'failed' THEN 1 ELSE 0 END) as failed_payments
        FROM orders
    """)
    payment_stats = cur.fetchone()
    
    # Get top selling products
    cur.execute("""
        SELECT 
            p.name as product_name,
            SUM(oi.quantity) as total_sold,
            SUM(oi.quantity * oi.price) as total_revenue
        FROM order_items oi
        JOIN products p ON oi.product_id = p.id
        GROUP BY p.id, p.name
        ORDER BY total_sold DESC
        LIMIT 5
    """)
    top_products = cur.fetchall()
    
    # Get order timeline
    cur.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as order_count
        FROM orders
        WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 30 DAY)
        GROUP BY DATE(created_at)
        ORDER BY date
    """)
    order_timeline = cur.fetchall()
    
    cur.close()
    
    # Format data for Chart.js
    order_stats_data = json.dumps([
        order_stats[1] if order_stats else 0,
        order_stats[2] if order_stats else 0,
        order_stats[3] if order_stats else 0,
        order_stats[4] if order_stats else 0,
        order_stats[5] if order_stats else 0
    ])
    
    payment_stats_data = json.dumps([
        payment_stats[1] if payment_stats else 0,
        payment_stats[2] if payment_stats else 0,
        payment_stats[3] if payment_stats else 0
    ])
    
    return render_template('admin_analytics.html', 
        total_sales=total_sales,
        order_stats=order_stats_data,
        payment_stats=payment_stats_data,
        top_products=top_products,
        order_timeline=order_timeline)

# Admin Carts Route
@app.route('/admin/carts')
def admin_carts():
    if not session.get('admin'):
        return redirect(url_for('admin_login'))
    
    cur = mysql.connection.cursor()
    # Get all carts with user and product details
    cur.execute("""
        SELECT 
            c.id as cart_id,
            u.username,
            p.name as product_name,
            p.price,
            c.quantity,
            c.added_at
        FROM cart c
        JOIN users u ON c.user_id = u.id
        JOIN products p ON c.product_id = p.id
        ORDER BY c.added_at DESC
    """)
    carts = cur.fetchall()
    cur.close()
    
    return render_template('admin_carts.html', carts=carts)

# Order Cancellation Route
@app.route('/admin/orders/<int:order_id>/cancel', methods=['POST'])
def cancel_order(order_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    
    # Check if order exists and is not already cancelled
    cur.execute("SELECT * FROM orders WHERE id = %s AND status != 'Cancelled'", (order_id,))
    order = cur.fetchone()
    
    if not order:
        return jsonify({'error': 'Order not found or already cancelled'}), 404

    # Update order status to Cancelled
    cur.execute("UPDATE orders SET status = 'Cancelled' WHERE id = %s", (order_id,))
    mysql.connection.commit()
    
    # Refund payment if payment status is Completed
    if order[6] == 'Completed':
        cur.execute("UPDATE orders SET payment_status = 'Refunded' WHERE id = %s", (order_id,))
        mysql.connection.commit()
    
    cur.close()
    return jsonify({'message': 'Order cancelled successfully'})

# Order Refund Route
@app.route('/admin/orders/<int:order_id>/refund', methods=['POST'])
def refund_order(order_id):
    if not session.get('admin'):
        return jsonify({'error': 'Unauthorized'}), 401

    cur = mysql.connection.cursor()
    
    # Check if order exists and has a completed payment
    cur.execute("SELECT * FROM orders WHERE id = %s AND payment_status = 'Completed'", (order_id,))
    order = cur.fetchone()
    
    if not order:
        return jsonify({'error': 'Order not found or payment not completed'}), 404

    # Update payment status to Refunded
    cur.execute("UPDATE orders SET payment_status = 'Refunded' WHERE id = %s", (order_id,))
    mysql.connection.commit()
    
    cur.close()
    return jsonify({'message': 'Order refunded successfully'})

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        password = generate_password_hash(request.form['password'])

        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO users (username, name, email, phone, password)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, name, email, phone, password))
            mysql.connection.commit()
            flash('Registration successful! Login now.')
            return redirect(url_for('login'))
        except Exception as e:
            print(e)
            flash('Username or Email already exists or invalid data.')
        finally:
            cur.close()

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password_input = request.form['password']
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()
        if user and check_password_hash(user[5], password_input):
            session['username'] = username
            session['user_id'] = user[0]  # Save user_id in session (assuming user[0] is id)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid credentials')
    return render_template('login.html')


@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        return render_template('dashboard.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/profile')
def profile():
    if 'username' in session:
        return render_template('profile.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/users')
def show_users():
    if 'username' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, username, name, email, phone FROM users")
        users = cur.fetchall()
        cur.close()
        return render_template('users.html', users=users)
    return redirect(url_for('login'))

@app.route('/categories/<category>')
def show_category(category):
    if not session.get('username'):
        return redirect(url_for('login'))

    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM products WHERE category = %s", (category,))
    products = cursor.fetchall()
    cursor.close()
    conn.close()
    return render_template('categories.html', category=category, products=products)

@app.route('/category/<int:category_id>')
def show_products_by_category(category_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT name FROM categories WHERE id=%s", (category_id,))
    category = cur.fetchone()
    if not category:
        flash("Category not found")
        return redirect(url_for('home'))

    # Get products with their IDs and other details
    cur.execute("""
        SELECT p.id, p.name, p.description, p.price, p.image_url, p.category_id, c.name as category_name
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.category_id = %s
    """, (category_id,))
    products = cur.fetchall()
    
    # Verify we have products
    if not products:
        flash("No products found in this category")
        return redirect(url_for('home'))

    cur.close()
    return render_template('products.html', category=category[0], products=products)


@app.route('/add_to_cart/<int:product_id>', methods=['POST'])
def add_to_cart(product_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to add items to cart.'}), 401

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    try:
        # Check if product exists
        cur.execute("SELECT id FROM products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        if not product:
            return jsonify({'success': False, 'message': 'Product not found'}), 404

        # Check if product already in cart, increment quantity if yes
        cur.execute("SELECT id, quantity FROM cart WHERE user_id=%s AND product_id=%s", (user_id, product_id))
        existing = cur.fetchone()

        if existing:
            new_qty = existing[1] + 1
            cur.execute("UPDATE cart SET quantity=%s WHERE id=%s", (new_qty, existing[0]))
        else:
            cur.execute("INSERT INTO cart (user_id, product_id, quantity) VALUES (%s, %s, %s)", (user_id, product_id, 1))

        # Log user activity
        cur.execute("INSERT INTO user_activity (user_id, action, product_id) VALUES (%s, %s, %s)",
                    (user_id, 'add_to_cart', product_id))

        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Product added to cart successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in add_to_cart: {str(e)}")  # Add error logging
        return jsonify({'success': False, 'message': 'Failed to add product to cart'}), 500

    finally:
        cur.close()

@app.route('/update_cart/<int:cart_id>/<int:change>', methods=['POST'])
def update_cart(cart_id, change):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to update cart.'}), 401

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    try:
        # Check if cart item exists and belongs to user
        cur.execute("SELECT * FROM cart WHERE id=%s AND user_id=%s", (cart_id, user_id))
        cart_item = cur.fetchone()
        if not cart_item:
            return jsonify({'success': False, 'message': 'Cart item not found'}), 404

        new_quantity = cart_item[3] + change
        if new_quantity < 1:
            cur.execute("DELETE FROM cart WHERE id=%s", (cart_id,))
        else:
            cur.execute("UPDATE cart SET quantity=%s WHERE id=%s", (new_quantity, cart_id))

        mysql.connection.commit()
        return jsonify({'success': True, 'message': 'Cart updated successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in update_cart: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to update cart'}), 500

    finally:
        cur.close()

@app.route('/remove_from_cart/<int:cart_id>', methods=['POST'])
def remove_from_cart(cart_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': 'Please login to remove item.'}), 401

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    try:
        # Check if cart item exists and belongs to user
        cur.execute("SELECT * FROM cart WHERE id=%s AND user_id=%s", (cart_id, user_id))
        cart_item = cur.fetchone()
        if not cart_item:
            return jsonify({'success': False, 'message': 'Cart item not found'}), 404

        cur.execute("DELETE FROM cart WHERE id=%s", (cart_id,))
        mysql.connection.commit()
        
        # Log user activity
        cur.execute("INSERT INTO user_activity (user_id, action, product_id) VALUES (%s, %s, %s)",
                     (user_id, 'remove_from_cart', cart_item[2]))

        return jsonify({'success': True, 'message': 'Item removed successfully'}), 200

    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in remove_from_cart: {str(e)}")
        return jsonify({'success': False, 'message': 'Failed to remove item'}), 500

    finally:
        cur.close()

# Cart Route
@app.route('/cart')
def cart():
    if 'user_id' not in session:
        flash('Please login to view your cart')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    try:
        # Get cart items
        cur.execute("""
            SELECT c.id as cart_id, p.name as product_name, p.price, c.quantity, p.image_url, p.description
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cur.fetchall()

        # Calculate total
        total = sum(item[2] * item[3] for item in cart_items)

        return render_template('cart.html', cart_items=cart_items, total=total)

    except Exception as e:
        print(f"Error in cart: {str(e)}")
        flash('An error occurred while loading your cart.')
        return redirect(url_for('home'))

    finally:
        cur.close()

    try:
        # Get cart items
        cur.execute("""
            SELECT c.id, c.product_id, c.quantity, p.name, p.price, p.image_url, p.description
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cur.fetchall()

        # Calculate total
        total = sum(item[2] * item[4] for item in cart_items)

        return render_template('checkout.html', cart_items=cart_items, total=total)

    except Exception as e:
        print(f"Error in checkout: {str(e)}")
        flash('An error occurred while processing your checkout.')
        return redirect(url_for('cart'))

    finally:
        cur.close()

@app.route('/place_order', methods=['POST'])
def place_order():
    if 'user_id' not in session:
        flash('Please login to place an order.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    try:
        # Get form data
        full_name = request.form['full_name']
        phone = request.form['phone']
        email = request.form['email']
        shipping_address = request.form['shipping_address']
        city = request.form['city']
        state = request.form['state']
        zip_code = request.form['zip_code']
        payment_method = request.form['payment_method']

        # Get cart items
        cur.execute("""
            SELECT c.id, c.product_id, c.quantity, p.name, p.price
            FROM cart c
            JOIN products p ON c.product_id = p.id
            WHERE c.user_id = %s
        """, (user_id,))
        cart_items = cur.fetchall()

        if not cart_items:
            flash('Your cart is empty.')
            return redirect(url_for('cart'))

        # Calculate total amount
        total = sum(item[4] * item[2] for item in cart_items)

        # Insert order into orders table
        cur.execute("""
            INSERT INTO orders (user_id, full_name, phone, email, shipping_address, city, state, zip_code,
                              payment_method, total_amount, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'pending')
        """, (user_id, full_name, phone, email, shipping_address, city, state, zip_code,
             payment_method, total))
        order_id = cur.lastrowid

        # Insert order items
        for item in cart_items:
            cur.execute("""
                INSERT INTO order_items (order_id, product_id, quantity, price)
                VALUES (%s, %s, %s, %s)
            """, (order_id, item[1], item[2], item[4]))

        # Clear cart
        cur.execute("DELETE FROM cart WHERE user_id = %s", (user_id,))

        # Log order activity
        cur.execute("INSERT INTO user_activity (user_id, action, order_id) VALUES (%s, %s, %s)",
                   (user_id, 'placed_order', order_id))

        mysql.connection.commit()
        
        # Send order confirmation email
        send_order_confirmation_email(user_id, order_id, total)

        flash('Your order has been placed successfully! You will receive a confirmation email shortly.')
        return redirect(url_for('order_confirmation', order_id=order_id))

    except Exception as e:
        mysql.connection.rollback()
        print(f"Error in place_order: {str(e)}")
        flash('An error occurred while processing your order. Please try again.')
        return redirect(url_for('checkout'))

    finally:
        cur.close()

@app.route('/order_confirmation/<int:order_id>')
def order_confirmation(order_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    cur = mysql.connection.cursor()
    try:
        # Get order details
        cur.execute("""
            SELECT o.*, u.name as user_name
            FROM orders o
            JOIN users u ON o.user_id = u.id
            WHERE o.id = %s AND o.user_id = %s
        """, (order_id, session['user_id']))
        order = cur.fetchone()

        if not order:
            flash('Order not found or unauthorized access.')
            return redirect(url_for('home'))

        # Get order items
        cur.execute("""
            SELECT oi.*, p.name as product_name, p.image_url
            FROM order_items oi
            JOIN products p ON oi.product_id = p.id
            WHERE oi.order_id = %s
        """, (order_id,))
        order_items = cur.fetchall()

        return render_template('order_confirmation.html', order=order, order_items=order_items)

    except Exception as e:
        print(f"Error in order_confirmation: {str(e)}")
        flash('An error occurred while loading order confirmation.')
        return redirect(url_for('home'))

    finally:
        cur.close()

def update_cart_count():
    if 'user_id' not in session:
        return jsonify({'count': 0})
    
    cur = mysql.connection.cursor()
    cur.execute("SELECT COUNT(*) FROM cart WHERE user_id=%s", (session['user_id'],))
    count = cur.fetchone()[0]
    cur.close()
    return jsonify({'count': count})

@app.route('/check_session')
def check_session():
    return jsonify({
        'logged_in': 'user_id' in session,
        'user_id': session.get('user_id')
    })

@app.route('/cart')
def view_cart():
    if 'user_id' not in session:
        flash('Please login to view your cart.')
        return redirect(url_for('login'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT c.id, p.name, p.price, c.quantity
        FROM cart c JOIN products p ON c.product_id = p.id
        WHERE c.user_id = %s
    """, (user_id,))
    cart_items = cur.fetchall()
    cur.close()
    return render_template('cart.html', cart_items=cart_items)

@app.route('/search')
def search():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    query = request.args.get('query', '')
    if not query:
        flash("Please enter a search term.")
        return redirect(url_for('home'))

    user_id = session['user_id']
    cur = mysql.connection.cursor()

    # Search products by name
    cur.execute("SELECT * FROM products WHERE name LIKE %s", (f"%{query}%",))
    results = cur.fetchall()

    # Log user search in search_history table
    cur.execute("INSERT INTO search_history (user_id, query) VALUES (%s, %s)", (user_id, query))
    mysql.connection.commit()
    cur.close()

    return render_template('search_results.html', results=results, query=query)

@app.before_request
def update_cart_count():
    if 'user_id' in session:
        cur = mysql.connection.cursor()
        cur.execute("SELECT SUM(quantity) FROM cart WHERE user_id = %s", (session['user_id'],))
        result = cur.fetchone()
        session['cart_count'] = result[0] if result[0] else 0
        cur.close()
    else:
        session['cart_count'] = 0

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM products WHERE id = %s", (product_id,))
    product = cur.fetchone()
    cur.close()
    if not product:
        flash('Product not found')
        return redirect(url_for('home'))
    return render_template('product_detail.html', product=product)

@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True)
