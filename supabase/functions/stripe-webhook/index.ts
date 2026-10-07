// ============================================================================
// GRANKHA · Supabase Edge Function: stripe-webhook
// Marca el pedido como pagado cuando Stripe confirma el cobro.
//
// Despliegue:
//   supabase functions deploy stripe-webhook --no-verify-jwt
//   supabase secrets set STRIPE_WEBHOOK_SECRET=whsec_...
//
// En Stripe → Developers → Webhooks, añade el endpoint:
//   https://<proyecto>.functions.supabase.co/stripe-webhook
// con los eventos: checkout.session.completed, charge.refunded
// ============================================================================

import Stripe from "https://esm.sh/stripe@16?target=deno";
import { createClient } from "https://esm.sh/@supabase/supabase-js@2";

const stripe = new Stripe(Deno.env.get("STRIPE_SECRET_KEY")!, { apiVersion: "2024-06-20" });
const supa = createClient(
  Deno.env.get("SUPABASE_URL")!,
  Deno.env.get("SUPABASE_SERVICE_ROLE_KEY")!,
);
const SECRET = Deno.env.get("STRIPE_WEBHOOK_SECRET")!;

Deno.serve(async (req) => {
  const sig = req.headers.get("stripe-signature");
  if (!sig) return new Response("Sin firma", { status: 400 });

  const body = await req.text();
  let event: Stripe.Event;
  try {
    event = await stripe.webhooks.constructEventAsync(body, sig, SECRET);
  } catch (e) {
    console.error("Firma inválida", e);
    return new Response("Firma inválida", { status: 400 });
  }

  switch (event.type) {
    case "checkout.session.completed": {
      const s = event.data.object as Stripe.Checkout.Session;
      await supa.from("orders")
        .update({ status: "paid", stripe_payment_intent: String(s.payment_intent ?? "") })
        .eq("stripe_session_id", s.id);
      break;
    }
    case "charge.refunded": {
      const c = event.data.object as Stripe.Charge;
      await supa.from("orders")
        .update({ status: "refunded" })
        .eq("stripe_payment_intent", String(c.payment_intent ?? ""));
      break;
    }
    default:
      console.log("Evento no gestionado:", event.type);
  }

  return new Response(JSON.stringify({ received: true }), {
    status: 200, headers: { "Content-Type": "application/json" },
  });
});
