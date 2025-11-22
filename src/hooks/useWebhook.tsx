import { supabase } from "@/integrations/supabase/client";

export function useWebhook() {
  const sendWebhook = async (event: string, data: any) => {
    try {
      const payload = {
        event,
        data,
        timestamp: new Date().toISOString()
      };

      const { data: result, error } = await supabase.functions.invoke('n8n-webhook', {
        body: payload
      });

      if (error) {
        console.warn('Webhook no enviado:', error.message);
        // No retornar error para que no bloquee la aplicación
        return { data: null, error: null };
      }

      console.log('Webhook enviado exitosamente:', result);
      return { data: result, error: null };
    } catch (error: any) {
      console.warn('Error en useWebhook:', error);
      // No retornar error para que no bloquee la aplicación
      return { data: null, error: null };
    }
  };

  return { sendWebhook };
}
