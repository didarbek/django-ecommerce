from django.shortcuts import render, get_object_or_404
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from .models import Item,OrderItem,Order,Address,Payment,Category,Profile,Comment,Carousel,Coupon,Refund
from django.views.generic import ListView,DetailView,View,CreateView,UpdateView,DeleteView
from django.shortcuts import redirect
from django.utils import timezone
from django.contrib import messages
import stripe
import random
import string
from django.conf import settings
from .forms import CheckoutForm,UserForm,ProfileForm,CommentForm,CouponForm,RefundForm
from django.utils.decorators import method_decorator
from django.core.exceptions import PermissionDenied
from django.urls import reverse_lazy,reverse
from django.db import transaction
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.http import HttpResponseRedirect,HttpResponse
from django.db.models import F

# Create your views here.

stripe.api_key = "sk_test_LV84oXAHus7lmnQAluhvBNhD007lApVItl"

User = get_user_model()

def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))

class ProductList(ListView):
    model = Item
    paginate_by = 10
    template_name = 'product_list.html'

    def get_context_data(self,**kwargs):
        context = super(ProductList,self).get_context_data(**kwargs)
        context['slides'] = Carousel.objects.all()
        return context

method_decorator([login_required],name='dispatch')
class ProductCreateView(LoginRequiredMixin,CreateView):
    model = Item
    fields = ('title','price','description','category','image')
    template_name = 'product_create.html'

    def form_valid(self,form):
        post = form.save(commit=False)
        post.user = self.request.user
        post.save()
        messages.success(self.request,'Your post has been published')
        return redirect('core:product_list') 

method_decorator([login_required],name='dispatch')
class ProductUpdateView(LoginRequiredMixin,UpdateView):
    model = Item
    fields = ('title','price','description','image')
    template_name = 'product_update.html'

    def user_passes_test(self, request):
        if request.user.is_authenticated:
            self.object = self.get_object()
            return self.object.user == request.user
        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.user_passes_test(request):
            raise PermissionDenied("Only creator can update this product")
        return super(ProductUpdateView, self).dispatch(
            request, *args, **kwargs)

    def get_success_url(self):
        return reverse('core:product_list')

method_decorator([login_required],name='dispatch')
class ProductDeleteView(LoginRequiredMixin,DeleteView):
    model = Item
    context_object_name = 'product'
    template_name = 'product_delete.html'
    success_url = reverse_lazy('core:product_list')
    
    def user_passes_test(self, request):
        if request.user.is_authenticated:
            self.object = self.get_object()
            return self.object.user == request.user
        return False

    def dispatch(self, request, *args, **kwargs):
        if not self.user_passes_test(request):
            raise PermissionDenied("Only creator can delete this post")
        return super(ProductDeleteView, self).dispatch(
            request, *args, **kwargs)

    def delete(self,request,*args, **kwargs):
        item = self.get_object()
        messages.success(request,'Your product %s was deleted with success!' % item.title)
        return super().delete(request,*args, **kwargs)

class OrderSummaryView(LoginRequiredMixin,View):
    def get(self,*args,**kwargs):
        try:
            order = Order.objects.get(user=self.request.user,ordered=False)
            context = {
                'object':order
            }
            return render(self.request,'order_summary.html',context)
        except ObjectDoesNotExist:
            messages.error(self.request,"You do not have an active order")
            return redirect("/")

def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'order': order,
            }
            shipping_address_qs = Address.objects.filter(
                user=self.request.user,
                default=True
            )
            if shipping_address_qs.exists():
                context.update(
                    {'default_shipping_address': shipping_address_qs[0]})
            return render(self.request, "checkout-page.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkoutpage")
    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, ordered=False)
            if form.is_valid():
                use_default_shipping = form.cleaned_data.get(
                    'use_default_shipping')
                if use_default_shipping:
                    print("Using the defualt shipping address")
                    address_qs = Address.objects.filter(
                        user=self.request.user,
                        default=True
                    )
                    if address_qs.exists():
                        shipping_address = address_qs[0]
                        order.shipping_address = shipping_address
                        order.save()
                    else:
                        messages.info(
                            self.request, "No default shipping address available")
                        return redirect('core:checkoutpage')
                else:
                    print("User is entering a new shipping address")
                    shipping_address1 = form.cleaned_data.get(
                        'shipping_address')
                    shipping_address2 = form.cleaned_data.get(
                        'shipping_address2')
                    shipping_country = form.cleaned_data.get(
                        'shipping_country')
                    shipping_zip = form.cleaned_data.get('shipping_zip')
                    if is_valid_form([shipping_address1, shipping_country, shipping_zip]):
                        shipping_address = Address(
                            user=self.request.user,
                            street_address=shipping_address1,
                            apartment_address=shipping_address2,
                            country=shipping_country,
                            zip=shipping_zip,
                        )
                        shipping_address.save()
                        order.shipping_address = shipping_address
                        order.save()
                        set_default_shipping = form.cleaned_data.get(
                            'set_default_shipping')
                        if set_default_shipping:
                            shipping_address.default = True
                            shipping_address.save()
                    else:
                        messages.info(
                            self.request, "Please fill in the required shipping address fields")
                payment_option = form.cleaned_data.get('payment_option')
                if payment_option == 'S':
                    return redirect('core:payment', payment_option='stripe')
                elif payment_option == 'P':
                    return redirect('core:payment', payment_option='paypal')
                else:
                    messages.warning(
                        self.request, "Invalid payment option selected")
                    return redirect('core:checkout')
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")

def product_detail(request,pk):
    template_name = 'product_detail.html'
    item = get_object_or_404(Item,pk=pk)
    Item.objects.filter(pk=item.pk).update(views=F('views') + 1)
    item.views += 1
    comments = item.comments.filter(active=True)
    new_comment = None
    if request.method == 'POST':
        comment_form = CommentForm(data=request.POST)
        if comment_form.is_valid():
            new_comment = comment_form.save(commit=False)
            new_comment.item = item
            new_comment.save()    
            return HttpResponseRedirect(item.get_absolute_url())
    else:
        comment_form = CommentForm()
    return render(request,template_name,{
        'item':item,
        'comments':comments,
        'new_comment':new_comment,
        'comment_form':comment_form,
    })

def list_of_product_by_category(request,category_slug):
    categories = Category.objects.all()
    item = Item.objects.all()
    if category_slug:
        category = get_object_or_404(Category,slug=category_slug)
        item = item.filter(category=category)
    template = 'list_of_product_by_category.html'
    context = {'categories':categories,'item':item,'category':category}
    return render(request,template,context)

@login_required
def add_to_cart(request,pk):
    item = get_object_or_404(Item,pk=pk)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered = False,
    )
    order_qs = Order.objects.filter(user=request.user,ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This product quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(user=request.user,ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item quantity was updated.")
    return redirect("core:order-summary")

@login_required
def remove_from_cart(request,pk):
    item = get_object_or_404(Item,pk=pk)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered = False,
            )[0]
            order.items.remove(order_item)
            messages.info(request, "This product was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This product was not in your cart.")
            return redirect("core:product_detail", pk=pk)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect("core:product_detail", pk=pk)

@login_required
def remove_single_item_from_cart(request,pk):
    item = get_object_or_404(Item,pk=pk)
    order_qs = Order.objects.filter(user=request.user, ordered=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__pk=item.pk).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered = False,
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This product quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This product was not in your cart.")
            return redirect("core:product_detail",pk=pk)
    else:
        messages.info(request, "You do not have an active order.")
        return redirect("core:product_detail",pk=pk)

class PaymentView(View):
    def get(self,*args,**kwargs):
        order = Order.objects.get(user=self.request.user, ordered=False)
        context = {
            'order':order,
        }
        return render(self.request,"payment.html",context)

    def post(self,*args,**kwargs):
        order = Order.objects.get(user=self.request.user,ordered=False)
        token = self.request.POST.get('stripeToken')
        amount = int(order.get_total() * 100)
        try:
            charge = stripe.Charge.create(
                amount=amount,
                currency="usd",
                source=token,
            )

            payment = Payment()
            payment.stripe_charge_id = charge['id']
            payment.user = self.request.user
            payment.amount = order.get_total()
            payment.save()

            order_items = order.items.all()
            order_items.update(ordered=True)
            for item in order_items:
                item.save()

            order.ordered = True
            order.payment = payment
            order.save()
            messages.success(self.request,"Your order was successful!")
            return redirect("/")

        except stripe.error.CardError as e:
            # Since it's a decline, stripe.error.CardError will be caught
            messages.warning(self.request,F"{e.error.message}")
            return redirect("/")

        except stripe.error.RateLimitError as e:
            messages.warning(self.request,"Rate limit error")
            return redirect("/")

        except stripe.error.InvalidRequestError as e:
            messages.warning(self.request,"Invalid parameters")
            return redirect("/")

        except stripe.error.AuthenticationError as e:
            messages.warning(self.request,"Not authenticated")
            return redirect("/")

        except stripe.error.APIConnectionError as e:
            messages.warning(self.request,"Network error")
            return redirect("/")

        except stripe.error.StripeError as e:
            messages.warning(self.request,"Something went wrong. Your were not charged. Please try again.")
            return redirect("/")

        except Exception as e:
            messages.warning    (self.request,"A serious error occurred. We have been notifed.")
            return redirect("/")

method_decorator([login_required],name='dispatch')
def profile(request):
    user = request.user
    user_products = Item.objects.filter(user=request.user).order_by('-published_on')
    return render(request,'profile.html',{'user_products':user_products,'user': user,})

@login_required
@transaction.atomic
def update_profile(request):
    profile = Profile.objects.get(user=request.user)
    if request.method == 'POST':
        user_form = UserForm(request.POST,instance=request.user)
        profile_form = ProfileForm(request.POST,request.FILES,instance=profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, ('Your profile was successfully updated!'))
            return redirect('core:profile')
        else:
            messages.error(request, ('Please correct the error below.'))
    else:
        user_form = UserForm(instance=request.user)
        profile_form = ProfileForm(instance=profile)
    return render(request, 'account_update.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

class SearchResultsView(ListView):
    model = Item
    template_name = 'search_results.html'

    def get_queryset(self):
        query = self.request.GET.get('title','description')
        object_list = Item.objects.filter(
        Q(title__icontains=query) | Q(description__icontains=query)
        )
        return object_list

@login_required
def comment_remove(request, pk):
    comment = get_object_or_404(Comment, pk=pk)
    comment.delete()
    return redirect('core:product_detail', pk=comment.item.pk)

def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")

class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")

            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist")
                return redirect("core:request-refund")