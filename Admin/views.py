from django.shortcuts import render
from eCommApp.models import *
from eCommApp.utils import *
from .forms import *
from datetime import timedelta
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.views.generic import View, ListView
from django.db.models import Count, Sum, F, DecimalField, Q
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models.functions import TruncMonth
from django.http import JsonResponse
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.urls import reverse_lazy
from django.core.files.storage import default_storage
from django.contrib.auth.views import LoginView as DjangoLoginView

class StaffRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):

    login_url = '/storeAdmin/login/'

    def test_func(self):
        return self.request.user.is_staff or self.request.user.is_superuser

    def handle_no_permission(self):
        messages.error(self.request, "You do not have access to this area.")
        return redirect('eStore:home')

class AdminLoginView(DjangoLoginView):
    template_name = 'adminpanel/login.html'
    authentication_form = AdminLoginForm
    redirect_authenticated_user = True
    
    def get_success_url(self):
        return reverse_lazy('dashboard')

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)


class DashboardView(StaffRequiredMixin, View):
    template_name = 'adminpanel/dashboard.html'

    def get(self, request, *args, **kwargs):
        today = timezone.localdate()
        start_of_month = today.replace(day=1)
        
        total_orders = Order.objects.filter(ordered=True).count()
        
        total_revenue = Order.objects.filter(ordered=True)\
            .aggregate(total_sum=Sum(F('order_items__quantity') * F('order_items__price'), output_field=DecimalField()))['total_sum'] or Decimal('0.00')

        orders_today = Order.objects.filter(ordered=True, ordered_date__date=today).count()
        revenue_today = Order.objects.filter(ordered=True, ordered_date__date=today)\
            .aggregate(daily_revenue=Sum(F('order_items__quantity') * F('order_items__price'), output_field=DecimalField()))['daily_revenue'] or Decimal('0.00')

        orders_this_month = Order.objects.filter(ordered=True, ordered_date__date__gte=start_of_month).count()
        revenue_this_month = Order.objects.filter(ordered=True, ordered_date__date__gte=start_of_month)\
            .aggregate(monthly_revenue=Sum(F('order_items__quantity') * F('order_items__price'), output_field=DecimalField()))['monthly_revenue'] or Decimal('0.00')

        total_customers = Customer.objects.count()
        products_in_stock = Product.objects.filter(available=True, stock__gt=0).count()

        six_months_ago = (today - timedelta(days=6*30)).replace(day=1)
        monthly_sales_data = Order.objects.filter(
            ordered=True,
            ordered_date__date__gte=six_months_ago
        ).annotate(
            month=TruncMonth('ordered_date')
        ).values('month').annotate(
            total_sales=Sum(F('order_items__quantity') * F('order_items__price'))
        ).order_by('month')

        months = [ms['month'].strftime('%b %Y') for ms in monthly_sales_data]
        sales = [float(ms['total_sales']) for ms in monthly_sales_data]

        order_status_data = Order.objects.filter(ordered=True).values('status').annotate(count=Count('id'))
        status_labels = [entry['status'] for entry in order_status_data]
        status_counts = [entry['count'] for entry in order_status_data]

        top_products = Product.objects.filter(order_items__order__ordered=True)\
            .annotate(total_sold=Sum('order_items__quantity'))\
            .order_by('-total_sold')[:5]
        
        top_product_names = [p.name for p in top_products]
        top_product_quantities = [float(p.total_sold) for p in top_products]


        context = {
            'page_title': 'Ecom Admin Dashboard',
            'kpis': {
                'total_orders': total_orders,
                'total_revenue': total_revenue,
                'orders_today': orders_today,
                'revenue_today': revenue_today,
                'orders_this_month': orders_this_month,
                'revenue_this_month': revenue_this_month,
                'total_customers': total_customers,
                'products_in_stock': products_in_stock,
            },
            'chart_data': {
                'monthly_sales_labels': months,
                'monthly_sales_data': sales,
                'order_status_labels': status_labels,
                'order_status_counts': status_counts,
                'top_product_names': top_product_names,
                'top_product_quantities': top_product_quantities,
            }
        }
        return render(request, self.template_name, context)
    

class CategoryListView(StaffRequiredMixin, ListView):
    model = Category
    template_name = 'adminpanel/categories.html'
    context_object_name = 'categories'
    paginate_by = 10 

    def get_queryset(self):
        queryset = super().get_queryset()
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(name__icontains=query)
        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Categories'
        context['current_query'] = self.request.GET.get('q', '')
        return context


class CategoryFormView(StaffRequiredMixin, View):
    template_name = 'adminpanel/category_form.html'

    def get_object(self, category_id=None):
        if category_id:
            return get_object_or_404(Category, pk=category_id)
        return None

    def get(self, request, category_id=None):
        category = self.get_object(category_id)
        form = CategoryForm(instance=category)
        context = {
            'form': form,
            'category': category,
            'page_title': 'Edit Category' if category else 'Add New Category'
        }
        return render(request, self.template_name, context)

    def post(self, request, category_id=None):
        category = self.get_object(category_id)
        form = CategoryForm(request.POST, instance=category)

        if form.is_valid():
            form.save()
            success_message = "Category updated successfully!" if category else "Category added successfully!"
            messages.success(request, success_message)
            return redirect('ecom_admin:category_list')
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'category': category,
                'page_title': 'Edit Category' if category else 'Add New Category'
            }
            return render(request, self.template_name, context)


class CategoryDeleteAjaxView(StaffRequiredMixin, View):
    def post(self, request):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)
        
        category_id = request.POST.get('category_id')
        try:
            category = get_object_or_404(Category, pk=category_id)
            with transaction.atomic():
                category_name = category.name
                category.delete()
                messages.success(request, f"Category '{category_name}' deleted successfully.")
                return JsonResponse({'success': True, 'message': f'Category "{category_name}" deleted successfully.'})
        except Category.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Category not found.'}, status=404)
        except Exception as e:
            messages.error(request, f"Error deleting category: {e}")
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)

class OrderListView(StaffRequiredMixin, ListView):
    model = Order
    template_name = 'adminpanel/orders.html'
    context_object_name = 'orders'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().filter(ordered=True)
        query = self.request.GET.get('q')
        status = self.request.GET.get('status')
        
        if query:
            queryset = queryset.filter(
                Q(id__iexact=query) |
                Q(user__username__icontains=query) |
                Q(billing_address__email__icontains=query) |
                Q(billing_address__first_name__icontains=query) |
                Q(billing_address__last_name__icontains=query) |
                Q(dhl_tracking_number__icontains=query)
            )
        if status and status != 'ALL':
            queryset = queryset.filter(status=status)
            
        return queryset.order_by('-ordered_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Orders'
        context['current_query'] = self.request.GET.get('q', '')
        context['current_status'] = self.request.GET.get('status', 'ALL')
        context['status_choices'] = Order.STATUS_CHOICES
        return context


class OrderDetailView(StaffRequiredMixin, View):
    template_name = 'adminpanel/order_detail.html'

    def get(self, request, pk, *args, **kwargs):
        order = get_object_or_404(
            Order.objects.select_related('user', 'billing_address', 'payment')
                         .prefetch_related('order_items__product'),
            pk=pk, ordered=True
        )

        context = {
            'page_title': f'Order Details #{order.id}',
            'order': order,
            'order_items': order.order_items.all(),
            'status_choices': Order.STATUS_CHOICES,
        }
        return render(request, self.template_name, context)

    def post(self, request, pk, *args, **kwargs):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        order = get_object_or_404(Order, pk=pk, ordered=True)
        action = request.POST.get('action')

        if action == 'update_status':
            new_status = request.POST.get('status')
            if new_status and new_status in [choice[0] for choice in Order.STATUS_CHOICES]:
                old_status = order.status
                if old_status == new_status:
                    return JsonResponse({'success': False, 'message': 'Order already has this status.'})

                try:
                    with transaction.atomic():
                        order.status = new_status
                        order.save(update_fields=['status'])
                        send_order_status_update_email(order, new_status)
                        messages.success(request, f"Order #{order.id} status updated to {new_status}.")
                        return JsonResponse({'success': True, 'message': f'Status updated to {new_status}.', 'new_status': new_status})
                except Exception as e:
                    logger.error(f"Error updating order status for Order #{order.id}: {e}", exc_info=True)
                    messages.error(request, f"Failed to update status: {e}")
                    return JsonResponse({'success': False, 'message': f'Failed to update status: {str(e)}'})
            else:
                return JsonResponse({'success': False, 'message': 'Invalid status provided.'}, status=400)
        
        return JsonResponse({'success': False, 'message': 'Invalid action.'}, status=400)


class ProductListView(StaffRequiredMixin, ListView):
    model = Product
    template_name = 'adminpanel/products.html'
    context_object_name = 'products'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('category')
        query = self.request.GET.get('q')
        category_slug = self.request.GET.get('category')
        availability = self.request.GET.get('availability')
        
        if query:
            queryset = queryset.filter(
                Q(name__icontains=query) |
                Q(description__icontains=query) |
                Q(category__name__icontains=query)
            )
        if category_slug and category_slug != 'ALL':
            queryset = queryset.filter(category__slug=category_slug)
        
        if availability == 'available':
            queryset = queryset.filter(available=True, stock__gt=0)
        elif availability == 'unavailable':
            queryset = queryset.filter(Q(available=False) | Q(stock=0))

        return queryset.order_by('name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Products'
        context['current_query'] = self.request.GET.get('q', '')
        context['current_category'] = self.request.GET.get('category', 'ALL')
        context['current_availability'] = self.request.GET.get('availability', 'ALL')
        context['categories'] = Category.objects.all().order_by('name')
        context['availability_choices'] = [
            ('ALL', 'All Products'),
            ('available', 'In Stock & Available'),
            ('unavailable', 'Out of Stock / Unavailable'),
        ]
        return context


class ProductFormView(StaffRequiredMixin, View):
    template_name = 'adminpanel/product_form.html'

    def get_object(self, pk=None):
        if pk:
            return get_object_or_404(Product, pk=pk)
        return None

    def get(self, request, pk=None):
        product = self.get_object(pk)
        form = ProductAdminForm(instance=product)
        context = {
            'form': form,
            'product': product,
            'page_title': 'Edit Product' if product else 'Add New Product'
        }
        return render(request, self.template_name, context)

    def post(self, request, pk=None):
        product = self.get_object(pk)
        form = ProductAdminForm(request.POST, request.FILES, instance=product)

        if form.is_valid():
            if product and product.image and 'image' in form.cleaned_data and form.cleaned_data['image'] != product.image:
                if product.image.name != 'product_images/default.jpg' and default_storage.exists(product.image.name):
                    try:
                        default_storage.delete(product.image.name)
                        logger.info(f"Deleted old image for product {product.pk}: {product.image.name}")
                    except Exception as e:
                        logger.warning(f"Failed to delete old image {product.image.name} for product {product.pk}: {e}")

            form.save()
            success_message = "Product updated successfully!" if product else "Product added successfully!"
            messages.success(request, success_message)
            return redirect('ecom_admin:product_list')
        else:
            messages.error(request, "Please correct the errors below.")
            context = {
                'form': form,
                'product': product,
                'page_title': 'Edit Product' if product else 'Add New Product'
            }
            return render(request, self.template_name, context)


class ProductDeleteAjaxView(StaffRequiredMixin, View):
    def post(self, request):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)
        
        product_id = request.POST.get('product_id')
        try:
            product = get_object_or_404(Product, pk=product_id)
            with transaction.atomic():
                product_name = product.name
                
                if product.image and product.image.name != 'product_images/default.jpg':
                    if default_storage.exists(product.image.name):
                        try:
                            default_storage.delete(product.image.name)
                            logger.info(f"Deleted image for product {product.pk}: {product.image.name}")
                        except Exception as e:
                            logger.warning(f"Failed to delete image {product.image.name} for product {product.pk}: {e}")

                product.delete()
                messages.success(request, f"Product '{product_name}' deleted successfully.")
                return JsonResponse({'success': True, 'message': f'Product "{product_name}" deleted successfully.'})
        except Product.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Product not found.'}, status=404)
        except Exception as e:
            messages.error(request, f"Error deleting product: {e}")
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)


class ProductDetailAdminView(StaffRequiredMixin, View):
    template_name = 'adminpanel/product_detail.html'

    def get(self, request, pk, *args, **kwargs):
        product = get_object_or_404(Product.objects.select_related('category'), pk=pk)
        
        context = {
            'page_title': f'Product Details: {product.name}',
            'product': product,
        }
        return render(request, self.template_name, context)


class CustomerListView(StaffRequiredMixin, ListView):
    model = Customer
    template_name = 'adminpanel/customers.html'
    context_object_name = 'customers'
    paginate_by = 10

    def get_queryset(self):
        queryset = super().get_queryset().select_related('user')
        query = self.request.GET.get('q')
        
        if query:
            queryset = queryset.filter(
                Q(user__username__icontains=query) |
                Q(email__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query)
            )
        return queryset.order_by('user__username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = 'Manage Customers'
        context['current_query'] = self.request.GET.get('q', '')
        return context

class RatingDeleteAjaxView(StaffRequiredMixin, View):
    def post(self, request):
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid request.'}, status=400)

        rating_id = request.POST.get('rating_id')
        try:
            rating = get_object_or_404(Rating, pk=rating_id)
            with transaction.atomic():
                product_name = rating.product.name
                rating.delete()
                messages.success(request, f"Rating for '{product_name}' by '{rating.user.username}' deleted successfully.")
                return JsonResponse({'success': True, 'message': f'Rating deleted successfully.'})
        except Rating.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Rating not found.'}, status=404)
        except Exception as e:
            messages.error(request, f"Error deleting rating: {e}")
            return JsonResponse({'success': False, 'message': f'An error occurred: {str(e)}'}, status=500)
        

class ProductRatingListView(StaffRequiredMixin, ListView):
    
    model = Rating
    template_name = 'adminpanel/product_ratings.html'
    context_object_name = 'ratings'
    paginate_by = 10

    def get_queryset(self):
        product_pk = self.kwargs['pk'] 
        product = get_object_or_404(Product, pk=product_pk)
        queryset = super().get_queryset().filter(product=product).select_related('user') # Optimize
        
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(
                Q(comment__icontains=query) |
                Q(user__username__icontains=query)
            )

        return queryset.order_by('-created_at') # Order by newest first

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product_pk = self.kwargs['pk']
        product = get_object_or_404(Product, pk=product_pk)
        
        context['page_title'] = f'Ratings for {product.name}'
        context['product'] = product
        context['current_query'] = self.request.GET.get('q', '')
        return context