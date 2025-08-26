
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash
from flask_login import login_required, current_user
from stripe_config import (
    create_single_use_payment, 
    create_premium_monthly_subscription,
    create_premium_yearly_subscription,
    create_or_get_customer,
    handle_successful_payment
)
import stripe
import os

payment = Blueprint('payment', __name__, url_prefix='/payment')

@payment.route('/create-single-payment', methods=['POST'])
@login_required
def create_single_payment():
    """Tworzy płatność jednorazową za 9,99 PLN"""
    try:
        intent = create_single_use_payment()
        if intent:
            return jsonify({
                'success': True,
                'client_secret': intent.client_secret,
                'amount': 9.99
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się utworzyć płatności'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Błąd: {str(e)}'
        })

@payment.route('/create-premium-monthly', methods=['POST'])
@login_required
def create_premium_monthly():
    """Tworzy subskrypcję premium miesięczną za 30 PLN"""
    try:
        customer_id = create_or_get_customer(current_user)
        if not customer_id:
            return jsonify({
                'success': False,
                'message': 'Nie udało się utworzyć konta klienta'
            })
        
        session = create_premium_monthly_subscription(customer_id)
        if session:
            return jsonify({
                'success': True,
                'checkout_url': session.url
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się utworzyć subskrypcji'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Błąd: {str(e)}'
        })

@payment.route('/create-premium-yearly', methods=['POST'])
@login_required
def create_premium_yearly():
    """Tworzy subskrypcję premium roczną za 189,99 PLN"""
    try:
        customer_id = create_or_get_customer(current_user)
        if not customer_id:
            return jsonify({
                'success': False,
                'message': 'Nie udało się utworzyć konta klienta'
            })
        
        session = create_premium_yearly_subscription(customer_id)
        if session:
            return jsonify({
                'success': True,
                'checkout_url': session.url
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Nie udało się utworzyć subskrypcji'
            })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Błąd: {str(e)}'
        })

@payment.route('/success')
@login_required
def payment_success():
    """Strona sukcesu płatności"""
    session_id = request.args.get('session_id')
    
    if session_id:
        # Określ typ płatności na podstawie sesji
        try:
            session = stripe.checkout.Session.retrieve(session_id)
            if session.mode == 'subscription':
                line_item = session.list_line_items().data[0]
                if line_item.price.unit_amount == 3000:
                    payment_type = 'premium_monthly'
                else:
                    payment_type = 'premium_yearly'
            else:
                payment_type = 'single_use'
            
            success = handle_successful_payment(session_id, payment_type)
            
            if success:
                flash('Płatność przebiegła pomyślnie!', 'success')
            else:
                flash('Wystąpił problem z aktywacją usługi.', 'error')
                
        except Exception as e:
            flash(f'Błąd weryfikacji płatności: {str(e)}', 'error')
    
    return redirect(url_for('index'))

@payment.route('/cancel')
def payment_cancel():
    """Strona anulowanej płatności"""
    flash('Płatność została anulowana.', 'info')
    return redirect(url_for('index'))

@payment.route('/webhook', methods=['POST'])
def stripe_webhook():
    """Webhook Stripe do obsługi eventów płatności"""
    payload = request.get_data()
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.environ.get('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        return 'Invalid payload', 400
    except stripe.error.SignatureVerificationError:
        return 'Invalid signature', 400

    # Obsługa różnych typów eventów
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        # Dodatkowa logika obsługi płatności
        
    elif event['type'] == 'invoice.payment_succeeded':
        invoice = event['data']['object']
        # Obsługa odnowienia subskrypcji
        
    elif event['type'] == 'customer.subscription.deleted':
        subscription = event['data']['object']
        # Obsługa anulowania subskrypcji

    return 'Success', 200
