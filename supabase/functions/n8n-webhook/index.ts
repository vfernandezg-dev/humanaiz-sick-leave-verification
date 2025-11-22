const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface WebhookPayload {
  event: string;
  data: any;
  timestamp: string;
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const payload: WebhookPayload = await req.json();

    console.log("Enviando webhook a n8n:", payload);

    // Send to n8n webhook - Use environment variable or default to n8n production webhook
    const n8nWebhookUrl = Deno.env.get("N8N_WEBHOOK_URL") || "https://REDACTED-N8N-HOST.example/webhook/descansos";

    const response = await fetch(n8nWebhookUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });

    console.log("Respuesta de n8n:", {
      status: response.status,
      statusText: response.statusText,
      url: n8nWebhookUrl
    });

    if (!response.ok) {
      const errorText = await response.text().catch(() => "No response body");
      console.error("Error detallado de n8n:", errorText);
      throw new Error(`n8n webhook failed: ${response.status} ${response.statusText} - ${errorText}`);
    }

    const result = await response.json().catch(() => ({}));

    console.log("Webhook enviado exitosamente a n8n:", result);

    return new Response(
      JSON.stringify({
        success: true,
        message: "Webhook enviado a n8n",
        n8n_response: result,
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 200 },
    );
  } catch (error) {
    console.error("Error enviando webhook a n8n:", error);
    const errorMessage = error instanceof Error ? error.message : "Error desconocido";
    return new Response(
      JSON.stringify({
        success: false,
        error: errorMessage,
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 500 },
    );
  }
});
