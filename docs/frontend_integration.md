# Frontend Razorpay Integration & Premium Feature Gating Pattern

This document outlines the standard, premium design pattern for integrating the Razorpay payment checkout flow and dynamic feature gating on the frontend (React / Next.js / Vanilla JS).

---

## 1. User State Management

To restrict premium features and control the UI based on subscription status, fetch the current user's data from `/api/v1/auth/me` on app load and store it in your state/context.

### Fetching User Data (React Example)

```typescript
import React, { createContext, useContext, useState, useEffect } from 'react';

interface User {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  plan: 'free' | 'pro' | 'max' | 'ultra';
  is_pro: boolean;
  subscription_start: string | null;
  subscription_end: string | null;
  wallet: {
    balance: number;
  };
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const response = await fetch('/api/v1/auth/me', {
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`,
        },
      });
      const res = await response.json();
      if (res.success) {
        setUser(res.data);
      } else {
        setUser(null);
      }
    } catch (error) {
      console.error('Failed to load user state:', error);
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};
```

---

## 2. Dynamic Feature Gating (UI Gating)

Use the `user.is_pro` or `user.plan` variables in your frontend components to gate premium components or show high-converting up-sell overlays.

### Gated Feature Component

```tsx
import React from 'react';
import { useAuth } from './AuthContext';

export const AIBackgroundRemover: React.FC = () => {
  const { user } = useAuth();

  if (!user?.is_pro) {
    return (
      <div className="premium-overlay-card">
        <h3>✨ AI Background Remover</h3>
        <p>Remove backgrounds from high-res images in a single click.</p>
        <div className="upgrade-lock-box">
          <span className="lock-icon">🔒</span>
          <p>This premium feature is exclusive to Pro users.</p>
          <button className="upgrade-btn-vibrant" onClick={() => openCheckout('pro')}>
            Upgrade to Pro — ₹200/mo
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="premium-tool-container">
      <h3>✨ AI Background Remover</h3>
      {/* Upload and processing UI unlocked */}
    </div>
  );
};
```

---

## 3. Razorpay Payment Checkout Flow

### Step 1: Include Razorpay Standard SDK
Place this in your HTML `<head>` or load it dynamically:
```html
<script src="https://checkout.razorpay.com/v1/checkout.js"></script>
```

### Step 2: Implement Complete Payment & Verification Handler

```typescript
import { useAuth } from './AuthContext';

export const usePayment = () => {
  const { refreshUser } = useAuth();

  const handleSubscriptionUpgrade = async (planSlug: 'pro' | 'max' | 'ultra') => {
    const token = localStorage.getItem('token');
    if (!token) {
      alert('Please log in to purchase a subscription.');
      return;
    }

    try {
      // 1. Create order on the Backend
      const orderResponse = await fetch('/api/v1/payments/orders', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({ plan_slug: planSlug }),
      });
      const orderRes = await orderResponse.json();

      if (!orderRes.success) {
        alert(orderRes.detail || 'Failed to initialize payment order.');
        return;
      }

      const { keyId, order } = orderRes.data;

      // 2. Open Razorpay Checkout Modal
      const options = {
        key: keyId, // Razorpay Key ID (Never expose Key Secret here!)
        amount: order.amount_paise,
        currency: order.currency,
        name: 'VedaApex AI',
        description: `Subscribe to ${order.plan}`,
        order_id: order.order_id,
        prefill: {
          email: order.razorpay_order.notes.email || '',
        },
        theme: {
          color: '#6366f1', // Vibrant modern brand primary
        },
        handler: async (response: any) => {
          // This callback executes when payment completes successfully in Razorpay modal
          try {
            // 3. Send payment tokens to backend verification endpoint
            const verifyResponse = await fetch('/api/v1/payments/verify-payment', {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
              },
              body: JSON.stringify({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
              }),
            });

            const verifyRes = await verifyResponse.json();

            if (verifyRes.success) {
              alert('🎉 Pro plan successfully activated! Welcome aboard.');
              await refreshUser(); // Instantly unlocks premium UI elements
            } else {
              alert('Signature verification failed. Please contact support.');
            }
          } catch (err) {
            console.error('Payment verification request failed:', err);
          }
        },
        modal: {
          ondismiss: () => {
            console.log('Payment modal dismissed by user.');
          },
        },
      };

      const rzp = new (window as any).Razorpay(options);
      rzp.open();

    } catch (error) {
      console.error('Payment flow encountered an error:', error);
      alert('Something went wrong during payment initialization.');
    }
  };

  return { handleSubscriptionUpgrade };
};
```

---

## 4. Security Enforcement Rules

1. **Razorpay Key Secret Security**:
   - `RAZORPAY_KEY_SECRET` and `RAZORPAY_WEBHOOK_SECRET` must **ONLY** reside in the `.env` configuration file on the backend.
   - **NEVER** expose the Key Secret in any frontend code, static files, git commits, or API responses.
2. **Razorpay Key ID**:
   - Only the public `RAZORPAY_KEY_ID` (returned by `/api/v1/payments/orders`) can be safely used in the frontend `options` configuration block.
3. **Always Verify Signatures on Backend**:
   - Never trust frontend-reported payment success events. The actual subscription tier upgrade must ONLY trigger upon cryptographic verification of `razorpay_signature` using HMAC-SHA256 with the backend's secret key.
