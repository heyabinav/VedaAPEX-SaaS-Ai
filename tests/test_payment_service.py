from utils.time import utcnow

import asyncio
import hashlib
import hmac
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from sqlmodel import SQLModel, Session, create_engine, select

from app.core.config import settings
from app.models.token import (
    PaymentOrder,
    PaymentOrderStatus,
    PaymentTransaction,
    SubscriptionPlan,
    TokenWallet,
)
from app.models.user import Subscription, User
from app.services.generation_policy_service import GenerationPolicyService
from app.services.payment_service import PaymentService
from app.services.subscription_service import SubscriptionService
from app.services.token_service import TokenService


@pytest.fixture()
def razorpay_session():
    db_dir = Path(__file__).resolve().parents[1] / 'tmp_razorpay_tests'
    db_dir.mkdir(parents=True, exist_ok=True)
    db_path = db_dir / f'razorpay-{uuid.uuid4().hex}.db'
    engine = create_engine(f'sqlite:///{db_path.as_posix()}')
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session


def _seed_user_plan_and_wallet(session: Session) -> tuple[User, SubscriptionPlan]:
    user = User(
        email='pay@example.com',
        hashed_password='hashed-password',
        referral_code='VEDARAZOR1',
        role='USER',
    )
    session.add(user)
    session.commit()
    session.refresh(user)

    plan = SubscriptionPlan(
        name='Pro',
        slug='pro',
        price=10.0,
        currency='INR',
        billing_cycle='monthly',
        token_allocation=250,
        daily_credits=25,
        features='["priority"]',
    )
    session.add(plan)
    session.commit()
    session.refresh(plan)

    TokenService.create_wallet(session, user.id, initial_balance=100)
    return user, plan


class FakeResponse:
    def __init__(self, status_code: int = 201, payload: dict | None = None, text: str = ''):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


class FakeAsyncClient:
    instances = []

    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs
        self.posts = []
        FakeAsyncClient.instances.append(self)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, url, json=None):
        self.posts.append((url, json))
        return FakeResponse(
            201,
            {
                'id': 'order_test_123',
                'amount': json['amount'],
                'currency': json['currency'],
                'receipt': json['receipt'],
            },
        )


def test_create_order_uses_razorpay_credentials(monkeypatch, razorpay_session):
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_key')
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')
    monkeypatch.setattr(settings, 'RAZORPAY_CURRENCY', 'INR')
    FakeAsyncClient.instances.clear()
    monkeypatch.setattr('app.services.payment_service.httpx.AsyncClient', FakeAsyncClient)

    user, _plan = _seed_user_plan_and_wallet(razorpay_session)

    result = asyncio.run(
        PaymentService.create_order(
            razorpay_session,
            user,
            'pro',
            notes={'source': 'unit-test'},
        )
    )

    assert result['keyId'] == 'rzp_test_key'
    assert result['order']['order_id'] == 'order_test_123'
    assert FakeAsyncClient.instances[0].kwargs['auth'] == ('rzp_test_key', 'test_secret')
    assert FakeAsyncClient.instances[0].posts[0][0] == 'https://api.razorpay.com/v1/orders'

    saved = razorpay_session.exec(
        select(PaymentOrder).where(PaymentOrder.order_id == 'order_test_123')
    ).first()
    assert saved is not None
    assert saved.amount_paise == 1000
    assert saved.currency == 'INR'


def test_verify_checkout_payment_activates_subscription(monkeypatch, razorpay_session):
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_key')
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')

    user, plan = _seed_user_plan_and_wallet(razorpay_session)
    order = PaymentOrder(
        user_id=user.id,
        plan_id=plan.id,
        provider='RAZORPAY',
        order_id='order_123',
        receipt='receipt_123',
        amount_paise=1000,
        currency='INR',
        purpose='VEDAAPEX_SUBSCRIPTION',
        status=PaymentOrderStatus.CREATED,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    razorpay_session.add(order)
    razorpay_session.commit()
    razorpay_session.refresh(order)

    signature = hmac.new(
        b'test_secret',
        f'{order.order_id}|payment_456'.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    result = PaymentService.verify_checkout_payment(
        razorpay_session,
        user,
        order.order_id,
        'payment_456',
        signature,
    )

    assert result['status'] == 'verified'
    assert result['subscription']['plan_slug'] == 'pro'
    assert result['subscription']['payment_id'] == 'payment_456'

    updated_order = razorpay_session.exec(
        select(PaymentOrder).where(PaymentOrder.order_id == order.order_id)
    ).first()
    assert updated_order is not None
    assert updated_order.status == PaymentOrderStatus.PAID
    assert updated_order.payment_id == 'payment_456'

    transaction = razorpay_session.exec(
        select(PaymentTransaction).where(PaymentTransaction.payment_order_id == updated_order.id)
    ).first()
    assert transaction is not None
    assert transaction.payment_id == 'payment_456'
    assert transaction.signature == signature

    wallet = razorpay_session.exec(
        select(TokenWallet).where(TokenWallet.user_id == user.id)
    ).first()
    assert wallet is not None
    assert wallet.balance == 350

    refreshed_user = razorpay_session.get(User, user.id)
    assert refreshed_user.is_pro is True
    assert refreshed_user.plan == 'pro'


def test_verify_checkout_payment_rejects_invalid_signature(monkeypatch, razorpay_session):
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_ID', 'rzp_test_key')
    monkeypatch.setattr(settings, 'RAZORPAY_KEY_SECRET', 'test_secret')

    user, plan = _seed_user_plan_and_wallet(razorpay_session)
    order = PaymentOrder(
        user_id=user.id,
        plan_id=plan.id,
        provider='RAZORPAY',
        order_id='order_bad_sig',
        receipt='receipt_bad_sig',
        amount_paise=1000,
        currency='INR',
        purpose='VEDAAPEX_SUBSCRIPTION',
        status=PaymentOrderStatus.CREATED,
        created_at=utcnow(),
        updated_at=utcnow(),
    )
    razorpay_session.add(order)
    razorpay_session.commit()
    razorpay_session.refresh(order)

    with pytest.raises(ValueError, match='Invalid Razorpay signature'):
        PaymentService.verify_checkout_payment(
            razorpay_session,
            user,
            order.order_id,
            'payment_bad',
            'not-a-valid-signature',
        )


def test_verify_webhook_signature_valid_and_invalid(monkeypatch):
    monkeypatch.setattr(settings, 'RAZORPAY_WEBHOOK_SECRET', 'webhook_secret')
    raw_body = b'{"event":"payment.captured"}'
    signature = hmac.new(
        b'webhook_secret',
        raw_body,
        hashlib.sha256,
    ).hexdigest()

    PaymentService.verify_webhook_signature(raw_body, signature)

    with pytest.raises(ValueError, match='Invalid Razorpay webhook signature'):
        PaymentService.verify_webhook_signature(raw_body, 'bad-signature')


def test_legacy_subscription_plan_name_normalizes_for_gating(monkeypatch, razorpay_session):
    user, _plan = _seed_user_plan_and_wallet(razorpay_session)

    legacy = Subscription(
        user_id=user.id,
        plan='Pro Plan',
        status='active',
        current_period_end=utcnow() + timedelta(days=30),
    )
    razorpay_session.add(legacy)
    razorpay_session.commit()

    fresh_user = razorpay_session.get(User, user.id)
    summary = SubscriptionService.get_subscription_summary(razorpay_session, user.id)
    policy = GenerationPolicyService.build_policy(razorpay_session, fresh_user, 'text')

    assert SubscriptionService.is_paid_plan('Pro Plan') is True
    assert summary['plan_slug'] == 'pro'
    assert summary['plan_code'] == 'PRO'
    assert policy.plan_name == 'PRO'
    assert policy.allow_premium_fallback is True