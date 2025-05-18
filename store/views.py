from django.shortcuts import render, redirect
from django.contrib import messages
from .models import Customer, Section, Category, Product, Order, ProductImage, Cart, Size, Color, ContactSubmission, ProductRating
from django.utils import timezone
import random
from django.contrib.auth.hashers import make_password, check_password
from django.urls import reverse
from django.http import HttpResponse, JsonResponse
from django.template.loader import get_template
from django.views.decorators.csrf import csrf_exempt

# Create your views here.

def splash(request):
    return render(request, 'splash.html')

def welcome(request):
    sections = Section.objects.all()
    categories = Category.objects.select_related('secid').all()
    products = Product.objects.select_related('catid').prefetch_related('images').all()
    query = request.GET.get('q', '').strip()
    if query:
        # Filter products by name, category, or section
        products = [p for p in products if query.lower() in p.title.lower() or
                    query.lower() in p.catid.title.lower() or
                    query.lower() in p.catid.secid.title.lower()]
    section_data = []
    for section in sections:
        section_categories = [cat for cat in categories if cat.secid_id == section.seid]
        cat_data = []
        for cat in section_categories:
            cat_products = [prod for prod in products if prod.catid_id == cat.catid]
            cat_data.append({'category': cat, 'products': cat_products})
        section_data.append({'section': section, 'categories': cat_data})
    return render(request, 'welcome.html', {'section_data': section_data, 'search_query': query})

def contact(request):
    return render(request, 'contact.html')

def admin_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username == 'admin1' and password == 'Admin@123':
            request.session['admin_logged_in'] = True
            return redirect('admin_dashboard')
        else:
            return render(request, 'admin_login.html', {'error': 'Invalid credentials'})
    
    return render(request, 'admin_login.html')

def admin_dashboard(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Basic stats
    product_count = Product.objects.count()
    customer_count = Customer.objects.count()
    category_count = Category.objects.count()
    order_count = Order.objects.count()
    
    # Report data
    from django.db.models import Count, Sum
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models.functions import TruncMonth
    
    # Top Products
    top_products = Product.objects.annotate(
        order_count=Count('order')
    ).order_by('-order_count')[:5]
    
    # Active Customers (last 30 days)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    active_customers = Customer.objects.filter(
        order__date__gte=thirty_days_ago
    ).annotate(
        order_count=Count('order')
    ).order_by('-order_count')[:5]
    
    # Sales by Category (Category -> Product -> Order)
    sales_by_category = Category.objects.annotate(
        total_sales=Sum('product__order__amount')
    ).order_by('-total_sales')[:5]
    
    # Orders by Status
    orders_by_status = Order.objects.values('status').annotate(
        count=Count('orderid')
    ).order_by('status')
    
    # Recent Orders
    recent_orders = Order.objects.select_related('custid').order_by('-date')[:5]
    
    # Monthly Revenue
    revenue_by_month = Order.objects.exclude(status='Cancelled').annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_revenue=Sum('amount')
    ).order_by('-month')[:6]  # Last 6 months
    
    # Low Stock Products
    low_stock_products = Product.objects.filter(quantity__lt=10).select_related('catid').order_by('quantity')
    
    # Calculate statistics
    total_low_stock = low_stock_products.count()
    critical_stock = low_stock_products.filter(quantity__lte=5).count()
    low_stock = low_stock_products.filter(quantity__gt=5).count()
    
    # Popular Sizes (Size -> Product -> Order)
    popular_sizes = Size.objects.annotate(
        order_count=Count('products__order')
    ).order_by('-order_count')[:5]
    
    # Customer Registration Trend
    customer_trend = Customer.objects.annotate(
        month=TruncMonth('regdate')
    ).values('month').annotate(
        new_customers=Count('custid')
    ).order_by('-month')[:6]  # Last 6 months
    
    # Never Ordered Customers
    customers_without_orders = Customer.objects.filter(order__isnull=True)[:5]
    
    return render(request, 'admin_dashboard.html', {
        'product_count': product_count,
        'customer_count': customer_count,
        'category_count': category_count,
        'order_count': order_count,
        'top_products': top_products,
        'active_customers': active_customers,
        'sales_by_category': sales_by_category,
        'orders_by_status': orders_by_status,
        'recent_orders': recent_orders,
        'monthly_revenue': revenue_by_month,
        'low_stock_products': low_stock_products,
        'popular_sizes': popular_sizes,
        'customer_trend': customer_trend,
        'customers_without_orders': customers_without_orders,
        'total_low_stock': total_low_stock,
        'critical_stock': critical_stock,
        'low_stock': low_stock
    })

def admin_logout(request):
    request.session.flush()
    return redirect('admin_login')

def register(request):
    if request.method == 'POST':
        custname = request.POST.get('custname')
        state = request.POST.get('state')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        dob = request.POST.get('dob')
        password = request.POST.get('password')
        reglocation = request.META.get('REMOTE_ADDR', '127.0.0.1')
        
        # Create customer directly without OTP verification
        Customer.objects.create(
            custname=custname,
            state=state,
            city=city,
            pincode=pincode,
            address=address,
            phone=phone,
            dob=dob,
            reglocation=reglocation,
            regdate=timezone.now().date(),
            password=make_password(password)
        )
        messages.success(request, 'Registration successful!')
        return redirect('welcome')
    return render(request, 'register.html')

def section_list(request):
    sections = Section.objects.all()
    return render(request, 'admin_section_list.html', {'sections': sections})

def section_add(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        if title:
            Section.objects.create(title=title)
            messages.success(request, 'Section added successfully!')
            return redirect('admin_section_list')
        else:
            messages.error(request, 'Title is required.')
    return render(request, 'admin_section_add.html')

def section_edit(request, seid):
    from .models import Section
    from django.contrib import messages
    section = Section.objects.get(seid=seid)
    if request.method == 'POST':
        title = request.POST.get('title')
        if title:
            section.title = title
            section.save()
            messages.success(request, 'Section updated successfully!')
            return redirect('admin_section_list')
        else:
            messages.error(request, 'Title is required.')
    return render(request, 'admin_section_edit.html', {'section': section})

def section_delete(request, seid):
    from .models import Section
    from django.contrib import messages
    section = Section.objects.get(seid=seid)
    if request.method == 'POST':
        section.delete()
        messages.success(request, 'Section deleted successfully!')
        return redirect('admin_section_list')
    return render(request, 'admin_section_delete.html', {'section': section})

def forgot_password(request):
    if request.method == 'POST':
        phone = request.POST.get('phone')
        from .models import Customer
        if Customer.objects.filter(phone=phone).exists():
            request.session['reset_phone'] = phone
            return redirect('reset_password')
        else:
            messages.error(request, 'No user found with this phone number.')
    return render(request, 'forgot_password.html')

def reset_password(request):
    phone = request.session.get('reset_phone')
    if not phone:
        return redirect('forgot_password')
    from .models import Customer
    if request.method == 'POST':
        password = request.POST.get('password')
        Customer.objects.filter(phone=phone).update(password=make_password(password))
        del request.session['reset_phone']
        messages.success(request, 'Password reset successful! Please login.')
        return redirect('user_login')
    return render(request, 'reset_password.html')

def user_login(request):
    from .models import Customer
    from django.contrib.auth.hashers import check_password
    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone')
        password = request.POST.get('password')
        try:
            customer = Customer.objects.get(phone=phone)
            if check_password(password, customer.password):
                request.session['customer_id'] = customer.custid
                request.session['customer_name'] = customer.custname
                return redirect('welcome')
            else:
                error = 'Invalid phone or password.'
        except Customer.DoesNotExist:
            error = 'Invalid phone or password.'
    return render(request, 'user_login.html', {'error': error})

def category_list(request):
    categories = Category.objects.select_related('secid').all()
    return render(request, 'admin_category_list.html', {'categories': categories})

def category_add(request):
    from .models import Section, Category
    from django.contrib import messages
    sections = Section.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        secid = request.POST.get('secid')
        if title and secid:
            Category.objects.create(title=title, secid_id=secid)
            messages.success(request, 'Category added successfully!')
            return redirect('admin_category_list')
        else:
            messages.error(request, 'All fields are required.')
    return render(request, 'admin_category_add.html', {'sections': sections})

def category_edit(request, catid):
    from .models import Section, Category
    from django.contrib import messages
    category = Category.objects.get(catid=catid)
    sections = Section.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        secid = request.POST.get('secid')
        if title and secid:
            category.title = title
            category.secid_id = secid
            category.save()
            messages.success(request, 'Category updated successfully!')
            return redirect('admin_category_list')
        else:
            messages.error(request, 'All fields are required.')
    return render(request, 'admin_category_edit.html', {'category': category, 'sections': sections})

def category_delete(request, catid):
    from .models import Category
    from django.contrib import messages
    category = Category.objects.get(catid=catid)
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Category deleted successfully!')
        return redirect('admin_category_list')
    return render(request, 'admin_category_delete.html', {'category': category})

def product_list(request):
    products = Product.objects.select_related('catid').all()
    return render(request, 'admin_product_list.html', {'products': products})

def product_add(request):
    from .models import Category, Product, ProductImage, Size, Color
    from django.contrib import messages
    categories = Category.objects.select_related('secid').all()
    sizes = Size.objects.all()
    colors = Color.objects.all()
    if request.method == 'POST':
        title = request.POST.get('title')
        image = request.FILES.get('image')
        additional_images = request.FILES.getlist('additional_images')
        description = request.POST.get('description')
        catid = request.POST.get('catid')
        price = request.POST.get('price')
        selected_sizes = request.POST.getlist('available_sizes')
        selected_colors = request.POST.getlist('available_colors')
        quantity = request.POST.get('quantity')
        if title and image and description and catid and price and quantity:
            product = Product.objects.create(
                title=title,
                image=image,
                description=description,
                catid_id=catid,
                price=price,
                quantity=quantity
            )
            # Set sizes and colors
            product.sizes.set(selected_sizes)
            product.colors.set(selected_colors)
            # Add additional images
            for img in additional_images:
                ProductImage.objects.create(product=product, image=img)
            messages.success(request, 'Product added successfully!')
            return redirect('admin_product_list')
        else:
            messages.error(request, 'All fields are required.')
    return render(request, 'admin_product_add.html', {'categories': categories, 'sizes': sizes, 'colors': colors})

def product_edit(request, pid):
    from .models import Category, Product, ProductImage, Size, Color
    from django.contrib import messages
    product = Product.objects.get(pid=pid)
    categories = Category.objects.select_related('secid').all()
    sizes = Size.objects.all()
    colors = Color.objects.all()
    selected_sizes = product.sizes.values_list('id', flat=True)
    selected_colors = product.colors.values_list('id', flat=True)
    additional_images = ProductImage.objects.filter(product=product)
    if request.method == 'POST':
        title = request.POST.get('title')
        description = request.POST.get('description')
        catid = request.POST.get('catid')
        price = request.POST.get('price')
        image = request.FILES.get('image')
        selected_sizes_post = request.POST.getlist('available_sizes')
        selected_colors_post = request.POST.getlist('available_colors')
        quantity = request.POST.get('quantity')
        new_additional_images = request.FILES.getlist('additional_images')
        if title and description and catid and price and quantity:
            product.title = title
            product.description = description
            product.catid_id = catid
            product.price = price
            product.quantity = quantity
            if image:
                product.image = image
            product.save()
            product.sizes.set(selected_sizes_post)
            product.colors.set(selected_colors_post)
            for img in new_additional_images:
                ProductImage.objects.create(product=product, image=img)
            messages.success(request, 'Product updated successfully!')
            return redirect('admin_product_list')
        else:
            messages.error(request, 'All fields are required.')
    return render(request, 'admin_product_edit.html', {
        'product': product,
        'categories': categories,
        'sizes': sizes,
        'colors': colors,
        'selected_sizes': selected_sizes,
        'selected_colors': selected_colors,
        'additional_images': additional_images
    })

def product_delete(request, pid):
    from .models import Product
    from django.contrib import messages
    product = Product.objects.get(pid=pid)
    if request.method == 'POST':
        product.delete()
        messages.success(request, 'Product deleted successfully!')
        return redirect('admin_product_list')
    return render(request, 'admin_product_delete.html', {'product': product})

def customer_list(request):
    customers = Customer.objects.all()
    return render(request, 'admin_customer_list.html', {'customers': customers})

def customer_edit(request, custid):
    from .models import Customer
    from django.contrib import messages
    from django.contrib.auth.hashers import make_password
    customer = Customer.objects.get(custid=custid)
    
    if request.method == 'POST':
        custname = request.POST.get('custname')
        state = request.POST.get('state')
        city = request.POST.get('city')
        pincode = request.POST.get('pincode')
        address = request.POST.get('address')
        phone = request.POST.get('phone')
        dob = request.POST.get('dob')
        password = request.POST.get('password')
        
        if custname and state and city and pincode and address and phone and dob:
            customer.custname = custname
            customer.state = state
            customer.city = city
            customer.pincode = pincode
            customer.address = address
            customer.phone = phone
            customer.dob = dob
            if password:  # Only update password if a new one is provided
                customer.password = make_password(password)
            customer.save()
            messages.success(request, 'Customer updated successfully!')
            return redirect('admin_customer_list')
        else:
            messages.error(request, 'All fields are required.')
    
    return render(request, 'admin_customer_edit.html', {'customer': customer})

def customer_delete(request, custid):
    from .models import Customer
    from django.contrib import messages
    customer = Customer.objects.get(custid=custid)
    
    if request.method == 'POST':
        customer.delete()
        messages.success(request, 'Customer deleted successfully!')
        return redirect('admin_customer_list')
    
    return render(request, 'admin_customer_delete.html', {'customer': customer})

def order_list(request):
    from .models import Order
    # Only show orders where payment_mode is not 'Pending' and not empty
    orders = Order.objects.select_related('custid', 'pid').exclude(payment_mode__iexact='Pending').exclude(payment_mode__exact='').order_by('-date')
    return render(request, 'admin_order_list.html', {'orders': orders})

def add_to_cart(request, pid):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to add items to cart')
        return redirect('user_login')
    
    if request.method == 'POST':
        customer_id = request.session['customer_id']
        product = Product.objects.get(pid=pid)
        size = request.POST.get('size')
        color_id = request.POST.get('color')
        if not size:
            messages.error(request, 'Please select a size.')
            return redirect('welcome')
        if not color_id:
            messages.error(request, 'Please select a color.')
            return redirect('welcome')
        if product.quantity < 1:
            messages.error(request, 'This product is out of stock.')
            return redirect('welcome')
        # Check if product with same size and color already in cart
        cart_item = Cart.objects.filter(custid_id=customer_id, pid_id=pid, size=size, color_id=color_id).first()
        if cart_item:
            if product.quantity > cart_item.quantity:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, 'Product added to cart successfully!')
            else:
                messages.error(request, 'Not enough stock for this product.')
        else:
            Cart.objects.create(custid_id=customer_id, pid_id=pid, size=size, color_id=color_id)
            messages.success(request, 'Product added to cart successfully!')
    return redirect('welcome')

def cart(request):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to view your cart')
        return redirect('user_login')
    
    customer_id = request.session['customer_id']
    cart_items = Cart.objects.select_related('pid').filter(custid_id=customer_id)
    
    total_items = sum(item.quantity for item in cart_items)
    total_amount = sum(item.quantity * item.pid.price for item in cart_items)
    
    return render(request, 'cart.html', {
        'cart_items': cart_items,
        'total_items': total_items,
        'total_amount': total_amount
    })

def update_cart(request, cartid):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to update cart')
        return redirect('user_login')
    
    cart_item = Cart.objects.get(cartid=cartid)
    action = request.GET.get('action')
    
    if action == 'increase':
        if cart_item.quantity < cart_item.pid.quantity:
            cart_item.quantity += 1
        else:
            messages.error(request, 'Not enough stock for this product.')
    elif action == 'decrease':
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart')
            return redirect('cart')
    
    cart_item.save()
    return redirect('cart')

def remove_from_cart(request, cartid):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to remove items from cart')
        return redirect('user_login')
    
    Cart.objects.get(cartid=cartid).delete()
    messages.success(request, 'Item removed from cart')
    return redirect('cart')

def book_item(request, pid):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to book items')
        return redirect('user_login')
    
    customer_id = request.session['customer_id']
    product = Product.objects.get(pid=pid)
    # Get the cart item to get the size and color
    cart_item = Cart.objects.filter(custid_id=customer_id, pid_id=pid).first()
    size = cart_item.size if cart_item else ''
    color = cart_item.color if cart_item else None
    if not color:
        messages.error(request, 'No color selected for this product.')
        return redirect('cart')
    if product.quantity < 1 or (cart_item and cart_item.quantity > product.quantity):
        messages.error(request, 'Not enough stock for this product.')
        return redirect('cart')
    # Create order for this product only, quantity is 1
    order = Order.objects.create(
        pid=product,
        custid_id=customer_id,
        amount=product.price,
        quantity=1,
        size=size,
        color=color,
        status='Pending'
    )
    # Decrease product quantity
    product.quantity -= 1
    product.save()
    # Redirect to bill page for this order
    return redirect(reverse('bill_page') + f'?order_ids={order.orderid}')

def user_logout(request):
    request.session.flush()
    return redirect('user_login')

def checkout(request):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to checkout')
        return redirect('user_login')
    customer_id = request.session['customer_id']
    cart_items = Cart.objects.select_related('pid').filter(custid_id=customer_id)
    if not cart_items:
        messages.error(request, 'Your cart is empty!')
        return redirect('cart')
    order_ids = []
    for item in cart_items:
        if not item.color:
            messages.error(request, f'No color selected for {item.pid.title}.')
            return redirect('cart')
        if item.quantity > item.pid.quantity:
            messages.error(request, f'Not enough stock for {item.pid.title}.')
            return redirect('cart')
    for item in cart_items:
        order = Order.objects.create(
            pid=item.pid,
            custid_id=customer_id,
            amount=item.pid.price * item.quantity,
            quantity=item.quantity,
            size=item.size,
            color=item.color,
            status='Pending'
        )
        # Decrease product quantity
        item.pid.quantity -= item.quantity
        item.pid.save()
        order_ids.append(str(order.orderid))
    # Optionally clear the cart after checkout (or after payment)
    # cart_items.delete()
    return redirect(reverse('bill_page') + f'?order_ids={"-".join(order_ids)}')

def bill_page(request):
    order_ids = request.GET.get('order_ids', '')
    order_id_list = [int(oid) for oid in order_ids.split('-') if oid.isdigit()]
    orders = Order.objects.filter(orderid__in=order_id_list)
    total_amount = sum(order.amount for order in orders)
    return render(request, 'bill_page.html', {
        'orders': orders,
        'total_amount': total_amount
    })

def cod_payment(request):
    if request.method == 'POST':
        order_ids = request.POST.get('order_ids', '')
        order_id_list = [int(oid) for oid in order_ids.split('-') if oid.isdigit()]
        print(f"Order IDs received: {order_ids}")
        print(f"Order ID list: {order_id_list}")
        orders = Order.objects.filter(orderid__in=order_id_list)
        print(f"Orders queryset: {orders}")
        for order in orders:
            order.payment_mode = 'COD'
            order.status = 'Placed'
            order.save()
        return render(request, 'cod_confirmation.html', {'orders': orders})
    return redirect('welcome')

def admin_order_detail(request, orderid):
    from .models import Order
    order = Order.objects.select_related('custid', 'pid').get(orderid=orderid)
    return render(request, 'admin_order_detail.html', {'order': order})

def admin_update_order_status(request, orderid):
    from .models import Order
    order = Order.objects.get(orderid=orderid)
    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in ['Placed', 'Shipped', 'Delivered']:
            order.status = new_status
            order.save()
    return redirect('admin_order_detail', orderid=orderid)

def remove_product_image(request, image_id):
    from .models import ProductImage
    img = ProductImage.objects.get(id=image_id)
    pid = img.product.pid
    img.delete()
    messages.success(request, 'Image removed successfully!')
    return redirect('admin_product_edit', pid=pid)

def size_list(request):
    from .models import Size
    sizes = Size.objects.all()
    return render(request, 'admin_size_list.html', {'sizes': sizes})

def size_add(request):
    from .models import Size
    from django.contrib import messages
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            Size.objects.create(name=name)
            messages.success(request, 'Size added successfully!')
            return redirect('admin_size_list')
        else:
            messages.error(request, 'Size name is required.')
    return render(request, 'admin_size_add.html')

def size_edit(request, sizeid):
    from .models import Size
    from django.contrib import messages
    size = Size.objects.get(id=sizeid)
    if request.method == 'POST':
        name = request.POST.get('name')
        if name:
            size.name = name
            size.save()
            messages.success(request, 'Size updated successfully!')
            return redirect('admin_size_list')
        else:
            messages.error(request, 'Size name is required.')
    return render(request, 'admin_size_edit.html', {'size': size})

def size_delete(request, sizeid):
    from .models import Size
    from django.contrib import messages
    size = Size.objects.get(id=sizeid)
    if request.method == 'POST':
        size.delete()
        messages.success(request, 'Size deleted successfully!')
        return redirect('admin_size_list')
    return render(request, 'admin_size_delete.html', {'size': size})

def report_top_products(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get top 10 products by number of orders
    from django.db.models import Count
    top_products = Product.objects.annotate(
        order_count=Count('order')
    ).order_by('-order_count')[:10]
    
    return render(request, 'admin_report_top_products.html', {
        'products': top_products
    })

def report_active_customers(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get customers who have placed orders in the last 30 days
    from django.utils import timezone
    from datetime import timedelta
    from django.db.models import Count
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    active_customers = Customer.objects.filter(
        order__date__gte=thirty_days_ago
    ).annotate(
        order_count=Count('order')
    ).order_by('-order_count')
    
    return render(request, 'admin_report_active_customers.html', {
        'customers': active_customers
    })

def report_sales_by_category(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get sales data grouped by category
    from django.db.models import Sum
    sales_by_category = Category.objects.annotate(
        total_sales=Sum('product__order__amount')
    ).order_by('-total_sales')
    
    return render(request, 'admin_report_sales_by_category.html', {
        'categories': sales_by_category
    })

def report_orders_by_status(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get count of orders by status
    from django.db.models import Count
    orders_by_status = Order.objects.values('status').annotate(
        count=Count('orderid')
    ).order_by('status')
    
    return render(request, 'admin_report_orders_by_status.html', {
        'status_counts': orders_by_status
    })

def report_revenue_by_month(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get revenue data grouped by month
    from django.db.models import Sum
    from django.db.models.functions import TruncMonth
    
    revenue_by_month = Order.objects.exclude(status='Cancelled').annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_revenue=Sum('amount')
    ).order_by('-month')[:6]  # Last 6 months
    
    return render(request, 'admin_report_revenue_by_month.html', {
        'monthly_revenue': revenue_by_month
    })

def report_low_stock(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get products with low stock (less than 10 units)
    low_stock_products = Product.objects.filter(quantity__lt=10).select_related('catid').order_by('quantity')
    
    # Calculate statistics
    total_low_stock = low_stock_products.count()
    critical_stock = low_stock_products.filter(quantity__lte=5).count()
    low_stock = low_stock_products.filter(quantity__gt=5).count()
    
    return render(request, 'admin_report_low_stock.html', {
        'products': low_stock_products,
        'total_low_stock': total_low_stock,
        'critical_stock': critical_stock,
        'low_stock': low_stock
    })

def report_recent_orders(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get recent orders with customer details
    recent_orders = Order.objects.select_related('custid').order_by('-date')[:20]
    
    return render(request, 'admin_report_recent_orders.html', {
        'orders': recent_orders
    })

def report_popular_sizes(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get most ordered sizes
    from django.db.models import Count
    popular_sizes = Size.objects.annotate(
        order_count=Count('products__order')
    ).order_by('-order_count')
    
    return render(request, 'admin_report_popular_sizes.html', {
        'sizes': popular_sizes
    })

def report_customer_trend(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get customer registration trend by month
    from django.db.models import Count
    from django.db.models.functions import TruncMonth
    
    customer_trend = Customer.objects.annotate(
        month=TruncMonth('regdate')
    ).values('month').annotate(
        new_customers=Count('custid')
    ).order_by('month')
    
    return render(request, 'admin_report_customer_trend.html', {
        'customer_trend': customer_trend
    })

def report_never_ordered(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    # Get customers who have never placed an order
    customers_without_orders = Customer.objects.filter(order_set__isnull=True)
    
    return render(request, 'admin_report_never_ordered.html', {
        'customers': customers_without_orders
    })

def color_list(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    colors = Color.objects.all().prefetch_related('products')
    return render(request, 'admin_color_list.html', {'colors': colors})

def color_add(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        
        # Validate hex color code
        if not code.startswith('#') or len(code) != 7 or not all(c in '0123456789ABCDEFabcdef' for c in code[1:]):
            messages.error(request, 'Please enter a valid hex color code (e.g., #FF0000)')
            return render(request, 'admin_color_add.html')
        
        # Check if color name already exists
        if Color.objects.filter(name__iexact=name).exists():
            messages.error(request, 'A color with this name already exists')
            return render(request, 'admin_color_add.html')
        
        # Check if color code already exists
        if Color.objects.filter(code__iexact=code).exists():
            messages.error(request, 'A color with this code already exists')
            return render(request, 'admin_color_add.html')
        
        try:
            Color.objects.create(name=name, code=code.upper())
            messages.success(request, 'Color added successfully!')
            return redirect('admin_color_list')
        except Exception as e:
            messages.error(request, f'Error adding color: {str(e)}')
    
    return render(request, 'admin_color_add.html')

def color_edit(request, colorid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    try:
        color = Color.objects.get(id=colorid)
    except Color.DoesNotExist:
        messages.error(request, 'Color not found')
        return redirect('admin_color_list')
    
    if request.method == 'POST':
        name = request.POST.get('name')
        code = request.POST.get('code')
        
        # Validate hex color code
        if not code.startswith('#') or len(code) != 7 or not all(c in '0123456789ABCDEFabcdef' for c in code[1:]):
            messages.error(request, 'Please enter a valid hex color code (e.g., #FF0000)')
            return render(request, 'admin_color_edit.html', {'color': color})
        
        # Check if color name already exists (excluding current color)
        if Color.objects.filter(name__iexact=name).exclude(id=colorid).exists():
            messages.error(request, 'A color with this name already exists')
            return render(request, 'admin_color_edit.html', {'color': color})
        
        # Check if color code already exists (excluding current color)
        if Color.objects.filter(code__iexact=code).exclude(id=colorid).exists():
            messages.error(request, 'A color with this code already exists')
            return render(request, 'admin_color_edit.html', {'color': color})
        
        try:
            color.name = name
            color.code = code.upper()
            color.save()
            messages.success(request, 'Color updated successfully!')
            return redirect('admin_color_list')
        except Exception as e:
            messages.error(request, f'Error updating color: {str(e)}')
    
    return render(request, 'admin_color_edit.html', {'color': color})

def color_delete(request, colorid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    
    try:
        color = Color.objects.get(id=colorid)
    except Color.DoesNotExist:
        messages.error(request, 'Color not found')
        return redirect('admin_color_list')
    
    if request.method == 'POST':
        try:
            color.delete()
            messages.success(request, 'Color deleted successfully!')
            return redirect('admin_color_list')
        except Exception as e:
            messages.error(request, f'Error deleting color: {str(e)}')
    
    return render(request, 'admin_color_delete.html', {'color': color})

def order_history(request):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to view your order history')
        return redirect('user_login')
    customer_id = request.session['customer_id']
    orders = Order.objects.filter(custid_id=customer_id).select_related('pid', 'color').order_by('-date')
    return render(request, 'order_history.html', {'orders': orders})

def view_order_bill(request, orderid):
    if not request.session.get('customer_id'):
        return redirect('user_login')
    order = Order.objects.select_related('pid', 'color').get(orderid=orderid, custid_id=request.session['customer_id'])
    return render(request, 'bill_page.html', {
        'orders': [order],
        'total_amount': order.amount,
        'from_history': True
    })

def cancel_order(request, orderid):
    if not request.session.get('customer_id'):
        return redirect('user_login')
    order = Order.objects.get(orderid=orderid, custid_id=request.session['customer_id'])
    if order.status == 'Placed':
        order.status = 'Cancelled'
        order.save()
        # Restock product
        order.pid.quantity += order.quantity
        order.pid.save()
        messages.success(request, 'Order cancelled successfully.')
    else:
        messages.error(request, 'Order cannot be cancelled.')
    return redirect('order_history')

def return_order(request, orderid):
    if not request.session.get('customer_id'):
        return redirect('user_login')
    order = Order.objects.get(orderid=orderid, custid_id=request.session['customer_id'])
    if order.status == 'Delivered':
        order.status = 'Return Requested'
        order.save()
        messages.success(request, 'Return request submitted.')
    else:
        messages.error(request, 'Order cannot be returned.')
    return redirect('order_history')

def exchange_order(request, orderid):
    if not request.session.get('customer_id'):
        messages.error(request, 'Please login to exchange an order.')
        return redirect('user_login')
    try:
        # Find the specific order item for the logged-in customer
        order = Order.objects.get(orderid=orderid, custid_id=request.session['customer_id'])
        
        # Only allow exchange if the status is Delivered
        if order.status == 'Delivered':
            order.status = 'Exchange Requested'
            order.save()
            messages.success(request, 'Exchange request submitted for Order #' + str(order.orderid))
        else:
            messages.error(request, 'Order cannot be exchanged unless it is Delivered.')
            
    except Order.DoesNotExist:
        messages.error(request, 'Order not found or does not belong to you.')
        
    return redirect('order_history')

@csrf_exempt
def mark_payment_done(request, orderid):
    if not request.session.get('customer_id'):
        return redirect('user_login')
    order = Order.objects.get(orderid=orderid, custid_id=request.session['customer_id'])
    order.payment_mode = 'Online'
    order.status = 'Pending'
    order.save()
    return JsonResponse({'status': 'success'})

def product_detail(request, pid):
    product = Product.objects.select_related('catid').prefetch_related('images', 'sizes', 'colors').get(pid=pid)
    return render(request, 'product_detail.html', {'product': product})

def contact_submit(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        email = request.POST.get('email')
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        if name and email and subject and message:
            ContactSubmission.objects.create(
                name=name,
                email=email,
                subject=subject,
                message=message
            )
            messages.success(request, 'Your message has been sent successfully!')
        else:
            messages.error(request, 'Please fill out all fields.')

    return redirect('contact')

def admin_feedback(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    feedbacks = ContactSubmission.objects.all().order_by('-submitted_at')
    return render(request, 'admin_feedback.html', {'feedbacks': feedbacks})

def admin_payment_history(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    # Get orders with payment_mode 'Online' and status 'Pending'
    pending_payments = Order.objects.select_related('custid', 'pid').filter(payment_mode='Online', status='Pending').order_by('-date')
    return render(request, 'admin_payment_history.html', {'pending_payments': pending_payments})

def submit_product_rating(request):
    if request.method == 'POST':
        if not request.session.get('customer_id'):
            messages.error(request, 'Please login to submit a rating.')
            return redirect('user_login')

        customer_id = request.session['customer_id']
        product_id = request.POST.get('product_id')
        order_id = request.POST.get('order_id') # We might not strictly need order_id here, but it's in the form
        rating = request.POST.get('rating')
        feedback = request.POST.get('feedback', '')

        if not product_id or not rating:
            messages.error(request, 'Invalid rating submission.')
            # Redirect to a relevant page, maybe order history or welcome page
            return redirect('welcome') # Or redirect to order history

        try:
            product = Product.objects.get(pid=product_id)
            customer = Customer.objects.get(custid=customer_id)

            # Check if a rating already exists for this product by this user
            existing_rating = ProductRating.objects.filter(product=product, customer=customer).first()
            if existing_rating:
                # Update existing rating
                existing_rating.rating = rating
                existing_rating.feedback = feedback
                existing_rating.save()
                messages.success(request, 'Your rating has been updated!')
            else:
                # Create new rating
                ProductRating.objects.create(
                    product=product,
                    customer=customer,
                    rating=rating,
                    feedback=feedback
                )
                messages.success(request, 'Thank you for your rating!')

        except (Product.DoesNotExist, Customer.DoesNotExist):
            messages.error(request, 'Invalid product or customer.')

        # Redirect back to the page they came from or a confirmation page
        # For now, redirect to order history as they just booked.
        return redirect('order_history')

def admin_product_ratings(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    from django.db.models import Avg

    # Annotate products with their average rating
    product_ratings = Product.objects.annotate(average_rating=Avg('ratings__rating'))

    return render(request, 'admin_product_ratings.html', {'product_ratings': product_ratings})

def admin_product_individual_ratings(request, pid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    product = Product.objects.get(pid=pid)
    individual_ratings = ProductRating.objects.filter(product=product).select_related('customer').order_by('-created_at')

    return render(request, 'admin_product_individual_ratings.html', {
        'product': product,
        'individual_ratings': individual_ratings
    })

def admin_sales_by_category_detail(request, catid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    category = Category.objects.get(catid=catid)
    # Get all orders for products within this category
    category_orders = Order.objects.select_related('pid', 'custid').filter(pid__catid=category).order_by('-date')

    return render(request, 'admin_sales_by_category_detail.html', {
        'category': category,
        'category_orders': category_orders
    })

def admin_orders_by_status_detail(request, status):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    # Get all orders with the given status
    orders_with_status = Order.objects.select_related('pid', 'custid').filter(status=status).order_by('-date')

    return render(request, 'admin_orders_by_status_detail.html', {
        'status': status,
        'orders_with_status': orders_with_status
    })

def admin_top_product_orders(request, pid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    product = Product.objects.get(pid=pid)
    product_orders = Order.objects.select_related('custid').filter(pid=product).order_by('-date')

    return render(request, 'admin_top_product_orders.html', {
        'product': product,
        'product_orders': product_orders
    })

def admin_customer_detail_report(request, custid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    customer = Customer.objects.get(custid=custid)
    customer_orders = Order.objects.select_related('pid').filter(custid=customer).order_by('-date')

    return render(request, 'admin_customer_detail_report.html', {
        'customer': customer,
        'customer_orders': customer_orders
    })

def admin_product_detail_report(request, pid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    product = Product.objects.select_related('catid').prefetch_related('images', 'sizes', 'colors').get(pid=pid)

    return render(request, 'admin_product_detail_report.html', {'product': product})

def admin_size_products(request, sizeid):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    size = Size.objects.get(id=sizeid)
    products_in_size = Product.objects.select_related('catid').prefetch_related('images').filter(sizes=size).order_by('title')

    return render(request, 'admin_size_products.html', {
        'size': size,
        'products_in_size': products_in_size
    })

def admin_sales_trends(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    from django.db.models import Sum
    from django.db.models.functions import TruncMonth

    # Monthly Sales Trend (excluding cancelled orders)
    monthly_sales = Order.objects.exclude(status='Cancelled').annotate(
        month=TruncMonth('date')
    ).values('month').annotate(
        total_sales=Sum('amount')
    ).order_by('month')

    return render(request, 'admin_sales_trends.html', {'monthly_sales': monthly_sales})

def admin_average_order_value(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    from django.db.models import Avg

    # Calculate Average Order Value (excluding cancelled orders)
    average_value = Order.objects.exclude(status='Cancelled').aggregate(Avg('amount'))['amount__avg']

    return render(request, 'admin_average_order_value.html', {'average_value': average_value})

def admin_sales_by_location(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')

    from django.db.models import Sum

    # Sales by Customer Location (State and City)
    sales_by_state = Order.objects.exclude(status='Cancelled').values('custid__state').annotate(
        total_sales=Sum('amount')
    ).order_by('-total_sales')

    sales_by_city = Order.objects.exclude(status='Cancelled').values('custid__city').annotate(
        total_sales=Sum('amount')
    ).order_by('-total_sales')

    return render(request, 'admin_sales_by_location.html', {
        'sales_by_state': sales_by_state,
        'sales_by_city': sales_by_city
    })

def admin_advanced_reports(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    return render(request, 'admin_advanced_reports_landing.html')

def admin_report_payments_by_mode(request):
    if not request.session.get('admin_logged_in'):
        return JsonResponse({'error': 'Unauthorized'}, status=401)

    from django.db.models import Count, Sum
    # Exclude orders with empty or pending payment mode if they shouldn't be in the report
    payment_mode_data = Order.objects.exclude(payment_mode__exact='').exclude(payment_mode='Pending').values('payment_mode').annotate(count=Count('orderid'), total_amount=Sum('amount'))

    labels = [item['payment_mode'] for item in payment_mode_data]
    counts = [item['count'] for item in payment_mode_data]
    amounts = [str(item['total_amount'] or 0) for item in payment_mode_data] # Handle None for total_amount

    data = {
        'labels': labels,
        'counts': counts,
        'amounts': amounts,
    }
    return JsonResponse(data)

def admin_payments_by_mode_chart_view(request):
    if not request.session.get('admin_logged_in'):
        return redirect('admin_login')
    return render(request, 'admin_report_payments_by_mode.html')
