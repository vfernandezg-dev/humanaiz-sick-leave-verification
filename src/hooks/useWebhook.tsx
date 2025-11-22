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
        console.error('Error enviando webhook:', error);
        return { error };
      }

      console.log('Webhook enviado exitosamente:', result);
      return { data: result, error: null };
    } catch (error: any) {
      console.error('Error en useWebhook:', error);
      return { error };
    }
  };

  return { sendWebhook };
}
