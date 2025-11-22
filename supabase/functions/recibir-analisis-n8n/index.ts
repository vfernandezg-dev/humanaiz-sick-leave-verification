import { createClient } from 'https://esm.sh/@supabase/supabase-js@2.39.3'

const corsHeaders = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Headers": "authorization, x-client-info, apikey, content-type",
};

interface AnalisisPayload {
  descanso_id: string;
  output: {
    extraidos?: any;
    validaciones?: any;
    estado_documento?: string;
    motivos_rechazo?: string[];
    comentario_general?: string;
  };
}

Deno.serve(async (req) => {
  if (req.method === "OPTIONS") {
    return new Response(null, { headers: corsHeaders });
  }

  try {
    const payload: AnalisisPayload = await req.json();

    console.log("Recibiendo análisis de n8n:", payload);

    // Crear cliente de Supabase
    const supabaseUrl = Deno.env.get('SUPABASE_URL')!;
    const supabaseServiceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!;
    const supabase = createClient(supabaseUrl, supabaseServiceKey);

    // Actualizar el descanso médico con el análisis
    const { error } = await supabase
      .from('descansos_medicos')
      .update({
        analisis_n8n: payload.output
      })
      .eq('id', payload.descanso_id);

    if (error) {
      console.error("Error actualizando descanso:", error);
      throw new Error(`Error al guardar análisis: ${error.message}`);
    }

    console.log("Análisis guardado exitosamente para descanso:", payload.descanso_id);

    return new Response(
      JSON.stringify({
        success: true,
        message: "Análisis recibido y guardado correctamente",
      }),
      { headers: { ...corsHeaders, "Content-Type": "application/json" }, status: 200 },
    );
  } catch (error) {
    console.error("Error procesando análisis de n8n:", error);
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
