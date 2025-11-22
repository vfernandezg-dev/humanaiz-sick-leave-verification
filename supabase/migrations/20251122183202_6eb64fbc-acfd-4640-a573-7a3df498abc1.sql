-- Agregar campo para almacenar el análisis de n8n del certificado médico
ALTER TABLE public.descansos_medicos 
ADD COLUMN analisis_n8n JSONB DEFAULT NULL;

COMMENT ON COLUMN public.descansos_medicos.analisis_n8n IS 'Resultado del análisis automatizado del certificado médico por n8n';