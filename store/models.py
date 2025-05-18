from django.db import models

# Create your models here.

class Section(models.Model):
    seid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    def __str__(self):
        return self.title

class Category(models.Model):
    catid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    secid = models.ForeignKey(Section, on_delete=models.CASCADE)
    def __str__(self):
        return self.title

class Size(models.Model):
    name = models.CharField(max_length=10, unique=True)
    def __str__(self):
        return self.name

class Color(models.Model):
    name = models.CharField(max_length=50, unique=True)
    code = models.CharField(max_length=7, help_text='Hex color code (e.g. #FF0000)')
    
    def __str__(self):
        return self.name

class Product(models.Model):
    pid = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    image = models.ImageField(upload_to='products/')
    description = models.TextField()
    catid = models.ForeignKey(Category, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    sizes = models.ManyToManyField(Size, blank=True, related_name='products')
    colors = models.ManyToManyField(Color, blank=True, related_name='products')
    quantity = models.PositiveIntegerField(default=0)
    
    @property
    def is_low_stock(self):
        return self.quantity < 10
    
    def __str__(self):
        return self.title

class ProductImage(models.Model):
    product = models.ForeignKey(Product, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Image for {self.product.title}"

class Stock(models.Model):
    pid = models.OneToOneField(Product, on_delete=models.CASCADE, primary_key=True)
    stocksleft = models.PositiveIntegerField()
    def __str__(self):
        return f"{self.pid.title} - {self.stocksleft} left"

class Customer(models.Model):
    custid = models.AutoField(primary_key=True)
    custname = models.CharField(max_length=100)
    state = models.CharField(max_length=50)
    city = models.CharField(max_length=50)
    pincode = models.CharField(max_length=10)
    address = models.TextField()
    phone = models.CharField(max_length=15)
    dob = models.DateField()
    regdate = models.DateField(auto_now_add=True)
    reglocation = models.GenericIPAddressField()
    password = models.CharField(max_length=128, default='')
    def __str__(self):
        return self.custname

class Order(models.Model):
    orderid = models.AutoField(primary_key=True)
    pid = models.ForeignKey(Product, on_delete=models.CASCADE)
    custid = models.ForeignKey(Customer, on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True, help_text='Selected size for this order item')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    status = models.CharField(max_length=30)
    payment_mode = models.CharField(max_length=20, default='Pending')
    def __str__(self):
        return f"Order {self.orderid}"

class Cart(models.Model):
    cartid = models.AutoField(primary_key=True)
    custid = models.ForeignKey(Customer, on_delete=models.CASCADE)
    pid = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    size = models.CharField(max_length=10, blank=True, help_text='Selected size for this cart item')
    color = models.ForeignKey(Color, on_delete=models.SET_NULL, null=True, blank=True)
    def __str__(self):
        return f"Cart {self.cartid} for {self.custid}"

class ContactSubmission(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    subject = models.CharField(max_length=200)
    message = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Message from {self.name} ({self.email})"

class ProductRating(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='ratings')
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name='ratings')
    rating = models.PositiveIntegerField(choices=[(i, str(i)) for i in range(1, 6)]) # 1 to 5 stars
    feedback = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('product', 'customer') # Limit one rating per product per user

    def __str__(self):
        return f"Rating for {self.product.title} by {self.customer.custname}: {self.rating} stars"
