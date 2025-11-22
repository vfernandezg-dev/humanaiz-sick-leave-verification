-- Hacer el bucket certificados-medicos público para que las imágenes sean accesibles
UPDATE storage.buckets 
SET public = true 
WHERE id = 'certificados-medicos';

-- Crear política para permitir que todos puedan ver los certificados médicos
CREATE POLICY "Los certificados médicos son visibles públicamente"
ON storage.objects FOR SELECT
USING (bucket_id = 'certificados-medicos');

-- Política para permitir que usuarios autenticados suban sus propios certificados
CREATE POLICY "Usuarios pueden subir sus propios certificados"
ON storage.objects FOR INSERT
WITH CHECK (
  bucket_id = 'certificados-medicos' 
  AND auth.uid()::text = (storage.foldername(name))[1]
);