/**
 * Zomato AI - Frontend Runtime Configuration
 *
 * When deploying frontend on Vercel and backend on Railway:
 * - Option 1: Leave window.__BACKEND_URL__ as "" if you configured vercel.json rewrites.
 * - Option 2: Set window.__BACKEND_URL__ to your Railway domain (e.g. "https://your-service.up.railway.app").
 * - Option 3: Provide it dynamically via ?backend=https://... or the in-app Settings modal.
 */
window.__BACKEND_URL__ = window.__BACKEND_URL__ || "https://zomato-ai-project.onrender.com";
