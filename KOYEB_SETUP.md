# Deployment na Koyeb - Instrukcja

## Szybkie kroki:

1. **Połącz repozytorium GitHub z Koyeb**
2. **Ustaw zmienne środowiskowe** (Settings → Environment):

### WYMAGANE:
```
DATABASE_URL=postgresql://user:password@host:port/database
SESSION_SECRET=wygeneruj_losowy_sekret_min_32_znaki
OPENROUTER_API_KEY=sk-or-v1-twoj-klucz-api
```

### OPCJONALNE (dla Stripe):
```
STRIPE_SECRET_KEY=sk_test_lub_sk_live_
STRIPE_PUBLISHABLE_KEY=pk_test_lub_pk_live_
STRIPE_WEBHOOK_SECRET=whsec_
```

3. **Deploy** - Koyeb wykryje automatycznie:
   - `Procfile` → uruchomi Gunicorn
   - `requirements.txt` → zainstaluje pakiety
   - `runtime.txt` → użyje Python 3.11

## Bezpieczeństwo API Keys:

✅ **Teraz aplikacja waliduje wszystkie klucze API:**
- OPENROUTER_API_KEY - sprawdza format i nie pozwala na testowe klucze
- STRIPE keys - rozróżnia tryb test/live
- SESSION_SECRET - ostrzega gdy używa wartości domyślnej

Aplikacja **nie startuje z niepoprawnymi kluczami API**.
