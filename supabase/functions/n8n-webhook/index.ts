const corsHeaders = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

interface WebhookPayload {
  event: string
  data: any
  timestamp: string
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const payload: WebhookPayload = await req.json()
    
    console.log('Enviando webhook a n8n:', payload)

    // Send to n8n webhook - URL should be configured via environment variable
    const n8nWebhookUrl = Deno.env.get('N8N_WEBHOOK_URL')
    
    if (!n8nWebhookUrl) {
      console.log('N8N_WEBHOOK_URL no configurada, omitiendo envío de webhook')
      return new Response(
        JSON.stringify({ 
          success: true,
          message: 'Webhook no enviado (URL no configurada)',
          skipped: true
        }),
        { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
      )
    }
    
    const response = await fetch(n8nWebhookUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload)
    })

    if (!response.ok) {
      throw new Error(`n8n webhook failed: ${response.status} ${response.statusText}`)
    }

    const result = await response.json().catch(() => ({}))
    
    console.log('Webhook enviado exitosamente a n8n:', result)

    return new Response(
      JSON.stringify({ 
        success: true,
        message: 'Webhook enviado a n8n',
        n8n_response: result
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 200 }
    )

  } catch (error) {
    console.error('Error enviando webhook a n8n:', error)
    const errorMessage = error instanceof Error ? error.message : 'Error desconocido'
    return new Response(
      JSON.stringify({ 
        success: false,
        error: errorMessage
      }),
      { headers: { ...corsHeaders, 'Content-Type': 'application/json' }, status: 500 }
    )
  }
})
