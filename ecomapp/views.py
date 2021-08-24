

from django.contrib.auth import login, authenticate, logout
from django.shortcuts import render, redirect
from django.http import HttpResponseNotFound, Http404
from django.urls import reverse_lazy, reverse
from django.views.generic import TemplateView, View, CreateView, FormView, DetailView, ListView
from .models import *
from .forms import *
from django.db.models import Q
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

from django.core.mail import send_mail
from django.conf import settings

from allauth.account.forms import SignupForm, LoginForm
from allauth.account.views import SignupView


# Create your views here.
from allauth.account.views import PasswordChangeView
from django.contrib.auth.mixins import LoginRequiredMixin

from django.shortcuts import render, get_object_or_404
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.decorators import login_required

class MyPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    success_url = reverse_lazy("ecomapp:home")



@login_required
def profile(request):
    user = request.user
    return render(request, 'profile.html', {'user': user})


@login_required
def profile_update(request):
    user = request.user
    user_profile = UserProfile.objects.get(user=user)

    if request.method == "POST":
        form = ProfileForm(request.POST)

        if form.is_valid():
            user.first_name = form.cleaned_data['first_name']
            user.last_name = form.cleaned_data['last_name']
            user.save()

            user_profile.org = form.cleaned_data['org']
            user_profile.telephone = form.cleaned_data['telephone']
            user_profile.save()

            return HttpResponseRedirect(reverse('ecomapp:profile'))
    else:
        default_data = {'first_name': user.first_name, 'last_name': user.last_name,
                        'org': user_profile.org, 'telephone': user_profile.telephone, }
        form = ProfileForm(default_data)

    return render(request, 'profile_update.html', {'form': form, 'user': user})













class HomeView(TemplateView):
    template_name = "home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        all_products = Product.objects.all().order_by("-id")
        context['products'] = all_products

        paginator = Paginator(all_products, 3)
        page_number = self.request.GET.get('page')
        product_pages = paginator.get_page(page_number)
        context['product_pages'] = product_pages

        categories = Category.objects.all()
        context["categories"] = categories

        return context



class CategoryView(TemplateView):
    template_name = "category.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        category = Category.objects.get(slug=slug)
        products = Product.objects.filter(category=category).order_by("-id")
        paginator = Paginator(products, 3)

        page_number = self.request.GET.get('page')
        product_pages = paginator.get_page(page_number)
        context['product_pages'] = product_pages

        categories = Category.objects.all()
        context["categories"] = categories

        return context


class ProductDetailView(TemplateView):
    template_name = "productdetail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        slug = self.kwargs["slug"]
        try:
            context['product'] = Product.objects.get(slug=slug)
        except Product.DoesNotExist:
            raise Http404
        context['product'].view_count += 1
        context['product'].save()
        return context

class AddToCartView(TemplateView):
    template_name = "addtocart.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        try:
            context['product'] = Product.objects.get(id=self.kwargs['product_id'])
        except Product.DoesNotExist:
            raise Http404
        cart_id = self.request.session.get("cart_id",None)
        if cart_id:
            cart_obj = Cart.objects.get(id=cart_id)
            this_product_in_cart = cart_obj.cartproduct_set.filter(product=context["product"])
            if this_product_in_cart.exists():
                cartproduct = this_product_in_cart.last()
                cartproduct.quantity +=1
                cartproduct.subtotal += context['product'].selling_price
                cartproduct.save()
                cart_obj.total += context['product'].selling_price
                cart_obj.save()
            else:
                cartproduct = CartProduct.objects.create(
                    cart=cart_obj,
                    product=context["product"],
                    rate=context["product"].selling_price,
                    quantity=1,
                    subtotal=context["product"].selling_price
                )
                cart_obj.total += context['product'].selling_price
                cart_obj.save()
        else:
            cart_obj = Cart.objects.create(total=0)
            self.request.session["cart_id"] = cart_obj.id
            cartproduct = CartProduct.objects.create(
                cart=cart_obj,
                product=context["product"],
                rate=context["product"].selling_price,
                quantity=1,
                subtotal=context["product"].selling_price
            )
            cart_obj.total += context['product'].selling_price
            cart_obj.save()

        return context

class MyCartView(TemplateView):
    template_name = "mycart.html"
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id", None)
        if cart_id:
            cart = Cart.objects.get(id=cart_id)
        else:
            cart = None
        context['mycart'] = cart
        return context

class ManageCartView(View):
    def get(self,request,*args,**kwargs):
        cp_id = self.kwargs['cp_id']
        action = request.GET.get("action")
        cp_obj = CartProduct.objects.get(id=cp_id)
        cart_obj = cp_obj.cart

        # cart_id = request.session.get("cart_id",None)
        # if cart_id:
        #     cart2 = Cart.objects.get(id=cart_id)
        #     if cart_odj != cart2:
        #         return redirect("ecomapp:mycart")
        # else:
        #     return redirect("ecomapp:mycart")

        if action=="inc":
            cp_obj.quantity +=1
            cp_obj.subtotal += cp_obj.rate
            cp_obj.save()
            cart_obj.total += cp_obj.rate
            cart_obj.save()
        elif action=="dcr":
            cp_obj.quantity -= 1
            cp_obj.subtotal -= cp_obj.rate
            cp_obj.save()
            cart_obj.total -= cp_obj.rate
            cart_obj.save()
            if cp_obj.quantity ==0:
                cp_obj.delete()
        elif action=="rmv":
            cart_obj.total -= cp_obj.subtotal
            cart_obj.save()
            cp_obj.delete()
        else :
            pass

        return redirect("ecomapp:mycart")

class EmptyCartView(View):
    def get(self, request, *args, **kwargs):
        cart_id = request.session.get("cart_id",None)
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id)
            except Product.DoesNotExist:
                raise Http404
            cart.cartproduct_set.all().delete()
            cart.total = 0
            cart.save()
        return redirect("ecomapp:mycart")

class CeckoutView(CreateView):
    template_name = "checkout.html"
    form_class =checkoutForm
    success_url = reverse_lazy("ecomapp:home")

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            print("*****11111111111****")
        elif request.user.is_authenticated==False:
            try:
                if request.user:
                    return redirect('/register/?next=/checkout/')
            except:
                return redirect('/login/?next=/checkout/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        cart_id = self.request.session.get("cart_id",None)
        if cart_id:
            cart = Cart.objects.get(id=cart_id)
        else:
            cart = None
        context["checkcart"] = cart
        return context

    def form_valid(self, form):
        cart_id = self.request.session.get("cart_id",None)
        if cart_id:
            try:
                cart_obj = Cart.objects.get(id=cart_id)
            except Cart.DoesNotExist:
                raise Http404
            form.instance.cart = cart_obj
            form.instance.subtotal = cart_obj.total
            form.instance.discount = 0
            form.instance.total = cart_obj.total
            form.instance.order_status = "Order Received"
            del self.request.session["cart_id"]
        else:
            return redirect("ecomapp:home")
        return super().form_valid(form)



class customerProfileView(TemplateView):
    template_name = "customerprofile.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated :
            pass
        else:
            return redirect('login/?next=/profile/')
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.request.user
        context["customer"] = customer
        orders = Order.objects.filter(cart__customer=customer).order_by("-id")
        context['orders'] = orders
        return context

class customerOrderDetailView(DetailView):
    template_name = "customerorderdetail.html"
    model = Order
    context_object_name = "order_obj"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            order_id = self.kwargs["pk"]
            try:
                order = Order.objects.get(id=order_id)
            except Order.DoesNotExist:
                raise Http404
            if request.user != order.cart.customer:
                return redirect("ecomapp:customerprofile")
        else:
            return redirect('login/?next=/profile/')
        return super().dispatch(request, *args, **kwargs)

class AboutView( TemplateView):
    template_name = "about.html"


class ContactView( TemplateView):
    template_name = "contactus.html"

class searchView(TemplateView):
    template_name = "search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        search_for = self.request.GET.get("search_for")
        results = Product.objects.filter(
            Q(title__icontains=search_for)|
            Q(description__icontains=search_for)|
            Q(return_policy__icontains=search_for)
        )
        context["product_results"] = results
        return context
