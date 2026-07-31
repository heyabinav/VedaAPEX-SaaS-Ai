# Canva Frontend Example

This file explains the simple frontend example included at `app/frontend_examples/canva_voice_example.html`.

## Purpose
- Demonstrates a minimal Connect Canva button.
- Captures voice via Web Speech API (browser) and sends transcript to the backend.
- Calls `/api/v1/canva/command` to create a design using the connected Canva account.

## Steps
1. Ensure backend is running and reachable from the frontend (same origin or CORS configured).
2. Add Canva credentials to your environment and register redirect URI in Canva Developer console:
   - `CANVA_CLIENT_ID`
   - `CANVA_CLIENT_SECRET`
   - `CANVA_REDIRECT_URI` (must match Canva app)
3. Start the backend and open the example HTML in a browser (serve it from your frontend or open file).
4. Click `Connect Canva` and complete OAuth.
5. Click `Start Mic`, speak your design prompt, then `Create Design`.

## Notes
- The example uses `credentials: 'include'` so session cookie set by `/auth/callback` must be available to the frontend domain.
- The `CanvaDesignService` in the backend sends a generic payload; if Canva Connect API requires a different schema, update `app/services/canva_design_service.py` accordingly.
- For better UX, implement server-side token refresh and proper error handling on frontend.

## Next improvements
- Add spinner/UX state on create.
- Show design preview or open Canva editor link returned by the API.
- Use a build/hosting setup for the HTML page if not served by the backend.
