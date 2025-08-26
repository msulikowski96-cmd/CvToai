
import stripe
import os
from datetime import datetime, timedelta
from app import db
from models import User

# Konfiguracja Stripe
stripe.api_key = os.environ.get('STRIPE_SECRET_KEY')

# Ceny w groszach (PLN)
PRICES = {
    'single_use': 999,      # 9.99 PLN
    'premium_monthly': 3000, # 30.00 PLN
    'premium_yearly': 18999  # 189.99 PLN
}

def create_single_use_payment():
    """Tworzy płatność jednorazową za 9,99 PLN"""
    try:
        intent = stripe.PaymentIntent.create(
            amount=PRICES['single_use'],
            currency='pln',
            metadata={
                'service': 'cv_single_use',
                'type': 'one_time'
            }
        )
        return intent
    except Exception as e:
        print(f"Błąd tworzenia płatności jednorazowej: {e}")
        return None

def create_premium_monthly_subscription(customer_id):
    """Tworzy subskrypcję premium miesięczną za 30 PLN"""
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'pln',
                    'product_data': {
                        'name': 'CV Optimizer Premium - Miesięczny',
                        'description': '15 generowań CV miesięcznie'
                    },
                    'unit_amount': PRICES['premium_monthly'],
                    'recurring': {'interval': 'month'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://twoja-domena.replit.app/payment-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://twoja-domena.replit.app/payment-cancel'
        )
        return session
    except Exception as e:
        print(f"Błąd tworzenia subskrypcji miesięcznej: {e}")
        return None

def create_premium_yearly_subscription(customer_id):
    """Tworzy subskrypcję premium roczną za 189,99 PLN"""
    try:
        session = stripe.checkout.Session.create(
            customer=customer_id,
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'pln',
                    'product_data': {
                        'name': 'CV Optimizer Premium - Roczny',
                        'description': 'Nielimitowane generowania CV przez rok'
                    },
                    'unit_amount': PRICES['premium_yearly'],
                    'recurring': {'interval': 'year'},
                },
                'quantity': 1,
            }],
            mode='subscription',
            success_url='https://twoja-domena.replit.app/payment-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='https://twoja-domena.replit.app/payment-cancel'
        )
        return session
    except Exception as e:
        print(f"Błąd tworzenia subskrypcji rocznej: {e}")
        return None

def create_or_get_customer(user):
    """Tworzy lub pobiera klienta Stripe"""
    if user.stripe_customer_id:
        return user.stripe_customer_id
    
    try:
        customer = stripe.Customer.create(
            email=user.email,
            name=f"{user.first_name} {user.last_name}",
            metadata={'user_id': user.id}
        )
        
        user.stripe_customer_id = customer.id
        db.session.commit()
        
        return customer.id
    except Exception as e:
        print(f"Błąd tworzenia klienta Stripe: {e}")
        return None

def handle_successful_payment(session_id, payment_type):
    """Obsługuje pomyślną płatność"""
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        customer_id = session.customer
        
        # Znajdź użytkownika
        user = User.query.filter_by(stripe_customer_id=customer_id).first()
        if not user:
            return False
        
        if payment_type == 'single_use':
            # Jednorazowe użycie - dodaj 1 użycie
            if not hasattr(user, 'single_uses'):
                user.single_uses = 0
            user.single_uses += 1
            
        elif payment_type == 'premium_monthly':
            # Premium miesięczny - ustaw koniec subskrypcji na miesiąc
            user.premium_until = datetime.utcnow() + timedelta(days=30)
            user.premium_generations_left = 15
            
        elif payment_type == 'premium_yearly':
            # Premium roczny - ustaw koniec subskrypcji na rok
            user.premium_until = datetime.utcnow() + timedelta(days=365)
            user.premium_generations_left = -1  # Nielimitowane
        
        db.session.commit()
        return True
        
    except Exception as e:
        print(f"Błąd obsługi płatności: {e}")
        return False
